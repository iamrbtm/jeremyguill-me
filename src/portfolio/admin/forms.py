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
    order: int = 0
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
            form.order = int(data.get("order", "0") or "0")
        except ValueError:
            form.add_error("order", "Order must be a whole number")
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
            order=self.order,
        )


def project_form_for(entity) -> ProjectForm:
    return ProjectForm(
        title=entity.title,
        slug=entity.slug,
        summary=entity.summary,
        source_markdown=entity.source_markdown,
        order=entity.sort_position,
        version=entity.version,
    )


@dataclass
class ExperienceForm:
    organization: str = ""
    role: str = ""
    summary: str = ""
    source_markdown: str = ""
    start_date: str = ""
    end_date: str = ""
    order: int = 0
    visible: bool = True
    version: int | None = None
    errors: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, str]) -> "ExperienceForm":
        form = cls(
            organization=data.get("organization", "").strip(),
            role=data.get("role", "").strip(),
            summary=data.get("summary", "").strip(),
            source_markdown=data.get("source_markdown", ""),
            start_date=data.get("start_date", "").strip(),
            end_date=data.get("end_date", "").strip(),
            visible=data.get("visible", "on") == "on",
        )
        try:
            form.order = int(data.get("order", "0") or "0")
        except ValueError:
            form.add_error("order", "Order must be a whole number")
        try:
            form.version = int(data.get("version", ""))
        except ValueError:
            form.add_error("version", "Version is required")
        return form

    def validate(self) -> bool:
        if not self.organization:
            self.add_error("organization", "Organization is required")
        if not self.role:
            self.add_error("role", "Role is required")
        if self.version is None:
            self.add_error("version", "Version is required")
        return not self.errors

    def add_error(self, field_name: str, message: str) -> None:
        self.errors.setdefault(field_name, []).append(message)


def experience_form_for(entity) -> ExperienceForm:
    return ExperienceForm(
        organization=entity.organization,
        role=entity.role,
        summary=entity.summary,
        source_markdown=entity.source_markdown,
        start_date=entity.start_date or "",
        end_date=entity.end_date or "",
        order=entity.sort_position,
        visible=entity.visible,
        version=entity.version,
    )


@dataclass
class BlogForm:
    title: str = ""
    slug: str = ""
    summary: str = ""
    source_markdown: str = ""
    seo_title: str = ""
    seo_description: str = ""
    seo_target_query: str = ""
    version: int | None = None
    errors: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, str]) -> "BlogForm":
        form = cls(
            title=data.get("title", "").strip(),
            slug=data.get("slug", "").strip(),
            summary=data.get("summary", "").strip(),
            source_markdown=data.get("source_markdown", ""),
            seo_title=data.get("seo_title", "").strip(),
            seo_description=data.get("seo_description", "").strip(),
            seo_target_query=data.get("seo_target_query", "").strip(),
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
        if len(self.seo_title) > 180:
            self.add_error("seo_title", "SEO title must be 180 characters or fewer")
        if len(self.seo_description) > 320:
            self.add_error("seo_description", "SEO description must be 320 characters or fewer")
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


def blog_form_for(entity) -> BlogForm:
    return BlogForm(
        title=entity.title,
        slug=entity.slug,
        summary=entity.summary,
        source_markdown=entity.source_markdown,
        seo_title=entity.seo_title or "",
        seo_description=entity.seo_description or "",
        seo_target_query=entity.seo_target_query or "",
        version=entity.version,
    )
