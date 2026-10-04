from __future__ import annotations

import re

import nh3
from markdown_it import MarkdownIt

ALLOWED_TAGS = {
    "div",
    "p",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "b",
    "em",
    "i",
    "blockquote",
    "pre",
    "code",
    "br",
    "span",
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
    "div": {"class"},
    "img": {"src", "alt", "width", "height", "loading"},
    "li": {"class"},
    "ol": {"class"},
    "p": {"class"},
    "span": {"class"},
    "ul": {"class"},
}
UNSAFE_SCHEME_PATTERN = re.compile(r"(?i)\b(?:javascript|data|vbscript):")


def preclean_source(source: str) -> str:
    return UNSAFE_SCHEME_PATTERN.sub("", source)


def render_markdown(source: str) -> str:
    raw = MarkdownIt("commonmark", {"html": True}).enable("table").render(preclean_source(source))
    return nh3.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"https", "http", "mailto"},
        link_rel="noopener noreferrer",
    )


EXPERIENCE_ALLOWED_TAGS = {
    "p",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "br",
}
EXPERIENCE_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {}


def render_experience_markdown(source: str) -> str:
    raw = MarkdownIt("commonmark", {"html": False, "breaks": True}).render(preclean_source(source))
    return nh3.clean(
        raw,
        tags=EXPERIENCE_ALLOWED_TAGS,
        attributes=EXPERIENCE_ALLOWED_ATTRIBUTES,
        url_schemes={"https", "http", "mailto"},
        link_rel="noopener noreferrer",
    )
