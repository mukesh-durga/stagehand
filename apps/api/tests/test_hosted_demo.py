"""Tests for Milestone 18.5 — Free Hosted Demo Mode.

Covers deployment-mode flags, the Postgres trace fallback + TraceStore selection,
the in-API hosted-demo executor (run completes without a worker, traces stored and
readable, diff/eval work off Postgres traces), the ClickHouse-disabled health
behavior, and that local worker mode still enqueues to Redis.
"""

from typing import Any

from fastapi.testclient import TestClient

import app.api.routes.health as health_mod
import app.config as config_mod
import app.services.run_service as run_service
from app.api.deps import get_trace_store
from app.config import Settings
from app.db.models.run import WorkflowRun
from app.db.models.workflow import Workflow, WorkflowVersion
from app.db.trace_store import ClickHouseTraceStore, PostgresTraceStore, make_trace_store
from app.main import app
from app.schemas.run import WorkflowRunCreate
from app.services import demo_executor


def _hosted() -> Settings:
    return Settings(deployment_mode="hosted_demo")


def _local() -> Settings:
    return Settings(deployment_mode="local")


def _demo_graph() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "in", "type": "input", "config": {}},
            {"id": "a", "type": "agent", "config": {"modelPolicy": "adaptive", "prompt": "Hi"}},
            {"id": "t", "type": "tool", "config": {"toolName": "calculator", "expression": "2 + 3"}},
            {"id": "out", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "in", "target": "a"},
            {"source": "a", "target": "t"},
            {"source": "t", "target": "out"},
        ],
    }


def _make_run(db_session, graph: dict[str, Any] | None = None) -> WorkflowRun:
    wf = Workflow(name="demo")
    db_session.add(wf)
    db_session.flush()
    version = WorkflowVersion(
        workflow_id=wf.id, version_number=1, graph_json=graph or _demo_graph()
    )
    db_session.add(version)
    db_session.flush()
    wf.current_version_id = version.id
    run = WorkflowRun(
        workflow_id=wf.id, workflow_version_id=version.id, status="queued", input_json={}
    )
    db_session.add(run)
    db_session.flush()
    return run


# --- config / mode flags ---


def test_hosted_mode_defaults() -> None:
    s = _hosted()
    assert s.clickhouse_enabled is False
    assert s.worker_enabled is False
    assert s.hosted_demo_execution is True
    assert s.trace_storage == "postgres"
    assert s.use_postgres_traces is True


def test_local_mode_defaults() -> None:
    s = _local()
    assert s.clickhouse_enabled is True
    assert s.worker_enabled is True
    assert s.trace_storage == "clickhouse"
    assert s.use_postgres_traces is False


def test_explicit_env_overrides_mode_default() -> None:
    # Explicitly enabling ClickHouse in hosted mode must win over the mode default.
    s = Settings(deployment_mode="hosted_demo", clickhouse_enabled=True)
    assert s.clickhouse_enabled is True


# --- TraceStore selection ---


def test_make_trace_store_postgres_when_configured(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config_mod, "get_settings", _hosted)
    assert isinstance(make_trace_store(db_session), PostgresTraceStore)


def test_make_trace_store_clickhouse_in_local_mode(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config_mod, "get_settings", _local)
    fake_client = object()
    store = make_trace_store(db_session, clickhouse_client=fake_client)
    assert isinstance(store, ClickHouseTraceStore)


# --- ClickHouse health when disabled ---


