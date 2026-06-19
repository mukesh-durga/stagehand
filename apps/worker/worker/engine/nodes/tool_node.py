from typing import Any

from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor


class ToolNode(NodeExecutor):
    node_type = "tool"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        # No real tool call yet (Milestone 9). Deterministic placeholder.
        return {
            "type": "tool_output",
            "node_id": node["id"],
            "message": "Tool execution placeholder",
            "input": node_input,
        }
