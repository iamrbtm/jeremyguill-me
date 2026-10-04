from __future__ import annotations

import pytest

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project, Redirect
from portfolio.extensions import db


@pytest.fixture()
def published_project(db_session):
    project = Project(
        title="Published Project",
        slug="published-project",
        summary="Published summary",
        source_markdown="Body",
        rendered_html="<p>Body</p>",
        state=PublicationState.PUBLISHED,
        featured=True,
    )
    db.session.add(project)
    db.session.commit()
    return project


def test_project_canonical_uses_public_origin(client, app, published_project):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"

    response = client.get(f"/work/{published_project.slug}")

    assert response.status_code == 200
    assert (
        f'<link rel="canonical" href="https://jeremyguill.me/work/{published_project.slug}">'
        in response.text
    )


def test_old_slug_redirects_permanently(client, db_session):
    redirect = Redirect(old_path="/work/old", new_path="/work/new")
    db.session.add(redirect)
    db.session.commit()

    response = client.get("/work/old")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/work/new")


def test_redirect_chains_collapse_to_one_hop(client, db_session):
    db.session.add_all(
        [
            Redirect(old_path="/work/old", new_path="/work/middle"),
            Redirect(old_path="/work/middle", new_path="/work/final"),
        ]
    )
    db.session.commit()

    response = client.get("/work/old")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/work/final")


def test_sitemap_includes_only_published_canonical_projects(
    client, app, db_session, published_project
):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"
    draft = Project(title="Draft", slug="draft", summary="", state=PublicationState.DRAFT)
    db.session.add(draft)
    db.session.commit()

    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "https://jeremyguill.me/" in response.text
    assert f"https://jeremyguill.me/work/{published_project.slug}" in response.text
    assert "https://jeremyguill.me/work/draft" not in response.text


def test_robots_txt_points_to_sitemap(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://jeremyguill.me"

    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Sitemap: https://jeremyguill.me/sitemap.xml" in response.text
