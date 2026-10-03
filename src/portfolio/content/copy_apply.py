"""Apply owner-reviewed Markdown copy files to projects, blog posts and experience entries.

The data files live in the sibling ``copy/`` directory (data only, not a Python package).
This module is deliberately not named ``copy`` so it never collides with that directory
or shadows the standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from portfolio.content.models import BlogPost, Experience, Project
from portfolio.content.rendering import render_experience_markdown, render_markdown
from portfolio.extensions import db

COPY_DIR = Path(__file__).parent / "copy"
KINDS = {"project", "blog", "experience"}
FIELDS = {
    "project": {
        "title",
        "summary",
        "role",
        "stack",
        "year",
        "result_headline",
        "seo_title",
        "seo_description",
    },
    "blog": {"title", "summary", "seo_title", "seo_description"},
    "experience": {"summary"},
}


class CopyError(ValueError):
    pass


@dataclass(frozen=True)
class CopyDoc:
    kind: str
    match: str
    fields: dict[str, str] = field(default_factory=dict)
    body: str = ""


def parse_copy_file(text: str) -> CopyDoc:
    if not text.startswith("---\n"):
        raise CopyError("missing front matter (file must start with '---')")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise CopyError("missing front matter terminator '---'")
    meta: dict[str, str] = {}
    for line in head.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, colon, value = line.partition(":")
        if not colon:
            raise CopyError(f"bad front matter line: {line!r}")
        meta[key.strip()] = value.split("  #", 1)[0].strip()
    kind, match = meta.pop("type", ""), meta.pop("match", "")
    if kind not in KINDS:
        raise CopyError(f"type must be one of {sorted(KINDS)} (got {kind!r})")
    if not match:
        raise CopyError("match is required")
    unknown = set(meta) - FIELDS[kind]
    if unknown:
        raise CopyError(f"unknown field(s) for {kind}: {sorted(unknown)}")
    if len(meta.get("summary", "")) > 320:
        raise CopyError("summary must be 320 characters or fewer")
    clean_body = body.strip("\n") + "\n" if body.strip() else ""
    return CopyDoc(kind=kind, match=match, fields=meta, body=clean_body)


def _find(doc: CopyDoc) -> Project | BlogPost | Experience:
    entity: Project | BlogPost | Experience | None
    if doc.kind == "project":
        entity = db.session.scalar(select(Project).where(Project.slug == doc.match))
    elif doc.kind == "blog":
        entity = db.session.scalar(select(BlogPost).where(BlogPost.slug == doc.match))
    else:
        organization, _, role = (part.strip() for part in doc.match.partition("|"))
        entity = db.session.scalar(
            select(Experience).where(
                Experience.organization == organization, Experience.role == role
            )
        )
    if entity is None:
        if doc.kind == "experience":
            raise CopyError(f"no experience entry {doc.match!r}")
        raise CopyError(f"no {doc.kind} with slug {doc.match!r}")
    return entity


def apply_copy_doc(doc: CopyDoc, *, dry_run: bool = False) -> str:
    entity = _find(doc)
    changes: dict[str, str] = dict(doc.fields)
    if doc.body:
        changes["source_markdown"] = doc.body
        changes["rendered_html"] = (
            render_experience_markdown(doc.body)
            if doc.kind == "experience"
            else render_markdown(doc.body)
        )
    changed = [
        name for name, value in changes.items() if (getattr(entity, name, None) or "") != value
    ]
    if not changed:
        return f"{doc.kind} {doc.match}: unchanged"
    if not dry_run:
        for name in changed:
            setattr(entity, name, changes[name])
        entity.version = (entity.version or 0) + 1
    prefix = "would update" if dry_run else "updated"
    return f"{doc.kind} {doc.match}: {prefix} {', '.join(sorted(changed))}"
