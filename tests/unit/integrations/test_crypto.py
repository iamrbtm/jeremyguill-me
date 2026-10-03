from __future__ import annotations

import pytest

from portfolio.integrations.crypto import decrypt_secret, encrypt_secret


def test_encrypted_api_key_does_not_contain_plaintext(app):
    with app.app_context():
        ciphertext = encrypt_secret("openai-super-secret")

        assert b"openai-super-secret" not in ciphertext
        assert decrypt_secret(ciphertext) == "openai-super-secret"


def test_encryption_is_not_deterministic(app):
    with app.app_context():
        first = encrypt_secret("openai-super-secret")
        second = encrypt_secret("openai-super-secret")

        assert first != second


def test_production_requires_settings_encryption_key(app):
    app.config["APP_ENV"] = "production"
    app.config["SETTINGS_ENCRYPTION_KEY"] = ""

    with app.app_context():
        with pytest.raises(RuntimeError, match="SETTINGS_ENCRYPTION_KEY"):
            encrypt_secret("openai-super-secret")
