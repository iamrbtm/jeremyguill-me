from __future__ import annotations


def test_begin_authentication_returns_usernameless_options(client):
    response = client.post("/admin/auth/passkey/begin")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["challenge_id"]
    assert payload["options"]["userVerification"] == "required"
    assert "allowCredentials" not in payload["options"]


def test_finish_authentication_creates_admin_session(client):
    begin = client.post("/admin/auth/passkey/begin").get_json()
    response = client.post(
        "/admin/auth/passkey/finish",
        json={
            "challenge_id": begin["challenge_id"],
            "credential": {
                "origin": "http://localhost:5000",
                "rp_id": "localhost",
                "user_verified": True,
            },
        },
    )

    assert response.status_code == 204


def test_bootstrap_token_signs_in_once(client, app):
    with app.app_context():
        token = app.test_cli_runner().invoke(args=["admin", "bootstrap-passkeys"]).output.rsplit(
            "token=", 1
        )[1].strip()

    bootstrap = client.get(f"/admin/bootstrap?token={token}")
    assert bootstrap.status_code == 200
    assert b"Open admin dashboard" in bootstrap.data

    response = client.post("/admin/bootstrap", data={"token": token})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")

    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert b"Dashboard" in dashboard.data

    reused = client.post("/admin/bootstrap", data={"token": token})
    assert reused.status_code == 400
