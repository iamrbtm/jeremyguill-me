from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_seo_automation"
down_revision = "0003_ai_revision_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("site_profiles", "projects", "blog_posts"):
        op.add_column(table_name, sa.Column("seo_title", sa.String(length=180), nullable=True))
        op.add_column(table_name, sa.Column("seo_description", sa.String(length=320), nullable=True))
        op.add_column(table_name, sa.Column("seo_target_query", sa.String(length=180), nullable=True))
        op.add_column(
            table_name, sa.Column("seo_last_reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_table(
        "seo_automation_settings",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("nvidia_model", sa.String(length=160), nullable=False),
        sa.Column("daily_request_limit", sa.Integer(), nullable=False),
        sa.Column("publish_policy", sa.String(length=40), nullable=False),
        sa.Column("weekly_summary_recipient", sa.String(length=255), nullable=False),
        sa.Column("last_daily_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_weekly_summary_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "seo_target_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=180), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seo_target_queries_entity_id"), "seo_target_queries", ["entity_id"])
    op.create_index(op.f("ix_seo_target_queries_entity_type"), "seo_target_queries", ["entity_type"])
    op.create_index(op.f("ix_seo_target_queries_query"), "seo_target_queries", ["query"])
    op.create_index(op.f("ix_seo_target_queries_state"), "seo_target_queries", ["state"])
    op.create_table(
        "seo_action_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("target_query", sa.String(length=180), nullable=True),
        sa.Column("model", sa.String(length=160), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seo_action_logs_action"), "seo_action_logs", ["action"])
    op.create_index(op.f("ix_seo_action_logs_entity_id"), "seo_action_logs", ["entity_id"])
    op.create_index(op.f("ix_seo_action_logs_entity_type"), "seo_action_logs", ["entity_type"])
    op.create_index(op.f("ix_seo_action_logs_status"), "seo_action_logs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_seo_action_logs_status"), "seo_action_logs")
    op.drop_index(op.f("ix_seo_action_logs_entity_type"), "seo_action_logs")
    op.drop_index(op.f("ix_seo_action_logs_entity_id"), "seo_action_logs")
    op.drop_index(op.f("ix_seo_action_logs_action"), "seo_action_logs")
    op.drop_table("seo_action_logs")
    op.drop_index(op.f("ix_seo_target_queries_state"), "seo_target_queries")
    op.drop_index(op.f("ix_seo_target_queries_query"), "seo_target_queries")
    op.drop_index(op.f("ix_seo_target_queries_entity_type"), "seo_target_queries")
    op.drop_index(op.f("ix_seo_target_queries_entity_id"), "seo_target_queries")
    op.drop_table("seo_target_queries")
    op.drop_table("seo_automation_settings")
    for table_name in ("blog_posts", "projects", "site_profiles"):
        op.drop_column(table_name, "seo_last_reviewed_at")
        op.drop_column(table_name, "seo_target_query")
        op.drop_column(table_name, "seo_description")
        op.drop_column(table_name, "seo_title")
