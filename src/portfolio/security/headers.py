from __future__ import annotations

from flask import Response, current_app, request

from portfolio.security.analytics import analytics_origin

STATIC_HEADERS = {
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

NO_STORE_PREFIXES = ("/admin/sign-in", "/admin/bootstrap", "/admin/auth/")


def content_security_policy(path: str, analytics_origin: str | None) -> str:
    is_admin = path.startswith("/admin")
    script_src = "'self'"
    connect_src = "'self'"
    if is_admin:
        connect_src += " https://api.openai.com"
    elif analytics_origin:
        script_src += f" {analytics_origin}"
        connect_src += f" {analytics_origin}"
    return (
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        f"img-src 'self' data:; font-src 'self'; object-src 'none'; script-src {script_src}; "
        f"style-src 'self'; connect-src {connect_src}"
    )


def _analytics_origin() -> str | None:
    return analytics_origin(
        current_app.config.get("ANALYTICS_SCRIPT_URL"),
        current_app.config.get("ANALYTICS_WEBSITE_ID"),
    )


def apply_security_headers(response: Response) -> Response:
    response.headers.setdefault(
        "Content-Security-Policy", content_security_policy(request.path, _analytics_origin())
    )
    for name, value in STATIC_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.path.startswith(NO_STORE_PREFIXES):
        response.headers["Cache-Control"] = "no-store"
    return response
