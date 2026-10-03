from __future__ import annotations

import uuid

import httpx
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
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from portfolio.audit.services import record_event
from portfolio.auth.decorators import passkey_required
from portfolio.content.enums import PublicationState
from portfolio.content.models import (
    BlogPost,
    Experience,
    Project,
    ProjectGalleryItem,
    SiteProfile,
)
from portfolio.content.rendering import render_experience_markdown
from portfolio.content.services import (
    ContentConflict,
    ContentValidationError,
    publish,
    save_draft,
)
from portfolio.extensions import db
from portfolio.integrations.services import IntegrationNotConfigured
from portfolio.media.models import MediaAsset
from portfolio.media.services import list_media, store_upload_file
from portfolio.media.validation import InvalidUpload
from portfolio.seo.automation import run_blog_seo

from .forms import (
    BlogForm,
    ExperienceForm,
    ProjectForm,
    blog_form_for,
    experience_form_for,
    project_form_for,
)
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
    return render_template("admin/dashboard.html", view=build_dashboard_view(), settings=True)


def _collect_project_uploads() -> tuple[MediaAsset | None, list[MediaAsset]]:
    hero_asset = None
    hero_file = request.files.get("hero_image")
    if hero_file is not None and hero_file.filename:
        hero_asset = store_upload_file(
            hero_file.stream,
            hero_file.filename,
            hero_file.mimetype,
            alt_text=request.form.get("hero_alt_text", "").strip(),
        )
    gallery_assets: list[MediaAsset] = []
    for gallery_file in request.files.getlist("gallery_images"):
        if gallery_file is not None and gallery_file.filename:
            gallery_assets.append(
                store_upload_file(
                    gallery_file.stream,
                    gallery_file.filename,
                    gallery_file.mimetype,
                    alt_text=request.form.get("gallery_alt_text", "").strip(),
                )
            )
    return hero_asset, gallery_assets


def _attach_project_gallery(project: Project, gallery_assets: list[MediaAsset]) -> None:
    if not gallery_assets:
        return
    next_position = (
        db.session.execute(
            select(ProjectGalleryItem.position)
            .where(ProjectGalleryItem.project_id == project.id)
            .order_by(ProjectGalleryItem.position.desc())
        )
        .scalars()
        .first()
        or 0
    )
    for asset in gallery_assets:
        next_position += 1
        db.session.add(
            ProjectGalleryItem(project_id=project.id, media_id=asset.id, position=next_position)
        )


def _remove_project_gallery_items(project: Project) -> None:
    for raw_id in request.form.getlist("remove_gallery"):
        try:
            media_id = uuid.UUID(raw_id)
        except ValueError:
            continue
        db.session.execute(
            delete(ProjectGalleryItem).where(
                ProjectGalleryItem.project_id == project.id,
                ProjectGalleryItem.media_id == media_id,
            )
        )


@admin_bp.get("/projects")
@passkey_required
def projects():
    result = db.session.execute(select(Project).order_by(Project.sort_position, Project.title))
    items = result.scalars()
    return render_template("admin/content/list.html", content_type="projects", items=list(items))


@admin_bp.get("/projects/new")
@passkey_required
def new_project():
    return render_template(
        "admin/content/edit.html",
        entity=None,
        form=ProjectForm(version=0),
        content_type="projects",
        is_new=True,
        media_assets=list_media(),
    )


def _apply_glance_fields(project: Project, form: ProjectForm) -> None:
    project.role = form.role or None
    project.stack = form.stack or None
    project.year = form.year or None
    project.result_headline = form.result_headline or None


