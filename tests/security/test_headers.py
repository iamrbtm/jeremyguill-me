from __future__ import annotations

from portfolio.security.headers import content_security_policy


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


def test_public_pages_do_not_allow_openai_connections(client):
    csp = client.get("/").headers["Content-Security-Policy"]

    assert "api.openai.com" not in csp
    assert "connect-src 'self'" in csp


def test_admin_pages_still_allow_openai_connections(client):
    csp = client.get("/admin/sign-in").headers["Content-Security-Policy"]

    assert "https://api.openai.com" in csp


def test_cross_origin_opener_policy_is_set(client):
    assert client.get("/").headers["Cross-Origin-Opener-Policy"] == "same-origin"


def test_analytics_origin_is_added_to_public_script_and_connect_src_only_when_given():
    with_origin = content_security_policy("/", "https://stats.example.test")
    without = content_security_policy("/", None)

    assert "script-src 'self' https://stats.example.test" in with_origin
    assert "connect-src 'self' https://stats.example.test" in with_origin
    assert "stats.example.test" not in without


def test_admin_csp_never_includes_analytics_origin():
    csp = content_security_policy("/admin/projects", "https://stats.example.test")

    assert "stats.example.test" not in csp


def test_csp_never_allows_inline_or_wildcards():
    csp = content_security_policy("/", "https://stats.example.test")

    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp and " * " not in csp
