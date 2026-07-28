from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from .services import (
    InvalidChallenge,
    InvalidCredential,
    begin_authentication,
    finish_authentication,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")


@auth_bp.get("/sign-in")
def sign_in():
    return render_template("auth/sign_in.html")


@auth_bp.get("/bootstrap")
def bootstrap():
    return render_template("auth/bootstrap.html")


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


@auth_bp.get("")
def admin_root():
    if "admin_session_id" not in session:
        return redirect(url_for("auth.sign_in"))
    return render_template("admin/security.html")
