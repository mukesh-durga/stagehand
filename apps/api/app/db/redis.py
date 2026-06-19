"""Redis client setup.

Used for the workflow run queue and (later) trace fanout. ``get_redis`` is a
FastAPI dependency so it can be overridden in tests.
"""

from functools import lru_cache

import redis
import redis.asyncio as aioredis

from app.config import get_settings

# Queue key for pending workflow run jobs (consumed by the worker in Milestone 6).
RUN_QUEUE_KEY = "queue:workflow_runs"


def run_events_key(run_id: str) -> str:
    """Redis list key holding a run's trace events (written by the worker)."""
    return f"run:{run_id}:events"


@lru_cache
def _client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    """FastAPI dependency returning a shared (sync) Redis client."""
    return _client()


@lru_cache
def _async_client() -> aioredis.Redis:
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def get_async_redis() -> aioredis.Redis:
    """FastAPI dependency returning a shared async Redis client (for WebSockets)."""
    return _async_client()
