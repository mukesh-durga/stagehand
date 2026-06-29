"""Redis job consumer: parse jobs and dispatch them to the orchestrator."""

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

import redis
import redis.exceptions
from sqlalchemy.orm import Session

from worker.clickhouse import ensure_trace_table, get_clickhouse
from worker.config import get_settings
from worker.db import SessionLocal, session_scope
from worker.engine.errors import InvalidJobError
from worker.engine.orchestrator import execute_run
from worker.engine.trace_emitter import TraceEmitter
from worker.models import WorkflowRun

logger = logging.getLogger(__name__)

RUN_QUEUE_KEY = "queue:workflow_runs"

_UNSET = object()


def _build_clickhouse() -> Any | None:
    """Create a ClickHouse client and ensure the trace table exists.

    Returns None when ClickHouse is disabled (CLICKHOUSE_ENABLED=false) or
    unavailable, so the worker still runs without ClickHouse trace persistence.
    """
    if not get_settings().clickhouse_enabled:
        logger.info("ClickHouse disabled (CLICKHOUSE_ENABLED=false); skipping")
        return None
    try:
        client = get_clickhouse()
        ensure_trace_table(client)
        return client
    except Exception:  # noqa: BLE001 - trace storage is optional
        logger.warning("ClickHouse unavailable; trace storage disabled", exc_info=True)
        return None


def parse_job(raw: str) -> dict[str, Any]:
    """Parse and minimally validate a raw Redis job payload."""
    try:
        job = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidJobError(f"Job is not valid JSON: {exc}") from exc
    if not isinstance(job, dict) or "run_id" not in job:
        raise InvalidJobError("Job payload missing 'run_id'.")
    return job


def process_job(
    db: Session,
    job: dict[str, Any],
    *,
    redis_client: Any | None = None,
    clickhouse_client: Any | None = None,
) -> WorkflowRun | None:
    """Load the run referenced by a job and execute it with tracing."""
    run_id = uuid.UUID(str(job["run_id"]))
    run = db.get(WorkflowRun, run_id)
    if run is None:
        logger.warning("run %s not found; skipping job", run_id)
        return None
    emitter = TraceEmitter.from_run(
        run, redis_client=redis_client, clickhouse_client=clickhouse_client
    )
    return execute_run(db, run, job.get("run_config"), emitter=emitter)


def run_worker_loop(
    redis_client: redis.Redis | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
    clickhouse_client: Any = _UNSET,
    *,
    stop_after: int | None = None,
    block_timeout: int = 5,
) -> int:
    """Consume jobs from the queue.

    Runs forever by default. ``stop_after`` bounds the number of loop iterations
    (used by tests). Returns the number of jobs processed.
    """
    if redis_client is None:
        settings = get_settings()
        redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    if clickhouse_client is _UNSET:
        clickhouse_client = _build_clickhouse()

    processed = 0
    while True:
        try:
            item = redis_client.blpop(RUN_QUEUE_KEY, timeout=block_timeout)
        except redis.exceptions.TimeoutError:
            # No job arrived within the BLPOP window — normal when idle. Keep polling.
            logger.debug("BLPOP timed out with no job; continuing to poll")
            continue
        except redis.exceptions.ConnectionError as exc:
            # Redis temporarily unavailable — back off briefly and retry.
            logger.warning("Redis connection error: %s; retrying shortly", exc)
            time.sleep(min(max(block_timeout, 1), 5))
            continue

        if item is None:
            if stop_after is not None:
                break
            continue

        _, raw = item
        try:
            job = parse_job(raw)
        except InvalidJobError as exc:
            logger.warning("discarding invalid job: %s", exc)
            processed += 1
            if stop_after is not None and processed >= stop_after:
                break
            continue

        try:
            with session_scope(session_factory) as db:
                process_job(
                    db,
                    job,
                    redis_client=redis_client,
                    clickhouse_client=clickhouse_client,
                )
        except Exception:  # noqa: BLE001 - keep the worker alive across jobs
            logger.exception("failed to process job %s", job.get("run_id"))

        processed += 1
        if stop_after is not None and processed >= stop_after:
            break

    return processed