@admin_bp.post("/projects")
@passkey_required
def create_project():
    form = ProjectForm.from_mapping(request.form)
    if not form.validate():
        return (
            render_template(
                "admin/content/edit.html",
                entity=None,
                form=form,
                content_type="projects",
                is_new=True,
                media_assets=list_media(),
            ),
            422,
        )
    try:
        hero_asset, gallery_assets = _collect_project_uploads()
    except InvalidUpload as exc:
        form.add_error("hero_image", str(exc))
        return (
            render_template(
                "admin/content/edit.html",
                entity=None,
                form=form,
                content_type="projects",
                is_new=True,
                media_assets=list_media(),
                error=str(exc),
            ),
            422,
        )
    project = Project(state=PublicationState.DRAFT, version=0)
    if hero_asset is not None:
        project.hero_media_id = hero_asset.id
    elif request.form.get("hero_media_id"):
        project.hero_media_id = uuid.UUID(request.form["hero_media_id"])
    _apply_glance_fields(project, form)
    try:
        save_draft(project, form.to_command(), expected_version=None)
    except IntegrityError:
        db.session.rollback()
        form.add_error("slug", "A project with this slug already exists")
        return (
            render_template(
                "admin/content/edit.html",
                entity=None,
                form=form,
                content_type="projects",
                is_new=True,
                error="A project with this slug already exists. Choose a different slug.",
                media_assets=list_media(),
            ),
            409,
        )
    except ContentValidationError as exc:
        form.add_error("source_markdown", str(exc))
        return (
            render_template(
                "admin/content/edit.html",
                entity=None,
                form=form,
                content_type="projects",
                is_new=True,
                media_assets=list_media(),
            ),
            422,
        )
    _attach_project_gallery(project, gallery_assets)
    db.session.commit()
    return redirect(url_for("admin.edit_project", project_id=project.id))


@admin_bp.get("/projects/<uuid:project_id>")
@passkey_required
def edit_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    return render_template(
        "admin/content/edit.html",
        entity=project,
        form=project_form_for(project),
        content_type="projects",
        media_assets=list_media(),
        hero_asset=(
            db.session.get(MediaAsset, project.hero_media_id) if project.hero_media_id else None
        ),
        gallery=project.gallery_assets(),
    )


@admin_bp.post("/projects/<uuid:project_id>")
@passkey_required
def update_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    form = ProjectForm.from_mapping(request.form)
    if not form.validate():
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=form,
                content_type="projects",
                media_assets=list_media(),
            ),
            422,
        )
    try:
        hero_asset, gallery_assets = _collect_project_uploads()
    except InvalidUpload as exc:
        form.add_error("hero_image", str(exc))
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=form,
                content_type="projects",
                media_assets=list_media(),
                error=str(exc),
            ),
            422,
        )
    if hero_asset is not None:
        project.hero_media_id = hero_asset.id
    elif request.form.get("hero_media_id"):
        project.hero_media_id = uuid.UUID(request.form["hero_media_id"])
    _apply_glance_fields(project, form)
    try:
        save_draft(project, form.to_command(), expected_version=form.version)
    except IntegrityError:
        db.session.rollback()
        form.add_error("slug", "A project with this slug already exists")
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=form,
                content_type="projects",
                error="A project with this slug already exists. Choose a different slug.",
                media_assets=list_media(),
            ),
            409,
        )
    except ContentConflict:
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=form,
                content_type="projects",
                media_assets=list_media(),
                conflict=True,
            ),
            409,
        )
    except ContentValidationError as exc:
        form.add_error("source_markdown", str(exc))
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=form,
                content_type="projects",
                media_assets=list_media(),
            ),
            422,
        )
    _remove_project_gallery_items(project)
    _attach_project_gallery(project, gallery_assets)
    db.session.commit()
    return redirect(url_for("admin.edit_project", project_id=project.id))


