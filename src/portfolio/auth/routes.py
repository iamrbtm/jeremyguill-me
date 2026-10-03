from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from portfolio.extensions import limiter

from .services import (
    InvalidBootstrapToken,
    InvalidChallenge,
    InvalidCredential,
    begin_authentication,
    consume_bootstrap_token,
    finish_authentication,
    validate_bootstrap_token,
    verify_password_login,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")


@auth_bp.get("/sign-in")
def sign_in():
    return render_template("auth/sign_in.html")


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def password_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    admin_session = verify_password_login(username, password)
    if admin_session is None:
        return (
            render_template(
                "auth/sign_in.html", error="Invalid username or password."
            ),
            401,
        )
    session.clear()
    session["admin_session_id"] = str(admin_session.id)
    return redirect(url_for("admin.dashboard"))


@auth_bp.get("/bootstrap")
def bootstrap():
    token = request.args.get("token", "")
    return render_template(
        "auth/bootstrap.html", token=token, token_is_valid=validate_bootstrap_token(token)
    )


@auth_bp.post("/bootstrap")
def complete_bootstrap():
    try:
        admin_session = consume_bootstrap_token(request.form.get("token"))
    except InvalidBootstrapToken:
        return render_template("auth/bootstrap.html", token="", token_is_valid=False), 400
    session.clear()
    session["admin_session_id"] = str(admin_session.id)
    return redirect(url_for("admin.dashboard"))


@auth_bp.post("/auth/passkey/begin")
def begin_passkey_authentication():
    challenge_id, options = begin_authentication()
    return jsonify({"challenge_id": str(challenge_id), "options": options})


@auth_bp.post("/auth/passkey/finish")
def finish_passkey_authentication():
    payload = request.get_json(silent=True) or {}
    try:
        challenge_id = uuid.UUID(str(payload.get("challenge_id")))
        admin_session = finish_authentication(payload, challenge_id)
    except (ValueError, InvalidChallenge, InvalidCredential):
        return jsonify({"error": "invalid-passkey-ceremony"}), 400
    session.clear()
    session["admin_session_id"] = str(admin_session.id)
    return "", 204
