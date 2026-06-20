"""Safe tool framework base classes."""

from typing import Any


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute (-> tool_failed event, node fails)."""


class Tool:
    name: str
    description: str
    # Lightweight schema describing expected input fields.
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
