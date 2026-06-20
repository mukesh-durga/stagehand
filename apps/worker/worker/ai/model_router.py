"""Simple model selection: resolve a model name + provider from policy/settings.

Defaults to the MockModelProvider so local runs and tests work without API keys.
Adaptive routing (UCB) is a later milestone — "adaptive" maps to the cheap model
for now.
"""

import logging

from worker.ai.providers.base import ModelProvider
from worker.ai.providers.mock_provider import MockModelProvider
from worker.config import Settings, get_settings

logger = logging.getLogger(__name__)


def resolve_model_name(policy: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if policy == "strong":
        return settings.strong_model_name or "mock-strong"
    # "cheap" and "adaptive" both use the cheap model for this milestone.
    return settings.cheap_model_name or "mock-cheap"


def get_provider(settings: Settings | None = None) -> ModelProvider:
    settings = settings or get_settings()
    if settings.openai_api_key:
        try:
            from worker.ai.providers.openai_provider import OpenAIProvider

            return OpenAIProvider(api_key=settings.openai_api_key)
        except Exception:  # noqa: BLE001 - fall back to mock if SDK missing/misconfigured
            logger.warning("OpenAI provider unavailable; using MockModelProvider", exc_info=True)
    return MockModelProvider()


def select(policy: str, settings: Settings | None = None) -> tuple[ModelProvider, str]:
    settings = settings or get_settings()
    return get_provider(settings), resolve_model_name(policy, settings)
