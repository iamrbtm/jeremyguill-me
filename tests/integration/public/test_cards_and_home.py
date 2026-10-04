from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile
from portfolio.media.models import MediaAsset
from portfolio.public.view_models import build_project_cards


def _project(**kw):
    defaults = dict(title="P", slug="p", summary="Does a thing.", state=PublicationState.PUBLISHED)
    defaults.update(kw)
    return Project(**defaults)


def _asset(alt_text: str) -> MediaAsset:
    return MediaAsset(
        original_filename="a.png",
        storage_key="k/a",
        mime_type="image/png",
        byte_size=1,
        alt_text=alt_text,
        private=False,
    )


def test_card_without_hero_stack_or_year_renders_cleanly(client, db_session):
    db_session.add(SiteProfile())
    db_session.add(_project())
    db_session.commit()

    html = client.get("/").get_data(as_text=True)

    assert 'href="/work/p"' in html and "Does a thing." in html
    assert 'class="tag-list"' not in html
    assert "<img" not in html.split('id="work"')[1].split("</section>")[0]


def test_card_shows_stack_tags_year_result_and_alt_from_media(client, db_session):
    asset = _asset("Dashboard of trips")
    db_session.add_all([SiteProfile(), asset])
    db_session.flush()
    db_session.add(
        _project(
            stack="Flask, SQL",
            year="2025",
            result_headline="4h to 30m",
            hero_media_id=asset.id,
        )
    )
    db_session.commit()

    html = client.get("/").get_data(as_text=True)

    assert 'alt="Dashboard of trips"' in html
    assert "<li>Flask</li>" in html and "<li>SQL</li>" in html
    assert "2025" in html and "4h to 30m" in html


def test_build_project_cards_falls_back_to_title_alt(db_session):
    asset = _asset("")
    db_session.add(asset)
    db_session.flush()
    db_session.add(_project(hero_media_id=asset.id))
    db_session.commit()

    cards = build_project_cards(db_session.query(Project).all())

    assert cards[0].hero_alt == "P project preview"


def test_work_index_shows_thumbnails_like_home(client, db_session):
    asset = _asset("Alt")
    db_session.add(asset)
    db_session.flush()
    db_session.add(_project(hero_media_id=asset.id))
    db_session.commit()

    html = client.get("/work").get_data(as_text=True)

    assert f"/media/public/{asset.id}/hero_desktop.webp" in html and 'width="' in html


def test_latest_writing_hidden_until_three_posts(client, db_session):
    for index in range(2):
        db_session.add(
            BlogPost(
                title=f"T{index}", slug=f"t{index}", summary="s", state=PublicationState.PUBLISHED
            )
        )
    db_session.commit()
    assert 'id="writing"' not in client.get("/").get_data(as_text=True)

    db_session.add(BlogPost(title="T3", slug="t3", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()
    assert 'id="writing"' in client.get("/").get_data(as_text=True)


def test_availability_statement_and_single_h1(client, db_session):
    db_session.add(
        SiteProfile(availability_text="Open to full-time roles and select contract projects.")
    )
    db_session.commit()

    html = client.get("/").get_data(as_text=True)

    assert "Open to full-time roles and select contract projects." in html
    assert html.count("<h1") == 1


def test_homepage_has_no_testimonial_blockquote_attributed_to_owner(client):
    assert "<blockquote" not in client.get("/").get_data(as_text=True)


def test_empty_site_home_and_work_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/work").status_code == 200


def test_card_img_has_no_srcset_and_media_link_is_aria_hidden(client, db_session):
    asset = _asset("Alt")
    db_session.add_all([SiteProfile(), asset])
    db_session.flush()
    db_session.add(_project(hero_media_id=asset.id))
    db_session.commit()

    html = client.get("/").get_data(as_text=True)
    work = html.split('id="work"')[1].split("</section>")[0]

    assert "srcset" not in work and "hero_mobile" not in work
    assert f"/media/public/{asset.id}/hero_desktop.webp" in work
    assert 'class="project-card2__media" href="/work/p" aria-hidden="true" tabindex="-1"' in work


def _published_project(db_session, slug):
    from portfolio.content.enums import PublicationState
    from portfolio.content.models import Project

    db_session.add(
        Project(
            title=slug.title(), slug=slug, summary="S.", rendered_html="<p>x</p>",
            state=PublicationState.PUBLISHED, sort_position=1,
        )
    )
    db_session.commit()


def test_work_cards_use_h2_so_heading_order_is_valid(client, db_session):
    _published_project(db_session, "alpha")

    html = client.get("/work").get_data(as_text=True)

    assert html.count("<h1") == 1 and "<h3" not in html
    assert '<h2><a href="/work/alpha">Alpha</a></h2>' in html


def test_home_cards_stay_h3(client, db_session):
    _published_project(db_session, "alpha")

    html = client.get("/").get_data(as_text=True)

    assert '<h3><a href="/work/alpha">Alpha</a></h3>' in html


def test_experience_roles_are_h2_with_one_h1(client, db_session):
    from portfolio.content.models import Experience

    db_session.add(Experience(organization="Org", role="Builder", start_date="2024",
                              sort_position=1))
    db_session.commit()

    html = client.get("/experience").get_data(as_text=True)

    assert html.count("<h1") == 1 and "<h2>Builder</h2>" in html and "<h3" not in html
