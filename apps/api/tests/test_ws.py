"""Tests for WS /ws/runs/{run_id} live trace streaming."""

import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.db.models.run import WorkflowRun
from app.db.models.workflow import Workflow, WorkflowVersion
from app.db.redis import get_async_redis
from app.main import app


class FakeAsyncRedis:
    """Minimal async Redis stub backed by an in-memory list."""

    def __init__(self, items: list[str]):
        self.items = items

    async def llen(self, key: str) -> int:
        return len(self.items)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        return self.items[start : end + 1]


def _use_redis(items: list[str]) -> None:
    app.dependency_overrides[get_async_redis] = lambda: FakeAsyncRedis(items)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_async_redis, None)


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
        workflow_id=wf.id, workflow_version_id=version.id, status="queued", input_json={}
    )
    db_session.add(run)
    db_session.flush()
    return run


def _event(run_id, event_type: str, node_id: str = "") -> str:
    return json.dumps(
        {
            "event_id": str(uuid.uuid4()),
            "run_id": str(run_id),
            "workflow_id": "wf",
            "workflow_version_id": "ver",
            "node_id": node_id,
            "event_type": event_type,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": 0,
            "model_name": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "tool_name": "",
            "retry_count": 0,
            "error_message": "",
            "metadata_json": {},
        }
    )


def test_ws_connects_and_streams_events(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    _use_redis(
        [
            _event(run.id, "run_started"),
            _event(run.id, "node_started", "n1"),
            _event(run.id, "node_completed", "n1"),
            _event(run.id, "run_completed"),
        ]
    )

    with client.websocket_connect(f"/ws/runs/{run.id}") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        assert websocket.receive_json()["event_type"] == "run_started"
        assert websocket.receive_json()["event_type"] == "node_started"
        assert websocket.receive_json()["event_type"] == "node_completed"
        assert websocket.receive_json()["event_type"] == "run_completed"
        # Server closes after the terminal event.
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_ws_missing_run_closes(client: TestClient) -> None:
    _use_redis([])
    with client.websocket_connect(f"/ws/runs/{uuid.uuid4()}") as websocket:
        first = websocket.receive_json()
        assert first["type"] == "error"
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
