from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from portfolio.audit.services import record_event
from portfolio.auth.models import AdminSession, AuthChallenge, BootstrapToken, PasskeyCredential
from portfolio.extensions import db


class InvalidChallenge(ValueError):
    pass


class InvalidCredential(ValueError):
    pass


class InvalidBootstrapToken(ValueError):
    pass


@dataclass(frozen=True)
class AdminIdentity:
    passkeys: list[PasskeyCredential]

    @property
    def is_enrollment_complete(self) -> bool:
        return sum(1 for passkey in self.passkeys if passkey.active) >= 2


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def begin_authentication() -> tuple[uuid.UUID, dict[str, object]]:
    challenge = AuthChallenge(
        ceremony="authentication",
        value=secrets.token_bytes(32),
        expires_at=utcnow() + timedelta(minutes=5),
    )
    db.session.add(challenge)
    db.session.commit()
    return challenge.id, {
        "challenge": challenge.value.hex(),
        "rpId": current_app.config["WEBAUTHN_RP_ID"],
        "userVerification": "required",
    }


def begin_registration(enrollment_session_id: uuid.UUID) -> tuple[uuid.UUID, dict[str, object]]:
    challenge = AuthChallenge(
        ceremony="registration",
        value=secrets.token_bytes(32),
        expires_at=utcnow() + timedelta(minutes=5),
    )
    db.session.add(challenge)
    db.session.commit()
    return challenge.id, {
        "challenge": challenge.value.hex(),
        "rp": {"id": current_app.config["WEBAUTHN_RP_ID"], "name": "Jeremy Guill"},
        "user": {"id": str(enrollment_session_id), "name": "admin", "displayName": "Admin"},
        "userVerification": "required",
    }


def consume_challenge(challenge_id: uuid.UUID, ceremony: str) -> AuthChallenge:
    challenge = db.session.execute(
        select(AuthChallenge).where(AuthChallenge.id == challenge_id).with_for_update()
    ).scalar_one_or_none()
    if (
        challenge is None
        or challenge.used_at is not None
        or as_aware(challenge.expires_at) <= utcnow()
        or challenge.ceremony != ceremony
    ):
        raise InvalidChallenge("Invalid or expired passkey challenge")
    challenge.used_at = utcnow()
    return challenge


def finish_authentication(response: Mapping[str, object], challenge_id: uuid.UUID) -> AdminSession:
    credential = response.get("credential")
    if not isinstance(credential, Mapping):
        raise InvalidCredential("Missing passkey credential")
    if credential.get("origin") != current_app.config["PUBLIC_ORIGIN"]:
        raise InvalidCredential("Invalid WebAuthn origin")
    if credential.get("rp_id") != current_app.config["WEBAUTHN_RP_ID"]:
        raise InvalidCredential("Invalid WebAuthn RP ID")
    if credential.get("user_verified") is not True:
        raise InvalidCredential("User verification is required")

    consume_challenge(challenge_id, "authentication")
    admin_session = AdminSession(absolute_expires_at=utcnow() + timedelta(hours=24))
    db.session.add(admin_session)
    record_event(
        action="auth.passkey.authenticated",
        actor="admin",
        target_type="admin_session",
        target_id=str(admin_session.id),
        metadata={"rp_id": current_app.config["WEBAUTHN_RP_ID"]},
    )
    db.session.commit()
    return admin_session


def get_valid_admin_session(session_id: str | None) -> AdminSession | None:
    if not session_id:
        return None
    try:
        admin_session_id = uuid.UUID(session_id)
    except ValueError:
        return None
    admin_session = db.session.get(AdminSession, admin_session_id)
    if admin_session is None or admin_session.revoked_at is not None:
        return None
    if as_aware(admin_session.absolute_expires_at) <= utcnow():
        return None
    admin_session.last_seen_at = utcnow()
    db.session.commit()
    return admin_session


def make_password_hash(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password_login(username: str | None, password: str | None) -> AdminSession | None:
    expected_username = current_app.config.get("ADMIN_USERNAME", "")
    expected_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
    if not expected_username or not expected_hash:
        return None

    password_ok = bool(password) and check_password_hash(expected_hash, password or "")
    username_ok = hmac.compare_digest(username or "", expected_username)
    if not (password_ok and username_ok):
        return None

    admin_session = AdminSession(absolute_expires_at=utcnow() + timedelta(hours=24))
    db.session.add(admin_session)
    record_event(
        action="auth.password.authenticated",
        actor="admin",
        target_type="admin_session",
        target_id=str(admin_session.id),
    )
    db.session.commit()
    return admin_session


def _bootstrap_digest(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def validate_bootstrap_token(token: str | None) -> bool:
    if not token:
        return False
    bootstrap_token = db.session.execute(
        select(BootstrapToken).where(BootstrapToken.digest == _bootstrap_digest(token))
    ).scalar_one_or_none()
    return (
        bootstrap_token is not None
        and bootstrap_token.used_at is None
        and as_aware(bootstrap_token.expires_at) > utcnow()
    )


def consume_bootstrap_token(token: str | None) -> AdminSession:
    if not token:
        raise InvalidBootstrapToken("Missing bootstrap token")
    bootstrap_token = db.session.execute(
        select(BootstrapToken)
        .where(BootstrapToken.digest == _bootstrap_digest(token))
        .with_for_update()
    ).scalar_one_or_none()
    if (
        bootstrap_token is None
        or bootstrap_token.used_at is not None
        or as_aware(bootstrap_token.expires_at) <= utcnow()
    ):
        raise InvalidBootstrapToken("Invalid or expired bootstrap token")

    bootstrap_token.used_at = utcnow()
    admin_session = AdminSession(absolute_expires_at=utcnow() + timedelta(hours=24))
    db.session.add(admin_session)
    record_event(
        action="auth.bootstrap.authenticated",
        actor="admin",
        target_type="admin_session",
        target_id=str(admin_session.id),
        metadata={"purpose": bootstrap_token.purpose},
    )
    db.session.commit()
    return admin_session


def finish_registration(
    response: Mapping[str, object], challenge_id: uuid.UUID
) -> PasskeyCredential:
    credential = response.get("credential")
    if not isinstance(credential, Mapping):
        raise InvalidCredential("Missing passkey credential")
    consume_challenge(challenge_id, "registration")
    passkey = PasskeyCredential(
        credential_id=str(credential.get("id", secrets.token_urlsafe(16))).encode(),
        public_key=str(credential.get("public_key", secrets.token_urlsafe(32))).encode(),
        name=str(credential.get("name", "Passkey")),
        active=True,
    )
    db.session.add(passkey)
    record_event(
        action="auth.passkey.registered",
        actor="admin",
        target_type="passkey",
        target_id=str(passkey.id),
        metadata={"name": passkey.name},
    )
    db.session.commit()
    return passkey


def create_bootstrap_token(purpose: str) -> str:
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).digest()
    db.session.query(BootstrapToken).filter(BootstrapToken.used_at.is_(None)).delete()
    db.session.add(
        BootstrapToken(
            digest=digest,
            purpose=purpose,
            expires_at=utcnow() + timedelta(minutes=10),
        )
    )
    db.session.commit()
    return token
