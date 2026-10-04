from __future__ import annotations

import pytest

from portfolio import create_app
from portfolio.extensions import db


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "PUBLIC_ORIGIN": "https://jeremyguill.me",
        }
    )
    return app


@pytest.fixture()
def client(app):
    with app.app_context():
        db.create_all()
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.session.remove()
        db.drop_all()
