from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeoPage:
    title: str
    summary: str
    canonical_path: str
    is_published: bool
    kind: str = "website"
    seo_title: str | None = None
    seo_description: str | None = None
    social_image_url: str | None = None


@dataclass(frozen=True)
class PageMetadata:
    title: str
    description: str
    canonical: str
    robots: str
    open_graph_image: str | None
    json_ld: dict[str, object]
