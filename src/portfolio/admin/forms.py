from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from portfolio.content.schemas import ContentCommand


@dataclass
class ProjectForm:
    title: str = ""
    slug: str = ""
    summary: str = ""
    source_markdown: str = ""
    version: int | None = None
    errors: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, str]) -> "ProjectForm":
        form = cls(
            title=data.get("title", "").strip(),
            slug=data.get("slug", "").strip(),
            summary=data.get("summary", "").strip(),
            source_markdown=data.get("source_markdown", ""),
        )
        try:
            form.version = int(data.get("version", ""))
        except ValueError:
            form.add_error("version", "Version is required")
        return form

    def validate(self) -> bool:
        if not self.title:
            self.add_error("title", "Title is required")
        if not self.slug:
            self.add_error("slug", "Slug is required")
        if self.version is None:
            self.add_error("version", "Version is required")
        if len(self.summary) > 320:
            self.add_error("summary", "Summary must be 320 characters or fewer")
        return not self.errors

    def add_error(self, field_name: str, message: str) -> None:
        self.errors.setdefault(field_name, []).append(message)

    def to_command(self) -> ContentCommand:
        return ContentCommand(
            title=self.title,
            slug=self.slug,
            summary=self.summary,
            source_markdown=self.source_markdown,
        )


def project_form_for(entity) -> ProjectForm:
    return ProjectForm(
        title=entity.title,
        slug=entity.slug,
        summary=entity.summary,
        source_markdown=entity.source_markdown,
        version=entity.version,
    )
