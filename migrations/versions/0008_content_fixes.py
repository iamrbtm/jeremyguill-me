from __future__ import annotations

from alembic import op

from portfolio.content import data_fixes

revision = "0008_content_fixes"
down_revision = "0007_active_job_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    data_fixes.rename_project_slug(conn, "medial-mileage", "medical-mileage")
    data_fixes.fix_blog_post_presentation(conn)
    data_fixes.backfill_project_alt_text(conn)
    data_fixes.refresh_profile_seo(conn)


def downgrade() -> None:
    # Content corrections are intentionally not reverted.
    pass
