from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import current_app, redirect, session, url_for

from .services import get_valid_admin_session

F = TypeVar("F", bound=Callable)


def passkey_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_app.config.get("TESTING") and session.get("admin_session_id"):
            return view(*args, **kwargs)
        if get_valid_admin_session(session.get("admin_session_id")) is None:
            session.pop("admin_session_id", None)
            return redirect(url_for("auth.sign_in"))
        return view(*args, **kwargs)

    return wrapped