@admin_bp.post("/projects/<uuid:project_id>/publish")
@passkey_required
def publish_project(project_id: uuid.UUID):
    project = db.get_or_404(Project, project_id)
    try:
        publish(project)
    except ContentValidationError as exc:
        return (
            render_template(
                "admin/content/edit.html",
                entity=project,
                form=project_form_for(project),
                content_type="projects",
                media_assets=list_media(),
                hero_asset=(
                    db.session.get(MediaAsset, project.hero_media_id)
                    if project.hero_media_id
                    else None
                ),
                gallery=project.gallery_assets(),
                error=f"Cannot publish: {exc}",
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


@admin_bp.get("/blog/new")
@passkey_required
def new_blog():
    return render_template(
        "admin/content/edit_blog.html",
        entity=None,
        form=BlogForm(version=0),
        content_type="blog",
        is_new=True,
    )


@admin_bp.post("/blog")
@passkey_required
def create_blog():
    form = BlogForm.from_mapping(request.form)
    if not form.validate():
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=None,
                form=form,
                content_type="blog",
                is_new=True,
            ),
            422,
        )
    post = BlogPost(state=PublicationState.DRAFT, version=0)
    try:
        save_draft(post, form.to_command(), expected_version=None)
    except IntegrityError:
        db.session.rollback()
        form.add_error("slug", "A blog post with this slug already exists")
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=None,
                form=form,
                content_type="blog",
                is_new=True,
                error="A blog post with this slug already exists. Choose a different slug.",
            ),
            409,
        )
    except ContentValidationError as exc:
        form.add_error("source_markdown", str(exc))
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=None,
                form=form,
                content_type="blog",
                is_new=True,
            ),
            422,
        )
    post.seo_title = form.seo_title or None
    post.seo_description = form.seo_description or None
    post.seo_target_query = form.seo_target_query or None
    db.session.commit()
    return redirect(url_for("admin.edit_blog", blog_id=post.id))


@admin_bp.get("/blog/<uuid:blog_id>")
@passkey_required
def edit_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    return render_template(
        "admin/content/edit_blog.html",
        entity=post,
        form=blog_form_for(post),
        content_type="blog",
        seo_message=request.args.get("seo_message"),
        seo_error=request.args.get("seo_error"),
    )


@admin_bp.post("/blog/<uuid:blog_id>")
@passkey_required
def update_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    form = BlogForm.from_mapping(request.form)
    if not form.validate():
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=post,
                form=form,
                content_type="blog",
            ),
            422,
        )
    try:
        save_draft(post, form.to_command(), expected_version=form.version)
    except IntegrityError:
        db.session.rollback()
        form.add_error("slug", "A blog post with this slug already exists")
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=post,
                form=form,
                content_type="blog",
                error="A blog post with this slug already exists. Choose a different slug.",
            ),
            409,
        )
    except ContentConflict:
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=post,
                form=form,
                content_type="blog",
                conflict=True,
            ),
            409,
        )
    except ContentValidationError as exc:
        form.add_error("source_markdown", str(exc))
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=post,
                form=form,
                content_type="blog",
            ),
            422,
        )
    post.seo_title = form.seo_title or post.seo_title
    post.seo_description = form.seo_description or post.seo_description
    post.seo_target_query = form.seo_target_query or post.seo_target_query
    db.session.commit()
    return redirect(url_for("admin.edit_blog", blog_id=post.id))


@admin_bp.post("/blog/<uuid:blog_id>/seo")
@passkey_required
def optimize_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    try:
        run_blog_seo(post)
    except IntegrationNotConfigured:
        return redirect(
            url_for("admin.edit_blog", blog_id=blog_id, seo_error="OpenAI is not configured")
        )
    except (RuntimeError, httpx.HTTPError) as exc:
        return redirect(url_for("admin.edit_blog", blog_id=blog_id, seo_error=str(exc)[:200]))
    return redirect(
        url_for("admin.edit_blog", blog_id=blog_id, seo_message="AI SEO suggestions applied.")
    )


