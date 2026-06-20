"""Tests for the orchestrator run lifecycle."""

from sqlalchemy.orm import Session

from worker.engine.orchestrator import execute_run
from worker.engine.trace_emitter import TraceEmitter

from .conftest import (
    agent_graph,
    agent_tool_graph,
    simple_graph,
    tool_graph,
)


def test_executes_input_to_output(db_session: Session, make_run):
    run = make_run(simple_graph(), input_json={"query": "hello"})
    execute_run(db_session, run)
    assert run.status == "completed"
    # Output node passes through the input node's output (the workflow input).
    assert run.output_json == {"query": "hello"}


def test_executes_input_agent_output(db_session: Session, make_run):
    run = make_run(agent_graph(), input_json={"query": "hi"})
    execute_run(db_session, run)
    assert run.status == "completed"
    assert run.output_json["type"] == "agent_output"
    assert run.output_json["input"] == {"query": "hi"}


def test_stores_final_output_and_timing(db_session: Session, make_run):
    run = make_run(simple_graph(), input_json={"k": "v"})
    execute_run(db_session, run)
    assert run.output_json is not None
    assert run.total_latency_ms is not None
    assert run.total_latency_ms >= 0


def test_status_running_then_completed(db_session: Session, make_run):
    run = make_run(simple_graph())
    assert run.status == "queued"
    execute_run(db_session, run)
    # started_at is set during the running phase; final status is completed.
    assert run.started_at is not None
    assert run.completed_at is not None
    assert run.status == "completed"


def test_invalid_graph_marks_run_failed(db_session: Session, make_run):
    bad = {
        "nodes": [{"id": "out1", "type": "output", "position": {"x": 0, "y": 0}, "config": {}}],
        "edges": [],
    }
    run = make_run(bad)
    execute_run(db_session, run)
    assert run.status == "failed"
    assert run.error_message and "input" in run.error_message.lower()


def test_max_steps_exceeded_marks_run_failed(db_session: Session, make_run):
    run = make_run(agent_graph(), input_json={})
    execute_run(db_session, run, run_config={"max_steps": 1})
    assert run.status == "failed"
    assert run.error_message and "step" in run.error_message.lower()


def test_agent_graph_emits_model_events(db_session: Session, make_run):
    run = make_run(agent_graph(), input_json={"query": "x"})
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)
    assert run.status == "completed"
    types = [e.event_type for e in emitter.events]
    assert "model_called" in types
    assert "model_completed" in types
    # Agent output text is threaded into the final output.
    assert "text" in run.output_json


def test_tool_graph_emits_tool_events(db_session: Session, make_run):
    run = make_run(tool_graph("calculator"), input_json={})
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)
    assert run.status == "completed"
    types = [e.event_type for e in emitter.events]
    assert "tool_called" in types
    assert "tool_completed" in types
    assert run.output_json["result"]["result"] == 7


def test_agent_tool_graph_completes_with_all_events(db_session: Session, make_run):
    run = make_run(agent_tool_graph(), input_json={"query": "x"})
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)
    assert run.status == "completed"
    types = [e.event_type for e in emitter.events]
    for expected in ("model_called", "model_completed", "tool_called", "tool_completed"):
        assert expected in types


def _agent_graph_with_config(config: dict) -> dict:
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "ag1", "type": "agent", "position": {"x": 150, "y": 0}, "config": config},
            {"id": "out1", "type": "output", "position": {"x": 300, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "in1", "target": "ag1"},
            {"id": "e2", "source": "ag1", "target": "out1"},
        ],
    }


def test_agent_graph_succeeds_after_retry(db_session: Session, make_run):
    run = make_run(_agent_graph_with_config({"failTimes": 1, "maxRetries": 2}))
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)
    assert run.status == "completed"
    assert "retry_scheduled" in [e.event_type for e in emitter.events]


def test_agent_graph_succeeds_with_fallback(db_session: Session, make_run):
    run = make_run(
        _agent_graph_with_config(
            {"forceFailure": True, "maxRetries": 1, "fallbackModel": "strong"}
        )
    )
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)
    assert run.status == "completed"
    types = [e.event_type for e in emitter.events]
    assert "fallback_used" in types
    assert "run_completed" in types


def test_tool_graph_fails_after_retries(db_session: Session, make_run):
    graph = {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {
                "id": "t1",
                "type": "tool",
                "position": {"x": 150, "y": 0},
                "config": {"toolName": "calculator", "expression": "1/0", "maxRetries": 1},
            },
            {"id": "out1", "type": "output", "position": {"x": 300, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "in1", "target": "t1"},
            {"id": "e2", "source": "t1", "target": "out1"},
        ],
    }
    run = make_run(graph)
    emitter = TraceEmitter.from_run(run)
    execute_run(db_session, run, emitter=emitter)
    assert run.status == "failed"
    types = [e.event_type for e in emitter.events]
    assert "retry_scheduled" in types
    assert "tool_failed" in types
    assert "run_failed" in types
