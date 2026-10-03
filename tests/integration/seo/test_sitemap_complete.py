from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project


def test_sitemap_on_empty_site_is_valid_and_has_core_pages(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"

    body = client.get("/sitemap.xml").get_data(as_text=True)

    assert "<urlset" in body
    for path in ("/", "/work", "/experience", "/contact"):
        assert f"<loc>https://example.test{path}</loc>" in body
    assert "/blog" not in body


def test_sitemap_lists_blog_index_posts_and_lastmod(client, app, db_session):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    db_session.add(
        BlogPost(title="P", slug="p", summary="s", state=PublicationState.PUBLISHED)
    )
    db_session.add(
        Project(title="J", slug="j", summary="s", state=PublicationState.PUBLISHED)
    )
    db_session.add(
        Project(title="D", slug="d", summary="s", state=PublicationState.DRAFT)
    )
    db_session.commit()

    body = client.get("/sitemap.xml").get_data(as_text=True)

    assert "<loc>https://example.test/blog</loc>" in body
    assert "<loc>https://example.test/blog/p</loc>" in body
    assert "<loc>https://example.test/work/j</loc>" in body
    assert "/work/d" not in body
    assert "<lastmod>" in body


def test_robots_points_at_configured_origin(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"

    body = client.get("/robots.txt").get_data(as_text=True)

    assert "Sitemap: https://example.test/sitemap.xml" in body
