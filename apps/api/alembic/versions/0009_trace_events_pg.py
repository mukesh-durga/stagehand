"""trace_events_pg table (ClickHouse fallback for hosted demo mode)

Revision ID: 0009_trace_events_pg
Revises: 0008_usage_events
Create Date: 2026-06-29

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_trace_events_pg"
down_revision: str | None = "0008_usage_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trace_events_pg",
        sa.Column("event_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("latency_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("model_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tool_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    for col in ("run_id", "workflow_id", "timestamp", "event_type", "node_id"):
        op.create_index(f"ix_trace_events_pg_{col}", "trace_events_pg", [col])


def downgrade() -> None:
    for col in ("node_id", "event_type", "timestamp", "workflow_id", "run_id"):
        op.drop_index(f"ix_trace_events_pg_{col}", table_name="trace_events_pg")
    op.drop_table("trace_events_pg")
