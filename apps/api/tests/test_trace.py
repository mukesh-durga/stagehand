"""Tests for GET /runs/{run_id}/trace (Milestone 7)."""

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
    """A TraceStore that returns canned rows (TRACE_COLUMNS order)."""

    def __init__(self, rows: list[tuple[Any, ...]]):
        self.rows = rows

    def ensure_ready(self) -> None:
        pass

    def get_events_by_run_id(self, run_id: Any) -> list[tuple[Any, ...]]:
        return self.rows

    def insert_event(self, event: Any) -> None:
        pass

    def insert_events(self, events: list[Any]) -> None:
        pass


def _use_clickhouse(rows: list[tuple[Any, ...]]) -> FakeTraceStore:
    fake = FakeTraceStore(rows)
    app.dependency_overrides[get_trace_store] = lambda: fake
    return fake


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_trace_store, None)


def _trace_row(event_type: str, ts: datetime, node_id: str = "") -> tuple[Any, ...]:
    values = {
        "event_id": str(uuid.uuid4()),
        "run_id": "00000000-0000-0000-0000-000000000000",
        "workflow_id": "wf",
        "workflow_version_id": "ver",
        "node_id": node_id,
        "event_type": event_type,
        "status": "running",
        "timestamp": ts,
        "latency_ms": 1,
        "model_name": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "tool_name": "",
        "retry_count": 0,
        "error_message": "",
        "metadata_json": "{}",
    }
    return tuple(values[c] for c in TRACE_COLUMNS)


def _make_run(db_session) -> WorkflowRun:
    wf = Workflow(name="t")
    db_session.add(wf)
    db_session.flush()
    version = WorkflowVersion(
        workflow_id=wf.id, version_number=1, graph_json={"nodes": [], "edges": []}
    )
    db_session.add(version)
    db_session.flush()
    run = WorkflowRun(
        workflow_id=wf.id, workflow_version_id=version.id, status="completed", input_json={}
    )
    db_session.add(run)
    db_session.flush()
    return run


def test_trace_returns_events_ordered(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    t1 = datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 6, 18, 0, 0, 1, tzinfo=timezone.utc)
    _use_clickhouse(
        [
            _trace_row("run_started", t1),
            _trace_row("run_completed", t2),
        ]
    )

    resp = client.get(f"/runs/{run.id}/trace")
    assert resp.status_code == 200
    events = resp.json()
    assert [e["event_type"] for e in events] == ["run_started", "run_completed"]
    assert events[0]["timestamp"] < events[1]["timestamp"]


def test_trace_empty_for_existing_run(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    _use_clickhouse([])
    resp = client.get(f"/runs/{run.id}/trace")
    assert resp.status_code == 200
    assert resp.json() == []


def test_trace_missing_run_returns_404(client: TestClient) -> None:
    _use_clickhouse([])
    resp = client.get(f"/runs/{uuid.uuid4()}/trace")
    assert resp.status_code == 404
