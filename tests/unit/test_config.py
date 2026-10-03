from __future__ import annotations

import pytest

from portfolio.config import Settings

SECRET = "x" * 40


def _production(monkeypatch, origin: str | None) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", SECRET)
    if origin is None:
        monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    else:
        monkeypatch.setenv("PUBLIC_ORIGIN", origin)


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "http://localhost:5000",
        "https://localhost",
        "http://127.0.0.1:7777",
        "http://jeremyguill.me",
        "jeremyguill.me",
    ],
)
def test_production_rejects_bad_public_origin(monkeypatch, origin):
    _production(monkeypatch, origin)

    with pytest.raises(RuntimeError, match="PUBLIC_ORIGIN"):
        Settings.from_env()


def test_production_accepts_https_origin(monkeypatch):
    _production(monkeypatch, "https://jeremyguill.me")

    assert Settings.from_env().public_origin == "https://jeremyguill.me"


def test_development_allows_localhost_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://localhost:5000")

    assert Settings.from_env().public_origin == "http://localhost:5000"


def test_analytics_settings_default_to_empty_and_read_env(monkeypatch):
    monkeypatch.delenv("ANALYTICS_SCRIPT_URL", raising=False)
    monkeypatch.delenv("ANALYTICS_WEBSITE_ID", raising=False)
    assert Settings.from_env().analytics_script_url == ""

    monkeypatch.setenv("ANALYTICS_SCRIPT_URL", "https://stats.example.test/script.js")
    monkeypatch.setenv("ANALYTICS_WEBSITE_ID", "abc")
    settings = Settings.from_env()
    assert (settings.analytics_script_url, settings.analytics_website_id) == (
        "https://stats.example.test/script.js",
        "abc",
    )