def test_clickhouse_health_disabled(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(health_mod, "get_settings", _hosted)
    resp = client.get("/health/clickhouse")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "disabled"
    assert "demo" in body["message"].lower()


# --- hosted demo executor ---


def test_demo_run_completes_and_stores_traces(db_session) -> None:
    run = _make_run(db_session)
    store = PostgresTraceStore(db_session)

    demo_executor.execute_demo_run_with_session(
        db_session, run, store, settings=_hosted(), redis_client=None
    )

    assert run.status == "completed"
    assert run.output_json is not None
    assert run.estimated_cost_usd is not None

    rows = store.get_events_by_run_id(run.id)
    event_types = {r[5] for r in rows}  # column index 5 == event_type
    assert {"run_started", "run_completed", "model_completed", "tool_completed"} <= event_types


def test_demo_run_trace_endpoint_reads_postgres(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    store = PostgresTraceStore(db_session)
    demo_executor.execute_demo_run_with_session(
        db_session, run, store, settings=_hosted(), redis_client=None
    )

    app.dependency_overrides[get_trace_store] = lambda: store
    try:
        resp = client.get(f"/runs/{run.id}/trace")
    finally:
        app.dependency_overrides.pop(get_trace_store, None)

    assert resp.status_code == 200
    events = resp.json()
    assert [e["event_type"] for e in events][0] == "run_started"
    assert any(e["tool_name"] == "calculator" for e in events)


def test_demo_diff_uses_postgres_traces(client: TestClient, db_session) -> None:
    run_a = _make_run(db_session)
    run_b = _make_run(db_session)
    store = PostgresTraceStore(db_session)
    for r in (run_a, run_b):
        demo_executor.execute_demo_run_with_session(
            db_session, r, store, settings=_hosted(), redis_client=None
        )

    app.dependency_overrides[get_trace_store] = lambda: store
    try:
        resp = client.get(f"/runs/{run_a.id}/diff/{run_b.id}")
    finally:
        app.dependency_overrides.pop(get_trace_store, None)

    assert resp.status_code == 200
    body = resp.json()
    assert "node_diffs" in body
    assert any(n["tool_b"] == "calculator" or n["tool_a"] == "calculator" for n in body["node_diffs"])


def test_demo_eval_tool_usage_uses_postgres_traces(client: TestClient, db_session) -> None:
    run = _make_run(db_session)
    store = PostgresTraceStore(db_session)
    demo_executor.execute_demo_run_with_session(
        db_session, run, store, settings=_hosted(), redis_client=None
    )

    app.dependency_overrides[get_trace_store] = lambda: store
    try:
        resp = client.post(
            f"/runs/{run.id}/eval",
            json={"eval_types": ["tool_usage"], "expected_tools": ["calculator"]},
        )
    finally:
        app.dependency_overrides.pop(get_trace_store, None)

    assert resp.status_code == 201
    results = resp.json()
    tool_eval = next(r for r in results if r["eval_type"] == "tool_usage")
    assert tool_eval["tool_correctness_score"] == 1.0
    assert tool_eval["passed"] is True


# --- dispatch behavior: hosted demo vs local worker ---


def test_create_run_hosted_dispatches_demo(db_session, monkeypatch) -> None:
    """Hosted demo mode schedules the in-API executor and does not enqueue Redis."""
    monkeypatch.setattr(run_service, "get_settings", _hosted)

    scheduled: list[Any] = []

    class FakeBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            scheduled.append((func, args))

    class FakeRedis:
        def __init__(self):
            self.pushes: list[Any] = []

        def rpush(self, key, value):
            self.pushes.append((key, value))

    monkeypatch.setattr(demo_executor, "execute_demo_run", lambda run_id: None)

    wf = Workflow(name="demo")
    db_session.add(wf)
    db_session.flush()
    version = WorkflowVersion(workflow_id=wf.id, version_number=1, graph_json=_demo_graph())
    db_session.add(version)
    db_session.flush()
    wf.current_version_id = version.id
    db_session.flush()

    redis = FakeRedis()
    bg = FakeBackgroundTasks()
    run_service.create_run(
        db_session, redis, wf.id, WorkflowRunCreate(input={}), background_tasks=bg
    )

    assert len(scheduled) == 1  # demo executor scheduled
    assert redis.pushes == []  # nothing enqueued to the worker queue


def test_create_run_local_enqueues_redis(db_session, monkeypatch) -> None:
    """Local/full-stack mode (worker enabled) enqueues to Redis as before."""
    monkeypatch.setattr(run_service, "get_settings", _local)

    class FakeRedis:
        def __init__(self):
            self.pushes: list[Any] = []

        def rpush(self, key, value):
            self.pushes.append((key, value))

    wf = Workflow(name="demo")
    db_session.add(wf)
    db_session.flush()
    version = WorkflowVersion(workflow_id=wf.id, version_number=1, graph_json=_demo_graph())
    db_session.add(version)
    db_session.flush()
    wf.current_version_id = version.id
    db_session.flush()

    redis = FakeRedis()
    run_service.create_run(
        db_session, redis, wf.id, WorkflowRunCreate(input={}), background_tasks=None
    )

    assert len(redis.pushes) == 1  # job enqueued for the worker
