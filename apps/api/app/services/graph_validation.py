"""MVP semantic validation for workflow graphs.

Structural validation (field types, node-type enum) is handled by Pydantic and
yields HTTP 422. This module covers semantic rules and yields HTTP 400 via
``GraphValidationError``.
"""

from app.schemas.workflow import NodeType, WorkflowGraph
from app.services.exceptions import GraphValidationError


def validate_graph(graph: WorkflowGraph) -> None:
    nodes = graph.nodes
    edges = graph.edges

    if not nodes:
        raise GraphValidationError("Graph must contain at least one node.")

    node_ids = [n.id for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise GraphValidationError("Node ids must be unique.")

    edge_ids = [e.id for e in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise GraphValidationError("Edge ids must be unique.")

    node_types = {n.type for n in nodes}
    if NodeType.input not in node_types:
        raise GraphValidationError("Graph must contain at least one input node.")
    if NodeType.output not in node_types:
        raise GraphValidationError("Graph must contain at least one output node.")

    id_set = set(node_ids)
    for edge in edges:
        if edge.source not in id_set:
            raise GraphValidationError(
                f"Edge '{edge.id}' source '{edge.source}' does not reference an existing node."
            )
        if edge.target not in id_set:
            raise GraphValidationError(
                f"Edge '{edge.id}' target '{edge.target}' does not reference an existing node."
            )

    # A multi-node workflow must be connected by at least one edge.
    if len(nodes) > 1 and not edges:
        raise GraphValidationError(
            "Graph with multiple nodes must contain at least one edge."
        )
