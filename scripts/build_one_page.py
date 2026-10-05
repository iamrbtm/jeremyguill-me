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
import nh3
from jinja2 import Environment, StrictUndefined, UndefinedError
from markupsafe import Markup

from portfolio.content.copy_apply import CopyError, parse_copy_file
from portfolio.content.rendering import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_TAGS,
    EXPERIENCE_ALLOWED_ATTRIBUTES,
    EXPERIENCE_ALLOWED_TAGS,
    render_markdown,
)
from portfolio.content.toc import enhance_case_study_html

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = Path(__file__).resolve().parent / "one_page"
COPY_DIR = REPO_ROOT / "src" / "portfolio" / "content" / "copy"
DEFAULT_ORIGIN = "https://jeremyguill.me"
DEFAULT_OUTPUT = REPO_ROOT / "one_page" / "index.html"
FETCH_TIMEOUT = 20.0

_SAFE_ABSOLUTE = re.compile(r"(?:https?://|mailto:)", re.IGNORECASE)
_UNSAFE_CHARS = re.compile(r"[\x00-\x20\x7f]")
_TABLE_WRAPPER = '<div class="table-scroll">'
# Scrollable regions must be keyboard focusable (axe: scrollable-region-focusable). nh3 strips
# tabindex/role/aria-label, so these are added after sanitising, by exact string replacement.
_TABLE_WRAPPER_FOCUSABLE = (
    '<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable table">'
)
_PRE_FOCUSABLE = '<pre tabindex="0" role="region" aria-label="Code sample">'


def _safe_url(value: str, origin: str) -> str | None:
    """Keep fragment, http(s)/mailto URLs; absolutise root-relative ones; drop everything else."""
    if _UNSAFE_CHARS.search(value):
        return None
    if value.startswith("#") or _SAFE_ABSOLUTE.match(value):
        return value
    if value.startswith("/") and value[1:2] not in ("/", "\\"):
        return origin + value
    return None


class BuildError(Exception):
    pass


class SourceNotFound(BuildError):
    """The URL source answered HTTP 404 (production not deployed yet)."""


def _prepare_body(html: str, origin: str, *, tables: bool) -> Markup:
    """Re-sanitise CMS HTML with the site allowlist (parser based) and absolutise URLs.

    The export is normally already clean, but a hijacked or hand-edited source must not be able
    to inject script, event handlers or unsafe URLs into the published page.
    """
    html = html or ""
    if tables:
        html, _ = enhance_case_study_html(html)

    def attribute_filter(tag: str, attr: str, value: str) -> str | None:
        if attr in ("src", "href"):
            return _safe_url(value, origin)
        return value

    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS if tables else EXPERIENCE_ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES if tables else EXPERIENCE_ALLOWED_ATTRIBUTES,
        url_schemes={"https", "http", "mailto"},
        link_rel="noopener noreferrer",
        strip_comments=True,
        attribute_filter=attribute_filter,
    )
    if tables:
        cleaned = cleaned.replace(_TABLE_WRAPPER, _TABLE_WRAPPER_FOCUSABLE)
        cleaned = cleaned.replace("<pre>", _PRE_FOCUSABLE)
    return Markup(cleaned)  # noqa: S704 - sanitised by nh3 above


def _origin_image(image: Any, origin: str) -> dict[str, Any] | None:
    """Keep an image only if its URL is served by the origin site."""
    if isinstance(image, dict) and str(image.get("url", "")).startswith(origin + "/"):
        return dict(image)
    return None


def _https_url(value: Any) -> str | None:
    return value if isinstance(value, str) and value.startswith("https://") else None


def _public_source(source: str) -> str:
    """Name the source in the page comment without leaking local filesystem paths."""
    if source.startswith(("http://", "https://")):
        return source
    return Path(source).name


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
        if project["slug"] in overrides:
            print(f"applied copy override: {project['slug']}", file=sys.stderr)
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
    allow_origin_mismatch: bool = False,
    now: datetime | None = None,
) -> str:
    origin = origin.rstrip("/")
    export_origin = str(data.get("origin") or "").rstrip("/")
    if export_origin != origin and not allow_origin_mismatch:
        raise BuildError(
            f"export origin {export_origin or '(missing)'} does not match --origin {origin}; "
            "pass --allow-origin-mismatch if this is intended"
        )
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
        if not str(item.get("url", "")).startswith(origin + "/"):
            raise BuildError(
                f"project {item.get('slug')!r} url is not on {origin}: {item.get('url')!r}"
            )
        item["hero"] = _origin_image(item.get("hero"), origin)
        item["gallery"] = [
            img for img in (_origin_image(g, origin) for g in item.get("gallery") or []) if img
        ]
        item["body_html"] = _prepare_body(item.get("body_html", ""), origin, tables=True)
        projects.append(item)

    experience = []
    for entry in data.get("experience", []):
        item = dict(entry)
        item["logo"] = _origin_image(item.get("logo"), origin)
        item["body_html"] = _prepare_body(item.get("body_html", ""), origin, tables=False)
        experience.append(item)

    css = (ASSET_DIR / "style.css").read_text(encoding="utf-8").replace("__ORIGIN__", origin)
    js = (ASSET_DIR / "app.js").read_text(encoding="utf-8")
    template = _environment().from_string((ASSET_DIR / "template.html").read_text("utf-8"))
    return template.render(
        origin=origin,
        source=_public_source(source).replace("--", "- -"),
        year=now.year,
        title=f"{name} | Software and Workflow Portfolio",
        description=summary,
        name=name,
        headline=profile.get("headline") or "",
        summary=summary,
        availability=profile.get("availability_text"),
        linkedin_url=_https_url(profile.get("linkedin_url")),
        github_url=_https_url(profile.get("github_url")),
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
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise SourceNotFound(
                f"production not ready: {source} returned 404 (deploy the main site first)"
            ) from exc
        raise BuildError(f"could not read {source}: {exc}") from exc
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
    parser.add_argument(
        "--allow-origin-mismatch",
        action="store_true",
        help="build even if the export's own origin differs from --origin",
    )
    args = parser.parse_args(argv)
    origin = args.origin.rstrip("/")
    source = args.source or f"{origin}/api/site-content.json"
    try:
        data = load_source(source)
        overrides = None if args.no_copy_overrides else load_copy_overrides()
        html = build_page(
            data,
            origin=origin,
            overrides=overrides,
            source=source,
            allow_origin_mismatch=args.allow_origin_mismatch,
        )
    except SourceNotFound as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (BuildError, KeyError, TypeError, UndefinedError) as exc:
        detail = repr(exc) if isinstance(exc, KeyError | TypeError | UndefinedError) else str(exc)
        print(f"error: {detail}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"wrote {args.output} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
