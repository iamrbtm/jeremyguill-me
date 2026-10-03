from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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
