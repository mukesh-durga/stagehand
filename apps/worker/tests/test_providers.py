"""Tests for the model provider abstraction."""

from worker.ai.model_router import get_provider, resolve_model_name, select
from worker.ai.providers.base import ModelResponse
from worker.ai.providers.mock_provider import MockModelProvider
from worker.config import Settings


def test_mock_provider_returns_deterministic_response():
    provider = MockModelProvider()
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hello world"},
    ]
    r1 = provider.generate(model="mock-cheap", messages=messages)
    r2 = provider.generate(model="mock-cheap", messages=messages)
    assert isinstance(r1, ModelResponse)
    assert r1.text == r2.text
    assert r1.model_name == "mock-cheap"
    assert r1.output_tokens > 0
    assert r1.estimated_cost_usd == 0.0


def test_get_provider_defaults_to_mock_without_keys():
    settings = Settings(openai_api_key="")
    assert isinstance(get_provider(settings), MockModelProvider)


def test_resolve_model_name_by_policy():
    settings = Settings(cheap_model_name="", strong_model_name="")
    assert resolve_model_name("cheap", settings) == "mock-cheap"
    assert resolve_model_name("strong", settings) == "mock-strong"
    assert resolve_model_name("adaptive", settings) == "mock-cheap"


def test_select_returns_provider_and_model():
    settings = Settings(openai_api_key="")
    provider, model = select("strong", settings)
    assert isinstance(provider, MockModelProvider)
    assert model == "mock-strong"
