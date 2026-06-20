"""Optional OpenAI provider.

Only used when OPENAI_API_KEY is set AND the `openai` package is installed.
The model router falls back to MockModelProvider otherwise, so local runs and
tests never require this provider or a real key.
"""

import time

from worker.ai.providers.base import Message, ModelProvider, ModelResponse

# Rough per-1K-token prices (USD); extend as needed.
_PRICE_PER_1K = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.005, 0.015),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    for key, (in_price, out_price) in _PRICE_PER_1K.items():
        if key in model:
            return (input_tokens / 1000) * in_price + (output_tokens / 1000) * out_price
    return 0.0


class OpenAIProvider(ModelProvider):
    def __init__(self, api_key: str) -> None:
        # Imported lazily so the package is only required when this provider is used.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> ModelResponse:
        start = time.monotonic()
        completion = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        text = completion.choices[0].message.content or ""
        usage = completion.usage
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return ModelResponse(
            text=text,
            model_name=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
            latency_ms=latency_ms,
            raw_response=None,
        )
