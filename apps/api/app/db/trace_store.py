"""Trace storage abstraction.

A single ``TraceStore`` interface backed by either ClickHouse (full local/cloud
stack) or PostgreSQL (free-tier hosted demo, when ClickHouse is disabled). All
read paths (trace timeline, diff, eval, usage backfill) and the hosted-demo
executor go through this so they work regardless of the configured backend.

Read contract: ``get_events_by_run_id`` returns rows as tuples in ``TRACE_COLUMNS``
order, with ``metadata_json`` as a JSON **string** — matching what the ClickHouse
read path already produced, so existing row-handling code is unchanged.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.clickhouse import (
    TRACE_COLUMNS,
    ensure_trace_table,
    query_run_trace_events,
)
from app.db.models.trace import TraceEventPg

TRACE_TABLE = "trace_events"


@dataclass
class TraceRecord:
    """A normalized trace event accepted by every TraceStore."""

    event_id: str
    run_id: str
    workflow_id: str
    workflow_version_id: str
    event_type: str
    status: str
    timestamp: datetime
    node_id: str = ""
    latency_ms: int = 0
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_name: str = ""
    retry_count: int = 0
    error_message: str = ""
    metadata_json: dict[str, Any] = field(default_factory=dict)


def _naive_utc(ts: datetime) -> datetime:
    return ts.astimezone(timezone.utc).replace(tzinfo=None) if ts.tzinfo else ts


class TraceStore(ABC):
    """Interface for inserting and reading trace events."""

    @abstractmethod
    def ensure_ready(self) -> None:
        """Idempotently ensure the backing table exists."""

    @abstractmethod
    def insert_event(self, event: TraceRecord) -> None: ...

    @abstractmethod
    def insert_events(self, events: list[TraceRecord]) -> None: ...

    @abstractmethod
    def get_events_by_run_id(self, run_id: uuid.UUID | str) -> list[tuple[Any, ...]]:
        """Return rows in TRACE_COLUMNS order, metadata_json as a JSON string."""


class ClickHouseTraceStore(TraceStore):
    def __init__(self, client: Any) -> None:
        self._client = client

    def ensure_ready(self) -> None:
        ensure_trace_table(self._client)

    def _row(self, e: TraceRecord) -> list[Any]:
        return [
            e.event_id,
            e.run_id,
            e.workflow_id,
            e.workflow_version_id,
            e.node_id,
            e.event_type,
            e.status,
            _naive_utc(e.timestamp),
            int(e.latency_ms),
            e.model_name,
            int(e.input_tokens),
            int(e.output_tokens),
            float(e.estimated_cost_usd),
            e.tool_name,
            int(e.retry_count),
            e.error_message,
            json.dumps(e.metadata_json or {}),
        ]

    def insert_event(self, event: TraceRecord) -> None:
        self.insert_events([event])

    def insert_events(self, events: list[TraceRecord]) -> None:
        if not events:
            return
        self._client.insert(
            TRACE_TABLE, [self._row(e) for e in events], column_names=TRACE_COLUMNS
        )

    def get_events_by_run_id(self, run_id: uuid.UUID | str) -> list[tuple[Any, ...]]:
        return query_run_trace_events(self._client, str(run_id))


class PostgresTraceStore(TraceStore):
    def __init__(self, db: Session) -> None:
        self._db = db

    def ensure_ready(self) -> None:
        # The table is created by Alembic migrations; nothing to do at runtime.
        return None

    def insert_event(self, event: TraceRecord) -> None:
        self.insert_events([event])

    def insert_events(self, events: list[TraceRecord]) -> None:
        if not events:
            return
        for e in events:
            self._db.add(
                TraceEventPg(
                    event_id=e.event_id,
                    run_id=uuid.UUID(str(e.run_id)),
                    workflow_id=uuid.UUID(str(e.workflow_id)),
                    workflow_version_id=uuid.UUID(str(e.workflow_version_id)),
                    node_id=e.node_id or "",
                    event_type=e.event_type,
                    status=e.status or "",
                    timestamp=e.timestamp,
                    latency_ms=int(e.latency_ms),
                    model_name=e.model_name or "",
                    input_tokens=int(e.input_tokens),
                    output_tokens=int(e.output_tokens),
                    estimated_cost_usd=float(e.estimated_cost_usd),
                    tool_name=e.tool_name or "",
                    retry_count=int(e.retry_count),
                    error_message=e.error_message or "",
                    metadata_json=e.metadata_json or {},
                )
            )
        self._db.commit()

    def get_events_by_run_id(self, run_id: uuid.UUID | str) -> list[tuple[Any, ...]]:
        rid = run_id if isinstance(run_id, uuid.UUID) else uuid.UUID(str(run_id))
        rows = self._db.scalars(
            select(TraceEventPg)
            .where(TraceEventPg.run_id == rid)
            .order_by(TraceEventPg.timestamp.asc())
        ).all()
        # Emit metadata_json as a JSON string to match the ClickHouse read contract.
        return [
            (
                r.event_id,
                str(r.run_id),
                str(r.workflow_id),
                str(r.workflow_version_id),
                r.node_id,
                r.event_type,
                r.status,
                r.timestamp,
                int(r.latency_ms),
                r.model_name,
                int(r.input_tokens),
                int(r.output_tokens),
                float(r.estimated_cost_usd),
                r.tool_name,
                int(r.retry_count),
                r.error_message,
                json.dumps(r.metadata_json or {}),
            )
            for r in rows
        ]


def make_trace_store(db: Session, clickhouse_client: Any | None = None) -> TraceStore:
    """Build the TraceStore for the current configuration.

    Postgres when ClickHouse is disabled or TRACE_STORAGE=postgres; otherwise
    ClickHouse (lazily constructing a client unless one is supplied).
    """
    from app.config import get_settings

    settings = get_settings()
    if settings.use_postgres_traces:
        return PostgresTraceStore(db)
    if clickhouse_client is None:
        from app.db.clickhouse import get_clickhouse

        clickhouse_client = get_clickhouse()
    return ClickHouseTraceStore(clickhouse_client)
