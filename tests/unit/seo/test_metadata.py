from __future__ import annotations

from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_json_ld, build_metadata


def test_metadata_uses_public_origin_and_published_robots(app):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"
    with app.app_context():
        metadata = build_metadata(
            SeoPage(
                title="Project",
                summary="Summary",
                canonical_path="/work/project",
                is_published=True,
            )
        )

    assert metadata.canonical == "https://jeremyguill.me/work/project"
    assert metadata.robots == "index,follow"


def test_metadata_noindexes_unpublished_pages(app):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"
    with app.app_context():
        metadata = build_metadata(
            SeoPage(
                title="Draft",
                summary="Draft summary",
                canonical_path="/work/draft",
                is_published=False,
            )
        )

    assert metadata.robots == "noindex,nofollow"


def test_json_ld_builds_creative_work_for_project(app):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"
    with app.app_context():
        data = build_json_ld(
            SeoPage(
                title="Project",
                summary="Summary",
                canonical_path="/work/project",
                is_published=True,
                kind="project",
            )
        )

    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "CreativeWork"
    assert data["url"] == "https://jeremyguill.me/work/project"


def test_metadata_prefers_explicit_seo_fields(app):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"
    with app.app_context():
        metadata = build_metadata(
            SeoPage(
                title="Title",
                summary="Summary",
                canonical_path="/",
                is_published=True,
                seo_title="SEO Title",
                seo_description="SEO Description",
            )
        )

    assert metadata.title == "SEO Title"
    assert metadata.description == "SEO Description"
