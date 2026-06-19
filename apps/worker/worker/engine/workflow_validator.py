"""Graph validation for the worker engine (mirrors the API's MVP rules)."""

from typing import Any

from worker.engine.errors import GraphValidationError
from worker.engine.execution_planner import topological_order

SUPPORTED_NODE_TYPES = {"input", "agent", "tool", "router", "output"}


def validate_graph(graph: dict[str, Any]) -> None:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    if not nodes:
        raise GraphValidationError("Graph must contain at least one node.")

    node_ids = [n["id"] for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise GraphValidationError("Node ids must be unique.")

    edge_ids = [e["id"] for e in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise GraphValidationError("Edge ids must be unique.")

    types = {n["type"] for n in nodes}
    unsupported = types - SUPPORTED_NODE_TYPES
    if unsupported:
        raise GraphValidationError(
            f"Unsupported node types: {sorted(unsupported)}"
        )
    if "input" not in types:
        raise GraphValidationError("Graph must contain at least one input node.")
    if "output" not in types:
        raise GraphValidationError("Graph must contain at least one output node.")

    id_set = set(node_ids)
    for edge in edges:
        if edge["source"] not in id_set:
            raise GraphValidationError(
                f"Edge '{edge['id']}' source references a missing node."
            )
        if edge["target"] not in id_set:
            raise GraphValidationError(
                f"Edge '{edge['id']}' target references a missing node."
            )

    # Basic acyclic validation — raises GraphValidationError on a cycle.
    topological_order(nodes, edges)
