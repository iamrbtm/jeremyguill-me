from __future__ import annotations

import re

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Experience, Project, SiteProfile
from portfolio.media.models import MediaAsset


def test_homepage_uses_required_headline(client, db_session):
    db_session.add(SiteProfile())
    db_session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"I build practical software for real-world problems." in response.data


def test_blog_navigation_is_hidden_without_published_posts(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'href="/blog"' not in response.data


def test_blog_navigation_shows_with_published_posts(client, db_session):
    db_session.add(
        BlogPost(
            title="Post",
            slug="post",
            summary="Summary",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    response = client.get("/")

    assert b'href="/blog"' in response.data


def test_homepage_does_not_render_experience_entries(client, db_session):
    db_session.add(SiteProfile())
    logo = MediaAsset(
        original_filename="dudefish.png",
        storage_key="test/dudefish.png",
        mime_type="image/png",
        byte_size=1,
        alt_text="Dudefish Printing logo",
        private=False,
    )
    db_session.add(logo)
    db_session.flush()
    db_session.add(
        Experience(
            organization="Dudefish Printing",
            role="Owner Operator",
            start_date="November 2024",
            end_date="Present",
            sort_position=1,
            logo_media_id=logo.id,
        )
    )
    db_session.commit()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="mini-timeline-header"' not in html
    assert 'class="work-card-logo"' not in html
    assert "Owner Operator" not in html
    assert "Dudefish Printing" not in html


def test_experience_page_uses_mini_timeline_layout_with_100px_logo(client, db_session):
    db_session.add(SiteProfile())
    logo = MediaAsset(
        original_filename="dudefish.png",
        storage_key="test/dudefish.png",
        mime_type="image/png",
        byte_size=1,
        alt_text="Dudefish Printing logo",
        private=False,
    )
    db_session.add(logo)
    db_session.flush()
    db_session.add(
        Experience(
            organization="Dudefish Printing",
            role="Owner Operator",
            start_date="November 2024",
            end_date="Present",
            sort_position=1,
            logo_media_id=logo.id,
            summary="Managed business operations and custom software.",
        )
    )
    db_session.commit()

    response = client.get("/experience")
    html = response.get_data(as_text=True)
    header = re.search(r'<header class="mini-timeline-header">(.*?)</header>', html, re.DOTALL)

    assert response.status_code == 200
    assert header is not None
    assert "November 2024 - Present" in header.group(1)
    assert "Owner Operator" in header.group(1)
    assert "Dudefish Printing" in header.group(1)
    assert 'class="mini-timeline-logo"' in header.group(1)
    assert 'height="100"' in header.group(1)


def test_draft_project_is_not_public(client, db_session):
    draft_project = Project(
        title="Draft",
        slug="draft",
        summary="Draft",
        state=PublicationState.DRAFT,
    )
    db_session.add(draft_project)
    db_session.commit()

    assert client.get(f"/work/{draft_project.slug}").status_code == 404


def test_published_project_has_public_page(client, db_session):
    project = Project(
        title="Pollywog",
        slug="pollywog",
        summary="Scheduling automation",
        source_markdown="Replaced a manual process with an automated workflow.",
        rendered_html="<p>Replaced a manual process with an automated workflow.</p>",
        state=PublicationState.PUBLISHED,
    )
    db_session.add(project)
    db_session.commit()

    response = client.get("/work/pollywog")

    assert response.status_code == 200
    assert b"Pollywog" in response.data


def test_work_index_lists_published_projects(client, app):
    from portfolio.content.enums import PublicationState
    from portfolio.content.models import Project, SiteProfile
    from portfolio.extensions import db

    with app.app_context():
        db.session.add(SiteProfile())
        db.session.add(Project(title="Alpha", slug="alpha", summary="a", state=PublicationState.PUBLISHED, sort_position=1))
        db.session.add(Project(title="Beta", slug="beta", summary="b", state=PublicationState.DRAFT, sort_position=0))
        db.session.commit()

    response = client.get("/work")
    assert response.status_code == 200
    assert b"Alpha" in response.data
    assert b"Beta" not in response.data
