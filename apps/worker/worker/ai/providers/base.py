"""Model provider abstraction."""

from typing import Any

from pydantic import BaseModel

# A chat message: {"role": "system"|"user"|"assistant", "content": "..."}
Message = dict[str, str]


class ModelProviderError(Exception):
    """Raised when a model provider call fails (treated as retryable)."""


class ModelResponse(BaseModel):
    text: str
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    raw_response: dict[str, Any] | None = None


class ModelProvider:
    """Synchronous model provider interface."""

    def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> ModelResponse:
        raise NotImplementedError


def estimate_tokens(messages: list[Message]) -> int:
    """Very rough token estimate (word count) for deterministic local accounting."""
    return sum(len(str(m.get("content", "")).split()) for m in messages)


__all__ = [
    "Message",
    "ModelResponse",
    "ModelProvider",
    "ModelProviderError",
    "estimate_tokens",
]
