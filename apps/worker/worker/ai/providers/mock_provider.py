"""Deterministic mock model provider (default; requires no API keys)."""

import time

from worker.ai.providers.base import (
    Message,
    ModelProvider,
    ModelProviderError,
    ModelResponse,
    estimate_tokens,
)


class MockModelProvider(ModelProvider):
    """Deterministic provider with optional, test-only failure triggers.

    - ``force_failure``: every call raises ModelProviderError.
    - ``fail_times``: the first N calls raise, then calls succeed.

    The call counter is per-instance, so it persists across RetryManager retries
    within a single node execution.
    """

    def __init__(self, *, fail_times: int = 0, force_failure: bool = False) -> None:
        self.fail_times = fail_times
        self.force_failure = force_failure
        self._calls = 0

    def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> ModelResponse:
        self._calls += 1
        if self.force_failure:
            raise ModelProviderError(f"mock forced failure (call {self._calls})")
        if self._calls <= self.fail_times:
            raise ModelProviderError(
                f"mock transient failure {self._calls}/{self.fail_times}"
            )

        start = time.monotonic()
        user = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        snippet = user[:80]
        text = f"Mock model response for: {snippet}" if snippet else "Mock model response"
        input_tokens = estimate_tokens(messages)
        output_tokens = len(text.split())
        latency_ms = int((time.monotonic() - start) * 1000)
        return ModelResponse(
            text=text,
            model_name=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=0.0,
            latency_ms=latency_ms,
            raw_response={"mock": True},
        )
