from __future__ import annotations

from pathlib import Path


def test_compose_keeps_database_private():
    compose = Path("compose.yaml").read_text()

    db_section = compose.split("  db:", 1)[1].split("  backup:", 1)[0]
    assert "ports:" not in db_section


def test_compose_binds_web_to_localhost_only():
    compose = Path("compose.yaml").read_text()

    assert '"127.0.0.1:7777:8000"' in compose


def test_dockerignore_excludes_private_reference_assets():
    dockerignore = Path(".dockerignore").read_text()

    assert "reference" in dockerignore
