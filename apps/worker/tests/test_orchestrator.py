"""Tests for the orchestrator run lifecycle."""

from sqlalchemy.orm import Session

from worker.engine.orchestrator import execute_run

from .conftest import agent_graph, simple_graph


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