@admin_bp.post("/blog/<uuid:blog_id>/publish")
@passkey_required
def publish_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    try:
        run_blog_seo(post)
    except IntegrationNotConfigured, RuntimeError, httpx.HTTPError:
        pass
    try:
        publish(post)
    except ContentValidationError as exc:
        return (
            render_template(
                "admin/content/edit_blog.html",
                entity=post,
                form=blog_form_for(post),
                content_type="blog",
                error=f"Cannot publish: {exc}",
            ),
            422,
        )
    return redirect(url_for("admin.edit_blog", blog_id=post.id))


@admin_bp.post("/blog/<uuid:blog_id>/archive")
@passkey_required
def archive_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    post.state = PublicationState.ARCHIVED
    post.version += 1
    record_event(
        action="content.archived",
        actor="admin",
        target_type="blog",
        target_id=str(post.id),
    )
    db.session.commit()
    return redirect(url_for("admin.blog"))


@admin_bp.post("/blog/<uuid:blog_id>/restore")
@passkey_required
def restore_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    post.state = PublicationState.DRAFT
    post.version += 1
    record_event(
        action="content.restored",
        actor="admin",
        target_type="blog",
        target_id=str(post.id),
    )
    db.session.commit()
    return redirect(url_for("admin.blog"))


@admin_bp.post("/blog/<uuid:blog_id>/delete")
@passkey_required
def delete_blog(blog_id: uuid.UUID):
    post = db.get_or_404(BlogPost, blog_id)
    record_event(
        action="content.deleted",
        actor="admin",
        target_type="blog",
        target_id=str(post.id),
    )
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("admin.blog"))


@admin_bp.get("/experience")
@passkey_required
def experience():
    items = db.session.execute(select(Experience).order_by(Experience.sort_position)).scalars()
    return render_template("admin/content/list.html", content_type="experience", items=list(items))


@admin_bp.get("/experience/new")
@passkey_required
def new_experience():
    return render_template(
        "admin/content/edit_experience.html",
        entity=None,
        form=ExperienceForm(version=0),
        content_type="experience",
        is_new=True,
        media_assets=list_media(),
    )


@admin_bp.post("/experience")
@passkey_required
def create_experience():
    form = ExperienceForm.from_mapping(request.form)
    if not form.validate():
        return (
            render_template(
                "admin/content/edit_experience.html",
                entity=None,
                form=form,
                content_type="experience",
                is_new=True,
                media_assets=list_media(),
            ),
            422,
        )
    logo_asset = None
    logo_file = request.files.get("logo_image")
    if logo_file is not None and logo_file.filename:
        try:
            logo_asset = store_upload_file(
                logo_file.stream,
                logo_file.filename,
                logo_file.mimetype,
                alt_text=request.form.get("logo_alt_text", "").strip(),
            )
        except InvalidUpload as exc:
            form.add_error("logo_image", str(exc))
            return (
                render_template(
                    "admin/content/edit_experience.html",
                    entity=None,
                    form=form,
                    content_type="experience",
                    is_new=True,
                    media_assets=list_media(),
                    error=str(exc),
                ),
                422,
            )
    experience_entry = Experience(
        source_markdown=form.source_markdown,
        rendered_html="",
        visible=form.visible,
        version=0,
    )
    experience_entry.organization = form.organization
    experience_entry.role = form.role
    experience_entry.summary = form.summary
    experience_entry.source_markdown = form.source_markdown
    experience_entry.rendered_html = render_experience_markdown(form.source_markdown)
    experience_entry.start_date = form.start_date
    experience_entry.end_date = form.end_date
    experience_entry.sort_position = form.order
    if logo_asset is not None:
        experience_entry.logo_media_id = logo_asset.id
    elif request.form.get("logo_media_id"):
        experience_entry.logo_media_id = uuid.UUID(request.form["logo_media_id"])
    db.session.add(experience_entry)
    experience_entry.version += 1
    record_event(
        action="content.experience.created",
        actor="admin",
        target_type="experience",
        target_id=str(experience_entry.id),
        metadata={"version": experience_entry.version},
    )
    db.session.commit()
    return redirect(url_for("admin.edit_experience", experience_id=experience_entry.id))


