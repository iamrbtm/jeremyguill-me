from __future__ import annotations


def test_passkey_sign_in_and_bootstrap_pages_load(client):
    sign_in = client.get("/admin/sign-in")
    bootstrap = client.get("/admin/bootstrap")
    begin = client.post("/admin/auth/passkey/begin")

    assert sign_in.status_code == 200
    assert bootstrap.status_code == 200
    assert begin.status_code == 200
    assert begin.get_json()["options"]["userVerification"] == "required"


def test_admin_dashboard_requires_passkey_session(client):
    response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/sign-in")
