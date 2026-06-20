"""Agent node — model call with retry + fallback, emitting model trace events."""

import json
from typing import Any

from worker.ai.model_router import get_provider, resolve_model_name, select
from worker.ai.providers.base import ModelResponse
from worker.ai.providers.mock_provider import MockModelProvider
from worker.config import get_settings
from worker.engine.context import ExecutionContext
from worker.engine.nodes.base import NodeExecutor
from worker.engine.retry_manager import RetryManager, RetryPolicy

_POLICIES = {"cheap", "strong", "adaptive"}


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return str(value)


def _summary(text: str, limit: int = 200) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def _resolve_fallback(fallback_model: str, settings: Any) -> tuple[Any, str]:
    """Return (provider, model_name) for a fallback configured as a policy or name."""
    if fallback_model in _POLICIES:
        return get_provider(settings), resolve_model_name(fallback_model, settings)
    return get_provider(settings), fallback_model


class AgentNode(NodeExecutor):
    node_type = "agent"

    def execute(
        self, node: dict[str, Any], context: ExecutionContext, node_input: Any
    ) -> Any:
        config = node.get("config") or {}
        node_id = node["id"]
        policy = config.get("modelPolicy") or config.get("model_policy") or "adaptive"
        prompt = config.get("prompt") or "You are a helpful agent."
        temperature = float(config.get("temperature", 0.2))
        max_tokens = int(config.get("maxTokens") or config.get("max_tokens") or 512)
        max_retries = int(config.get("maxRetries", 2))
        timeout_ms = int(config.get("timeoutMs") or config.get("timeout_ms") or 30000)
        fallback_model = config.get("fallbackModel") or config.get("fallback_model")

        settings = get_settings()
        provider, model_name = select(policy, settings)
        # Test-only deterministic failure triggers (mock provider only).
        if isinstance(provider, MockModelProvider):
            provider.fail_times = int(config.get("failTimes") or 0)
            provider.force_failure = bool(config.get("forceFailure") or False)

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": _stringify(node_input)},
        ]
        emitter = context.emitter

        def make_on_attempt(model: str, fallback: bool):
            def _on_attempt(attempt: int) -> None:
                if emitter is not None:
                    emitter.emit_model_called(
                        node_id,
                        model,
                        metadata={
                            "model_policy": policy,
                            "attempt": attempt,
                            "fallback": fallback,
                            "prompt_summary": _summary(prompt),
                        },
                    )

            return _on_attempt

        def on_retry(attempt: int, exc: BaseException, delay_ms: int) -> None:
            if emitter is not None:
                emitter.emit_retry_scheduled(
                    node_id,
                    attempt=attempt,
                    max_retries=max_retries,
                    reason=str(exc),
                    next_delay_ms=delay_ms,
                    model_name=model_name,
                )

        def call(prov: Any, model: str):
            return lambda: prov.generate(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        policy_obj = RetryPolicy(max_retries=max_retries, timeout_ms=timeout_ms)
        rm = RetryManager(
            policy_obj, on_attempt=make_on_attempt(model_name, False), on_retry=on_retry
        )

        try:
            response: ModelResponse = rm.run(call(provider, model_name))
            used_model = model_name
        except Exception as primary_exc:
            if not fallback_model:
                raise
            fb_provider, fb_model = _resolve_fallback(str(fallback_model), settings)
            if emitter is not None:
                emitter.emit_fallback_used(
                    node_id, fallback_model=fb_model, reason=str(primary_exc)
                )
            # Single fallback attempt (with timeout, no further retries).
            fb_rm = RetryManager(
                RetryPolicy(max_retries=0, timeout_ms=timeout_ms),
                on_attempt=make_on_attempt(fb_model, True),
            )
            response = fb_rm.run(call(fb_provider, fb_model))
            used_model = response.model_name or fb_model

        if emitter is not None:
            emitter.emit_model_completed(
                node_id,
                response.model_name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                estimated_cost_usd=response.estimated_cost_usd,
                latency_ms=response.latency_ms,
                metadata={"output_summary": _summary(response.text)},
            )

        return {
            "type": "agent_output",
            "node_id": node_id,
            "model": used_model,
            "text": response.text,
            "input": node_input,
        }