@admin_bp.get("/experience/<uuid:experience_id>")
@passkey_required
def edit_experience(experience_id: uuid.UUID):
    experience_entry = db.get_or_404(Experience, experience_id)
    logo_asset = (
        db.session.get(MediaAsset, experience_entry.logo_media_id)
        if experience_entry.logo_media_id
        else None
    )
    return render_template(
        "admin/content/edit_experience.html",
        entity=experience_entry,
        form=experience_form_for(experience_entry),
        content_type="experience",
        media_assets=list_media(),
        logo_asset=logo_asset,
    )


@admin_bp.post("/experience/<uuid:experience_id>")
@passkey_required
def update_experience(experience_id: uuid.UUID):
    experience_entry = db.get_or_404(Experience, experience_id)
    form = ExperienceForm.from_mapping(request.form)
    if not form.validate():
        logo_asset = (
            db.session.get(MediaAsset, experience_entry.logo_media_id)
            if experience_entry.logo_media_id
            else None
        )
        return (
            render_template(
                "admin/content/edit_experience.html",
                entity=experience_entry,
                form=form,
                content_type="experience",
                media_assets=list_media(),
                logo_asset=logo_asset,
            ),
            422,
        )
    logo_asset = None
    logo_file = request.files.get("logo_image")
    if logo_file is not None and logo_file.filename:
        try:
            logo_asset = store_upload_file(
                logo_file.stream,
                logo_file.filename,
                logo_file.mimetype,
                alt_text=request.form.get("logo_alt_text", "").strip(),
            )
        except InvalidUpload as exc:
            form.add_error("logo_image", str(exc))
            logo_asset = (
                db.session.get(MediaAsset, experience_entry.logo_media_id)
                if experience_entry.logo_media_id
                else None
            )
            return (
                render_template(
                    "admin/content/edit_experience.html",
                    entity=experience_entry,
                    form=form,
                    content_type="experience",
                    media_assets=list_media(),
                    logo_asset=logo_asset,
                    error=str(exc),
                ),
                422,
            )
    if logo_asset is not None:
        experience_entry.logo_media_id = logo_asset.id
    elif request.form.get("logo_media_id"):
        experience_entry.logo_media_id = uuid.UUID(request.form["logo_media_id"])
    elif "remove_logo" in request.form:
        experience_entry.logo_media_id = None
    experience_entry.organization = form.organization
    experience_entry.role = form.role
    experience_entry.summary = form.summary
    experience_entry.source_markdown = form.source_markdown
    experience_entry.rendered_html = render_experience_markdown(form.source_markdown)
    experience_entry.start_date = form.start_date
    experience_entry.end_date = form.end_date
    experience_entry.sort_position = form.order
    experience_entry.visible = form.visible
    experience_entry.version += 1
    record_event(
        action="content.experience.updated",
        actor="admin",
        target_type="experience",
        target_id=str(experience_entry.id),
        metadata={"version": experience_entry.version},
    )
    db.session.commit()
    return redirect(url_for("admin.edit_experience", experience_id=experience_entry.id))


@admin_bp.post("/experience/<uuid:experience_id>/delete")
@passkey_required
def delete_experience(experience_id: uuid.UUID):
    experience_entry = db.get_or_404(Experience, experience_id)
    record_event(
        action="content.experience.deleted",
        actor="admin",
        target_type="experience",
        target_id=str(experience_entry.id),
    )
    db.session.delete(experience_entry)
    db.session.commit()
    return redirect(url_for("admin.experience"))


@admin_bp.get("/profile")
@passkey_required
def profile():
    profile = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
    return render_template("admin/dashboard.html", view=build_dashboard_view(), profile=profile)


@admin_bp.get("/settings")
@passkey_required
def settings():
    return render_template("admin/dashboard.html", view=build_dashboard_view(), settings=True)
