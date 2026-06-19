from typing import Any

from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor


class InputNode(NodeExecutor):
    node_type = "input"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        # The input node surfaces the workflow input into the graph.
        return context.input
