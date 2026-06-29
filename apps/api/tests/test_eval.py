"""Tests for the eval harness (Milestone 14)."""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_trace_store
from app.db.clickhouse import TRACE_COLUMNS
from app.db.models.run import WorkflowRun
from app.db.models.workflow import Workflow, WorkflowVersion
from app.main import app


class FakeTraceStore:
    def __init__(self, by_run: dict[str, list[tuple[Any, ...]]] | None = None):
        self.by_run = by_run or {}

    def ensure_ready(self) -> None:
        pass

    def get_events_by_run_id(self, run_id: Any) -> list[tuple[Any, ...]]:
        return self.by_run.get(str(run_id), [])

    def insert_event(self, event: Any) -> None:
        pass

    def insert_events(self, events: list[Any]) -> None:
        pass


@pytest.fixture(autouse=True)
def _ch():
    app.dependency_overrides[get_trace_store] = lambda: FakeTraceStore()
    yield
    app.dependency_overrides.pop(get_trace_store, None)


def _use_ch(by_run: dict[str, list[tuple[Any, ...]]]) -> None:
    app.dependency_overrides[get_trace_store] = lambda: FakeTraceStore(by_run)


def _make_run(db_session, **fields: Any) -> WorkflowRun:
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


def _tool_row(run_id, tool_name) -> tuple[Any, ...]:
    values = {c: "" for c in TRACE_COLUMNS}
    values.update(
        {
            "event_id": str(uuid.uuid4()),
            "run_id": str(run_id),
            "node_id": "t1",
            "event_type": "tool_completed",
            "status": "success",
            "timestamp": datetime.now(timezone.utc),
            "latency_ms": 1,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "retry_count": 0,
            "tool_name": tool_name,
            "metadata_json": "{}",
        }
    )
    return tuple(values[c] for c in TRACE_COLUMNS)


def _eval(client, run_id, payload):
    return client.post(f"/runs/{run_id}/eval", json=payload)


def test_eval_missing_run_404(client: TestClient) -> None:
    assert _eval(client, uuid.uuid4(), {}).status_code == 404


def test_eval_completed_run_default_types(client: TestClient, db_session) -> None:
    run = _make_run(db_session, total_latency_ms=100, output_json={"x": 1})
    resp = _eval(client, run.id, {})
    assert resp.status_code == 201
    types = sorted(r["eval_type"] for r in resp.json())
    assert types == ["cost", "latency", "llm_as_judge"]


def test_eval_failed_run_creates_results(client: TestClient, db_session) -> None:
    run = _make_run(db_session, status="failed", error_message="boom")
    resp = _eval(client, run.id, {"eval_types": ["latency", "llm_as_judge"]})
    assert resp.status_code == 201
    assert len(resp.json()) == 2


def test_eval_queued_run_409(client: TestClient, db_session) -> None:
    run = _make_run(db_session, status="queued")
    assert _eval(client, run.id, {}).status_code == 409


def test_exact_match_pass_and_fail(client: TestClient, db_session) -> None:
    run = _make_run(db_session, output_json={"a": 1})
    ok = _eval(client, run.id, {"eval_types": ["exact_match"], "expected_output": {"a": 1}}).json()[0]
    assert ok["success_score"] == 1.0 and ok["passed"] is True
    bad = _eval(client, run.id, {"eval_types": ["exact_match"], "expected_output": {"a": 2}}).json()[0]
    assert bad["success_score"] == 0.0 and bad["passed"] is False


def test_json_schema_pass_and_fail(client: TestClient, db_session) -> None:
    schema = {"type": "object", "required": ["x"], "properties": {"x": {"type": "integer"}}}
    good = _make_run(db_session, output_json={"x": 5})
    r1 = _eval(client, good.id, {"eval_types": ["json_schema"], "expected_schema": schema}).json()[0]
    assert r1["passed"] is True
    bad = _make_run(db_session, output_json={"y": 5})
    r2 = _eval(client, bad.id, {"eval_types": ["json_schema"], "expected_schema": schema}).json()[0]
    assert r2["passed"] is False


def test_tool_usage_detects_and_fails(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    _use_ch({str(run.id): [_tool_row(run.id, "calculator")]})
    ok = _eval(client, run.id, {"eval_types": ["tool_usage"], "expected_tools": ["calculator"]}).json()[0]
    assert ok["passed"] is True
    assert ok["tool_correctness_score"] == 1.0

    miss = _eval(client, run.id, {"eval_types": ["tool_usage"], "expected_tools": ["mock_search"]}).json()[0]
    assert miss["passed"] is False
    assert miss["success_score"] == 0.0


def test_latency_eval(client: TestClient, db_session) -> None:
    fast = _make_run(db_session, total_latency_ms=100)
    r = _eval(client, fast.id, {"eval_types": ["latency"], "max_latency_ms": 5000}).json()[0]
    assert r["latency_score"] == 1.0 and r["passed"] is True

    slow = _make_run(db_session, total_latency_ms=10000)
    r2 = _eval(client, slow.id, {"eval_types": ["latency"], "max_latency_ms": 5000}).json()[0]
    assert r2["passed"] is False and r2["latency_score"] < 1.0


def test_cost_eval(client: TestClient, db_session) -> None:
    run = _make_run(db_session, estimated_cost_usd=0.0)
    r = _eval(client, run.id, {"eval_types": ["cost"], "max_cost_usd": 0.05}).json()[0]
    assert r["cost_score"] == 1.0 and r["passed"] is True


def test_llm_as_judge_mock(client: TestClient, db_session) -> None:
    run = _make_run(db_session, status="completed", output_json={"text": "hi"})
    r = _eval(client, run.id, {"eval_types": ["llm_as_judge"]}).json()[0]
    assert r["quality_score"] == 0.85
    assert r["passed"] is True
    assert r["feedback"]


def test_unknown_eval_type_400(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    assert _eval(client, run.id, {"eval_types": ["bogus"]}).status_code == 400


def test_list_evals_returns_stored(client: TestClient, db_session) -> None:
    run = _make_run(db_session, total_latency_ms=100)
    _eval(client, run.id, {"eval_types": ["latency", "cost"]})
    resp = client.get(f"/runs/{run.id}/evals")
    assert resp.status_code == 200
    assert {r["eval_type"] for r in resp.json()} == {"latency", "cost"}
