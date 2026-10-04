from __future__ import annotations

from flask import Blueprint, jsonify

from .services import readiness_checks

operations_bp = Blueprint("operations", __name__)


@operations_bp.get("/health/ready")
def readiness():
    checks, ready = readiness_checks()
    status_code = 200 if ready else 503
    status = "ready" if ready else "not-ready"
    return jsonify({"status": status, "checks": checks}), status_code
