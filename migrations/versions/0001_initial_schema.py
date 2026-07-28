from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def editable_columns() -> list[sa.Column]:
    return [*timestamps(), sa.Column("version", sa.Integer(), nullable=False)]


def upgrade() -> None:
    publication_state = sa.Enum(
        "DRAFT", "SCHEDULED", "PUBLISHED", "ARCHIVED", name="publicationstate", native_enum=False
    )

    op.create_table(
        "site_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("headline", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=160), nullable=True),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=240), nullable=False),
        sa.Column("storage_key", sa.String(length=240), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("alt_text", sa.String(length=240), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("private", sa.Boolean(), nullable=False),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.String(length=320), nullable=False),
        sa.Column("source_markdown", sa.Text(), nullable=False),
        sa.Column("rendered_html", sa.Text(), nullable=False),
        sa.Column("state", publication_state, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_position", sa.Integer(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("hero_media_id", sa.Uuid(), nullable=True),
        *editable_columns(),
        sa.ForeignKeyConstraint(["hero_media_id"], ["media_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_projects_slug"), "projects", ["slug"])
    op.create_index(op.f("ix_projects_state"), "projects", ["state"])
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.String(length=320), nullable=False),
        sa.Column("source_markdown", sa.Text(), nullable=False),
        sa.Column("rendered_html", sa.Text(), nullable=False),
        sa.Column("state", publication_state, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_blog_posts_slug"), "blog_posts", ["slug"])
    op.create_index(op.f("ix_blog_posts_state"), "blog_posts", ["state"])
    op.create_table(
        "experience_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization", sa.String(length=180), nullable=False),
        sa.Column("role", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("start_date", sa.String(length=40), nullable=True),
        sa.Column("end_date", sa.String(length=40), nullable=True),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("sort_position", sa.Integer(), nullable=False),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "education_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution", sa.String(length=180), nullable=False),
        sa.Column("program", sa.String(length=180), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("sort_position", sa.Integer(), nullable=False),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("issuer", sa.String(length=180), nullable=True),
        sa.Column("issued_at", sa.String(length=40), nullable=True),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("sort_position", sa.Integer(), nullable=False),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "content_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("source_markdown", sa.Text(), nullable=False),
        sa.Column("rendered_html", sa.Text(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_content_revisions_entity_id"), "content_revisions", ["entity_id"])
    op.create_index(op.f("ix_content_revisions_entity_type"), "content_revisions", ["entity_type"])
    op.create_table(
        "redirects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("old_path", sa.String(length=240), nullable=False),
        sa.Column("new_path", sa.String(length=240), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("old_path"),
    )
    op.create_index(op.f("ix_redirects_old_path"), "redirects", ["old_path"])
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("delivery_status", sa.String(length=40), nullable=False),
        sa.Column("delivery_error_code", sa.String(length=80), nullable=True),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "integration_secrets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("encrypted_value", sa.LargeBinary(), nullable=False),
        sa.Column("key_hint", sa.String(length=32), nullable=True),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "passkey_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        *editable_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "entity_type", "entity_id", "state"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    for table_name in (
        "audit_events",
        "jobs",
        "passkey_credentials",
        "integration_secrets",
        "contact_submissions",
        "redirects",
        "content_revisions",
        "credentials",
        "education_entries",
        "experience_entries",
        "blog_posts",
        "projects",
        "media_assets",
        "site_profiles",
    ):
        op.drop_table(table_name)
