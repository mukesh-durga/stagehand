"""Base node executor interface."""

from typing import Any

from worker.engine.context import ExecutionContext


class NodeExecutor:
    """Executes a single node. Subclasses implement deterministic behavior."""

    node_type: str

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        raise NotImplementedError
