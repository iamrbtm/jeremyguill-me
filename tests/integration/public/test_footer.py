from __future__ import annotations

import re

from portfolio.content.models import SiteProfile


def _footer(client):
    html = client.get("/").get_data(as_text=True)
    match = re.search(r'<footer class="site-footer">.*?</footer>', html, re.DOTALL)
    assert match is not None
    return match.group(0)


def test_footer_shows_social_links_when_configured(client, db_session):
    db_session.add(
        SiteProfile(
            linkedin_url="https://www.linkedin.com/in/x", github_url="https://github.com/x"
        )
    )
    db_session.commit()

    footer = _footer(client)

    assert 'href="https://www.linkedin.com/in/x"' in footer and 'rel="noopener' in footer
    assert 'href="https://github.com/x"' in footer


def test_footer_hides_unconfigured_links(client):
    footer = _footer(client)

    assert "linkedin" not in footer.lower() and "github" not in footer.lower()
    assert 'href="/resume"' not in footer


def test_footer_has_copyright_and_site_links(client):
    footer = _footer(client)

    assert "©" in footer and 'href="/work"' in footer and 'href="/contact"' in footer


def test_footer_resume_link_when_pdf_exists(client, app, tmp_path):
    (tmp_path / "resume").mkdir()
    (tmp_path / "resume" / "Resume2026.pdf").write_bytes(b"%PDF-1.4")
    app.static_folder = str(tmp_path)

    assert 'href="/resume"' in _footer(client)


def test_resume_route_404s_without_file_and_serves_pdf_with_it(client, app, tmp_path):
    app.static_folder = str(tmp_path)
    assert client.get("/resume").status_code == 404
    (tmp_path / "resume").mkdir()
    (tmp_path / "resume" / "Resume2026.pdf").write_bytes(b"%PDF-1.4")

    response = client.get("/resume")

    assert response.status_code == 200 and response.mimetype == "application/pdf"
