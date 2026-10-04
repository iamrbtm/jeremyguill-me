"""Generate the one-page github.io portfolio from the public site-content JSON export.

Usage:
    uv run python scripts/build_one_page.py [--source URL_OR_FILE] [--origin ORIGIN]
        [--output PATH] [--no-copy-overrides]

The page is a single self-contained HTML file (CSS and JS inlined from scripts/one_page/).
Images and fonts are linked from the origin site.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, StrictUndefined
from markupsafe import Markup

from portfolio.content.copy_apply import CopyError, parse_copy_file
from portfolio.content.rendering import render_markdown
from portfolio.content.toc import enhance_case_study_html

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = Path(__file__).resolve().parent / "one_page"
COPY_DIR = REPO_ROOT / "src" / "portfolio" / "content" / "copy"
DEFAULT_ORIGIN = "https://jeremyguill.me"
DEFAULT_OUTPUT = REPO_ROOT / "one_page" / "index.html"
FETCH_TIMEOUT = 20.0

_TAG_SPAN = re.compile(r"<[^>]*>")
_ID_ATTR = re.compile(r"""\sid\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
_SCRIPT = re.compile(r"<script\b.*?</script\s*>|<script\b[^>]*>", re.IGNORECASE | re.DOTALL)
_TEMPLATE_TAG = re.compile(r"</?template\b[^>]*>", re.IGNORECASE)
_ROOT_URL = re.compile(r"""\b(src|href)(\s*=\s*)(["']?)/(?!/)""", re.IGNORECASE)
_MAX_PASSES = 20


def _strip_dangerous(html: str) -> str:
    """Remove comments, scripts and template tags until nothing more can be removed."""
    for _ in range(_MAX_PASSES):
        cleaned = _TEMPLATE_TAG.sub("", _SCRIPT.sub("", _COMMENT.sub("", html)))
        if cleaned == html:
            return cleaned
        html = cleaned
    # Still changing after the cap: drop every angle bracket rather than risk a reassembled tag.
    return html.replace("<", "&lt;")


def _fix_tag(origin: str, match: re.Match[str]) -> str:
    tag = _ID_ATTR.sub("", match.group(0))
    return _ROOT_URL.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{origin}/", tag)


class BuildError(Exception):
    pass


def _prepare_body(html: str, origin: str, *, tables: bool) -> Markup:
    """Make CMS-sanitized HTML safe to embed: no ids, scripts or template tags; absolute URLs."""
    html = _strip_dangerous(html or "")
    if tables:
        html, _ = enhance_case_study_html(html)
    html = _TAG_SPAN.sub(lambda m: _fix_tag(origin, m), html)
    return Markup(html)  # noqa: S704 - sanitized upstream by nh3, hardened above


def _apply_overrides(
    projects: list[dict[str, Any]], overrides: dict[str, dict[str, Any]] | None
) -> list[dict[str, Any]]:
    overrides = overrides or {}
    known = {p["slug"] for p in projects}
    for slug in sorted(set(overrides) - known):
        print(f"warning: copy override for unknown project {slug!r} ignored", file=sys.stderr)
    merged = []
    for project in projects:
        item = dict(project)
        for key, value in overrides.get(project["slug"], {}).items():
            item[key] = value
        merged.append(item)
    return merged


def _environment() -> Environment:
    return Environment(autoescape=True, undefined=StrictUndefined, trim_blocks=True)


def build_page(
    data: dict[str, Any],
    *,
    origin: str,
    overrides: dict[str, dict[str, Any]] | None = None,
    source: str = "site-content.json",
    now: datetime | None = None,
) -> str:
    origin = origin.rstrip("/")
    now = now or datetime.now(UTC)
    profile = data["profile"]
    name = profile.get("display_name") or "Jeremy Guill"
    summary = profile.get("summary") or (
        "A portfolio of practical software, database, automation, and support work built "
        "around real problems and measurable workflow improvements."
    )

    projects = []
    for project in _apply_overrides(list(data.get("projects", [])), overrides):
        item = dict(project)
        item["stack"] = list(item.get("stack") or [])
        item["gallery"] = list(item.get("gallery") or [])
        item["body_html"] = _prepare_body(item.get("body_html", ""), origin, tables=True)
        projects.append(item)

    experience = []
    for entry in data.get("experience", []):
        item = dict(entry)
        item["body_html"] = _prepare_body(item.get("body_html", ""), origin, tables=False)
        experience.append(item)

    css = (ASSET_DIR / "style.css").read_text(encoding="utf-8").replace("__ORIGIN__", origin)
    js = (ASSET_DIR / "app.js").read_text(encoding="utf-8")
    template = _environment().from_string((ASSET_DIR / "template.html").read_text("utf-8"))
    return template.render(
        origin=origin,
        source=source.replace("--", "- -"),
        generated_on=now.strftime("%Y-%m-%d"),
        year=now.year,
        title=f"{name} | Software and Workflow Portfolio",
        description=summary,
        name=name,
        headline=profile.get("headline") or "",
        summary=summary,
        availability=profile.get("availability_text"),
        linkedin_url=profile.get("linkedin_url"),
        github_url=profile.get("github_url"),
        capabilities=data.get("capabilities", []),
        projects=projects,
        experience=experience,
        css=Markup(css),  # noqa: S704 - repository-controlled asset
        js=Markup(js),  # noqa: S704 - repository-controlled asset
    )


def load_copy_overrides(copy_dir: Path = COPY_DIR) -> dict[str, dict[str, Any]]:
    """Read reviewed project copy files (front matter plus Markdown body) as overrides."""
    overrides: dict[str, dict[str, Any]] = {}
    for path in sorted(copy_dir.glob("project-*.md")):
        try:
            doc = parse_copy_file(path.read_text(encoding="utf-8"))
        except CopyError as exc:
            raise BuildError(f"{path.name}: {exc}") from exc
        if doc.kind != "project":
            continue
        fields: dict[str, Any] = {
            key: doc.fields[key]
            for key in ("title", "summary", "role", "year", "result_headline")
            if doc.fields.get(key)
        }
        if doc.fields.get("stack"):
            fields["stack"] = [s.strip() for s in doc.fields["stack"].split(",") if s.strip()]
        if doc.body:
            fields["body_html"] = render_markdown(doc.body)
        overrides[doc.match] = fields
    return overrides


def load_source(source: str) -> dict[str, Any]:
    try:
        if source.startswith(("http://", "https://")):
            response = httpx.get(source, timeout=FETCH_TIMEOUT, follow_redirects=True)
            response.raise_for_status()
            text = response.text
        else:
            text = Path(source).read_text(encoding="utf-8")
        data = json.loads(text)
    except (httpx.HTTPError, OSError) as exc:
        raise BuildError(f"could not read {source}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"{source} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "profile" not in data:
        raise BuildError(f"{source} does not look like a site-content export")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", help="URL or file of the JSON export")
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-copy-overrides", action="store_true")
    args = parser.parse_args(argv)
    origin = args.origin.rstrip("/")
    source = args.source or f"{origin}/api/site-content.json"
    try:
        data = load_source(source)
        overrides = None if args.no_copy_overrides else load_copy_overrides()
        html = build_page(data, origin=origin, overrides=overrides, source=source)
    except (BuildError, KeyError, TypeError) as exc:
        detail = repr(exc) if isinstance(exc, KeyError | TypeError) else str(exc)
        print(f"error: {detail}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"wrote {args.output} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
