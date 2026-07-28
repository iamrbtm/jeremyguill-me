from __future__ import annotations

import uuid

from flask import (
    Blueprint,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select

from portfolio.audit.services import record_event
from portfolio.auth.decorators import passkey_required
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Experience, Project, SiteProfile
from portfolio.content.services import ContentConflict, ContentValidationError, save_draft
from portfolio.extensions import db

from .forms import ProjectForm, project_form_for
from .view_models import (
    ExpiredPreview,
    InvalidPreview,
    build_dashboard_view,
    create_preview_token,
    load_preview_token,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("")
@passkey_required
def dashboard():
    return render_template("admin/dashboard.html", view=build_dashboard_view())


@admin_bp.get("/projects")
@passkey_required
def projects():
    result = db.session.execute(select(Project).order_by(Project.sort_position, Project.title))
    items = result.scalars()
    return render_template("admin/content/list.html", content_type="projects", items=list(items))


@admin_bp.get("/projects/<uuid:project_id>")
@passkey_required
def edit_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    return render_template(
        "admin/content/edit.html",
        entity=project,
        form=project_form_for(project),
        content_type="projects",
    )


@admin_bp.post("/projects/<uuid:project_id>")
@passkey_required
def update_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    form = ProjectForm.from_mapping(request.form)
    if not form.validate():
        return (
            render_template(
                "admin/content/edit.html", entity=project, form=form, content_type="projects"
            ),
            422,
        )
    try:
        save_draft(project, form.to_command(), expected_version=form.version)
    except ContentConflict:
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=form,
                content_type="projects",
                conflict=True,
            ),
            409,
        )
    except ContentValidationError as exc:
        form.add_error("source_markdown", str(exc))
        return (
            render_template(
                "admin/content/edit.html", entity=project, form=form, content_type="projects"
            ),
            422,
        )
    return redirect(url_for("admin.edit_project", project_id=project.id))


@admin_bp.post("/projects/<uuid:project_id>/archive")
@passkey_required
def archive_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    project.state = PublicationState.ARCHIVED
    project.version += 1
    record_event(
        action="content.archived",
        actor="admin",
        target_type="project",
        target_id=str(project.id),
    )
    db.session.commit()
    return redirect(url_for("admin.projects"))


@admin_bp.post("/projects/<uuid:project_id>/restore")
@passkey_required
def restore_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    project.state = PublicationState.DRAFT
    project.version += 1
    record_event(
        action="content.restored",
        actor="admin",
        target_type="project",
        target_id=str(project.id),
    )
    db.session.commit()
    return redirect(url_for("admin.projects"))


@admin_bp.post("/projects/sort")
@passkey_required
def sort_project():
    project_id = uuid.UUID(request.form["project_id"])
    project = db.get_or_404(Project, project_id)
    project.sort_position = int(request.form["sort_position"])
    project.version += 1
    record_event(
        action="content.sorted",
        actor="admin",
        target_type="project",
        target_id=str(project.id),
        metadata={"sort_position": project.sort_position},
    )
    db.session.commit()
    return redirect(url_for("admin.projects"))


@admin_bp.get("/projects/<uuid:project_id>/preview")
@passkey_required
def project_preview_url(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    token = create_preview_token(project, session["admin_session_id"])
    return redirect(url_for("admin.preview", token=token))


@admin_bp.get("/preview/<token>")
@passkey_required
def preview(token: str):
    try:
        claims = load_preview_token(token)
    except ExpiredPreview:
        abort(410)
    except InvalidPreview:
        abort(403)
    if claims.admin_session_id != session.get("admin_session_id"):
        abort(403)
    if claims.entity_type != "project":
        abort(404)
    project = db.get_or_404(Project, uuid.UUID(claims.entity_id))
    if project.version != claims.version:
        return "Preview version no longer matches this record.", 409
    response = make_response(render_template("admin/content/preview.html", project=project))
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@admin_bp.get("/blog")
@passkey_required
def blog():
    items = db.session.execute(select(BlogPost).order_by(BlogPost.published_at.desc())).scalars()
    return render_template("admin/content/list.html", content_type="blog", items=list(items))


@admin_bp.get("/experience")
@passkey_required
def experience():
    items = db.session.execute(select(Experience).order_by(Experience.sort_position)).scalars()
    return render_template("admin/content/list.html", content_type="experience", items=list(items))


@admin_bp.get("/profile")
@passkey_required
def profile():
    profile = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
    return render_template("admin/dashboard.html", view=build_dashboard_view(), profile=profile)


@admin_bp.get("/settings")
@passkey_required
def settings():
    return render_template("admin/dashboard.html", view=build_dashboard_view(), settings=True)
