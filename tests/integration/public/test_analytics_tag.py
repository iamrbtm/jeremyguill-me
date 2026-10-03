from __future__ import annotations

import re

SITE_ID = "11111111-2222-3333-4444-555555555555"
SCRIPT = "https://stats.example.test/script.js"


def _configure(app, url=SCRIPT, site_id=SITE_ID):
    app.config["ANALYTICS_SCRIPT_URL"] = url
    app.config["ANALYTICS_WEBSITE_ID"] = site_id


def _csp(client, path="/"):
    return client.get(path).headers["Content-Security-Policy"]


def test_no_tag_when_unconfigured(client):
    assert "data-website-id" not in client.get("/").get_data(as_text=True)


def test_tag_rendered_when_configured_and_honours_do_not_track(client, app):
    _configure(app)

    html = client.get("/").get_data(as_text=True)

    assert re.search(
        r'<script defer src="https://stats\.example\.test/script\.js" '
        r'data-website-id="11111111-2222-3333-4444-555555555555"',
        html,
    )
    assert 'data-do-not-track="true"' in html


def test_tag_requires_both_settings(client, app):
    app.config["ANALYTICS_SCRIPT_URL"] = SCRIPT

    assert "data-website-id" not in client.get("/").get_data(as_text=True)


def test_non_https_script_url_is_ignored(client, app):
    _configure(app, url="http://stats.example.test/script.js")

    assert "data-website-id" not in client.get("/").get_data(as_text=True)
    assert "stats.example.test" not in _csp(client)


def test_userinfo_script_url_is_ignored(client, app):
    _configure(app, url="https://user:pw@stats.example.test/script.js")

    assert "stats.example.test" not in _csp(client)
    assert "data-website-id" not in client.get("/").get_data(as_text=True)


def test_csp_allows_only_the_analytics_origin(client, app):
    _configure(app)

    csp = _csp(client)

    assert "script-src 'self' https://stats.example.test" in csp
    assert "https://stats.example.test/script.js" not in csp


def test_csp_preserves_port(client, app):
    _configure(app, url="https://stats.example.test:8443/script.js")

    assert "script-src 'self' https://stats.example.test:8443" in _csp(client)


def test_csp_unchanged_when_website_id_missing(client, app):
    baseline = _csp(client)
    _configure(app, site_id="")

    assert _csp(client) == baseline
    assert "stats.example.test" not in _csp(client)


def test_admin_pages_never_load_tracker(client, app):
    _configure(app)

    response = client.get("/admin/sign-in")

    assert "data-website-id" not in response.get_data(as_text=True)
    assert "stats.example.test" not in response.headers["Content-Security-Policy"]


def test_cta_events_are_declared(client):
    html = client.get("/").get_data(as_text=True)

    assert 'data-umami-event="cta-view-work"' in html
    assert 'data-umami-event="cta-connect-hero"' in html


def test_bad_port_means_no_tag_and_closed_csp(client, app):
    baseline = _csp(client)
    for url in ("https://stats.example.test:abc/s.js", "https://stats.example.test:99999/s.js"):
        _configure(app, url=url)

        assert "data-website-id" not in client.get("/").get_data(as_text=True)
        assert _csp(client) == baseline


def test_ipv6_origin_renders_tag_and_csp(client, app):
    _configure(app, url="https://[::1]:8443/s.js")

    assert "data-website-id" in client.get("/").get_data(as_text=True)
    assert "script-src 'self' https://[::1]:8443" in _csp(client)


import pytest  # noqa: E402


@pytest.mark.parametrize(
    ("url", "site_id", "origin"),
    [
        (SCRIPT, SITE_ID, "https://stats.example.test"),
        ("http://stats.example.test/s.js", SITE_ID, "http://stats.example.test"),
        ("https://u:p@stats.example.test/s.js", SITE_ID, "stats.example.test"),
        (SCRIPT, "", "stats.example.test"),
        ("https://stats.example.test:abc/s.js", SITE_ID, "stats.example.test"),
        ("https://[::1]:8443/s.js", SITE_ID, "https://[::1]:8443"),
    ],
)
def test_tag_present_iff_origin_in_csp(client, app, url, site_id, origin):
    _configure(app, url=url, site_id=site_id)

    tag = "data-website-id" in client.get("/").get_data(as_text=True)
    in_csp = f"script-src 'self' {origin}" in _csp(client)

    assert tag == in_csp
