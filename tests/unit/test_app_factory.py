from __future__ import annotations

import pytest

from portfolio import create_app
from portfolio.config import Settings


def test_create_app_uses_testing_overrides():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only"})
    assert app.testing is True


def test_rate_limit_storage_is_explicit():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only"})
    assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"


def test_liveness_endpoint(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_production_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings.from_env()
