from __future__ import annotations

from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_metadata


def _meta(app, **kw):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    with app.app_context():
        return build_metadata(
            SeoPage(
                title="T | Jeremy Guill",
                summary="S",
                canonical_path="/x",
                is_published=True,
                **kw,
            )
        )


def test_social_image_defaults_to_absolute_site_card(app):
    meta = _meta(app)

    assert meta.open_graph_image == "https://example.test/static/assets/img/og-default.png"


def test_person_json_ld_uses_display_name_not_seo_title(app):
    meta = _meta(app, kind="person", seo_title="Custom Software Portfolio", name="Jeremy Guill")

    assert meta.json_ld["@type"] == "Person"
    assert meta.json_ld["name"] == "Jeremy Guill"


def test_blog_pages_use_article_og_type(app):
    assert _meta(app, kind="blog").og_type == "article"
    assert _meta(app).og_type == "website"


def test_homepage_renders_twitter_and_og_tags(client):
    html = client.get("/").get_data(as_text=True)

    assert 'name="twitter:card" content="summary_large_image"' in html
    assert 'property="og:site_name" content="Jeremy Guill"' in html
    assert 'property="og:image" content="' in html
    assert 'property="og:image:width" content="1200"' in html
