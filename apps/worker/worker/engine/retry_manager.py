"""RetryManager: run an operation with retries, timeout, and exponential backoff.

Kept synchronous to match the engine. Emits nothing itself — callers pass
``on_attempt`` / ``on_retry`` hooks to emit trace events on the main thread (the
operation runs in a worker thread only so a timeout can be enforced).
"""

import logging
import random
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_retries: int = 2
    initial_backoff_ms: int = 250
    backoff_multiplier: float = 2.0
    timeout_ms: int = 30000
    jitter_ms: int = 50


def compute_backoff_ms(policy: RetryPolicy, attempt: int, *, jitter: bool = True) -> int:
    """Delay before the retry following a failed ``attempt`` (0-based)."""
    base = policy.initial_backoff_ms * (policy.backoff_multiplier**attempt)
    delay = int(base)
    if jitter and policy.jitter_ms:
        delay += random.randint(0, policy.jitter_ms)
    return delay


# on_attempt(attempt_number); on_retry(attempt_number, exc, next_delay_ms)
OnAttempt = Callable[[int], None]
OnRetry = Callable[[int, BaseException, int], None]


class RetryManager:
    def __init__(
        self,
        policy: RetryPolicy | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        on_attempt: OnAttempt | None = None,
        on_retry: OnRetry | None = None,
        non_retryable: tuple[type[BaseException], ...] = (),
    ) -> None:
        self.policy = policy or RetryPolicy()
        self._sleep = sleep
        self._on_attempt = on_attempt
        self._on_retry = on_retry
        self._non_retryable = non_retryable

    def _call_with_timeout(self, operation: Callable[[], T]) -> T:
        timeout_s = self.policy.timeout_ms / 1000 if self.policy.timeout_ms else None
        if not timeout_s:
            return operation()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(operation)
            try:
                return future.result(timeout=timeout_s)
            except FuturesTimeout as exc:
                raise TimeoutError(
                    f"operation timed out after {self.policy.timeout_ms}ms"
                ) from exc

    def run(self, operation: Callable[[], T]) -> T:
        for attempt in range(self.policy.max_retries + 1):
            if self._on_attempt is not None:
                self._on_attempt(attempt + 1)
            try:
                return self._call_with_timeout(operation)
            except self._non_retryable:
                raise
            except Exception as exc:  # noqa: BLE001 - retry on any other failure
                if attempt >= self.policy.max_retries:
                    raise
                delay_ms = compute_backoff_ms(self.policy, attempt)
                if self._on_retry is not None:
                    self._on_retry(attempt + 1, exc, delay_ms)
                self._sleep(delay_ms / 1000)
        raise RuntimeError("unreachable")  # pragma: no cover
