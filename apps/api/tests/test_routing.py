"""Tests for routing stats endpoints and eval-driven stats updates."""

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db.clickhouse import TRACE_COLUMNS, get_clickhouse
from app.db.models.routing import ModelRoutingStats
from app.db.models.run import WorkflowRun
from app.db.models.workflow import Workflow, WorkflowVersion
from app.main import app


class FakeClickHouse:
    def __init__(self, by_run: dict[str, list[tuple[Any, ...]]] | None = None):
        self.by_run = by_run or {}

    def command(self, sql: str) -> None:
        pass

    def query(self, sql: str, parameters: dict | None = None):
        run_id = (parameters or {}).get("run_id", "")
        return SimpleNamespace(result_rows=self.by_run.get(run_id, []))


@pytest.fixture(autouse=True)
def _ch():
    app.dependency_overrides[get_clickhouse] = lambda: FakeClickHouse()
    yield
    app.dependency_overrides.pop(get_clickhouse, None)


def _use_ch(by_run):
    app.dependency_overrides[get_clickhouse] = lambda: FakeClickHouse(by_run)


def _make_run(db_session, **fields):
    wf = Workflow(name="t")
    db_session.add(wf)
    db_session.flush()
    version = WorkflowVersion(
        workflow_id=wf.id, version_number=1, graph_json={"nodes": [], "edges": []}
    )
    db_session.add(version)
    db_session.flush()
    run = WorkflowRun(
        workflow_id=wf.id,
        workflow_version_id=version.id,
        status=fields.pop("status", "completed"),
        input_json=fields.pop("input_json", {}),
        **fields,
    )
    db_session.add(run)
    db_session.flush()
    return run


def _routing_row(run, route_key, selected_model) -> tuple[Any, ...]:
    values = {c: "" for c in TRACE_COLUMNS}
    values.update(
        {
            "event_id": str(uuid.uuid4()),
            "run_id": str(run.id),
            "node_id": "ag1",
            "event_type": "routing_decision",
            "status": "running",
            "timestamp": datetime.now(timezone.utc),
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "retry_count": 0,
            "model_name": selected_model,
            "metadata_json": json.dumps(
                {"route_key": route_key, "selected_model": selected_model, "policy": "adaptive"}
            ),
        }
    )
    return tuple(values[c] for c in TRACE_COLUMNS)


# --- endpoints ---

def test_routing_stats_empty_list(client: TestClient) -> None:
    resp = client.get("/routing/stats")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_routing_stats_by_route_key_empty(client: TestClient) -> None:
    resp = client.get("/routing/stats/unknown:key:node")
    assert resp.status_code == 200
    assert resp.json() == []


def test_routing_stats_returns_row(client: TestClient, db_session) -> None:
    db_session.add(
        ModelRoutingStats(
            route_key="wf:ver:ag1", model_name="mock-cheap", node_id="ag1",
            pulls=3, total_reward=2.4, average_reward=0.8,
        )
    )
    db_session.flush()
    rows = client.get("/routing/stats", params={"route_key": "wf:ver:ag1"}).json()
    assert len(rows) == 1
    assert rows[0]["model_name"] == "mock-cheap"
    assert rows[0]["pulls"] == 3
    assert rows[0]["average_reward"] == 0.8


# --- eval updates routing stats ---

def test_eval_updates_routing_stats(client: TestClient, db_session) -> None:
    run = _make_run(db_session, total_latency_ms=100, estimated_cost_usd=0.0, output_json={"x": 1})
    route_key = f"{run.workflow_id}:{run.workflow_version_id}:ag1"
    _use_ch({str(run.id): [_routing_row(run, route_key, "mock-cheap")]})

    resp = client.post(f"/runs/{run.id}/eval", json={"eval_types": ["latency", "cost", "llm_as_judge"]})
    assert resp.status_code == 201

    stats = client.get("/routing/stats", params={"route_key": route_key}).json()
    assert len(stats) == 1
    s = stats[0]
    assert s["model_name"] == "mock-cheap"
    assert s["pulls"] == 1
    assert s["average_reward"] > 0.0
    assert s["average_quality_score"] > 0.0


def test_repeated_eval_does_not_double_count(client: TestClient, db_session) -> None:
    run = _make_run(db_session, total_latency_ms=100, output_json={"x": 1})
    route_key = f"{run.workflow_id}:{run.workflow_version_id}:ag1"
    _use_ch({str(run.id): [_routing_row(run, route_key, "mock-cheap")]})

    client.post(f"/runs/{run.id}/eval", json={"eval_types": ["latency"]})
    client.post(f"/runs/{run.id}/eval", json={"eval_types": ["latency"]})

    stats = client.get("/routing/stats", params={"route_key": route_key}).json()
    assert stats[0]["pulls"] == 1  # only the first eval counted


def test_eval_without_routing_decision_no_stats(client: TestClient, db_session) -> None:
    run = _make_run(db_session, total_latency_ms=100)
    _use_ch({str(run.id): []})  # no routing_decision events
    client.post(f"/runs/{run.id}/eval", json={"eval_types": ["latency"]})
    # No stats created for this run's workflow.
    stats = client.get("/routing/stats", params={"workflow_id": str(run.workflow_id)}).json()
    assert stats == []


def test_reset_routing_stats(client: TestClient, db_session) -> None:
    db_session.add(
        ModelRoutingStats(route_key="rk", model_name="m", pulls=1, total_reward=0.5, average_reward=0.5)
    )
    db_session.flush()
    resp = client.post("/routing/stats/reset")
    assert resp.status_code == 200
    assert resp.json()["deleted"] >= 1
