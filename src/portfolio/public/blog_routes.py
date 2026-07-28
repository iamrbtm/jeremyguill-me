from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.extensions import db
from portfolio.public.view_models import build_home_view
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
        "public/blog_index.html", view=build_home_view(), posts=list(posts), metadata=metadata
    )


@blog_bp.get("/blog/<slug>")
def detail(slug: str):
    post = db.session.execute(
        select(BlogPost).where(BlogPost.slug == slug, BlogPost.state == PublicationState.PUBLISHED)
    ).scalar_one_or_none()
    if post is None:
        abort(404)
    metadata = build_metadata(
        SeoPage(
            title=f"{post.title} | Jeremy Guill",
            summary=post.summary,
            canonical_path=f"/blog/{post.slug}",
            is_published=True,
            kind="blog",
        )
    )
    return render_template(
        "public/blog_post.html", view=build_home_view(), post=post, metadata=metadata
    )


@blog_bp.get("/resume")
def resume():
    return redirect("/static/resume/Resume2026.pdf")
