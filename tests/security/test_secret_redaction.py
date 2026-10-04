from __future__ import annotations

import logging

from portfolio.security.logging import RedactingFilter, redact_text


def test_redact_text_removes_authorization_and_secret_values():
    redacted = redact_text("Authorization: Bearer abc123 api_key=secret-token")

    assert "abc123" not in redacted
    assert "secret-token" not in redacted


def test_logging_filter_redacts_message_arguments():
    record = logging.LogRecord(
        name="portfolio",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token=%s",
        args=("super-secret",),
        exc_info=None,
    )

    RedactingFilter().filter(record)

    assert "super-secret" not in record.getMessage()
