"""Shared worker test fixtures.

Uses the same transactional-rollback pattern as the API: each test runs inside a
transaction that is rolled back at teardown, so the shared database stays clean.
Requires PostgreSQL to be running with the API migrations applied.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy.orm import Session

from worker.db import engine
from worker.models import Workflow, WorkflowRun, WorkflowVersion


@pytest.fixture
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def simple_graph() -> dict[str, Any]:
    """Input -> Output."""
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "out1", "type": "output", "position": {"x": 200, "y": 0}, "config": {}},
        ],
        "edges": [{"id": "e1", "source": "in1", "target": "out1"}],
    }


def agent_graph() -> dict[str, Any]:
    """Input -> Agent -> Output."""
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "ag1", "type": "agent", "position": {"x": 150, "y": 0}, "config": {}},
            {"id": "out1", "type": "output", "position": {"x": 300, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "in1", "target": "ag1"},
            {"id": "e2", "source": "ag1", "target": "out1"},
        ],
    }


def tool_graph(tool_name: str = "calculator") -> dict[str, Any]:
    """Input -> Tool -> Output."""
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {
                "id": "t1",
                "type": "tool",
                "position": {"x": 150, "y": 0},
                "config": {"toolName": tool_name, "expression": "3 + 4"},
            },
            {"id": "out1", "type": "output", "position": {"x": 300, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "in1", "target": "t1"},
            {"id": "e2", "source": "t1", "target": "out1"},
        ],
    }


def agent_tool_graph() -> dict[str, Any]:
    """Input -> Agent -> Tool -> Output."""
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "ag1", "type": "agent", "position": {"x": 120, "y": 0}, "config": {}},
            {
                "id": "t1",
                "type": "tool",
                "position": {"x": 240, "y": 0},
                "config": {"toolName": "calculator", "expression": "2 * 5"},
            },
            {"id": "out1", "type": "output", "position": {"x": 360, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "in1", "target": "ag1"},
            {"id": "e2", "source": "ag1", "target": "t1"},
            {"id": "e3", "source": "t1", "target": "out1"},
        ],
    }


@pytest.fixture
def make_run(db_session: Session):
    """Factory creating a workflow + version + queued run in the test DB."""

    def _make(graph: dict[str, Any], input_json: dict[str, Any] | None = None) -> WorkflowRun:
        workflow = Workflow(name="test-wf")
        db_session.add(workflow)
        db_session.flush()

        version = WorkflowVersion(
            workflow_id=workflow.id, version_number=1, graph_json=graph
        )
        db_session.add(version)
        db_session.flush()

        workflow.current_version_id = version.id

        run = WorkflowRun(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            status="queued",
            input_json=input_json or {},
        )
        db_session.add(run)
        db_session.flush()
        return run

    return _make
