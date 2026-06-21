"""templates table

Revision ID: 0007_templates
Revises: 0006_routing_stats
Create Date: 2026-06-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_templates"
down_revision: str | None = "0006_routing_stats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column(
            "tags", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("graph_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "is_public", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
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
    )
    op.create_index("ix_templates_slug", "templates", ["slug"], unique=True)
    op.create_index("ix_templates_category", "templates", ["category"])
    op.create_index("ix_templates_is_public", "templates", ["is_public"])
    op.create_index("ix_templates_created_at", "templates", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_templates_created_at", table_name="templates")
    op.drop_index("ix_templates_is_public", table_name="templates")
    op.drop_index("ix_templates_category", table_name="templates")
    op.drop_index("ix_templates_slug", table_name="templates")
    op.drop_table("templates")
