"""PostgreSQL trace-event fallback model.

Used when ClickHouse is disabled (hosted demo / free-tier mode). Mirrors the
ClickHouse ``trace_events`` schema field-for-field so the TraceStore abstraction
can read/write traces from either backend transparently.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class TraceEventPg(Base):
    """A single trace event stored in PostgreSQL (ClickHouse fallback)."""

    __tablename__ = "trace_events_pg"

    # The engine generates a UUID event_id per event; use it as the primary key.
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    latency_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_trace_events_pg_run_id", "run_id"),
        Index("ix_trace_events_pg_workflow_id", "workflow_id"),
        Index("ix_trace_events_pg_timestamp", "timestamp"),
        Index("ix_trace_events_pg_event_type", "event_type"),
        Index("ix_trace_events_pg_node_id", "node_id"),
    )
