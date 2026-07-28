from __future__ import annotations


def test_challenge_cannot_be_consumed_twice(client):
    begin = client.post("/admin/auth/passkey/begin").get_json()
    assertion = {
        "challenge_id": begin["challenge_id"],
        "credential": {
            "origin": "http://localhost:5000",
            "rp_id": "localhost",
            "user_verified": True,
        },
    }

    first = client.post("/admin/auth/passkey/finish", json=assertion)
    second = client.post("/admin/auth/passkey/finish", json=assertion)

    assert first.status_code == 204
    assert second.status_code == 400


def test_wrong_origin_is_rejected(client):
    begin = client.post("/admin/auth/passkey/begin").get_json()
    response = client.post(
        "/admin/auth/passkey/finish",
        json={
            "challenge_id": begin["challenge_id"],
            "credential": {
                "origin": "https://evil.example",
                "rp_id": "localhost",
                "user_verified": True,
            },
        },
    )

    assert response.status_code == 400
