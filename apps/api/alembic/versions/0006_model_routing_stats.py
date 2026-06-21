"""model_routing_stats table

Revision ID: 0006_routing_stats
Revises: 0005_eval_results
Create Date: 2026-06-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_routing_stats"
down_revision: str | None = "0005_eval_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_routing_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("route_key", sa.String(length=512), nullable=False),
        sa.Column("pulls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_reward", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_reward", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("route_key", "model_name", name="uq_routing_route_model"),
    )
    op.create_index("ix_model_routing_stats_workflow_id", "model_routing_stats", ["workflow_id"])
    op.create_index(
        "ix_model_routing_stats_workflow_version_id",
        "model_routing_stats",
        ["workflow_version_id"],
    )
    op.create_index("ix_model_routing_stats_node_id", "model_routing_stats", ["node_id"])
    op.create_index("ix_model_routing_stats_model_name", "model_routing_stats", ["model_name"])
    op.create_index("ix_model_routing_stats_route_key", "model_routing_stats", ["route_key"])


def downgrade() -> None:
    op.drop_index("ix_model_routing_stats_route_key", table_name="model_routing_stats")
    op.drop_index("ix_model_routing_stats_model_name", table_name="model_routing_stats")
    op.drop_index("ix_model_routing_stats_node_id", table_name="model_routing_stats")
    op.drop_index(
        "ix_model_routing_stats_workflow_version_id", table_name="model_routing_stats"
    )
    op.drop_index("ix_model_routing_stats_workflow_id", table_name="model_routing_stats")
    op.drop_table("model_routing_stats")
