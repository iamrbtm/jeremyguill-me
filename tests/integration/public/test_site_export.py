from __future__ import annotations

import json

from portfolio.content.enums import PublicationState
from portfolio.content.models import Experience, Project, ProjectGalleryItem, SiteProfile
from portfolio.media.models import MediaAsset

ORIGIN = "https://example.test"


def _asset(alt_text: str = "") -> MediaAsset:
    return MediaAsset(
        original_filename="a.png",
        storage_key=f"k/{alt_text or 'blank'}",
        mime_type="image/png",
        byte_size=1,
        alt_text=alt_text,
        private=False,
    )


def _get(app, client):
    app.config["PUBLIC_ORIGIN"] = ORIGIN
    return client.get("/api/site-content.json")


def test_empty_site_export_has_all_keys(app, client):
    response = _get(app, client)

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.headers["Cache-Control"] == "public, max-age=300"
    data = response.get_json()
    assert set(data) == {
        "generated_at",
        "origin",
        "profile",
        "capabilities",
        "projects",
        "experience",
    }
    assert data["origin"] == ORIGIN
    assert data["projects"] == [] and data["experience"] == []
    assert data["profile"]["display_name"]
    assert "email" not in data["profile"]
    assert len(data["capabilities"]) == 3


def test_published_project_fields(app, client, db_session):
    asset = _asset("Dashboard")
    db_session.add(asset)
    db_session.flush()
    db_session.add(
        Project(
            title="Pollywog",
            slug="pollywog",
            summary="Sum",
            role="Dev",
            stack="Flask, SQL",
            year="2024",
            result_headline="Saved hours",
            rendered_html="<p>Body</p>",
            state=PublicationState.PUBLISHED,
            hero_media_id=asset.id,
        )
    )
    db_session.commit()

    project = _get(app, client).get_json()["projects"][0]

    assert project["slug"] == "pollywog"
    assert project["role"] == "Dev" and project["year"] == "2024"
    assert project["result_headline"] == "Saved hours"
    assert project["stack"] == ["Flask", "SQL"]
    assert project["body_html"] == "<p>Body</p>"
    assert project["url"] == f"{ORIGIN}/work/pollywog"
    assert project["hero"] == {
        "url": f"{ORIGIN}/media/public/{asset.id}/hero_desktop.webp",
        "alt": "Dashboard",
        "width": 1600,
        "height": 900,
    }
    assert project["gallery"] == []


def test_gallery_items_are_exported(app, client, db_session):
    asset = _asset("Shot")
    project = Project(title="G", slug="g", summary="s", state=PublicationState.PUBLISHED)
    db_session.add_all([asset, project])
    db_session.flush()
    db_session.add(ProjectGalleryItem(project_id=project.id, media_id=asset.id, position=0))
    db_session.commit()

    gallery = _get(app, client).get_json()["projects"][0]["gallery"]

    assert gallery == [
        {
            "url": f"{ORIGIN}/media/public/{asset.id}/hero_desktop.webp",
            "alt": "Shot",
            "width": 1600,
            "height": 900,
        }
    ]


def test_drafts_and_hidden_experience_are_excluded(app, client, db_session):
    db_session.add_all(
        [
            Project(title="Live", slug="live", summary="s", state=PublicationState.PUBLISHED),
            Project(title="Draft", slug="draft", summary="s", state=PublicationState.DRAFT),
            Experience(organization="Shown", role="r", summary="s", visible=True),
            Experience(organization="Hidden", role="r", summary="s", visible=False),
        ]
    )
    db_session.commit()

    data = _get(app, client).get_json()

    assert [p["slug"] for p in data["projects"]] == ["live"]
    assert [e["organization"] for e in data["experience"]] == ["Shown"]


def test_email_is_never_exported(app, client, db_session):
    db_session.add(SiteProfile(email="secret@example.test"))
    db_session.commit()

    text = _get(app, client).get_data(as_text=True)

    assert "secret@example.test" not in text
    assert '"email"' not in text


def test_missing_hero_and_blank_alt_fallback(app, client, db_session):
    asset = _asset("")
    db_session.add(asset)
    db_session.flush()
    db_session.add_all(
        [
            Project(
                title="NoHero",
                slug="a-nohero",
                summary="s",
                state=PublicationState.PUBLISHED,
                sort_position=1,
            ),
            Project(
                title="Blank",
                slug="b-blank",
                summary="s",
                state=PublicationState.PUBLISHED,
                sort_position=2,
                hero_media_id=asset.id,
            ),
        ]
    )
    db_session.commit()

    projects = _get(app, client).get_json()["projects"]

    assert projects[0]["hero"] is None
    assert projects[1]["hero"]["alt"] == "Blank project preview"


def test_experience_logo(app, client, db_session):
    asset = _asset("x")
    db_session.add(asset)
    db_session.flush()
    db_session.add_all(
        [
            Experience(
                organization="Acme",
                role="Dev",
                summary="s",
                start_date="2020",
                logo_media_id=asset.id,
                sort_position=1,
            ),
            Experience(organization="Plain", role="Dev", summary="s", sort_position=2),
        ]
    )
    db_session.commit()

    first, second = _get(app, client).get_json()["experience"]

    assert first["logo"]["url"] == f"{ORIGIN}/media/public/{asset.id}/profile.webp"
    assert first["logo"]["alt"] == "Acme logo"
    assert (first["logo"]["width"], first["logo"]["height"]) == (100, 100)
    assert first["start_date"] == "2020"
    assert second["logo"] is None


def test_cors_only_on_font_files(app, client):
    font = client.get("/static/assets/fonts/open-sans-var.woff2")
    assert font.headers["Access-Control-Allow-Origin"] == "*"

    etag = font.headers.get("ETag")
    if etag:
        cached = client.get(
            "/static/assets/fonts/open-sans-var.woff2", headers={"If-None-Match": etag}
        )
        assert cached.status_code == 304
        assert cached.headers["Access-Control-Allow-Origin"] == "*"

    assert "Access-Control-Allow-Origin" not in client.get("/").headers
    assert "Access-Control-Allow-Origin" not in client.get("/api/site-content.json").headers
    assert "Access-Control-Allow-Origin" not in client.get("/static/assets/site.css").headers


def test_cli_export_matches_route(app, client, db_session):
    db_session.add(Project(title="L", slug="l", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()
    expected = _get(app, client).get_json()

    result = app.test_cli_runner().invoke(args=["content", "export-site"])

    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    expected.pop("generated_at")
    actual.pop("generated_at")
    assert actual == expected
