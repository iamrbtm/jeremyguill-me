from __future__ import annotations

import logging
import re

AUTHORIZATION_PATTERN = re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(api_key|authorization|cookie|password|secret|token)=\S+", re.IGNORECASE
)


def redact_text(value: str) -> str:
    value = AUTHORIZATION_PATTERN.sub("Authorization: Bearer [REDACTED]", value)
    return SECRET_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True
