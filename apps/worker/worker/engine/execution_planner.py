"""Topological execution planning (Kahn's algorithm)."""

from collections import deque
from typing import Any

from worker.engine.errors import GraphValidationError


def topological_order(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> list[str]:
    """Return node ids in a valid execution order, or raise on a cycle."""
    ids = [n["id"] for n in nodes]
    indegree: dict[str, int] = {i: 0 for i in ids}
    adjacency: dict[str, list[str]] = {i: [] for i in ids}

    for edge in edges:
        source, target = edge["source"], edge["target"]
        if source in adjacency and target in indegree:
            adjacency[source].append(target)
            indegree[target] += 1

    # Preserve node declaration order among ready nodes for determinism.
    queue: deque[str] = deque([i for i in ids if indegree[i] == 0])
    order: list[str] = []

    while queue:
        current = queue.popleft()
        order.append(current)
        for neighbor in adjacency[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(ids):
        raise GraphValidationError("Graph contains a cycle.")
    return order
