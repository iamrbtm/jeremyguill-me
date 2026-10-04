from __future__ import annotations

import pytest

from portfolio.extensions import db


def test_readiness_reports_database_success(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready", "checks": {"database": "ok"}}


def test_readiness_reports_database_failure(client, monkeypatch: pytest.MonkeyPatch):
    def broken_execute(*args, **kwargs):
        raise RuntimeError("password=super-secret database down")

    monkeypatch.setattr(db.session, "execute", broken_execute)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.get_json() == {"status": "not-ready", "checks": {"database": "failed"}}


def test_readiness_does_not_expose_exception_text(client, monkeypatch: pytest.MonkeyPatch):
    def broken_execute(*args, **kwargs):
        raise RuntimeError("password=super-secret database down")

    monkeypatch.setattr(db.session, "execute", broken_execute)

    response = client.get("/health/ready")

    assert "password" not in response.text.lower()
    assert "super-secret" not in response.text
