"""Tests for the Redis job consumer."""

import json

import pytest
import redis.exceptions
from sqlalchemy.orm import Session

from worker.consumer import RUN_QUEUE_KEY, parse_job, process_job, run_worker_loop
from worker.engine.errors import InvalidJobError

from .conftest import simple_graph


def test_parse_job_valid():
    raw = json.dumps({"run_id": "abc", "workflow_id": "w", "input": {}})
    job = parse_job(raw)
    assert job["run_id"] == "abc"


def test_parse_job_invalid_json():
    with pytest.raises(InvalidJobError):
        parse_job("not json{")


def test_parse_job_missing_run_id():
    with pytest.raises(InvalidJobError):
        parse_job(json.dumps({"workflow_id": "w"}))


def test_process_job_completes_run(db_session: Session, make_run):
    run = make_run(simple_graph(), input_json={"query": "go"})
    job = {
        "run_id": str(run.id),
        "workflow_id": str(run.workflow_id),
        "workflow_version_id": str(run.workflow_version_id),
        "input": {"query": "go"},
        "run_config": {},
    }
    result = process_job(db_session, job)
    assert result is not None
    assert result.status == "completed"
    assert result.output_json == {"query": "go"}


class _FakeRedis:
    """Returns a single queued job, then signals empty."""

    def __init__(self, raws):
        self._raws = list(raws)

    def blpop(self, key, timeout=0):
        if self._raws:
            return (key, self._raws.pop(0))
        return None


class _ScriptedRedis:
    """Runs through a script of actions: ('raise', exc) or ('return', value)."""

    def __init__(self, actions):
        self._actions = list(actions)

    def blpop(self, key, timeout=0):
        action, payload = self._actions.pop(0)
        if action == "raise":
            raise payload
        return (key, payload) if payload is not None else None


class _NoopSession:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def test_run_worker_loop_consumes_job(monkeypatch):
    seen = []
    monkeypatch.setattr(
        "worker.consumer.process_job", lambda db, job, **kwargs: seen.append(job)
    )
    fake = _FakeRedis([json.dumps({"run_id": "r1"})])

    processed = run_worker_loop(
        redis_client=fake,
        session_factory=lambda: _NoopSession(),
        clickhouse_client=None,
        stop_after=1,
        block_timeout=0,
    )

    assert processed == 1
    assert seen == [{"run_id": "r1"}]


def test_run_worker_loop_discards_invalid_job(monkeypatch):
    called = []
    monkeypatch.setattr(
        "worker.consumer.process_job", lambda db, job, **kwargs: called.append(job)
    )
    fake = _FakeRedis(["not json{"])

    processed = run_worker_loop(
        redis_client=fake,
        session_factory=lambda: _NoopSession(),
        clickhouse_client=None,
        stop_after=1,
        block_timeout=0,
    )

    assert processed == 1
    assert called == []  # invalid job never reached process_job


def test_run_worker_loop_survives_redis_timeout(monkeypatch):
    """A BLPOP socket timeout must not crash the worker; it keeps polling."""
    seen = []
    monkeypatch.setattr(
        "worker.consumer.process_job", lambda db, job, **kwargs: seen.append(job)
    )
    fake = _ScriptedRedis(
        [
            ("raise", redis.exceptions.TimeoutError("Timeout reading from socket")),
            ("return", json.dumps({"run_id": "r1"})),
        ]
    )

    processed = run_worker_loop(
        redis_client=fake,
        session_factory=lambda: _NoopSession(),
        clickhouse_client=None,
        stop_after=1,
        block_timeout=0,
    )

    assert processed == 1
    assert seen == [{"run_id": "r1"}]


def test_run_worker_loop_survives_connection_error(monkeypatch):
    """A transient Redis connection error is retried, not fatal."""
    monkeypatch.setattr("worker.consumer.time.sleep", lambda _s: None)
    seen = []
    monkeypatch.setattr(
        "worker.consumer.process_job", lambda db, job, **kwargs: seen.append(job)
    )
    fake = _ScriptedRedis(
        [
            ("raise", redis.exceptions.ConnectionError("connection refused")),
            ("return", json.dumps({"run_id": "r2"})),
        ]
    )

    processed = run_worker_loop(
        redis_client=fake,
        session_factory=lambda: _NoopSession(),
        clickhouse_client=None,
        stop_after=1,
        block_timeout=0,
    )

    assert processed == 1
    assert seen == [{"run_id": "r2"}]


def test_queue_key_matches_api():
    assert RUN_QUEUE_KEY == "queue:workflow_runs"
