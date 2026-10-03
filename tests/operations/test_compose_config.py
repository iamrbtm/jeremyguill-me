from __future__ import annotations

from pathlib import Path


def test_compose_keeps_database_private():
    compose = Path("compose.yaml").read_text()

    db_section = compose.split("  db:", 1)[1].split("\n  analytics:", 1)[0]
    assert "ports:" not in db_section


def test_compose_binds_web_to_localhost_only():
    compose = Path("compose.yaml").read_text()

    assert '"127.0.0.1:7777:8000"' in compose


def test_compose_services_are_hardened():
    compose = Path("compose.yaml").read_text()

    assert "read_only: true" in compose
    assert "tmpfs:" in compose
    assert "restart: unless-stopped" in compose
    assert "logging:" in compose
    assert "mem_limit:" in compose


def test_dockerignore_excludes_private_reference_assets():
    dockerignore = Path(".dockerignore").read_text()

    assert "reference" in dockerignore


def test_backup_script_encrypts_and_requires_explicit_restore_confirmation():
    backup = Path("docker/backup.sh").read_text()

    assert "pg_dump --format=custom" in backup
    assert "age" in backup
    assert "RESTORE_CONFIRM" in backup
    assert "Refusing restore" in backup


def test_nginx_config_serves_static_media_and_denies_dotfiles():
    nginx = Path("docker/nginx/jeremyguill.me.conf").read_text()

    assert "proxy_pass http://127.0.0.1:7777" in nginx
    assert "client_max_body_size 15m" in nginx
    assert "location /static/" in nginx
    assert "location /media/" in nginx
    assert "deny all" in nginx


def test_analytics_service_is_private_and_hardened():
    compose = Path("compose.yaml").read_text()
    section = compose.split("  analytics:", 1)[1].split("\n  backup:", 1)[0]

    assert '"127.0.0.1:3001:3000"' in section
    assert "image: ghcr.io/umami-software/umami:postgresql-v2.20.2" in section
    assert "restart: unless-stopped" in section and "mem_limit:" in section
    assert 'profiles: ["analytics"]' in section
    assert "APP_SECRET: ${UMAMI_APP_SECRET:-}" in section
    assert "-ge 32" in section and "exec pnpm start-docker" in section
    assert "DATABASE_URL: postgresql://umami:${UMAMI_DB_PASSWORD:-}@db:5432/umami" in section
    assert "nginx-proxy-manager_default" in section


def test_umami_has_its_own_database_not_the_portfolio_one():
    section = Path("compose.yaml").read_text().split("  analytics:", 1)[1]
    section = section.split("\n  backup:", 1)[0]

    assert "/umami" in section
    assert "/portfolio" not in section
    assert "ports:" in section and "127.0.0.1:3001:3000" in section
