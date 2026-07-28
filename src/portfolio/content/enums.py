from __future__ import annotations

from enum import StrEnum


class PublicationState(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"
