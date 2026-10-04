from __future__ import annotations

from sqlalchemy import select

from portfolio.content import data_fixes
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, Redirect, SiteProfile
from portfolio.extensions import db
from portfolio.media.models import MediaAsset


def _conn():
    return db.session.connection()


def test_rename_slug_creates_redirect_and_is_idempotent(db_session):
    db_session.add(
        Project(
            title="Medical Mileage",
            slug="medial-mileage",
            summary="s",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    assert data_fixes.rename_project_slug(_conn(), "medial-mileage", "medical-mileage") == 1
    assert data_fixes.rename_project_slug(_conn(), "medial-mileage", "medical-mileage") == 0
    db_session.expire_all()

    assert db_session.scalar(select(Project.slug)) == "medical-mileage"
    redirect = db_session.scalar(select(Redirect))
    assert (redirect.old_path, redirect.new_path) == (
        "/work/medial-mileage",
        "/work/medical-mileage",
    )


def test_rename_slug_skips_when_target_exists(db_session):
    db_session.add_all(
        [
            Project(title="A", slug="old", summary="s", state=PublicationState.PUBLISHED),
            Project(title="B", slug="new", summary="s", state=PublicationState.PUBLISHED),
        ]
    )
    db_session.commit()

    assert data_fixes.rename_project_slug(_conn(), "old", "new") == 0


def test_old_slug_redirects_with_308(client, db_session):
    db_session.add(
        Project(
            title="Medical Mileage",
            slug="medial-mileage",
            summary="s",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()
    data_fixes.rename_project_slug(_conn(), "medial-mileage", "medical-mileage")
    db_session.commit()

    response = client.get("/work/medial-mileage?utm=x")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/work/medical-mileage")


def test_blog_fix_rewrites_truncated_summary_and_strips_duplicate_h1(db_session):
    db_session.add(
        BlogPost(
            title="Why Slapping a Jet Engine on a Unicycle Isn’t a Tech Strategy",
            slug="why-slapping-a-jet-engine-on-a-unicycle-isnt-a-tech-strategy",
            summary="Intro. Read on for a fresh, upbeat take",
            source_markdown=(
                "# Why Slapping a Jet Engine on a Unicycle Isn’t a Tech Strategy\n\nHello, world!"
            ),
            rendered_html=(
                "<p>Why Slapping a Jet Engine on a Unicycle Isn’t a Tech StrategyHello</p>"
            ),
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    assert data_fixes.fix_blog_post_presentation(_conn()) == 1
    assert data_fixes.fix_blog_post_presentation(_conn()) == 0
    db_session.expire_all()
    post = db_session.scalar(select(BlogPost))

    assert not post.summary.endswith("upbeat take")
    assert len(post.summary) <= 320
    assert post.source_markdown.startswith("Hello, world!")
    assert "Hello, world!" in post.rendered_html
    assert "Unicycle Isn’t a Tech StrategyHello" not in post.rendered_html


def test_alt_text_backfill_only_fills_blank_or_title_only_alts(db_session):
    blank = MediaAsset(
        original_filename="a.png",
        storage_key="k/a",
        mime_type="image/png",
        byte_size=1,
        alt_text="",
        private=False,
    )
    titled = MediaAsset(
        original_filename="b.png",
        storage_key="k/b",
        mime_type="image/png",
        byte_size=1,
        alt_text="Career Groove",
        private=False,
    )
    custom = MediaAsset(
        original_filename="c.png",
        storage_key="k/c",
        mime_type="image/png",
        byte_size=1,
        alt_text="Dashboard showing five jobs",
        private=False,
    )
    db_session.add_all([blank, titled, custom])
    db_session.flush()
    db_session.add_all(
        [
            Project(
                title="One",
                slug="one",
                summary="s",
                state=PublicationState.PUBLISHED,
                hero_media_id=blank.id,
            ),
            Project(
                title="Career Groove",
                slug="cg",
                summary="s",
                state=PublicationState.PUBLISHED,
                hero_media_id=titled.id,
            ),
            Project(
                title="Three",
                slug="three",
                summary="s",
                state=PublicationState.PUBLISHED,
                hero_media_id=custom.id,
            ),
        ]
    )
    db_session.commit()

    assert data_fixes.backfill_project_alt_text(_conn()) == 2
    db_session.expire_all()
    alts = {a.original_filename: a.alt_text for a in db_session.scalars(select(MediaAsset))}

    assert alts["a.png"] == "One project preview"
    assert alts["b.png"] == "Career Groove project preview"
    assert alts["c.png"] == "Dashboard showing five jobs"


def test_profile_seo_refresh_only_replaces_known_generic_text(db_session):
    db_session.add(
        SiteProfile(
            seo_title="Custom Software Development Portfolio",
            seo_description=(
                "Discover how Jeremy Guill specializes in custom software. "
                "Our portfolio showcases our expertise."
            ),
        )
    )
    db_session.commit()

    assert data_fixes.refresh_profile_seo(_conn()) == 1
    db_session.expire_all()
    profile = db_session.scalar(select(SiteProfile))

    assert profile.seo_title == "Jeremy Guill | Software and Workflow Portfolio"
    assert "Our portfolio" not in profile.seo_description
    assert data_fixes.refresh_profile_seo(_conn()) == 0
