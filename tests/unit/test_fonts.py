from __future__ import annotations

from pathlib import Path

ASSETS = Path("src/portfolio/static/assets")


def test_font_files_are_real_woff2():
    for name in ("poppins-600", "poppins-700", "open-sans-var"):
        data = (ASSETS / "fonts" / f"{name}.woff2").read_bytes()
        assert data[:4] == b"wOF2" and len(data) > 5000, name


def test_font_css_declares_faces_with_swap():
    css = (ASSETS / "fonts.css").read_text()

    assert css.count("@font-face") == 3
    assert css.count("font-display: swap") == 3
    assert "https://" not in css


def test_site_css_no_longer_references_geist():
    assert "Geist" not in (ASSETS / "site.css").read_text()


def test_base_template_loads_font_css_and_preloads_body_font(client):
    html = client.get("/").get_data(as_text=True)

    assert "assets/fonts.css" in html
    assert 'rel="preload"' in html and "open-sans-var.woff2" in html
