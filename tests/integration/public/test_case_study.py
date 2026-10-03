from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project


def _add(db_session, slug, position, html="<h2>A</h2><h2>B</h2><h2>C</h2><p>x</p>", **kw):
    project = Project(
        title=slug.title(),
        slug=slug,
        summary="Sum.",
        rendered_html=html,
        state=PublicationState.PUBLISHED,
        sort_position=position,
        **kw,
    )
    db_session.add(project)
    return project


def test_case_study_has_glance_toc_breadcrumb_and_single_h1(client, db_session):
    _add(db_session, "one", 1, role="Creator", stack="Flask, SQL", year="2025",
         result_headline="Faster")
    db_session.commit()

    html = client.get("/work/one").get_data(as_text=True)

    assert html.count("<h1") == 1
    assert 'aria-label="Breadcrumb"' in html and 'href="/work"' in html
    assert "Creator" in html and "Flask" in html and "2025" in html and "Faster" in html
    assert 'aria-label="On this page"' in html and 'href="#a"' in html
    assert "min read" in html


def test_case_study_without_glance_or_headings_omits_those_blocks(client, db_session):
    _add(db_session, "bare", 1, html="<p>Just text.</p>")
    db_session.commit()

    html = client.get("/work/bare").get_data(as_text=True)

    assert 'class="glance"' not in html and 'aria-label="On this page"' not in html


def test_previous_and_next_project_links(client, db_session):
    for index, slug in enumerate(("a", "b", "c"), start=1):
        _add(db_session, slug, index)
    db_session.commit()

    middle = client.get("/work/b").get_data(as_text=True)
    first = client.get("/work/a").get_data(as_text=True)

    assert 'href="/work/a"' in middle and 'href="/work/c"' in middle
    assert 'rel="prev"' not in first and 'rel="next"' in first


def test_case_study_ends_with_call_to_action(client, db_session):
    _add(db_session, "one", 1)
    db_session.commit()

    page = client.get("/work/one").get_data(as_text=True)
    assert 'href="/contact"' in page.split("</article>")[1]


def test_hero_serves_desktop_variant_only(client, db_session):
    from portfolio.media.models import MediaAsset

    asset = MediaAsset(original_filename="a.png", storage_key="k/a", mime_type="image/png",
                       byte_size=1, alt_text="Alt", private=False)
    db_session.add(asset)
    db_session.flush()
    _add(db_session, "one", 1, hero_media_id=asset.id)
    db_session.commit()

    page = client.get("/work/one").get_data(as_text=True)
    tag = page[page.index('<img class="project-hero"'):].split(">")[0]

    assert "srcset" not in tag and "sizes=" not in tag
    assert f"/media/public/{asset.id}/hero_desktop.webp" in tag
    assert "hero_mobile" not in page


def test_project_missing_from_published_list_has_no_pager(client, db_session, monkeypatch):
    _add(db_session, "one", 1)
    _add(db_session, "two", 2)
    db_session.commit()
    monkeypatch.setattr("portfolio.public.routes.published_projects", lambda: [])

    response = client.get("/work/one")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'rel="prev"' not in html and 'rel="next"' not in html
