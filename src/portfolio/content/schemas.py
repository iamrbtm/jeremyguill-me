from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentCommand:
    title: str
    summary: str
    source_markdown: str
    slug: str | None = None
