from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

_H2 = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class TocItem:
    id: str
    text: str


def _slug(text: str) -> str:
    return _NON_SLUG.sub("-", text.lower()).strip("-") or "section"


def enhance_case_study_html(html: str) -> tuple[str, list[TocItem]]:
    """Add ids to h2 headings, collect a TOC, and make tables scroll on small screens.

    Input is already sanitized by nh3; ids are derived from visible text only.
    """
    items: list[TocItem] = []
    used: set[str] = set()

    def add_id(match: re.Match[str]) -> str:
        text = unescape(_TAG.sub("", match.group(1))).strip()
        base = _slug(text)
        slug, count = base, 2
        while slug in used:
            slug, count = f"{base}-{count}", count + 1
        used.add(slug)
        items.append(TocItem(slug, text))
        return f'<h2 id="{slug}">{match.group(1)}</h2>'

    out = _H2.sub(add_id, html)
    out = out.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )
    return out, items


def reading_minutes(html: str) -> int:
    words = len(unescape(_TAG.sub(" ", html)).split())
    return max(1, round(words / 250))
