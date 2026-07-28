from __future__ import annotations


def test_security_headers_are_present(client):
    response = client.get("/")

    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )


def test_authentication_pages_are_not_cached(client):
    response = client.get("/admin/sign-in")

    assert response.headers["Cache-Control"] == "no-store"
