from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

_LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "0.0.0.0", "::1"}


def validate_public_origin(env: str, origin: str) -> None:
    if env != "production":
        return
    parsed = urlparse(origin)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host in _LOCAL_HOSTS or host.endswith(".localhost"):
        raise RuntimeError(
            f"PUBLIC_ORIGIN must be the public https origin in production (got {origin!r})"
        )


@dataclass(frozen=True)
class Settings:
    app_env: str
    secret_key: str
    database_url: str
    public_origin: str
    rp_id: str
    rate_limit_storage_uri: str
    static_folder: str
    settings_encryption_key: str
    openai_model: str
    admin_username: str
    admin_password_hash: str

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("APP_ENV", "development")
        secret = os.getenv("SECRET_KEY", "")
        if env == "production" and len(secret) < 32:
            raise RuntimeError("SECRET_KEY must contain at least 32 characters")
        public_origin = os.getenv("PUBLIC_ORIGIN", "http://localhost:5000")
        validate_public_origin(env, public_origin)
        return cls(
            app_env=env,
            secret_key=secret or "development-only-secret",
            database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"),
            public_origin=public_origin,
            rp_id=os.getenv("WEBAUTHN_RP_ID", "localhost"),
            rate_limit_storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
            static_folder=os.getenv("STATIC_FOLDER", "static"),
            settings_encryption_key=os.getenv("SETTINGS_ENCRYPTION_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            admin_username=os.getenv("ADMIN_USERNAME", "admin"),
            admin_password_hash=os.getenv("ADMIN_PASSWORD_HASH", ""),
        )
