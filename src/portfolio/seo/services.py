from __future__ import annotations

from urllib.parse import urljoin

from flask import current_app
from sqlalchemy import select

from portfolio.content.models import Redirect
from portfolio.extensions import db

from .schemas import PageMetadata, SeoPage

DEFAULT_SOCIAL_IMAGE_PATH = "/static/assets/img/og-default.png"


def build_metadata(page: SeoPage) -> PageMetadata:
    canonical = absolute_url(page.canonical_path)
    return PageMetadata(
        title=page.seo_title or page.title,
        description=page.seo_description or page.summary,
        canonical=canonical,
        robots="index,follow" if page.is_published else "noindex,nofollow",
        open_graph_image=page.social_image_url or absolute_url(DEFAULT_SOCIAL_IMAGE_PATH),
        json_ld=build_json_ld(page),
        og_title=page.seo_title or page.title,
        og_type="article" if page.kind == "blog" else "website",
        extra_json_ld=[breadcrumb_json_ld(page.breadcrumbs)] if page.breadcrumbs else [],
    )


def build_json_ld(page: SeoPage) -> dict[str, object]:
    schema_type = {
        "blog": "BlogPosting",
        "person": "Person",
        "project": "CreativeWork",
    }.get(page.kind, "WebSite")
    data: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": page.name or page.seo_title or page.title,
        "description": page.seo_description or page.summary,
        "url": absolute_url(page.canonical_path),
    }
    data["image"] = page.social_image_url or absolute_url(DEFAULT_SOCIAL_IMAGE_PATH)
    if page.extra:
        data.update(page.extra)
    return data


def breadcrumb_json_ld(crumbs: list[tuple[str, str]]) -> dict[str, object]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute_url(path)}
            for i, (name, path) in enumerate(crumbs, start=1)
        ],
    }


def absolute_url(path: str) -> str:
    origin = current_app.config["PUBLIC_ORIGIN"].rstrip("/") + "/"
    return urljoin(origin, path.lstrip("/"))


def resolve_redirect_chain(path: str) -> str | None:
    current = path
    seen: set[str] = set()
    resolved = False
    while current not in seen:
        seen.add(current)
        redirect = db.session.execute(
            select(Redirect).where(Redirect.old_path == current)
        ).scalar_one_or_none()
        if redirect is None:
            return current if resolved else None
        current = redirect.new_path
        resolved = True
    return current if resolved else None
