from __future__ import annotations

from dataclasses import dataclass, field


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
    name: str | None = None
    extra: dict[str, object] | None = None
    breadcrumbs: list[tuple[str, str]] | None = None


@dataclass(frozen=True)
class PageMetadata:
    title: str
    description: str
    canonical: str
    robots: str
    open_graph_image: str
    json_ld: dict[str, object]
    og_title: str
    og_type: str
    extra_json_ld: list[dict[str, object]] = field(default_factory=list)
