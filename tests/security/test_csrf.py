from __future__ import annotations

from portfolio import create_app
from portfolio.extensions import db


def test_contact_post_requires_csrf_when_enabled():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "WTF_CSRF_ENABLED": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
        }
    )
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        response = client.post("/contact", data={})

    assert response.status_code == 400
