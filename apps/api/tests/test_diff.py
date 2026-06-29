"""Tests for GET /runs/{run_id}/diff/{other_run_id} (Milestone 13)."""

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
    """Returns canned rows keyed by run_id."""

    def __init__(self, by_run: dict[str, list[tuple[Any, ...]]]):
        self.by_run = by_run

    def ensure_ready(self) -> None:
        pass

    def get_events_by_run_id(self, run_id: Any) -> list[tuple[Any, ...]]:
        return self.by_run.get(str(run_id), [])

    def insert_event(self, event: Any) -> None:
        pass

    def insert_events(self, events: list[Any]) -> None:
        pass


def _use_clickhouse(by_run: dict[str, list[tuple[Any, ...]]]) -> None:
    app.dependency_overrides[get_trace_store] = lambda: FakeTraceStore(by_run)


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_trace_store, None)


def _make_run(db_session, **fields: Any) -> WorkflowRun:
    wf = Workflow(name="t")
    db_session.add(wf)
    db_session.flush()
    version_id = fields.pop("version_id", None)
    version = WorkflowVersion(
        id=version_id or uuid.uuid4(),
        workflow_id=wf.id,
        version_number=1,
        graph_json={"nodes": [], "edges": []},
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


def _row(run_id, event_type, node_id="", model_name="", tool_name="",
         latency_ms=0, input_tokens=0, output_tokens=0, cost=0.0, error="",
         metadata="{}") -> tuple[Any, ...]:
    values = {
        "event_id": str(uuid.uuid4()),
        "run_id": str(run_id),
        "workflow_id": "wf",
        "workflow_version_id": "ver",
        "node_id": node_id,
        "event_type": event_type,
        "status": "running",
        "timestamp": datetime.now(timezone.utc),
        "latency_ms": latency_ms,
        "model_name": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "tool_name": tool_name,
        "retry_count": 0,
        "error_message": error,
        "metadata_json": metadata,
    }
    return tuple(values[c] for c in TRACE_COLUMNS)


def test_diff_missing_run_404(client: TestClient, db_session) -> None:
    a = _make_run(db_session)
    _use_clickhouse({})
    resp = client.get(f"/runs/{a.id}/diff/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_diff_two_completed_runs(client: TestClient, db_session) -> None:
    a = _make_run(db_session, total_latency_ms=100, total_output_tokens=5)
    b = _make_run(db_session, total_latency_ms=140, total_output_tokens=8)
    _use_clickhouse(
        {
            str(a.id): [_row(a.id, "model_completed", "ag1", model_name="mock-cheap", output_tokens=5)],
            str(b.id): [_row(b.id, "model_completed", "ag1", model_name="mock-cheap", output_tokens=8)],
        }
    )
    resp = client.get(f"/runs/{a.id}/diff/{b.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_a"]["id"] == str(a.id)
    assert body["summary"]["latency_delta_ms"] == 40
    assert body["summary"]["output_tokens_delta"] == 3
    assert len(body["node_diffs"]) == 1


def test_status_change_detected(client: TestClient, db_session) -> None:
    a = _make_run(db_session, status="completed")
    b = _make_run(db_session, status="failed", error_message="boom")
    _use_clickhouse({str(a.id): [], str(b.id): []})
    s = client.get(f"/runs/{a.id}/diff/{b.id}").json()["summary"]
    assert s["status_changed"] is True
    assert s["error_changed"] is True


def test_model_and_tool_change_detected(client: TestClient, db_session) -> None:
    a = _make_run(db_session)
    b = _make_run(db_session)
    _use_clickhouse(
        {
            str(a.id): [
                _row(a.id, "model_completed", "ag1", model_name="mock-cheap"),
                _row(a.id, "tool_completed", "t1", tool_name="calculator"),
            ],
            str(b.id): [
                _row(b.id, "model_completed", "ag1", model_name="mock-strong"),
                _row(b.id, "tool_completed", "t1", tool_name="mock_search"),
            ],
        }
    )
    body = client.get(f"/runs/{a.id}/diff/{b.id}").json()
    assert body["summary"]["model_changed"] is True
    assert body["summary"]["tool_changed"] is True
    ag = next(n for n in body["node_diffs"] if n["node_id"] == "ag1")
    assert ag["model_a"] == "mock-cheap" and ag["model_b"] == "mock-strong"
    assert ag["model_changed"] is True


def test_retry_and_fallback_change_detected(client: TestClient, db_session) -> None:
    a = _make_run(db_session)
    b = _make_run(db_session)
    _use_clickhouse(
        {
            str(a.id): [_row(a.id, "model_completed", "ag1", model_name="mock-cheap")],
            str(b.id): [
                _row(b.id, "retry_scheduled", "ag1"),
                _row(b.id, "fallback_used", "ag1", model_name="mock-strong"),
                _row(b.id, "model_completed", "ag1", model_name="mock-strong"),
            ],
        }
    )
    s = client.get(f"/runs/{a.id}/diff/{b.id}").json()["summary"]
    assert s["retry_count_delta"] == 1
    assert s["fallback_changed"] is True


def test_output_changed_detected(client: TestClient, db_session) -> None:
    a = _make_run(db_session, output_json={"x": 1})
    b = _make_run(db_session, output_json={"x": 2})
    _use_clickhouse({str(a.id): [], str(b.id): []})
    od = client.get(f"/runs/{a.id}/diff/{b.id}").json()["output_diff"]
    assert od["changed"] is True


def test_output_same_unchanged(client: TestClient, db_session) -> None:
    a = _make_run(db_session, output_json={"x": 1})
    b = _make_run(db_session, output_json={"x": 1})
    _use_clickhouse({str(a.id): [], str(b.id): []})
    od = client.get(f"/runs/{a.id}/diff/{b.id}").json()["output_diff"]
    assert od["changed"] is False


def test_workflow_version_changed_flag(client: TestClient, db_session) -> None:
    a = _make_run(db_session)
    b = _make_run(db_session)  # different workflow + version
    _use_clickhouse({str(a.id): [], str(b.id): []})
    s = client.get(f"/runs/{a.id}/diff/{b.id}").json()["summary"]
    assert s["workflow_version_changed"] is True


def test_event_diffs_present(client: TestClient, db_session) -> None:
    a = _make_run(db_session)
    b = _make_run(db_session)
    _use_clickhouse(
        {
            str(a.id): [_row(a.id, "node_completed", "ag1")],
            str(b.id): [
                _row(b.id, "node_completed", "ag1"),
                _row(b.id, "retry_scheduled", "ag1"),
            ],
        }
    )
    body = client.get(f"/runs/{a.id}/diff/{b.id}").json()
    retry = next(
        e for e in body["event_diffs"]
        if e["event_type"] == "retry_scheduled" and e["node_id"] == "ag1"
    )
    assert retry["count_a"] == 0 and retry["count_b"] == 1 and retry["changed"] is True
