from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import redirect, session, url_for

F = TypeVar("F", bound=Callable)


def passkey_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin_session_id" not in session:
            return redirect(url_for("auth.sign_in"))
        return view(*args, **kwargs)

    return wrapped
