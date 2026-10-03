from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, SiteProfile


def _make_post(title, slug, state, summary="Summary", body="Body"):
    return BlogPost(
        title=title,
        slug=slug,
        summary=summary,
        source_markdown=body,
        rendered_html=f"<p>{body}</p>",
        state=state,
    )


def test_homepage_shows_published_blog_posts(client, db_session):
    db_session.add(SiteProfile())
    db_session.add(_make_post("Published One", "one", PublicationState.PUBLISHED))
    db_session.add(_make_post("Draft Hidden", "draft", PublicationState.DRAFT))
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Latest writing" in response.data
    assert b"Published One" in response.data
    assert b"Draft Hidden" not in response.data
    assert b'href="/blog/one"' in response.data


def test_homepage_blog_section_absent_without_posts(client, db_session):
    db_session.add(SiteProfile())
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Latest writing" not in response.data


def test_blog_index_lists_only_published(client, db_session):
    db_session.add(_make_post("Published One", "one", PublicationState.PUBLISHED))
    db_session.add(_make_post("Draft Hidden", "draft", PublicationState.DRAFT))
    db_session.commit()

    response = client.get("/blog")

    assert response.status_code == 200
    assert b"Published One" in response.data
    assert b"Draft Hidden" not in response.data


def test_blog_detail_404_for_draft_and_200_for_published(client, db_session):
    db_session.add(_make_post("Published One", "one", PublicationState.PUBLISHED))
    db_session.add(_make_post("Draft Hidden", "draft", PublicationState.DRAFT))
    db_session.commit()

    assert client.get("/blog/one").status_code == 200
    assert client.get("/blog/draft").status_code == 404


def test_blog_detail_uses_seo_fields(client, db_session):
    db_session.add(
        BlogPost(
            title="SEO Post",
            slug="seo-post",
            summary="Summary",
            source_markdown="Body",
            rendered_html="<p>Body</p>",
            state=PublicationState.PUBLISHED,
            seo_title="Custom SEO Title",
            seo_description="Custom SEO description",
        )
    )
    db_session.commit()

    response = client.get("/blog/seo-post")

    assert response.status_code == 200
    assert b"Custom SEO Title" in response.data
    assert b"Custom SEO description" in response.data
