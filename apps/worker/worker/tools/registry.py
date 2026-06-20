"""Tool registry and lookup."""

from worker.tools.base import Tool
from worker.tools.calculator import CalculatorTool
from worker.tools.mock_search import MockSearchTool


class ToolNotFoundError(Exception):
    """Raised when a workflow references a tool that is not registered."""


_TOOLS: dict[str, Tool] = {
    tool.name: tool for tool in (CalculatorTool(), MockSearchTool())
}


def get_tool(name: str) -> Tool:
    tool = _TOOLS.get(name)
    if tool is None:
        raise ToolNotFoundError(f"Unknown tool: {name!r}")
    return tool


def list_tools() -> list[str]:
    return list(_TOOLS)
