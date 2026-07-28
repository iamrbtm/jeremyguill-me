from __future__ import annotations

from portfolio.auth.models import PasskeyCredential
from portfolio.auth.services import AdminIdentity


def test_normal_admin_access_requires_two_active_passkeys():
    admin_identity = AdminIdentity(passkeys=[PasskeyCredential(active=True)])
    assert admin_identity.is_enrollment_complete is False


def test_normal_admin_access_allows_two_active_passkeys():
    admin_identity = AdminIdentity(
        passkeys=[PasskeyCredential(active=True), PasskeyCredential(active=True)]
    )
    assert admin_identity.is_enrollment_complete is True
