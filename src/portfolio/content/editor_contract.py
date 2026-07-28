from __future__ import annotations

import re
from dataclasses import dataclass

MAX_EDITOR_BYTES = 500_000
RAW_HTML_PATTERN = re.compile(r"<!--.*?-->|</?[a-zA-Z][^>]*>", re.DOTALL)
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
APPROVED_IMAGE_PREFIXES = ("/media/", "https://jeremyguill.me/media/")


@dataclass(frozen=True)
class EditorValidation:
    valid: bool
    errors: tuple[str, ...] = ()


def validate_editor_source(source: str) -> EditorValidation:
    errors: list[str] = []
    if len(source.encode("utf-8")) > MAX_EDITOR_BYTES:
        errors.append("Content exceeds 500 KB.")
    if RAW_HTML_PATTERN.search(source):
        errors.append("Raw HTML is not supported.")
    if _contains_unapproved_image(source):
        errors.append("Images must use approved media paths.")
    return EditorValidation(valid=not errors, errors=tuple(errors))


def _contains_unapproved_image(source: str) -> bool:
    for match in IMAGE_PATTERN.finditer(source):
        target = match.group(1).strip("<>")
        if not target.startswith(APPROVED_IMAGE_PREFIXES):
            return True
    return False
