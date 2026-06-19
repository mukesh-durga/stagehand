from typing import Any

from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor


class AgentNode(NodeExecutor):
    node_type = "agent"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        # No real AI call yet (Milestone 9). Deterministic placeholder.
        return {
            "type": "agent_output",
            "node_id": node["id"],
            "message": "Agent execution placeholder",
            "input": node_input,
        }
