from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from flask import Blueprint, Response, render_template
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project
from portfolio.extensions import db
from portfolio.seo.services import absolute_url

seo_bp = Blueprint("seo", __name__)


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: datetime | None = None


@seo_bp.get("/sitemap.xml")
def sitemap():
    projects = list(
        db.session.execute(
            select(Project)
            .where(Project.state == PublicationState.PUBLISHED)
            .order_by(Project.sort_position, Project.title)
        ).scalars()
    )
    posts = list(
        db.session.execute(
            select(BlogPost)
            .where(BlogPost.state == PublicationState.PUBLISHED)
            .order_by(BlogPost.published_at.desc(), BlogPost.title)
        ).scalars()
    )
    entries = [
        SitemapEntry(absolute_url(path)) for path in ("/", "/work", "/experience", "/contact")
    ]
    if posts:
        entries.append(SitemapEntry(absolute_url("/blog"), max(p.updated_at for p in posts)))
    entries.extend(SitemapEntry(absolute_url(f"/work/{p.slug}"), p.updated_at) for p in projects)
    entries.extend(SitemapEntry(absolute_url(f"/blog/{p.slug}"), p.updated_at) for p in posts)
    return Response(render_template("sitemap.xml", entries=entries), mimetype="application/xml")


@seo_bp.get("/robots.txt")
def robots():
    return Response(
        render_template("robots.txt", sitemap_url=absolute_url("/sitemap.xml")),
        mimetype="text/plain",
    )


def _rfc822(value: datetime) -> str:
    # SQLite returns naive datetimes; Postgres returns aware ones.
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return format_datetime(value)


@seo_bp.get("/rss.xml")
def rss():
    posts = list(
        db.session.execute(
            select(BlogPost)
            .where(BlogPost.state == PublicationState.PUBLISHED)
            .order_by(BlogPost.published_at.desc(), BlogPost.title)
            .limit(20)
        ).scalars()
    )
    items = [
        {
            "title": p.title,
            "link": absolute_url(f"/blog/{p.slug}"),
            "summary": p.summary,
            "date": _rfc822(p.published_at or p.updated_at),
        }
        for p in posts
    ]
    return Response(
        render_template(
            "rss.xml",
            items=items,
            site_url=absolute_url("/"),
            feed_url=absolute_url("/rss.xml"),
        ),
        mimetype="application/rss+xml",
    )


@seo_bp.get("/.well-known/security.txt")
def security_txt():
    expires = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = (
        f"Contact: {absolute_url('/contact')}\n"
        f"Expires: {expires}\n"
        f"Canonical: {absolute_url('/.well-known/security.txt')}\n"
        "Preferred-Languages: en\n"
    )
    return Response(body, mimetype="text/plain")
