from __future__ import annotations

import re


def test_css_link_carries_content_hash(client):
    html = client.get("/").get_data(as_text=True)

    assert re.search(r'href="/static/assets/site\.css\?v=[0-9a-f]{10}"', html)


def test_hashed_static_urls_are_immutable_forever(client):
    html = client.get("/").get_data(as_text=True)
    href = re.search(r'href="(/static/assets/site\.css\?v=[0-9a-f]{10})"', html).group(1)

    assert "immutable" in client.get(href).headers["Cache-Control"]
    assert "max-age=31536000" in client.get(href).headers["Cache-Control"]


def test_unhashed_static_urls_get_short_cache(client):
    cache = client.get("/static/assets/site.css").headers["Cache-Control"]

    assert "max-age=3600" in cache
    assert "immutable" not in cache


def test_html_pages_are_not_given_long_cache(client):
    assert "max-age=31536000" not in client.get("/").headers.get("Cache-Control", "")


def test_static_url_for_missing_file_does_not_crash(app):
    from portfolio.assets import static_url

    with app.test_request_context():
        assert static_url("assets/nope.css") == "/static/assets/nope.css"
