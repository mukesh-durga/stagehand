"""Tests for usage tracking and billing (Milestone 17)."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.clickhouse import TRACE_COLUMNS, get_clickhouse
from app.db.models.run import WorkflowRun
from app.db.models.usage import UsageEvent
from app.db.models.workflow import Workflow, WorkflowVersion
from app.main import app
from app.services import usage_service


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


def _make_run(db_session, **fields) -> WorkflowRun:
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


def _row(run, event_type, model_name="", tool_name="", in_tok=0, out_tok=0, cost=0.0):
    values = {c: "" for c in TRACE_COLUMNS}
    values.update(
        {
            "event_id": str(uuid.uuid4()),
            "run_id": str(run.id),
            "node_id": "n1",
            "event_type": event_type,
            "status": "success",
            "timestamp": datetime.now(timezone.utc),
            "latency_ms": 1,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "estimated_cost_usd": cost,
            "retry_count": 0,
            "model_name": model_name,
            "tool_name": tool_name,
            "metadata_json": "{}",
        }
    )
    return tuple(values[c] for c in TRACE_COLUMNS)


# --- record_run_usage (service) ---

def test_record_run_usage_creates_events(db_session) -> None:
    run = _make_run(db_session, estimated_cost_usd=0.02, total_input_tokens=10, total_output_tokens=5)
    trace = [
        {"event_type": "model_completed", "model_name": "mock-cheap", "input_tokens": 10, "output_tokens": 5, "estimated_cost_usd": 0.02},
        {"event_type": "tool_completed", "tool_name": "calculator"},
    ]
    inserted = usage_service.record_run_usage(db_session, run, trace)
    assert inserted == 3  # model_usage + tool_usage + run_completed
    types = {e.event_type for e in db_session.query(UsageEvent).filter_by(run_id=run.id)}
    assert types == {"model_usage", "tool_usage", "run_completed"}


def test_record_run_usage_idempotent(db_session) -> None:
    run = _make_run(db_session, estimated_cost_usd=0.01)
    trace = [{"event_type": "model_completed", "model_name": "mock-cheap", "input_tokens": 1, "output_tokens": 1, "estimated_cost_usd": 0.01}]
    assert usage_service.record_run_usage(db_session, run, trace) == 2
    assert usage_service.record_run_usage(db_session, run, trace) == 0
    count = db_session.query(UsageEvent).filter_by(run_id=run.id).count()
    assert count == 2


# --- endpoints ---

def test_usage_events_and_summary(client: TestClient, db_session) -> None:
    run = _make_run(db_session, estimated_cost_usd=0.03, total_input_tokens=8, total_output_tokens=4)
    usage_service.record_run_usage(
        db_session,
        run,
        [{"event_type": "model_completed", "model_name": "mock-strong", "input_tokens": 8, "output_tokens": 4, "estimated_cost_usd": 0.03}],
    )
    events = client.get("/usage/events", params={"run_id": str(run.id)}).json()
    assert {e["event_type"] for e in events} == {"model_usage", "run_completed"}

    summary = client.get("/usage/summary").json()
    assert summary["total_runs"] >= 1
    assert summary["total_model_calls"] >= 1
    assert summary["total_estimated_cost_usd"] >= 0.03
    assert "mock-strong" in summary["cost_by_model"]


def test_backfill_records_completed_runs(client: TestClient, db_session) -> None:
    run = _make_run(db_session, status="completed", estimated_cost_usd=0.0)
    _use_ch({str(run.id): [_row(run, "model_completed", model_name="mock-cheap", in_tok=3, out_tok=2)]})
    resp = client.post("/usage/backfill")
    assert resp.status_code == 200
    assert resp.json()["inserted"] >= 2  # this run's model_usage + run_completed
    events = client.get("/usage/events", params={"run_id": str(run.id)}).json()
    assert any(e["event_type"] == "model_usage" for e in events)


# --- billing ---

def test_billing_status_mock_without_key(client: TestClient) -> None:
    get_settings.cache_clear()
    resp = client.get("/billing/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "mock"
    assert body["stripe_configured"] is False


def test_checkout_session_mock_no_charge(client: TestClient) -> None:
    resp = client.post("/billing/create-checkout-session")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "mock"
    assert body["checkout_url"]
    assert body["session_id"] is None
