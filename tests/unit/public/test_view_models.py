from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile
from portfolio.public.view_models import build_home_view


def test_build_home_view_exposes_only_published_featured_projects(app, db_session):
    published = Project(
        title="Published",
        slug="published",
        summary="Published summary",
        state=PublicationState.PUBLISHED,
        featured=True,
    )
    draft = Project(
        title="Draft",
        slug="draft",
        summary="Draft summary",
        state=PublicationState.DRAFT,
        featured=True,
    )
    db_session.add_all([SiteProfile(), published, draft])
    db_session.commit()

    with app.app_context():
        view = build_home_view()

    assert [project.slug for project in view.home_projects] == ["published"]


def test_build_home_view_hides_empty_blog(app, db_session):
    db_session.add(SiteProfile())
    db_session.commit()

    with app.app_context():
        view = build_home_view()

    assert view.show_blog is False


def test_build_home_view_shows_published_blog(app, db_session):
    db_session.add(SiteProfile())
    db_session.add(
        BlogPost(title="Post", slug="post", summary="Summary", state=PublicationState.PUBLISHED)
    )
    db_session.commit()

    with app.app_context():
        view = build_home_view()

    assert view.show_blog is True


def test_home_shows_first_three_ordered_projects(app, db_session):
    db_session.add(SiteProfile())
    for index, slug in enumerate(["c", "a", "b", "d", "e"]):
        db_session.add(
            Project(
                title=slug,
                slug=slug,
                summary=f"{slug} summary",
                state=PublicationState.PUBLISHED,
                sort_position=index,
            )
        )
    db_session.commit()

    with app.app_context():
        view = build_home_view()

    slugs = [project.slug for project in view.home_projects]
    assert slugs == ["c", "a", "b"]
    assert view.has_more_projects is True


def test_home_hides_more_button_when_three_or_fewer(app, db_session):
    db_session.add(SiteProfile())
    for slug in ["a", "b"]:
        db_session.add(
            Project(
                title=slug,
                slug=slug,
                summary=f"{slug} summary",
                state=PublicationState.PUBLISHED,
                sort_position=0,
            )
        )
    db_session.commit()

    with app.app_context():
        view = build_home_view()

    assert view.has_more_projects is False
