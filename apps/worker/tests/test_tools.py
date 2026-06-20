"""Tests for the tool framework and registry."""

import pytest

from worker.tools.base import ToolExecutionError
from worker.tools.calculator import CalculatorTool, safe_eval
from worker.tools.mock_search import MockSearchTool
from worker.tools.registry import ToolNotFoundError, get_tool, list_tools


def test_registry_has_calculator_and_mock_search():
    names = list_tools()
    assert "calculator" in names
    assert "mock_search" in names


def test_get_tool_unknown_raises():
    with pytest.raises(ToolNotFoundError):
        get_tool("does_not_exist")


def test_calculator_evaluates_expression():
    result = CalculatorTool().execute({"expression": "2 + 3 * 4"})
    assert result["result"] == 14
    assert result["expression"] == "2 + 3 * 4"


def test_calculator_defaults_when_missing():
    result = CalculatorTool().execute({})
    assert result["result"] == 2  # default "1 + 1"


def test_calculator_rejects_unsafe_input():
    with pytest.raises(ToolExecutionError):
        safe_eval("__import__('os').system('ls')")
    with pytest.raises(ToolExecutionError):
        safe_eval("a + b")


def test_mock_search_returns_deterministic_results():
    out = MockSearchTool().execute({"query": "langsmith"})
    assert out["query"] == "langsmith"
    assert len(out["results"]) == 3
    assert out["results"][0]["title"].endswith("langsmith")
    # deterministic
    assert MockSearchTool().execute({"query": "langsmith"}) == out
