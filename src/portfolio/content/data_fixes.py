"""Idempotent production data fixes, shared by migration 0008 and tests.

Uses Core tables with only the needed columns so it works at any schema revision.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from portfolio.content.rendering import render_markdown

projects = sa.table(
    "projects",
    sa.column("id", sa.Uuid()),
    sa.column("title", sa.String()),
    sa.column("slug", sa.String()),
    sa.column("hero_media_id", sa.Uuid()),
)
blog_posts = sa.table(
    "blog_posts",
    sa.column("id", sa.Uuid()),
    sa.column("title", sa.String()),
    sa.column("slug", sa.String()),
    sa.column("summary", sa.String()),
    sa.column("source_markdown", sa.Text()),
    sa.column("rendered_html", sa.Text()),
)
redirects = sa.table(
    "redirects",
    sa.column("id", sa.Uuid()),
    sa.column("old_path", sa.String()),
    sa.column("new_path", sa.String()),
    sa.column("entity_type", sa.String()),
    sa.column("entity_id", sa.Uuid()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
media_assets = sa.table(
    "media_assets",
    sa.column("id", sa.Uuid()),
    sa.column("alt_text", sa.String()),
)
site_profiles = sa.table(
    "site_profiles",
    sa.column("id", sa.Uuid()),
    sa.column("seo_title", sa.String()),
    sa.column("seo_description", sa.String()),
)

BLOG_SLUG = "why-slapping-a-jet-engine-on-a-unicycle-isnt-a-tech-strategy"
BLOG_SUMMARY = (
    "Software should be the competent, mostly invisible sidekick in your workday, not the main "
    "character. Why digitizing a messy workflow only makes the mess faster, and what to do instead."
)
PROFILE_SEO_TITLE = "Jeremy Guill | Software and Workflow Portfolio"
PROFILE_SEO_DESCRIPTION = (
    "Jeremy Guill builds custom software, database workflows, and automation around real "
    "operational problems, then trains and supports the people who use it."
)


def rename_project_slug(conn: sa.Connection, old: str, new: str) -> int:
    project_id = conn.execute(
        sa.select(projects.c.id).where(projects.c.slug == old)
    ).scalar_one_or_none()
    taken = conn.execute(sa.select(projects.c.id).where(projects.c.slug == new)).first()
    if project_id is None or taken is not None:
        return 0
    conn.execute(sa.update(projects).where(projects.c.id == project_id).values(slug=new))
    now = datetime.now(UTC)
    exists = conn.execute(
        sa.select(redirects.c.id).where(redirects.c.old_path == f"/work/{old}")
    ).first()
    if exists is None:
        conn.execute(
            sa.insert(redirects).values(
                id=uuid.uuid4(),
                old_path=f"/work/{old}",
                new_path=f"/work/{new}",
                entity_type="project",
                entity_id=project_id,
                created_at=now,
                updated_at=now,
            )
        )
    return 1


def fix_blog_post_presentation(conn: sa.Connection) -> int:
    row = conn.execute(
        sa.select(
            blog_posts.c.id,
            blog_posts.c.title,
            blog_posts.c.summary,
            blog_posts.c.source_markdown,
        ).where(blog_posts.c.slug == BLOG_SLUG)
    ).first()
    if row is None:
        return 0
    values: dict[str, str] = {}
    if row.summary.rstrip().endswith("upbeat take"):
        values["summary"] = BLOG_SUMMARY
    first_line, _, rest = row.source_markdown.partition("\n")
    if first_line.strip() == f"# {row.title}":
        source = rest.lstrip("\n")
        values["source_markdown"] = source
        values["rendered_html"] = render_markdown(source)
    if not values:
        return 0
    conn.execute(sa.update(blog_posts).where(blog_posts.c.id == row.id).values(**values))
    return 1


def backfill_project_alt_text(conn: sa.Connection) -> int:
    rows = conn.execute(
        sa.select(projects.c.title, media_assets.c.id, media_assets.c.alt_text).select_from(
            projects.join(media_assets, media_assets.c.id == projects.c.hero_media_id)
        )
    ).all()
    changed = 0
    for row in rows:
        if (row.alt_text or "").strip() in ("", row.title):
            conn.execute(
                sa.update(media_assets)
                .where(media_assets.c.id == row.id)
                .values(alt_text=f"{row.title} project preview")
            )
            changed += 1
    return changed


def refresh_profile_seo(conn: sa.Connection) -> int:
    changed = 0
    for row in conn.execute(
        sa.select(site_profiles.c.id, site_profiles.c.seo_title, site_profiles.c.seo_description)
    ).all():
        values: dict[str, str] = {}
        if (row.seo_title or "") == "Custom Software Development Portfolio":
            values["seo_title"] = PROFILE_SEO_TITLE
        if (row.seo_description or "").startswith("Discover how Jeremy Guill"):
            values["seo_description"] = PROFILE_SEO_DESCRIPTION
        if values:
            conn.execute(
                sa.update(site_profiles).where(site_profiles.c.id == row.id).values(**values)
            )
            changed += 1
    return changed
