from __future__ import annotations

from alembic.script import ScriptDirectory


def test_migration_chain_head_is_latest(alembic_config):
    script = ScriptDirectory.from_config(alembic_config)
    assert script.get_current_head() == "0003_ai_revision_suggestions"


def test_initial_migration_declares_required_tables(initial_migration_source):
    required_tables = {
        "site_profiles",
        "projects",
        "blog_posts",
        "experience_entries",
        "education_entries",
        "credentials",
        "media_assets",
        "contact_submissions",
        "integration_secrets",
        "passkey_credentials",
        "content_revisions",
        "redirects",
        "jobs",
        "audit_events",
    }

    for table_name in required_tables:
        assert table_name in initial_migration_source
