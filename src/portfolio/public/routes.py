from flask import Blueprint, abort, jsonify, redirect, render_template
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db
from portfolio.public.view_models import build_home_view
from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_metadata, resolve_redirect_chain

public_bp = Blueprint("public", __name__)


@public_bp.route("/health/live")
def liveness():
    return jsonify({"status": "ok"})


@public_bp.get("/")
def home():
    view = build_home_view()
    metadata = build_metadata(
        SeoPage(
            title="Jeremy Guill | Practical Software Builder",
            summary=view.profile.summary
            or "Practical software, database workflows, and implementation support.",
            canonical_path="/",
            is_published=True,
            kind="person",
        )
    )
    return render_template("public/home.html", view=view, metadata=metadata)


@public_bp.get("/work/<slug>")
def project_detail(slug: str):
    project = db.session.execute(
        select(Project).where(Project.slug == slug, Project.state == PublicationState.PUBLISHED)
    ).scalar_one_or_none()
    if project is None:
        redirect_target = resolve_redirect_chain(f"/work/{slug}")
        if redirect_target:
            return redirect(redirect_target, code=308)
        abort(404)
    metadata = build_metadata(
        SeoPage(
            title=f"{project.title} | Jeremy Guill",
            summary=project.summary,
            canonical_path=f"/work/{project.slug}",
            is_published=True,
            kind="project",
        )
    )
    return render_template(
        "public/project.html", project=project, view=build_home_view(), metadata=metadata
    )


@public_bp.get("/experience")
def experience():
    metadata = build_metadata(
        SeoPage(
            title="Experience | Jeremy Guill",
            summary="Professional experience and credentials for Jeremy Guill.",
            canonical_path="/experience",
            is_published=True,
        )
    )
    return render_template("public/experience.html", view=build_home_view(), metadata=metadata)


@public_bp.get("/contact")
def contact():
    metadata = build_metadata(
        SeoPage(
            title="Contact | Jeremy Guill",
            summary="Start a conversation with Jeremy Guill about practical software work.",
            canonical_path="/contact",
            is_published=True,
        )
    )
    return render_template("public/contact.html", view=build_home_view(), metadata=metadata)
