"""Tests for Agent and Tool node executors (with trace emission)."""

import pytest

from worker.engine.context import ExecutionContext
from worker.engine.nodes.agent_node import AgentNode
from worker.engine.nodes.tool_node import ToolNode
from worker.engine.trace_emitter import TraceEmitter
from worker.tools.registry import ToolNotFoundError


def _context() -> ExecutionContext:
    emitter = TraceEmitter("r", "w", "v")  # sink-less; records to .events
    return ExecutionContext(
        run_id="r",
        workflow_id="w",
        workflow_version_id="v",
        input={"query": "hi"},
        run_config={},
        max_steps=25,
        max_runtime_seconds=120,
        max_cost_usd=0.5,
        emitter=emitter,
    )


def _types(ctx: ExecutionContext) -> list[str]:
    return [e.event_type for e in ctx.emitter.events]


# --- agent node ---

def test_agent_node_calls_provider_and_returns_output():
    ctx = _context()
    node = {"id": "ag1", "type": "agent", "config": {"modelPolicy": "cheap", "prompt": "P"}}
    out = AgentNode().execute(node, ctx, ctx.input)
    assert out["type"] == "agent_output"
    assert out["node_id"] == "ag1"
    assert out["model"]  # model name present
    assert out["text"]  # mock text present


def test_agent_node_emits_model_events():
    ctx = _context()
    node = {"id": "ag1", "type": "agent", "config": {}}
    AgentNode().execute(node, ctx, ctx.input)
    types = _types(ctx)
    assert "model_called" in types
    assert "model_completed" in types
    completed = [e for e in ctx.emitter.events if e.event_type == "model_completed"][0]
    assert completed.model_name
    assert completed.node_id == "ag1"


# --- tool node ---

def test_tool_node_executes_calculator():
    ctx = _context()
    node = {"id": "t1", "type": "tool", "config": {"toolName": "calculator", "expression": "6*7"}}
    out = ToolNode().execute(node, ctx, ctx.input)
    assert out["type"] == "tool_output"
    assert out["tool_name"] == "calculator"
    assert out["result"]["result"] == 42
    types = _types(ctx)
    assert "tool_called" in types and "tool_completed" in types


def test_tool_node_executes_mock_search():
    ctx = _context()
    node = {"id": "t1", "type": "tool", "config": {"toolName": "mock_search", "query": "x"}}
    out = ToolNode().execute(node, ctx, ctx.input)
    assert out["tool_name"] == "mock_search"
    assert len(out["result"]["results"]) == 3


def test_tool_node_invalid_tool_emits_failed_and_raises():
    ctx = _context()
    node = {"id": "t1", "type": "tool", "config": {"toolName": "nope"}}
    with pytest.raises(ToolNotFoundError):
        ToolNode().execute(node, ctx, ctx.input)
    assert "tool_failed" in _types(ctx)
    # Unknown tool is a config error: not retried.
    assert "retry_scheduled" not in _types(ctx)


# --- retry / fallback ---

def test_agent_retries_once_then_succeeds():
    ctx = _context()
    node = {
        "id": "ag1",
        "type": "agent",
        "config": {"modelPolicy": "cheap", "failTimes": 1, "maxRetries": 2},
    }
    out = AgentNode().execute(node, ctx, ctx.input)
    types = _types(ctx)
    assert types.count("model_called") == 2  # one retry
    assert "retry_scheduled" in types
    assert "model_completed" in types
    assert out["text"]


def test_agent_uses_fallback_after_failure():
    ctx = _context()
    node = {
        "id": "ag1",
        "type": "agent",
        "config": {
            "modelPolicy": "cheap",
            "forceFailure": True,
            "maxRetries": 1,
            "fallbackModel": "strong",
        },
    }
    out = AgentNode().execute(node, ctx, ctx.input)
    types = _types(ctx)
    assert "fallback_used" in types
    assert "model_completed" in types  # fallback succeeded
    assert out["model"] == "mock-strong"


def test_agent_final_failure_raises_without_fallback():
    ctx = _context()
    node = {
        "id": "ag1",
        "type": "agent",
        "config": {"modelPolicy": "cheap", "forceFailure": True, "maxRetries": 1},
    }
    with pytest.raises(Exception):
        AgentNode().execute(node, ctx, ctx.input)
    assert "retry_scheduled" in _types(ctx)
    assert "model_completed" not in _types(ctx)


def test_tool_node_retries_then_fails():
    ctx = _context()
    node = {
        "id": "t1",
        "type": "tool",
        "config": {"toolName": "calculator", "expression": "1/0", "maxRetries": 2},
    }
    with pytest.raises(Exception):
        ToolNode().execute(node, ctx, ctx.input)
    types = _types(ctx)
    assert types.count("tool_called") == 3  # initial + 2 retries
    assert "retry_scheduled" in types
    assert "tool_failed" in types
