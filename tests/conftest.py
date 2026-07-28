from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config

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
        }
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


@pytest.fixture()
def alembic_config():
    config = Config()
    config.set_main_option("script_location", "migrations")
    return config


@pytest.fixture()
def initial_migration_source():
    return Path("migrations/versions/0001_initial_schema.py").read_text()
