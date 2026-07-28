from __future__ import annotations

from flask import Blueprint, Response, render_template
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db
from portfolio.seo.services import absolute_url

seo_bp = Blueprint("seo", __name__)


@seo_bp.get("/sitemap.xml")
def sitemap():
    projects = db.session.execute(
        select(Project)
        .where(Project.state == PublicationState.PUBLISHED)
        .order_by(Project.sort_position, Project.title)
    ).scalars()
    urls = [absolute_url("/"), absolute_url("/experience"), absolute_url("/contact")]
    urls.extend(absolute_url(f"/work/{project.slug}") for project in projects)
    return Response(render_template("sitemap.xml", urls=urls), mimetype="application/xml")


@seo_bp.get("/robots.txt")
def robots():
    return Response(
        render_template("robots.txt", sitemap_url=absolute_url("/sitemap.xml")),
        mimetype="text/plain",
    )
