from __future__ import annotations

import os
from dataclasses import dataclass


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
    nvidia_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("APP_ENV", "development")
        secret = os.getenv("SECRET_KEY", "")
        if env == "production" and len(secret) < 32:
            raise RuntimeError("SECRET_KEY must contain at least 32 characters")
        return cls(
            app_env=env,
            secret_key=secret or "development-only-secret",
            database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"),
            public_origin=os.getenv("PUBLIC_ORIGIN", "http://localhost:5000"),
            rp_id=os.getenv("WEBAUTHN_RP_ID", "localhost"),
            rate_limit_storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
            static_folder=os.getenv("STATIC_FOLDER", "static"),
            settings_encryption_key=os.getenv("SETTINGS_ENCRYPTION_KEY", ""),
            nvidia_model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
        )
