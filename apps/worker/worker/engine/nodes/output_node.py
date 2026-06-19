from typing import Any

from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor


class OutputNode(NodeExecutor):
    node_type = "output"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        # The output node returns whatever it received from upstream.
        return node_input
