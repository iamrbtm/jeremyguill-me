from __future__ import annotations

from collections.abc import Mapping

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
    )
    if config:
        app.config.update(config)

    from .extensions import csrf, db, limiter

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from .public.routes import public_bp

    app.register_blueprint(public_bp)

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
