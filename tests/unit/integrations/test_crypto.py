from __future__ import annotations

import pytest

from portfolio.integrations.crypto import decrypt_secret, encrypt_secret


def test_encrypted_api_key_does_not_contain_plaintext(app):
    with app.app_context():
        ciphertext = encrypt_secret("nvapi-super-secret")

        assert b"nvapi-super-secret" not in ciphertext
        assert decrypt_secret(ciphertext) == "nvapi-super-secret"


def test_encryption_is_not_deterministic(app):
    with app.app_context():
        first = encrypt_secret("nvapi-super-secret")
        second = encrypt_secret("nvapi-super-secret")

        assert first != second


def test_production_requires_settings_encryption_key(app):
    app.config["APP_ENV"] = "production"
    app.config["SETTINGS_ENCRYPTION_KEY"] = ""

    with app.app_context():
        with pytest.raises(RuntimeError, match="SETTINGS_ENCRYPTION_KEY"):
            encrypt_secret("nvapi-super-secret")
