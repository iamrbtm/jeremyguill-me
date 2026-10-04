from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile

LD_PATTERN = r'<script type="application/ld\+json">(.*?)</script>'


def _ld(html: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(LD_PATTERN, html, re.DOTALL)]


def test_person_json_ld_has_same_as_when_links_configured(client, db_session):
    db_session.add(
        SiteProfile(
            linkedin_url="https://www.linkedin.com/in/x", github_url="https://github.com/x"
        )
    )
    db_session.commit()

    person = _ld(client.get("/").get_data(as_text=True))[0]

    assert person["@type"] == "Person" and person["name"] == "Jeremy Guill"
    assert person["sameAs"] == ["https://www.linkedin.com/in/x", "https://github.com/x"]


def test_person_json_ld_omits_same_as_when_none(client):
    assert "sameAs" not in _ld(client.get("/").get_data(as_text=True))[0]


def test_project_page_emits_breadcrumb_list(client, db_session):
    db_session.add(Project(title="One", slug="one", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()

    blocks = _ld(client.get("/work/one").get_data(as_text=True))
    crumbs = next(b for b in blocks if b["@type"] == "BreadcrumbList")

    assert [i["name"] for i in crumbs["itemListElement"]] == ["Home", "Work", "One"]


def test_blog_post_json_ld_has_dates_and_author(client, db_session):
    db_session.add(
        BlogPost(
            title="P",
            slug="p",
            summary="s",
            state=PublicationState.PUBLISHED,
            published_at=datetime(2026, 5, 1, tzinfo=UTC),
        )
    )
    db_session.commit()

    post = _ld(client.get("/blog/p").get_data(as_text=True))[0]

    assert post["@type"] == "BlogPosting" and post["datePublished"].startswith("2026-05-01")
    assert post["author"]["name"] == "Jeremy Guill"


def test_rss_is_valid_on_empty_site_and_lists_posts(client, db_session, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    empty = client.get("/rss.xml")
    assert empty.status_code == 200 and empty.mimetype == "application/rss+xml"
    assert "<item>" not in empty.get_data(as_text=True)

    db_session.add(
        BlogPost(
            title="Hello & <World>", slug="p", summary="s", state=PublicationState.PUBLISHED
        )
    )
    db_session.commit()
    body = client.get("/rss.xml").get_data(as_text=True)

    assert "<link>https://example.test/blog/p</link>" in body
    assert "Hello &amp; &lt;World&gt;" in body


def test_pages_advertise_rss_feed(client):
    assert 'rel="alternate" type="application/rss+xml"' in client.get("/").get_data(as_text=True)


def test_security_txt(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    response = client.get("/.well-known/security.txt")
    body = response.get_data(as_text=True)

    assert response.mimetype == "text/plain"
    assert "Contact: https://example.test/contact" in body and "Expires: " in body
    assert "Canonical: https://example.test/.well-known/security.txt" in body


def test_security_txt_expires_is_within_a_year(client):
    from datetime import UTC, datetime, timedelta

    body = client.get("/.well-known/security.txt").get_data(as_text=True)
    value = next(line for line in body.splitlines() if line.startswith("Expires: "))[9:]
    expires = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    now = datetime.now(UTC)

    assert now < expires < now + timedelta(days=365)


def test_project_title_uses_seo_title_when_set(client, db_session):
    db_session.add(
        Project(
            title="One",
            slug="one",
            summary="s",
            seo_title="One: a descriptor | Jeremy Guill",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    html = client.get("/work/one").get_data(as_text=True)

    assert "<title>One: a descriptor | Jeremy Guill</title>" in html


def test_json_ld_cannot_break_out_of_script_tag(client, db_session):
    db_session.add(
        Project(
            title="</script><script>alert(1)",
            slug="x",
            summary="s",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    html = client.get("/work/x").get_data(as_text=True)

    assert "</script><script>alert(1)" not in html
