from __future__ import annotations

import re

import nh3
from markdown_it import MarkdownIt

ALLOWED_TAGS = {
    "p",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "blockquote",
    "pre",
    "code",
    "a",
    "figure",
    "figcaption",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height", "loading"},
}
RAW_HTML_PATTERN = re.compile(r"<[^>]+>")
UNSAFE_SCHEME_PATTERN = re.compile(r"(?i)\b(?:javascript|data|vbscript):")


def preclean_source(source: str) -> str:
    without_html = RAW_HTML_PATTERN.sub("", source)
    return UNSAFE_SCHEME_PATTERN.sub("", without_html)


def render_markdown(source: str) -> str:
    raw = MarkdownIt("commonmark", {"html": False}).enable("table").render(preclean_source(source))
    return nh3.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"https", "http", "mailto"},
        link_rel="noopener noreferrer",
    )
