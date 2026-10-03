from __future__ import annotations

from portfolio.auth.services import make_password_hash, verify_password_login


def test_password_login_succeeds_with_correct_credentials(app, client):
    with app.app_context():
        digest = make_password_hash("correct horse battery")
        app.config["ADMIN_USERNAME"] = "admin"
        app.config["ADMIN_PASSWORD_HASH"] = digest

    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "correct horse battery"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200


def test_password_login_rejects_wrong_password(app, client):
    with app.app_context():
        digest = make_password_hash("correct horse battery")
        app.config["ADMIN_USERNAME"] = "admin"
        app.config["ADMIN_PASSWORD_HASH"] = digest

    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_password_login_rejects_wrong_username(app, client):
    with app.app_context():
        digest = make_password_hash("correct horse battery")
        app.config["ADMIN_USERNAME"] = "admin"
        app.config["ADMIN_PASSWORD_HASH"] = digest

    response = client.post(
        "/admin/login",
        data={"username": "notadmin", "password": "correct horse battery"},
    )

    assert response.status_code == 401


def test_password_login_disabled_without_hash(app, client):
    with app.app_context():
        assert verify_password_login("admin", "anything") is None
