from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from importlib import import_module

from flask import Flask

from .config import Settings


def create_app(config: Mapping[str, object] | None = None) -> Flask:
    settings = Settings.from_env()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.secret_key,
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        PUBLIC_ORIGIN=settings.public_origin,
        WEBAUTHN_RP_ID=settings.rp_id,
        RATELIMIT_STORAGE_URI=settings.rate_limit_storage_uri,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=settings.app_env == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    )
    if config:
        app.config.update(config)

    from .extensions import csrf, db, limiter, migrate

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    import_models()

    from .auth.routes import auth_bp
    from .public.routes import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)

    from .auth.cli import admin_cli

    app.cli.add_command(admin_cli)

    register_error_handlers(app)

    return app


def register_error_handlers(app: Flask) -> None:
    from flask import render_template

    @app.errorhandler(404)
    def not_found(_error: object):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error: object):
        return render_template("errors/500.html"), 500


def import_models() -> None:
    for module_name in (
        "portfolio.audit.models",
        "portfolio.auth.models",
        "portfolio.contact.models",
        "portfolio.content.models",
        "portfolio.integrations.models",
        "portfolio.jobs.models",
        "portfolio.media.models",
    ):
        import_module(module_name)
