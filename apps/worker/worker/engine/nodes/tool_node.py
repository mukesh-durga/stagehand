"""Tool node — safe tool execution with retry, emitting tool trace events."""

import time
from typing import Any

from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor
from worker.engine.retry_manager import RetryManager, RetryPolicy
from worker.tools.registry import ToolNotFoundError, get_tool


def _summary(text: str, limit: int = 200) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def _build_tool_input(config: dict[str, Any], node_input: Any) -> dict[str, Any]:
    """Merge upstream output with explicit config fields (config wins)."""
    data: dict[str, Any] = dict(node_input) if isinstance(node_input, dict) else {"value": node_input}
    for key in ("expression", "query", "input"):
        if config.get(key) is not None:
            data[key] = config[key]
    return data


class ToolNode(NodeExecutor):
    node_type = "tool"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        config = node.get("config") or {}
        node_id = node["id"]
        tool_name = config.get("toolName") or config.get("tool_name") or ""
        max_retries = int(config.get("maxRetries", 1))
        timeout_ms = int(config.get("timeoutMs") or config.get("timeout_ms") or 15000)
        emitter = context.emitter

        # Unknown tool is a configuration error — not retryable.
        try:
            tool = get_tool(tool_name)
        except ToolNotFoundError as exc:
            if emitter is not None:
                emitter.emit_tool_failed(node_id, tool_name, str(exc))
            raise

        tool_input = _build_tool_input(config, node_input)

        def on_attempt(attempt: int) -> None:
            if emitter is not None:
                emitter.emit_tool_called(
                    node_id,
                    tool_name,
                    metadata={"attempt": attempt, "input_summary": _summary(str(tool_input))},
                )

        def on_retry(attempt: int, exc: BaseException, delay_ms: int) -> None:
            if emitter is not None:
                emitter.emit_retry_scheduled(
                    node_id,
                    attempt=attempt,
                    max_retries=max_retries,
                    reason=str(exc),
                    next_delay_ms=delay_ms,
                    tool_name=tool_name,
                )

        rm = RetryManager(
            RetryPolicy(max_retries=max_retries, timeout_ms=timeout_ms),
            on_attempt=on_attempt,
            on_retry=on_retry,
        )

        start = time.monotonic()
        try:
            result = rm.run(lambda: tool.execute(tool_input))
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            if emitter is not None:
                emitter.emit_tool_failed(node_id, tool_name, str(exc), latency_ms=latency_ms)
            raise

        latency_ms = int((time.monotonic() - start) * 1000)
        if emitter is not None:
            emitter.emit_tool_completed(
                node_id,
                tool_name,
                latency_ms=latency_ms,
                metadata={"result_summary": _summary(str(result))},
            )

        return {
            "type": "tool_output",
            "node_id": node_id,
            "tool_name": tool_name,
            "result": result,
        }
