from typing import Any

from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor


class RouterNode(NodeExecutor):
    node_type = "router"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        # No real routing logic yet (later milestone). Pass-through placeholder.
        return {
            "type": "router_output",
            "node_id": node["id"],
            "message": "Router execution placeholder",
            "input": node_input,
        }
