from __future__ import annotations


def test_public_pages_have_basic_accessibility_landmarks(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Skip to content" in response.data
    assert b'<main id="main">' in response.data
    assert b'aria-label="Primary navigation"' in response.data


def test_contact_form_has_labels_and_error_summary(client):
    response = client.post("/contact", data={"email": "not-an-email"})

    assert response.status_code == 422
    assert b"Valid reply email is required" in response.data
    assert b"Name <input" in response.data
    assert b"Message <textarea" in response.data
