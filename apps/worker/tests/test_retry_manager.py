"""Tests for RetryManager."""

import time

import pytest

from worker.engine.retry_manager import RetryManager, RetryPolicy, compute_backoff_ms

_NO_SLEEP = lambda _s: None  # noqa: E731


def test_succeeds_on_first_attempt():
    calls = []
    rm = RetryManager(RetryPolicy(max_retries=2), sleep=_NO_SLEEP)
    result = rm.run(lambda: calls.append(1) or "ok")
    assert result == "ok"
    assert len(calls) == 1


def test_retries_once_then_succeeds():
    state = {"n": 0}
    retries = []

    def op():
        state["n"] += 1
        if state["n"] < 2:
            raise ValueError("boom")
        return "ok"

    rm = RetryManager(
        RetryPolicy(max_retries=2),
        sleep=_NO_SLEEP,
        on_retry=lambda attempt, exc, delay: retries.append(attempt),
    )
    assert rm.run(op) == "ok"
    assert state["n"] == 2
    assert retries == [1]


def test_exhausts_retries_and_raises():
    attempts = []
    rm = RetryManager(
        RetryPolicy(max_retries=2),
        sleep=_NO_SLEEP,
        on_attempt=lambda a: attempts.append(a),
    )
    with pytest.raises(ValueError):
        rm.run(lambda: (_ for _ in ()).throw(ValueError("always")))
    assert attempts == [1, 2, 3]  # initial + 2 retries


def test_non_retryable_raises_immediately():
    attempts = []
    rm = RetryManager(
        RetryPolicy(max_retries=3),
        sleep=_NO_SLEEP,
        on_attempt=lambda a: attempts.append(a),
        non_retryable=(KeyError,),
    )
    with pytest.raises(KeyError):
        rm.run(lambda: (_ for _ in ()).throw(KeyError("nope")))
    assert attempts == [1]  # no retries


def test_timeout_is_enforced():
    rm = RetryManager(RetryPolicy(max_retries=0, timeout_ms=50), sleep=_NO_SLEEP)
    with pytest.raises(TimeoutError):
        rm.run(lambda: time.sleep(0.5))


def test_compute_backoff_grows_exponentially():
    policy = RetryPolicy(initial_backoff_ms=100, backoff_multiplier=2.0, jitter_ms=0)
    assert compute_backoff_ms(policy, 0, jitter=False) == 100
    assert compute_backoff_ms(policy, 1, jitter=False) == 200
    assert compute_backoff_ms(policy, 2, jitter=False) == 400
