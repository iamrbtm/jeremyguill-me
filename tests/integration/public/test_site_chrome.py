from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.public.chrome import SiteChrome


def test_404_page_has_site_navigation_and_one_h1(client):
    response = client.get("/definitely-missing")
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert 'href="/work"' in html
    assert html.count("<h1") == 1
    assert 'class="skip-link"' in html


def test_nav_blog_link_uses_site_chrome(client, db_session):
    assert 'href="/blog"' not in client.get("/").get_data(as_text=True)
    db_session.add(BlogPost(title="P", slug="p", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()

    assert 'href="/blog"' in client.get("/").get_data(as_text=True)


def test_chrome_degrades_when_database_is_unavailable(app, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr("portfolio.public.chrome.db.session.execute", boom)
    with app.app_context():
        chrome = SiteChrome()

        assert chrome.show_blog is False
        assert chrome.profile.display_name == "Jeremy Guill"


def test_resume_and_portrait_flags_reflect_files(app, tmp_path):
    app.static_folder = str(tmp_path)
    (tmp_path / "resume").mkdir()
    with app.app_context():
        assert SiteChrome().has_resume is False
        (tmp_path / "resume" / "Resume2026.pdf").write_bytes(b"%PDF-1.4")
        assert SiteChrome().has_resume is True
