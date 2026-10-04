from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flask import current_app
from sqlalchemy import select

from portfolio.content.models import Experience, Project
from portfolio.extensions import db
from portfolio.media.models import MediaAsset
from portfolio.public.view_models import (
    build_project_cards,
    default_capabilities,
    get_profile,
    published_projects,
)
from portfolio.seo.services import absolute_url

DEFAULT_NAME = "Jeremy Guill"
HERO_SIZE = (1600, 900)
LOGO_SIZE = (100, 100)


def _image(media_id: uuid.UUID, variant: str, alt: str, size: tuple[int, int]) -> dict[str, object]:
    return {
        "url": absolute_url(f"/media/public/{media_id}/{variant}.webp"),
        "alt": alt,
        "width": size[0],
        "height": size[1],
    }


def _project(project: Project, hero_alt: str) -> dict[str, object]:
    hero = None
    if project.hero_media_id:
        hero = _image(project.hero_media_id, "hero_desktop", hero_alt, HERO_SIZE)
    fallback = f"{project.title} project preview"
    gallery = [
        _image(asset.id, "hero_desktop", asset.alt_text or fallback, HERO_SIZE)
        for asset in project.gallery_assets()
        if isinstance(asset, MediaAsset)
    ]
    return {
        "slug": project.slug,
        "title": project.title,
        "summary": project.summary,
        "role": project.role,
        "stack": project.stack_list,
        "year": project.year,
        "result_headline": project.result_headline,
        "body_html": project.rendered_html,
        "url": absolute_url(f"/work/{project.slug}"),
        "hero": hero,
        "gallery": gallery,
    }


def _experience(item: Experience) -> dict[str, object]:
    logo = None
    if item.logo_media_id:
        logo = _image(item.logo_media_id, "profile", f"{item.organization} logo", LOGO_SIZE)
    return {
        "organization": item.organization,
        "role": item.role,
        "start_date": item.start_date,
        "end_date": item.end_date,
        "summary": item.summary,
        "body_html": item.rendered_html,
        "logo": logo,
    }


def build_site_export() -> dict[str, object]:
    profile = get_profile()
    projects = published_projects()
    cards = {card.slug: card.hero_alt for card in build_project_cards(projects)}
    experience = (
        db.session.execute(
            select(Experience)
            .where(Experience.visible.is_(True))
            .order_by(Experience.sort_position)
        )
        .scalars()
        .all()
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "origin": current_app.config["PUBLIC_ORIGIN"].rstrip("/"),
        "profile": {
            "display_name": profile.display_name or DEFAULT_NAME,
            "headline": profile.headline or "",
            "summary": profile.summary or "",
            "location": profile.location,
            "availability_text": profile.availability_text,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
        },
        "capabilities": [{"title": c.title, "body": c.body} for c in default_capabilities()],
        "projects": [_project(p, cards[p.slug]) for p in projects],
        "experience": [_experience(e) for e in experience],
    }
