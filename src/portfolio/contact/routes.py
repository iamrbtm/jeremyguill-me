from __future__ import annotations

import uuid

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import select

from portfolio.auth.decorators import passkey_required
from portfolio.extensions import db
from portfolio.public.view_models import build_home_view
from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_metadata

from . import services
from .forms import ContactForm
from .models import ContactSubmission

contact_bp = Blueprint("contact", __name__)


@contact_bp.post("/contact")
def submit_contact():
    form = ContactForm.from_mapping(request.form)
    view = build_home_view()
    metadata = build_metadata(
        SeoPage(
            title="Contact | Jeremy Guill",
            summary="Start a conversation with Jeremy Guill about practical software work.",
            canonical_path="/contact",
            is_published=True,
        )
    )
    if not form.validate():
        return render_template("public/contact.html", view=view, metadata=metadata, form=form), 422
    submission = services.save_submission(form.command)
    if submission is None:
        return redirect(url_for("public.contact"))
    result = services.send_submission_notification(submission.id)
    services.mark_delivery_result(submission, result)
    return redirect(url_for("public.contact"))


@contact_bp.get("/admin/contact")
@passkey_required
def admin_index():
    submissions = db.session.execute(
        select(ContactSubmission).order_by(ContactSubmission.created_at.desc())
    ).scalars()
    return render_template("admin/contact/index.html", submissions=list(submissions))


@contact_bp.get("/admin/contact/<uuid:submission_id>")
@passkey_required
def admin_detail(submission_id: uuid.UUID):
    submission = db.get_or_404(ContactSubmission, submission_id)
    return render_template("admin/contact/detail.html", submission=submission)


@contact_bp.post("/admin/contact/<uuid:submission_id>/state")
@passkey_required
def admin_update_state(submission_id: uuid.UUID):
    services.update_contact_state(submission_id, request.form.get("state", ""))
    return redirect(url_for("contact.admin_detail", submission_id=submission_id))
