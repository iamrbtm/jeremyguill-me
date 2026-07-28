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
