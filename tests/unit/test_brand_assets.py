from __future__ import annotations

from pathlib import Path

from PIL import Image

IMG = Path("src/portfolio/static/assets/img")


def test_social_card_is_1200_by_630():
    with Image.open(IMG / "og-default.png") as image:
        assert image.size == (1200, 630)


def test_icons_have_expected_sizes():
    with Image.open(IMG / "favicon-32.png") as small:
        assert small.size == (32, 32)
    with Image.open(IMG / "apple-touch-icon.png") as touch:
        assert touch.size == (180, 180)
    assert (IMG / "favicon.svg").read_text().startswith("<svg")


def test_hero_background_is_webp_and_much_smaller_than_old_jpg():
    assert (IMG / "header-background.webp").stat().st_size < 200_000
    assert (IMG / "header-background-960.webp").stat().st_size < 90_000


def test_head_declares_icons_and_theme_color(client):
    html = client.get("/").get_data(as_text=True)

    assert 'rel="icon"' in html and "favicon.svg" in html
    assert 'rel="apple-touch-icon"' in html
    assert 'name="theme-color"' in html


def test_favicon_ico_route_serves_png(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_homepage_without_portrait_file_renders_no_broken_image(client):
    html = client.get("/").get_data(as_text=True)

    assert "jeremyguill_profile.jpg" not in html
