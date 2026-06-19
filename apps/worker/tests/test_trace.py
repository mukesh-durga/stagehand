"""Tests for the TraceEmitter and orchestrator trace emission."""

import json
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from worker.engine.orchestrator import execute_run
from worker.engine.trace import run_events_key
from worker.engine.trace_emitter import TraceEmitter

from .conftest import agent_graph, simple_graph


class _FakeRedis:
    def __init__(self):
        self.lists: dict[str, list[str]] = {}

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])


# --- TraceEmitter unit tests ---

def test_emitter_builds_valid_event():
    emitter = TraceEmitter("rid", "wid", "vid")
    event = emitter.emit_run_started()
    assert event.event_type == "run_started"
    assert event.status == "running"
    assert event.run_id == "rid"
    assert event.workflow_id == "wid"
    assert event.event_id
    assert event.timestamp is not None
    assert emitter.events == [event]


def test_emitter_publishes_to_redis():
    fake = _FakeRedis()
    emitter = TraceEmitter("rid", "wid", "vid", redis_client=fake)
    emitter.emit_node_started("node-1")

    key = run_events_key("rid")
    assert key in fake.lists
    assert len(fake.lists[key]) == 1
    payload = json.loads(fake.lists[key][0])
    assert payload["event_type"] == "node_started"
    assert payload["node_id"] == "node-1"


def test_emitter_inserts_into_clickhouse():
    ch = MagicMock()
    emitter = TraceEmitter("rid", "wid", "vid", clickhouse_client=ch)
    emitter.emit_run_completed(latency_ms=42)

    assert ch.insert.call_count == 1
    args, kwargs = ch.insert.call_args
    assert args[0] == "trace_events"


def test_emitter_tolerates_redis_failure():
    failing = MagicMock()
    failing.rpush.side_effect = RuntimeError("redis down")
    emitter = TraceEmitter("rid", "wid", "vid", redis_client=failing)
    # Should not raise despite the failing sink.
    event = emitter.emit_run_started()
    assert event.event_type == "run_started"
    assert len(emitter.events) == 1


# --- orchestrator emission tests ---

def test_orchestrator_emits_run_started_and_completed(db_session: Session, make_run):
    run = make_run(simple_graph(), input_json={"q": "x"})
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)

    types = [e.event_type for e in emitter.events]
    assert types[0] == "run_started"
    assert types[-1] == "run_completed"


def test_orchestrator_emits_node_events_per_node(db_session: Session, make_run):
    run = make_run(agent_graph(), input_json={})
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)

    types = [e.event_type for e in emitter.events]
    assert types.count("node_started") == 3
    assert types.count("node_completed") == 3
    # The agent node id appears in a node_started event.
    node_ids = {e.node_id for e in emitter.events if e.event_type == "node_started"}
    assert {"in1", "ag1", "out1"} == node_ids


def test_orchestrator_emits_run_failed_for_invalid_graph(db_session: Session, make_run):
    bad = {
        "nodes": [{"id": "out1", "type": "output", "position": {"x": 0, "y": 0}, "config": {}}],
        "edges": [],
    }
    run = make_run(bad)
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)

    types = [e.event_type for e in emitter.events]
    assert "run_failed" in types
    assert "run_completed" not in types
