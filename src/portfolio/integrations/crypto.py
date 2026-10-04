from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from flask import current_app


def encrypt_secret(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_secret(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode("utf-8")


def _fernet() -> Fernet:
    configured = current_app.config.get("SETTINGS_ENCRYPTION_KEY", "")
    if configured:
        return Fernet(configured.encode("utf-8"))
    if current_app.config.get("APP_ENV") == "production":
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY is required in production")
    digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
