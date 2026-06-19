"""Tests for the execution planner."""

import pytest

from worker.engine.errors import GraphValidationError
from worker.engine.execution_planner import topological_order


def test_topological_order_linear():
    nodes = [
        {"id": "in1", "type": "input"},
        {"id": "ag1", "type": "agent"},
        {"id": "out1", "type": "output"},
    ]
    edges = [
        {"id": "e1", "source": "in1", "target": "ag1"},
        {"id": "e2", "source": "ag1", "target": "out1"},
    ]
    order = topological_order(nodes, edges)
    assert order.index("in1") < order.index("ag1") < order.index("out1")


def test_topological_order_raises_on_cycle():
    nodes = [{"id": "a", "type": "agent"}, {"id": "b", "type": "agent"}]
    edges = [
        {"id": "e1", "source": "a", "target": "b"},
        {"id": "e2", "source": "b", "target": "a"},
    ]
    with pytest.raises(GraphValidationError):
        topological_order(nodes, edges)
