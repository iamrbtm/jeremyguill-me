from flask import Blueprint, abort, jsonify, redirect, render_template, send_from_directory
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db
from portfolio.media.models import MediaAsset
from portfolio.media.variants import media_root
from portfolio.public.view_models import build_home_view, published_projects
from portfolio.security.validation import safe_redirect_target
from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_metadata, resolve_redirect_chain

public_bp = Blueprint("public", __name__)


@public_bp.get("/media/<path:filename>")
def serve_public_media(filename: str):
    if ".." in filename or not filename.startswith("public/"):
        abort(404)
    return send_from_directory(media_root(), filename, max_age=2592000)


@public_bp.route("/health/live")
def liveness():
    return jsonify({"status": "ok"})


@public_bp.get("/")
def home():
    view = build_home_view()
    metadata = build_metadata(
        SeoPage(
            title="Jeremy Guill | Software and Workflow Portfolio",
            summary=view.profile.summary
            or "Portfolio of practical software, database workflows, automation, and implementation support.",
            canonical_path="/",
            is_published=True,
            kind="person",
            name=view.profile.display_name or "Jeremy Guill",
            seo_title=view.profile.seo_title,
            seo_description=view.profile.seo_description,
        )
    )
    return render_template("public/home.html", view=view, metadata=metadata)


@public_bp.get("/work")
def work_index():
    projects = published_projects()
    metadata = build_metadata(
        SeoPage(
            title="Work | Jeremy Guill",
            summary=(
                "Projects across scheduling automation, lending-library systems, "
                "FileMaker workflows, and database-backed operations."
            ),
            canonical_path="/work",
            is_published=True,
        )
    )
    return render_template(
        "public/work.html", projects=projects, view=build_home_view(), metadata=metadata
    )


@public_bp.get("/work/<slug>")
def project_detail(slug: str):
    project = db.session.execute(
        select(Project).where(Project.slug == slug, Project.state == PublicationState.PUBLISHED)
    ).scalar_one_or_none()
    if project is None:
        redirect_target = resolve_redirect_chain(f"/work/{slug}")
        safe_target = safe_redirect_target(redirect_target or "")
        if safe_target:
            return redirect(safe_target, code=308)
        abort(404)
    metadata = build_metadata(
        SeoPage(
            title=f"{project.title} | Jeremy Guill",
            summary=project.summary,
            canonical_path=f"/work/{project.slug}",
            is_published=True,
            kind="project",
            seo_title=project.seo_title,
            seo_description=project.seo_description,
        )
    )
    hero_asset = (
        db.session.get(MediaAsset, project.hero_media_id) if project.hero_media_id else None
    )
    gallery = project.gallery_assets()
    return render_template(
        "public/project.html",
        project=project,
        hero_asset=hero_asset,
        gallery=gallery,
        view=build_home_view(),
        metadata=metadata,
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
    import time

    metadata = build_metadata(
        SeoPage(
            title="Contact | Jeremy Guill",
            summary="Connect with Jeremy Guill about portfolio projects, software work, and technical collaboration.",
            canonical_path="/contact",
            is_published=True,
        )
    )
    return render_template(
        "public/contact.html",
        view=build_home_view(),
        metadata=metadata,
        form_started_at=str(time.time()),
    )
