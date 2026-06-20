"""add replay relationship to workflow_runs

Revision ID: 0004_run_replay
Revises: 0003_workflow_runs
Create Date: 2026-06-19

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_run_replay"
down_revision: str | None = "0003_workflow_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = "fk_workflow_runs_replay_of_run_id"
_IX = "ix_workflow_runs_replay_of_run_id"


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("replay_of_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        _FK,
        "workflow_runs",
        "workflow_runs",
        ["replay_of_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(_IX, "workflow_runs", ["replay_of_run_id"])


def downgrade() -> None:
    op.drop_index(_IX, table_name="workflow_runs")
    op.drop_constraint(_FK, "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "replay_of_run_id")
