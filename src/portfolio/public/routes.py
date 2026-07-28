from flask import Blueprint, jsonify

public_bp = Blueprint("public", __name__)


@public_bp.route("/health/live")
def liveness():
    return jsonify({"status": "ok"})
