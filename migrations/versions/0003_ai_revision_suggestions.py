from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_ai_revision_suggestions"
down_revision = "0002_auth_challenges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_revision_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("suggestion_markdown", sa.Text(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_revision_suggestions_entity_id"),
        "ai_revision_suggestions",
        ["entity_id"],
    )
    op.create_index(
        op.f("ix_ai_revision_suggestions_entity_type"),
        "ai_revision_suggestions",
        ["entity_type"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_revision_suggestions_entity_type"), "ai_revision_suggestions")
    op.drop_index(op.f("ix_ai_revision_suggestions_entity_id"), "ai_revision_suggestions")
    op.drop_table("ai_revision_suggestions")
