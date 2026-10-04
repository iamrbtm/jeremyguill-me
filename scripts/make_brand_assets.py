"""Generate favicon, social card, optimized backgrounds and portrait variants.

uv run python scripts/make_brand_assets.py --fonts DIR [--portrait PHOTO.jpg]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG = Path("src/portfolio/static/assets/img")
INK = (36, 38, 42)
BLUE = (34, 89, 236)
WHITE = (255, 255, 255)
MUTED = (190, 196, 206)

FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#24262a"/>'
    '<text x="32" y="43" text-anchor="middle" font-family="Poppins, Arial, sans-serif" '
    'font-size="28" font-weight="700" fill="#ffffff">JG</text></svg>\n'
)

BACKGROUNDS = (
    (1920, "header-background.webp", 72),
    (960, "header-background-960.webp", 70),
)


def icon(font_path: Path, size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), INK)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), int(size * 0.44))
    draw.text((size / 2, size / 2), "JG", font=font, fill=WHITE, anchor="mm")
    return image


def social_card(bold: Path, regular: Path) -> Image.Image:
    image = Image.new("RGB", (1200, 630), INK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 24, 630), fill=BLUE)
    draw.text((90, 210), "Jeremy Guill", font=ImageFont.truetype(str(bold), 112), fill=WHITE)
    draw.text(
        (94, 355),
        "Practical software for real-world workflows",
        font=ImageFont.truetype(str(regular), 46),
        fill=MUTED,
    )
    draw.text((94, 520), "jeremyguill.me", font=ImageFont.truetype(str(bold), 34), fill=BLUE)
    return image


def _fit_width(image: Image.Image, width: int) -> Image.Image:
    copy = image.copy()
    if copy.width > width:
        height = round(copy.height * width / copy.width)
        copy = copy.resize((width, height), Image.LANCZOS)
    return copy


def webp_background(source: Path) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        for width, name, quality in BACKGROUNDS:
            _fit_width(image, width).save(IMG / name, "WEBP", quality=quality, method=6)


def portrait(source: Path) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        for width, suffix in ((1200, ""), (600, "-600")):
            copy = _fit_width(image, width)
            copy.save(IMG / f"jeremyguill_profile{suffix}.webp", "WEBP", quality=80, method=6)
            print(f"portrait{suffix}: {copy.size}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, required=True)
    parser.add_argument("--portrait", type=Path)
    args = parser.parse_args()
    bold, regular = args.fonts / "Poppins-Bold.ttf", args.fonts / "Poppins-Regular.ttf"
    (IMG / "favicon.svg").write_text(FAVICON_SVG)
    icon(bold, 32).save(IMG / "favicon-32.png")
    icon(bold, 180).save(IMG / "apple-touch-icon.png")
    social_card(bold, regular).save(IMG / "og-default.png", optimize=True)
    jpg = IMG / "header-background.jpg"
    if jpg.exists():
        webp_background(jpg)
    if args.portrait:
        portrait(args.portrait)


if __name__ == "__main__":
    main()
