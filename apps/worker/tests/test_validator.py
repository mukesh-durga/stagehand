"""Tests for graph validation."""

import pytest

from worker.engine.errors import GraphValidationError
from worker.engine.workflow_validator import validate_graph


def _graph(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def test_accepts_valid_graph():
    validate_graph(
        _graph(
            [
                {"id": "in1", "type": "input"},
                {"id": "out1", "type": "output"},
            ],
            [{"id": "e1", "source": "in1", "target": "out1"}],
        )
    )


def test_rejects_empty_graph():
    with pytest.raises(GraphValidationError):
        validate_graph(_graph([], []))


def test_rejects_missing_input():
    with pytest.raises(GraphValidationError, match="input"):
        validate_graph(_graph([{"id": "out1", "type": "output"}], []))


def test_rejects_missing_output():
    with pytest.raises(GraphValidationError, match="output"):
        validate_graph(_graph([{"id": "in1", "type": "input"}], []))


def test_rejects_edge_referencing_missing_node():
    with pytest.raises(GraphValidationError, match="missing node"):
        validate_graph(
            _graph(
                [
                    {"id": "in1", "type": "input"},
                    {"id": "out1", "type": "output"},
                ],
                [{"id": "e1", "source": "in1", "target": "ghost"}],
            )
        )


def test_rejects_duplicate_node_ids():
    with pytest.raises(GraphValidationError, match="Node ids"):
        validate_graph(
            _graph(
                [
                    {"id": "in1", "type": "input"},
                    {"id": "in1", "type": "output"},
                ],
                [],
            )
        )


def test_rejects_unsupported_node_type():
    with pytest.raises(GraphValidationError, match="Unsupported"):
        validate_graph(
            _graph(
                [
                    {"id": "in1", "type": "input"},
                    {"id": "x1", "type": "banana"},
                    {"id": "out1", "type": "output"},
                ],
                [],
            )
        )


def test_rejects_cycle():
    with pytest.raises(GraphValidationError, match="cycle"):
        validate_graph(
            _graph(
                [
                    {"id": "in1", "type": "input"},
                    {"id": "a", "type": "agent"},
                    {"id": "b", "type": "agent"},
                    {"id": "out1", "type": "output"},
                ],
                [
                    {"id": "e1", "source": "a", "target": "b"},
                    {"id": "e2", "source": "b", "target": "a"},
                ],
            )
        )
