from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, send_from_directory
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.extensions import db
from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_metadata

blog_bp = Blueprint("blog", __name__)


@blog_bp.get("/blog")
def index():
    posts = db.session.execute(
        select(BlogPost)
        .where(BlogPost.state == PublicationState.PUBLISHED)
        .order_by(BlogPost.published_at.desc(), BlogPost.title)
    ).scalars()
    metadata = build_metadata(
        SeoPage(
            title="Blog | Jeremy Guill",
            summary="Notes from Jeremy Guill on practical software and workflow systems.",
            canonical_path="/blog",
            is_published=True,
            kind="blog",
        )
    )
    return render_template(
        "public/blog_index.html", posts=list(posts), metadata=metadata
    )


@blog_bp.get("/blog/<slug>")
def detail(slug: str):
    post = db.session.execute(
        select(BlogPost).where(BlogPost.slug == slug, BlogPost.state == PublicationState.PUBLISHED)
    ).scalar_one_or_none()
    if post is None:
        abort(404)
    extra: dict[str, object] = {"author": {"@type": "Person", "name": "Jeremy Guill"}}
    if post.published_at:
        extra["datePublished"] = post.published_at.isoformat()
    extra["dateModified"] = post.updated_at.isoformat()
    metadata = build_metadata(
        SeoPage(
            title=f"{post.title} | Jeremy Guill",
            summary=post.summary,
            canonical_path=f"/blog/{post.slug}",
            is_published=True,
            kind="blog",
            seo_title=post.seo_title,
            seo_description=post.seo_description,
            extra=extra,
        )
    )
    return render_template(
        "public/blog_post.html", post=post, metadata=metadata
    )


@blog_bp.get("/resume")
def resume():
    path = Path(current_app.static_folder or "") / "resume"
    if not (path / "Resume2026.pdf").is_file():
        abort(404)
    return send_from_directory(path, "Resume2026.pdf", mimetype="application/pdf", max_age=3600)
