from __future__ import annotations

import time

from portfolio.content.models import SiteProfile


def test_contact_page_has_no_hardcoded_fallback_email_or_plain_mailto(client, db_session):
    db_session.add(SiteProfile(email=None))
    db_session.commit()

    html = client.get("/contact").get_data(as_text=True)

    assert "rbtm2006@me.com" not in html and "mailto:" not in html


def test_email_is_not_in_plain_text_when_configured(client, db_session):
    db_session.add(SiteProfile(email="hello@example.test"))
    db_session.commit()

    html = client.get("/contact").get_data(as_text=True)

    assert "hello@example.test" not in html
    assert 'data-email-user="hello"' in html and 'data-email-domain="example.test"' in html


def test_form_has_autocomplete_and_reply_promise(client):
    html = client.get("/contact").get_data(as_text=True)

    assert 'autocomplete="name"' in html and 'autocomplete="email"' in html
    assert "usually reply within" in html


def test_success_banner_only_with_sent_flag(client):
    assert 'role="status"' not in client.get("/contact").get_data(as_text=True)
    assert 'role="status"' in client.get("/contact?sent=1").get_data(as_text=True)


def test_valid_submission_redirects_with_sent_flag(client):
    response = client.post(
        "/contact",
        data={
            "name": "Ada",
            "email": "a@example.test",
            "subject": "Hi",
            "message": "Hello there friend",
            "form_started_at": str(time.time() - 30),
            "company_website": "",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/contact?sent=1")


def test_invalid_submission_shows_field_error_and_keeps_input(client):
    response = client.post(
        "/contact",
        data={"name": "A", "email": "not-an-email", "subject": "", "message": ""},
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 422
    assert 'role="alert"' in html and 'value="A"' in html
