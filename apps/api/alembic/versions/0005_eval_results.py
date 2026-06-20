"""eval_results table

Revision ID: 0005_eval_results
Revises: 0004_run_replay
Create Date: 2026-06-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_eval_results"
down_revision: str | None = "0004_run_replay"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eval_type", sa.String(length=64), nullable=False),
        sa.Column("success_score", sa.Float(), nullable=False),
        sa.Column("tool_correctness_score", sa.Float(), nullable=True),
        sa.Column("format_score", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("cost_score", sa.Float(), nullable=True),
        sa.Column("latency_score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workflow_version_id"], ["workflow_versions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_eval_results_run_id", "eval_results", ["run_id"])
    op.create_index("ix_eval_results_workflow_id", "eval_results", ["workflow_id"])
    op.create_index(
        "ix_eval_results_workflow_version_id", "eval_results", ["workflow_version_id"]
    )
    op.create_index("ix_eval_results_eval_type", "eval_results", ["eval_type"])
    op.create_index("ix_eval_results_created_at", "eval_results", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_created_at", table_name="eval_results")
    op.drop_index("ix_eval_results_eval_type", table_name="eval_results")
    op.drop_index("ix_eval_results_workflow_version_id", table_name="eval_results")
    op.drop_index("ix_eval_results_workflow_id", table_name="eval_results")
    op.drop_index("ix_eval_results_run_id", table_name="eval_results")
    op.drop_table("eval_results")
