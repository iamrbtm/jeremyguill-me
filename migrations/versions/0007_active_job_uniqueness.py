from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_active_job_uniqueness"
down_revision = "0006_exp_logo_md"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("jobs_kind_entity_type_entity_id_state_key", "jobs", type_="unique")
    op.create_index(
        "uq_jobs_active_kind_entity",
        "jobs",
        ["kind", "entity_type", "entity_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('pending', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_jobs_active_kind_entity", table_name="jobs")
    op.create_unique_constraint(
        "jobs_kind_entity_type_entity_id_state_key",
        "jobs",
        ["kind", "entity_type", "entity_id", "state"],
    )
