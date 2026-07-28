from __future__ import annotations

import pytest

from portfolio import create_app


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
        }
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
