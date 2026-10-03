from __future__ import annotations

import re
from pathlib import Path

ASSETS = Path("src/portfolio/static/assets")


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lum(rgb: tuple[int, int, int]) -> float:
    channels = []
    for c in rgb:
        s = c / 255
        channels.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(_hex(a)), _lum(_hex(b))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", block))


def _dark_tokens() -> dict[str, str]:
    match = re.search(
        r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{(.*?)\}",
        (ASSETS / "theme.css").read_text(),
        re.DOTALL,
    )
    assert match
    return _tokens(match.group(1))


LIGHT = _tokens((ASSETS / "site.css").read_text().split("}", 1)[0])

PAIRS = [
    ("ink", "paper"),
    ("ink-soft", "paper"),
    ("ink-soft", "gray"),
    ("blue-bright", "paper"),
    ("blue-bright", "gray"),
    ("blue", "paper"),
]


def test_light_theme_meets_wcag_aa():
    for fg, bg in PAIRS:
        assert ratio(LIGHT[fg], LIGHT[bg]) >= 4.5, (fg, bg, LIGHT[fg], LIGHT[bg])


def test_dark_theme_meets_wcag_aa():
    merged = {**LIGHT, **_dark_tokens()}
    for fg, bg in PAIRS:
        assert ratio(merged[fg], merged[bg]) >= 4.5, (fg, bg, merged[fg], merged[bg])


def test_reveal_is_only_hidden_when_js_class_present():
    css = (ASSETS / "site.css").read_text()

    assert re.search(r"\.js \.reveal\s*\{\s*opacity:\s*0", css)
    assert not re.search(r"(^|\n)\.reveal\s*\{[^}]*opacity:\s*0", css)


def test_print_stylesheet_reveals_content_and_hides_chrome():
    css = (ASSETS / "theme.css").read_text()
    print_block = css.split("@media print", 1)[1]

    assert ".site-header" in print_block and "display: none" in print_block
    assert "opacity: 1" in print_block
    assert ".mark-hero, .mark-hero * { color: #000 !important; }" in print_block


def test_theme_is_linked_after_other_styles(client):
    html = client.get("/").get_data(as_text=True)

    assert html.index("components.css") < html.index("theme.css")
