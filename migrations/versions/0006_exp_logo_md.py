from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_exp_logo_md"
down_revision = "0005_project_gallery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "experience_entries",
        sa.Column("source_markdown", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "experience_entries",
        sa.Column("rendered_html", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "experience_entries",
        sa.Column("logo_media_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_experience_entries_logo_media_id_media_assets"),
        "experience_entries",
        "media_assets",
        ["logo_media_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_experience_entries_logo_media_id_media_assets"),
        "experience_entries",
        type_="foreignkey",
    )
    op.drop_column("experience_entries", "logo_media_id")
    op.drop_column("experience_entries", "rendered_html")
    op.drop_column("experience_entries", "source_markdown")
