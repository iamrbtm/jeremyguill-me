from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_project_gallery"
down_revision = "0004_seo_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_gallery_items",
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "media_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("media_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("project_id", "media_id"),
    )


def downgrade() -> None:
    op.drop_table("project_gallery_items")
