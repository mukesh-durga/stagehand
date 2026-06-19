"""initial baseline

Establishes the migration pipeline. No application tables yet (added in
Milestone 2). Ensures the pgcrypto extension is available for UUID generation.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
