from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_profile_project_fields"
down_revision = "0008_content_fixes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_profiles", sa.Column("linkedin_url", sa.String(300), nullable=True))
    op.add_column("site_profiles", sa.Column("github_url", sa.String(300), nullable=True))
    op.add_column("site_profiles", sa.Column("availability_text", sa.String(240), nullable=True))
    op.add_column("projects", sa.Column("role", sa.String(120), nullable=True))
    op.add_column("projects", sa.Column("stack", sa.String(240), nullable=True))
    op.add_column("projects", sa.Column("year", sa.String(20), nullable=True))
    op.add_column("projects", sa.Column("result_headline", sa.String(240), nullable=True))


def downgrade() -> None:
    for column in ("result_headline", "year", "stack", "role"):
        op.drop_column("projects", column)
    for column in ("availability_text", "github_url", "linkedin_url"):
        op.drop_column("site_profiles", column)
