from flask import Blueprint, abort, jsonify, render_template
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.extensions import db
from portfolio.public.view_models import build_home_view

public_bp = Blueprint("public", __name__)


@public_bp.route("/health/live")
def liveness():
    return jsonify({"status": "ok"})


@public_bp.get("/")
def home():
    return render_template("public/home.html", view=build_home_view())


@public_bp.get("/work/<slug>")
def project_detail(slug: str):
    project = db.session.execute(
        select(Project).where(Project.slug == slug, Project.state == PublicationState.PUBLISHED)
    ).scalar_one_or_none()
    if project is None:
        abort(404)
    return render_template("public/project.html", project=project, view=build_home_view())


@public_bp.get("/experience")
def experience():
    return render_template("public/experience.html", view=build_home_view())


@public_bp.get("/contact")
def contact():
    return render_template("public/contact.html", view=build_home_view())
