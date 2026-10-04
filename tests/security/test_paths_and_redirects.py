from __future__ import annotations

from portfolio.content.models import Redirect
from portfolio.extensions import db
from portfolio.security.validation import safe_redirect_target


def test_safe_redirect_target_rejects_external_destinations():
    assert safe_redirect_target("https://evil.example/path") is None
    assert safe_redirect_target("//evil.example/path") is None
    assert safe_redirect_target("/safe/path") == "/safe/path"


def test_stored_external_redirect_is_not_followed(client, db_session):
    db.session.add(Redirect(old_path="/work/old", new_path="https://evil.example/steal"))
    db.session.commit()

    response = client.get("/work/old")

    assert response.status_code == 404
