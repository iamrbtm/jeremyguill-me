from __future__ import annotations

from sqlalchemy import text

from portfolio.extensions import db


def readiness_checks() -> tuple[dict[str, str], bool]:
    checks: dict[str, str] = {}
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "failed"
    else:
        checks["database"] = "ok"
    return checks, all(value == "ok" for value in checks.values())
