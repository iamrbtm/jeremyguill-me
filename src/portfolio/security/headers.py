from __future__ import annotations

from flask import Response, request

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        "img-src 'self' data:; font-src 'self'; object-src 'none'; script-src 'self'; "
        "style-src 'self'; connect-src 'self' https://integrate.api.nvidia.com"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

NO_STORE_PREFIXES = ("/admin/sign-in", "/admin/bootstrap", "/admin/auth/")


def apply_security_headers(response: Response) -> Response:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.path.startswith(NO_STORE_PREFIXES):
        response.headers["Cache-Control"] = "no-store"
    return response
