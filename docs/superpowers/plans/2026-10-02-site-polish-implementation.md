# jeremyguill.me Site Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix what is broken on jeremyguill.me and polish it into a fast, accessible, well-presented portfolio for hiring managers and freelance clients, with privacy-friendly visitor analytics.

**Architecture:** Flask + SQLAlchemy app (`src/portfolio`), content stored in Postgres and edited through the CMS. Code changes ship through ordered tasks (each one test-first, one commit). Content changes ship through (a) idempotent data-fix functions run by Alembic migrations and (b) a `flask content apply-copy` command that applies reviewed Markdown files. New cross-page template data comes from one context processor (`site`). Analytics is a self-hosted Umami container.

**Tech Stack:** Python 3.14, Flask 3, SQLAlchemy 2, Alembic, Jinja2, pytest, ruff, mypy, Pillow, plain CSS/JS (no build step; CSP is `script-src 'self'; style-src 'self'`), Docker Compose, Umami.

**Spec:** `docs/superpowers/specs/2026-10-02-site-polish-design.md`

## Global Constraints

- Run Python through `uv run ...` from the repo root `/mnt/storage/docker/jeremyguill-me`.
- Quality gates after every task: `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`.
- **Known baseline failure, do not fix, do not "fix" by editing the test:** `tests/operations/test_compose_config.py::test_compose_binds_web_to_localhost_only` (compose publishes `7777:7777`, test expects `127.0.0.1:7777:8000`). Report it to the owner at the end; it is a deployment-security decision, not part of this work.
- CSP stays strict: no inline `<script>`/`<style>`/`style=""`, no third-party hosts, except the single analytics origin added in Task 17.
- Never invent facts, metrics, quotes, or testimonials. Copy comes from the owner or from text already on the site, and is flagged for owner review.
- The working tree holds ~113 unrelated staged changes. **Never `git add -A` / `git commit -a`.** Commit with explicit paths: `git add <paths> && git commit -m "<msg>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- <paths>`.
- Migration ids are strings: `0008_content_fixes`, `0009_profile_project_fields`; `down_revision` of 0008 is `0007_active_job_uniqueness`.
- Colours/spacing use the existing CSS custom properties in `static/assets/site.css` (`--ink`, `--ink-soft`, `--paper`, `--gray`, `--line`, `--blue`, `--blue-bright`, `--measure`).
- Every page keeps exactly one `<h1>`; every `<img>` has `alt` and `width`/`height`.
- Deviations from the spec (decided while planning, with reasons): (1) keep the existing Poppins + Open Sans pairing instead of a new pairing, to avoid a redesign; (2) media variants are cached 30 days, not 1 year, because a re-processed variant could reuse a URL; (3) no collapsible sections on the Dudefish page, the generated table of contents and scrollable tables cover the readability problem; (4) the profile has no admin editor today, so social links and availability are set with a new CLI command; (5) the Phase 4 prose is applied by `flask content apply-copy`, not by migrations, so the owner can review files first.

## Review Focus

Failure modes the spec implies but a single task's happy path would not catch. Each has a test in the task named.

1. Production starts with `PUBLIC_ORIGIN` unset (defaults to localhost) or `http://` → must refuse to boot, with a message naming the variable (Task 1).
2. Rendering an error page while the database is down must still return the 404/500 page, not a second exception (Task 5).
3. A project with no hero image, no stack, no year, or no headings must still render on `/`, `/work`, and its own page, with no empty chips/TOC/broken `<img>` (Tasks 12, 13).
4. The old slug `/work/medial-mileage` (with or without a query string) must 308 to `/work/medical-mileage`, and the data fix must be safe to run twice (Task 4).
5. A brand-new site with zero published posts and zero projects must produce a valid sitemap, RSS feed, and homepage (Tasks 3, 12, 16).
6. With JavaScript disabled the full nav is visible and `.reveal` content is visible (Tasks 10, 15).

## File Structure

| File | Responsibility |
|---|---|
| `src/portfolio/config.py` | env parsing + production origin validation + analytics settings |
| `src/portfolio/public/chrome.py` (new) | `SiteChrome`: lazy per-request data for every page (profile, nav flags, analytics, year) |
| `src/portfolio/assets.py` (new) | `static_url()` content-hash helper + static/media cache headers |
| `src/portfolio/content/data_fixes.py` (new) | idempotent Core-SQL fixes used by migration 0008 |
| `src/portfolio/content/copy.py` (new) | parse + apply reviewed Markdown copy files (`apply-copy`) |
| `src/portfolio/content/toc.py` (new) | heading ids, table of contents, table wrapping, reading time |
| `src/portfolio/public/view_models.py` | `ProjectCardView`, `build_project_cards`, blog-section rule |
| `src/portfolio/seo/*` | metadata, JSON-LD, sitemap, RSS, security.txt |
| `src/portfolio/security/headers.py` | per-path CSP, COOP |
| `src/portfolio/static/assets/components.css` (new) | new component styles (nav toggle, cards, glance, TOC, footer, forms) |
| `src/portfolio/static/assets/theme.css` (new) | dark mode + print + reduced-motion |
| `scripts/make_brand_assets.py` (new) | favicon, social card, WebP backgrounds, portrait variants |
| `migrations/versions/0008_content_fixes.py`, `0009_profile_project_fields.py` (new) | data fixes; new columns |

---

# Phase 0: Hotfixes

### Task 1: Refuse to boot with a wrong production origin

**Files:**
- Modify: `src/portfolio/config.py`
- Modify: `.env.example`
- Create: `tests/unit/test_config.py`

**Interfaces:**
- Produces: `validate_public_origin(env: str, origin: str) -> None` (raises `RuntimeError`), called inside `Settings.from_env()`.

- [ ] **Step 1: Write the failing test** `tests/unit/test_config.py`

```python
from __future__ import annotations

import pytest

from portfolio.config import Settings

SECRET = "x" * 40


def _production(monkeypatch, origin: str | None) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", SECRET)
    if origin is None:
        monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    else:
        monkeypatch.setenv("PUBLIC_ORIGIN", origin)


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "http://localhost:5000",
        "https://localhost",
        "http://127.0.0.1:7777",
        "http://jeremyguill.me",
        "jeremyguill.me",
    ],
)
def test_production_rejects_bad_public_origin(monkeypatch, origin):
    _production(monkeypatch, origin)

    with pytest.raises(RuntimeError, match="PUBLIC_ORIGIN"):
        Settings.from_env()


def test_production_accepts_https_origin(monkeypatch):
    _production(monkeypatch, "https://jeremyguill.me")

    assert Settings.from_env().public_origin == "https://jeremyguill.me"


def test_development_allows_localhost_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://localhost:5000")

    assert Settings.from_env().public_origin == "http://localhost:5000"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: the `rejects` cases FAIL (`DID NOT RAISE`).

- [ ] **Step 3: Implement.** In `src/portfolio/config.py` add at top `from urllib.parse import urlparse`, then above `class Settings`:

```python
_LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "0.0.0.0", "::1"}


def validate_public_origin(env: str, origin: str) -> None:
    if env != "production":
        return
    parsed = urlparse(origin)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host in _LOCAL_HOSTS or host.endswith(".localhost"):
        raise RuntimeError(
            f"PUBLIC_ORIGIN must be the public https origin in production (got {origin!r})"
        )
```

In `from_env`, replace the inline `public_origin=os.getenv(...)` with a local variable computed before `return cls(`:

```python
        public_origin = os.getenv("PUBLIC_ORIGIN", "http://localhost:5000")
        validate_public_origin(env, public_origin)
```
and pass `public_origin=public_origin,`.

- [ ] **Step 4: Update `.env.example`**: replace `PUBLIC_ORIGIN=http://localhost:5000` with

```
# Local dev uses http://localhost:5000. PRODUCTION MUST be the real https origin or the app will not start.
PUBLIC_ORIGIN=http://localhost:5000
```

- [ ] **Step 5: Verify**

Run: `uv run pytest tests/unit/test_config.py tests/unit/test_app_factory.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/config.py .env.example tests/unit/test_config.py
git commit -m "fix: refuse production boot with a localhost or non-https PUBLIC_ORIGIN" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- src/portfolio/config.py .env.example tests/unit/test_config.py
```

### Task 2: Correct social and JSON-LD metadata

**Files:**
- Modify: `src/portfolio/seo/schemas.py`, `src/portfolio/seo/services.py`, `src/portfolio/templates/components/metadata.html`, `src/portfolio/public/routes.py` (home route only)
- Create: `tests/unit/seo/test_social_metadata.py`

**Interfaces:**
- Produces: `SeoPage.name: str | None = None`; `PageMetadata.og_title: str`, `PageMetadata.og_type: str`; constant `DEFAULT_SOCIAL_IMAGE_PATH = "/static/assets/img/og-default.png"` in `seo/services.py`. `open_graph_image` is always an absolute URL (falls back to the default image).

- [ ] **Step 1: Write failing tests**

```python
from __future__ import annotations

from portfolio.seo.schemas import SeoPage
from portfolio.seo.services import build_metadata


def _meta(app, **kw):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    with app.app_context():
        return build_metadata(
            SeoPage(title="T | Jeremy Guill", summary="S", canonical_path="/x", is_published=True, **kw)
        )


def test_social_image_defaults_to_absolute_site_card(app):
    meta = _meta(app)

    assert meta.open_graph_image == "https://example.test/static/assets/img/og-default.png"


def test_person_json_ld_uses_display_name_not_seo_title(app):
    meta = _meta(app, kind="person", seo_title="Custom Software Portfolio", name="Jeremy Guill")

    assert meta.json_ld["@type"] == "Person"
    assert meta.json_ld["name"] == "Jeremy Guill"


def test_blog_pages_use_article_og_type(app):
    assert _meta(app, kind="blog").og_type == "article"
    assert _meta(app).og_type == "website"


def test_homepage_renders_twitter_and_og_tags(client):
    html = client.get("/").get_data(as_text=True)

    assert 'name="twitter:card" content="summary_large_image"' in html
    assert 'property="og:site_name" content="Jeremy Guill"' in html
    assert 'property="og:image" content="' in html
    assert 'property="og:image:width" content="1200"' in html
```

- [ ] **Step 2: Run:** `uv run pytest tests/unit/seo/test_social_metadata.py -v` → FAIL (attributes missing).

- [ ] **Step 3: Implement.** `schemas.py`: add `name: str | None = None` to `SeoPage` (after `social_image_url`); add `og_title: str` and `og_type: str` to `PageMetadata` (after `json_ld`, as non-default fields, so update every construction; only `build_metadata` constructs it).

`services.py`:

```python
DEFAULT_SOCIAL_IMAGE_PATH = "/static/assets/img/og-default.png"


def build_metadata(page: SeoPage) -> PageMetadata:
    canonical = absolute_url(page.canonical_path)
    return PageMetadata(
        title=page.seo_title or page.title,
        description=page.seo_description or page.summary,
        canonical=canonical,
        robots="index,follow" if page.is_published else "noindex,nofollow",
        open_graph_image=page.social_image_url or absolute_url(DEFAULT_SOCIAL_IMAGE_PATH),
        json_ld=build_json_ld(page),
        og_title=page.seo_title or page.title,
        og_type="article" if page.kind == "blog" else "website",
    )
```
In `build_json_ld`, set `"name": page.name or page.seo_title or page.title,` and make `image` use the default when `social_image_url` is empty: `data["image"] = page.social_image_url or absolute_url(DEFAULT_SOCIAL_IMAGE_PATH)`.

`metadata.html` (replace whole file):

```html
<meta name="description" content="{{ metadata.description }}">
<meta name="robots" content="{{ metadata.robots }}">
<link rel="canonical" href="{{ metadata.canonical }}">
<meta property="og:site_name" content="Jeremy Guill">
<meta property="og:locale" content="en_US">
<meta property="og:type" content="{{ metadata.og_type }}">
<meta property="og:title" content="{{ metadata.og_title }}">
<meta property="og:description" content="{{ metadata.description }}">
<meta property="og:url" content="{{ metadata.canonical }}">
<meta property="og:image" content="{{ metadata.open_graph_image }}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ metadata.og_title }}">
<meta name="twitter:description" content="{{ metadata.description }}">
<meta name="twitter:image" content="{{ metadata.open_graph_image }}">
<script type="application/ld+json">{{ metadata.json_ld|tojson }}</script>
```

`public/routes.py` `home()`: add `name=view.profile.display_name or "Jeremy Guill",` to the `SeoPage(...)` call.

- [ ] **Step 4: Verify:** `uv run pytest tests/unit/seo tests/integration/public tests/security -q` → PASS (existing metadata tests may assert the old `og_image` absence; update such assertions to the new behaviour).

- [ ] **Step 5: Commit**

```bash
git add src/portfolio/seo/schemas.py src/portfolio/seo/services.py src/portfolio/templates/components/metadata.html src/portfolio/public/routes.py tests/unit/seo/test_social_metadata.py
git commit -m "fix: complete Open Graph/Twitter metadata and correct Person JSON-LD name" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- src/portfolio/seo/schemas.py src/portfolio/seo/services.py src/portfolio/templates/components/metadata.html src/portfolio/public/routes.py tests/unit/seo/test_social_metadata.py
```
(include any existing test files you had to update in both path lists.)

### Task 3: Complete sitemap, correct robots

**Files:**
- Modify: `src/portfolio/seo/routes.py`, `src/portfolio/templates/sitemap.xml`
- Create: `tests/integration/seo/test_sitemap_complete.py`

**Interfaces:**
- Produces: `SitemapEntry(loc: str, lastmod: datetime | None)` dataclass in `seo/routes.py`.

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project


def test_sitemap_on_empty_site_is_valid_and_has_core_pages(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"

    body = client.get("/sitemap.xml").get_data(as_text=True)

    assert "<urlset" in body
    for path in ("/", "/work", "/experience", "/contact"):
        assert f"<loc>https://example.test{path}</loc>" in body
    assert "/blog" not in body


def test_sitemap_lists_blog_index_posts_and_lastmod(client, app, db_session):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    db_session.add(
        BlogPost(title="P", slug="p", summary="s", state=PublicationState.PUBLISHED)
    )
    db_session.add(
        Project(title="J", slug="j", summary="s", state=PublicationState.PUBLISHED)
    )
    db_session.add(
        Project(title="D", slug="d", summary="s", state=PublicationState.DRAFT)
    )
    db_session.commit()

    body = client.get("/sitemap.xml").get_data(as_text=True)

    assert "<loc>https://example.test/blog</loc>" in body
    assert "<loc>https://example.test/blog/p</loc>" in body
    assert "<loc>https://example.test/work/j</loc>" in body
    assert "/work/d" not in body
    assert "<lastmod>" in body


def test_robots_points_at_configured_origin(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"

    assert "Sitemap: https://example.test/sitemap.xml" in client.get("/robots.txt").get_data(
        as_text=True
    )
```

- [ ] **Step 2:** `uv run pytest tests/integration/seo/test_sitemap_complete.py -v` → FAIL.

- [ ] **Step 3: Implement** `src/portfolio/seo/routes.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from flask import Blueprint, Response, render_template
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project
from portfolio.extensions import db
from portfolio.seo.services import absolute_url

seo_bp = Blueprint("seo", __name__)


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: datetime | None = None


@seo_bp.get("/sitemap.xml")
def sitemap():
    projects = list(
        db.session.execute(
            select(Project)
            .where(Project.state == PublicationState.PUBLISHED)
            .order_by(Project.sort_position, Project.title)
        ).scalars()
    )
    posts = list(
        db.session.execute(
            select(BlogPost)
            .where(BlogPost.state == PublicationState.PUBLISHED)
            .order_by(BlogPost.published_at.desc(), BlogPost.title)
        ).scalars()
    )
    entries = [SitemapEntry(absolute_url(path)) for path in ("/", "/work", "/experience", "/contact")]
    if posts:
        entries.append(SitemapEntry(absolute_url("/blog"), max(p.updated_at for p in posts)))
    entries.extend(
        SitemapEntry(absolute_url(f"/work/{p.slug}"), p.updated_at) for p in projects
    )
    entries.extend(
        SitemapEntry(absolute_url(f"/blog/{p.slug}"), p.updated_at) for p in posts
    )
    return Response(render_template("sitemap.xml", entries=entries), mimetype="application/xml")


@seo_bp.get("/robots.txt")
def robots():
    return Response(
        render_template("robots.txt", sitemap_url=absolute_url("/sitemap.xml")),
        mimetype="text/plain",
    )
```

`templates/sitemap.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{% for entry in entries %}
  <url><loc>{{ entry.loc }}</loc>{% if entry.lastmod %}<lastmod>{{ entry.lastmod.date().isoformat() }}</lastmod>{% endif %}</url>
{% endfor %}
</urlset>
```

- [ ] **Step 4:** `uv run pytest tests/integration/seo tests/unit/seo -q` → PASS (update any old test that expected the exact old sitemap).

- [ ] **Step 5: Commit** the three source files + new test (+ any updated test) with message `feat: complete sitemap with work index, blog, posts and lastmod`.

### Task 4: Data fixes migration (slug typo, blog post, alt text, profile SEO)

**Files:**
- Create: `src/portfolio/content/data_fixes.py`, `migrations/versions/0008_content_fixes.py`, `tests/integration/content/test_data_fixes.py`

**Interfaces:**
- Produces (all take a SQLAlchemy `Connection`, are idempotent, return the number of rows changed): `rename_project_slug(conn, old: str, new: str) -> int`, `fix_blog_post_presentation(conn) -> int`, `backfill_project_alt_text(conn) -> int`, `refresh_profile_seo(conn) -> int`.

These use Core `sa.table(...)` with **only the columns they need**, never the ORM models, because migration 0009 adds model columns that do not exist yet when 0008 runs on a fresh database.

- [ ] **Step 1: Failing tests** `tests/integration/content/test_data_fixes.py`

```python
from __future__ import annotations

from sqlalchemy import select

from portfolio.content import data_fixes
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, Redirect, SiteProfile
from portfolio.extensions import db
from portfolio.media.models import MediaAsset


def _conn():
    return db.session.connection()


def test_rename_slug_creates_redirect_and_is_idempotent(db_session):
    db_session.add(
        Project(title="Medical Mileage", slug="medial-mileage", summary="s", state=PublicationState.PUBLISHED)
    )
    db_session.commit()

    assert data_fixes.rename_project_slug(_conn(), "medial-mileage", "medical-mileage") == 1
    assert data_fixes.rename_project_slug(_conn(), "medial-mileage", "medical-mileage") == 0
    db_session.expire_all()

    assert db_session.scalar(select(Project.slug)) == "medical-mileage"
    redirect = db_session.scalar(select(Redirect))
    assert (redirect.old_path, redirect.new_path) == ("/work/medial-mileage", "/work/medical-mileage")


def test_rename_slug_skips_when_target_exists(db_session):
    db_session.add_all(
        [
            Project(title="A", slug="old", summary="s", state=PublicationState.PUBLISHED),
            Project(title="B", slug="new", summary="s", state=PublicationState.PUBLISHED),
        ]
    )
    db_session.commit()

    assert data_fixes.rename_project_slug(_conn(), "old", "new") == 0


def test_old_slug_redirects_with_308(client, db_session):
    db_session.add(
        Project(title="Medical Mileage", slug="medial-mileage", summary="s", state=PublicationState.PUBLISHED)
    )
    db_session.commit()
    data_fixes.rename_project_slug(_conn(), "medial-mileage", "medical-mileage")
    db_session.commit()

    response = client.get("/work/medial-mileage?utm=x")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/work/medical-mileage")


def test_blog_fix_rewrites_truncated_summary_and_strips_duplicate_h1(db_session):
    db_session.add(
        BlogPost(
            title="Why Slapping a Jet Engine on a Unicycle Isn’t a Tech Strategy",
            slug="why-slapping-a-jet-engine-on-a-unicycle-isnt-a-tech-strategy",
            summary="Intro. Read on for a fresh, upbeat take",
            source_markdown="# Why Slapping a Jet Engine on a Unicycle Isn’t a Tech Strategy\n\nHello, world!",
            rendered_html="<p>Why Slapping a Jet Engine on a Unicycle Isn’t a Tech StrategyHello</p>",
            state=PublicationState.PUBLISHED,
        )
    )
    db_session.commit()

    assert data_fixes.fix_blog_post_presentation(_conn()) == 1
    assert data_fixes.fix_blog_post_presentation(_conn()) == 0
    db_session.expire_all()
    post = db_session.scalar(select(BlogPost))

    assert not post.summary.endswith("upbeat take")
    assert len(post.summary) <= 320
    assert post.source_markdown.startswith("Hello, world!")
    assert "Hello, world!" in post.rendered_html
    assert "Unicycle Isn’t a Tech StrategyHello" not in post.rendered_html


def test_alt_text_backfill_only_fills_blank_or_title_only_alts(db_session):
    blank = MediaAsset(original_filename="a.png", storage_key="k/a", mime_type="image/png", byte_size=1, alt_text="", private=False)
    titled = MediaAsset(original_filename="b.png", storage_key="k/b", mime_type="image/png", byte_size=1, alt_text="Career Groove", private=False)
    custom = MediaAsset(original_filename="c.png", storage_key="k/c", mime_type="image/png", byte_size=1, alt_text="Dashboard showing five jobs", private=False)
    db_session.add_all([blank, titled, custom])
    db_session.flush()
    db_session.add_all(
        [
            Project(title="One", slug="one", summary="s", state=PublicationState.PUBLISHED, hero_media_id=blank.id),
            Project(title="Career Groove", slug="cg", summary="s", state=PublicationState.PUBLISHED, hero_media_id=titled.id),
            Project(title="Three", slug="three", summary="s", state=PublicationState.PUBLISHED, hero_media_id=custom.id),
        ]
    )
    db_session.commit()

    assert data_fixes.backfill_project_alt_text(_conn()) == 2
    db_session.expire_all()
    alts = {a.original_filename: a.alt_text for a in db_session.scalars(select(MediaAsset))}

    assert alts["a.png"] == "One project preview"
    assert alts["b.png"] == "Career Groove project preview"
    assert alts["c.png"] == "Dashboard showing five jobs"


def test_profile_seo_refresh_only_replaces_known_generic_text(db_session):
    db_session.add(
        SiteProfile(
            seo_title="Custom Software Development Portfolio",
            seo_description="Discover how Jeremy Guill specializes in custom software. Our portfolio showcases our expertise.",
        )
    )
    db_session.commit()

    assert data_fixes.refresh_profile_seo(_conn()) == 1
    db_session.expire_all()
    profile = db_session.scalar(select(SiteProfile))

    assert profile.seo_title == "Jeremy Guill | Software and Workflow Portfolio"
    assert "Our portfolio" not in profile.seo_description
    assert data_fixes.refresh_profile_seo(_conn()) == 0
```

- [ ] **Step 2:** `uv run pytest tests/integration/content/test_data_fixes.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** `src/portfolio/content/data_fixes.py`:

```python
"""Idempotent production data fixes, shared by migration 0008 and tests.

Uses Core tables with only the needed columns so it works at any schema revision.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from portfolio.content.rendering import render_markdown

projects = sa.table(
    "projects",
    sa.column("id", sa.Uuid()),
    sa.column("title", sa.String()),
    sa.column("slug", sa.String()),
    sa.column("hero_media_id", sa.Uuid()),
)
blog_posts = sa.table(
    "blog_posts",
    sa.column("id", sa.Uuid()),
    sa.column("title", sa.String()),
    sa.column("slug", sa.String()),
    sa.column("summary", sa.String()),
    sa.column("source_markdown", sa.Text()),
    sa.column("rendered_html", sa.Text()),
)
redirects = sa.table(
    "redirects",
    sa.column("id", sa.Uuid()),
    sa.column("old_path", sa.String()),
    sa.column("new_path", sa.String()),
    sa.column("entity_type", sa.String()),
    sa.column("entity_id", sa.Uuid()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
media_assets = sa.table(
    "media_assets",
    sa.column("id", sa.Uuid()),
    sa.column("alt_text", sa.String()),
)
site_profiles = sa.table(
    "site_profiles",
    sa.column("id", sa.Uuid()),
    sa.column("seo_title", sa.String()),
    sa.column("seo_description", sa.String()),
)

BLOG_SLUG = "why-slapping-a-jet-engine-on-a-unicycle-isnt-a-tech-strategy"
BLOG_SUMMARY = (
    "Software should be the competent, mostly invisible sidekick in your workday, not the main "
    "character. Why digitizing a messy workflow only makes the mess faster, and what to do instead."
)
PROFILE_SEO_TITLE = "Jeremy Guill | Software and Workflow Portfolio"
PROFILE_SEO_DESCRIPTION = (
    "Jeremy Guill builds custom software, database workflows, and automation around real "
    "operational problems, then trains and supports the people who use it."
)


def rename_project_slug(conn: sa.Connection, old: str, new: str) -> int:
    project_id = conn.execute(
        sa.select(projects.c.id).where(projects.c.slug == old)
    ).scalar_one_or_none()
    taken = conn.execute(sa.select(projects.c.id).where(projects.c.slug == new)).first()
    if project_id is None or taken is not None:
        return 0
    conn.execute(sa.update(projects).where(projects.c.id == project_id).values(slug=new))
    now = datetime.now(UTC)
    exists = conn.execute(
        sa.select(redirects.c.id).where(redirects.c.old_path == f"/work/{old}")
    ).first()
    if exists is None:
        conn.execute(
            sa.insert(redirects).values(
                id=uuid.uuid4(),
                old_path=f"/work/{old}",
                new_path=f"/work/{new}",
                entity_type="project",
                entity_id=project_id,
                created_at=now,
                updated_at=now,
            )
        )
    return 1


def fix_blog_post_presentation(conn: sa.Connection) -> int:
    row = conn.execute(
        sa.select(
            blog_posts.c.id,
            blog_posts.c.title,
            blog_posts.c.summary,
            blog_posts.c.source_markdown,
        ).where(blog_posts.c.slug == BLOG_SLUG)
    ).first()
    if row is None:
        return 0
    values: dict[str, str] = {}
    if row.summary.rstrip().endswith("upbeat take"):
        values["summary"] = BLOG_SUMMARY
    first_line, _, rest = row.source_markdown.partition("\n")
    if first_line.strip() == f"# {row.title}":
        source = rest.lstrip("\n")
        values["source_markdown"] = source
        values["rendered_html"] = render_markdown(source)
    if not values:
        return 0
    conn.execute(sa.update(blog_posts).where(blog_posts.c.id == row.id).values(**values))
    return 1


def backfill_project_alt_text(conn: sa.Connection) -> int:
    rows = conn.execute(
        sa.select(projects.c.title, media_assets.c.id, media_assets.c.alt_text).select_from(
            projects.join(media_assets, media_assets.c.id == projects.c.hero_media_id)
        )
    ).all()
    changed = 0
    for row in rows:
        if (row.alt_text or "").strip() in ("", row.title):
            conn.execute(
                sa.update(media_assets)
                .where(media_assets.c.id == row.id)
                .values(alt_text=f"{row.title} project preview")
            )
            changed += 1
    return changed


def refresh_profile_seo(conn: sa.Connection) -> int:
    changed = 0
    for row in conn.execute(
        sa.select(site_profiles.c.id, site_profiles.c.seo_title, site_profiles.c.seo_description)
    ).all():
        values: dict[str, str] = {}
        if (row.seo_title or "") == "Custom Software Development Portfolio":
            values["seo_title"] = PROFILE_SEO_TITLE
        if (row.seo_description or "").startswith("Discover how Jeremy Guill"):
            values["seo_description"] = PROFILE_SEO_DESCRIPTION
        if values:
            conn.execute(sa.update(site_profiles).where(site_profiles.c.id == row.id).values(**values))
            changed += 1
    return changed
```

`migrations/versions/0008_content_fixes.py`:

```python
from __future__ import annotations

from alembic import op

from portfolio.content import data_fixes

revision = "0008_content_fixes"
down_revision = "0007_active_job_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    data_fixes.rename_project_slug(conn, "medial-mileage", "medical-mileage")
    data_fixes.fix_blog_post_presentation(conn)
    data_fixes.backfill_project_alt_text(conn)
    data_fixes.refresh_profile_seo(conn)


def downgrade() -> None:
    # Content corrections are intentionally not reverted.
    pass
```

- [ ] **Step 4:** `uv run pytest tests/integration/content/test_data_fixes.py tests/integration/test_initial_migration.py -v` → PASS. Also: `uv run pytest -q`.

- [ ] **Step 5: Commit** (`feat: data fixes for slug typo, blog post, alt text, profile SEO`) with the three new files.

---

# Phase 1: Shared plumbing, assets, performance

### Task 5: `site` template context + branded error pages

**Files:**
- Create: `src/portfolio/public/chrome.py`, `tests/integration/public/test_site_chrome.py`
- Modify: `src/portfolio/__init__.py`, `src/portfolio/templates/components/navigation.html`, `src/portfolio/templates/errors/404.html`, `src/portfolio/templates/errors/500.html`

**Interfaces:**
- Produces: template variable `site` (a `SiteChrome`) with lazy attributes: `show_blog: bool`, `profile: SiteProfile`, `has_resume: bool`, `has_portrait: bool`, `year: int`. All fail soft (database errors → safe defaults). Later tasks add `analytics`.

- [ ] **Step 1: Failing tests** `tests/integration/public/test_site_chrome.py`

```python
from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost
from portfolio.public.chrome import SiteChrome


def test_404_page_has_site_navigation_and_one_h1(client):
    response = client.get("/definitely-missing")
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert 'href="/work"' in html
    assert html.count("<h1") == 1
    assert 'class="skip-link"' in html


def test_nav_blog_link_uses_site_chrome(client, db_session):
    assert 'href="/blog"' not in client.get("/").get_data(as_text=True)
    db_session.add(BlogPost(title="P", slug="p", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()

    assert 'href="/blog"' in client.get("/").get_data(as_text=True)


def test_chrome_degrades_when_database_is_unavailable(app, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr("portfolio.public.chrome.db.session.execute", boom)
    with app.app_context():
        chrome = SiteChrome()

        assert chrome.show_blog is False
        assert chrome.profile.display_name == "Jeremy Guill"


def test_resume_and_portrait_flags_reflect_files(app, tmp_path):
    app.static_folder = str(tmp_path)
    (tmp_path / "resume").mkdir()
    with app.app_context():
        assert SiteChrome().has_resume is False
        (tmp_path / "resume" / "Resume2026.pdf").write_bytes(b"%PDF-1.4")
        assert SiteChrome().has_resume is True
```

- [ ] **Step 2:** run → FAIL (`ModuleNotFoundError: portfolio.public.chrome`).

- [ ] **Step 3: Implement** `src/portfolio/public/chrome.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path

from flask import current_app
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, SiteProfile
from portfolio.extensions import db


class SiteChrome:
    """Per-request data every public page needs. Every property fails soft."""

    @cached_property
    def show_blog(self) -> bool:
        try:
            return (
                db.session.execute(
                    select(BlogPost.id).where(BlogPost.state == PublicationState.PUBLISHED).limit(1)
                ).first()
                is not None
            )
        except Exception:
            db.session.rollback()
            return False

    @cached_property
    def profile(self) -> SiteProfile:
        try:
            found = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
        except Exception:
            db.session.rollback()
            found = None
        return found or SiteProfile(display_name="Jeremy Guill")

    @cached_property
    def has_resume(self) -> bool:
        return (Path(current_app.static_folder or "") / "resume" / "Resume2026.pdf").is_file()

    @cached_property
    def has_portrait(self) -> bool:
        return (
            Path(current_app.static_folder or "") / "assets" / "img" / "jeremyguill_profile.webp"
        ).is_file()

    @cached_property
    def year(self) -> int:
        return datetime.now(UTC).year
```

`__init__.py`: after `app.after_request(apply_security_headers)` add

```python
    from .public.chrome import SiteChrome

    app.context_processor(lambda: {"site": SiteChrome()})
```

`navigation.html`: replace `{% if view.show_blog %}` with `{% if site.show_blog %}`.

`errors/404.html` and `500.html` become:

```html
{% extends "public/base.html" %}
{% block title %}Page not found | Jeremy Guill{% endblock %}
{% block content %}
<section class="page-section">
  <p class="eyebrow">404</p>
  <h1>That page isn't here.</h1>
  <p class="lede">The link may be old or mistyped. Here are some good places to start.</p>
  <p class="hero-actions">
    <a class="button button-primary" href="/work">See my work</a>
    <a class="button button-outline" href="/contact">Get in touch</a>
  </p>
</section>
{% endblock %}
```
(500: title `Something went wrong | Jeremy Guill`, eyebrow `500`, h1 `Something broke on my end.`, lede `I've been notified. Please try again in a moment.`, same buttons but the second link is `/` "Back to home".)

- [ ] **Step 4:** `uv run pytest -q` → PASS (existing nav tests keep passing).

- [ ] **Step 5: Commit** `feat: add site chrome context and branded 404/500 pages`.

### Task 6: Profile and project fields (migration 0009, model, CLI, admin form)

**Files:**
- Create: `migrations/versions/0009_profile_project_fields.py`, `tests/unit/content/test_glance_fields.py`, `tests/integration/content/test_set_profile_cli.py`
- Modify: `src/portfolio/content/models.py`, `src/portfolio/content/seed.py`, `src/portfolio/admin/forms.py`, `src/portfolio/admin/routes.py`, `src/portfolio/templates/admin/content/edit.html`

**Interfaces:**
- Produces: `SiteProfile.linkedin_url`, `.github_url`, `.availability_text` (all `str | None`); `Project.role`, `.stack`, `.year`, `.result_headline` (all `str | None`) and `Project.stack_list -> list[str]`; `ProjectForm.role/stack/year/result_headline`; CLI `flask --app portfolio content set-profile [--linkedin URL] [--github URL] [--availability TEXT] [--email EMAIL]`.

- [ ] **Step 1: Failing tests**

`tests/unit/content/test_glance_fields.py`:

```python
from __future__ import annotations

from portfolio.admin.forms import ProjectForm
from portfolio.content.models import Project


def test_stack_list_splits_and_trims():
    assert Project(stack=" Flask, PostgreSQL ,, Docker ").stack_list == ["Flask", "PostgreSQL", "Docker"]
    assert Project(stack=None).stack_list == []


def test_project_form_reads_glance_fields():
    form = ProjectForm.from_mapping(
        {
            "title": "T", "slug": "t", "version": "1",
            "role": "Creator & Developer", "stack": "Next.js, SQL",
            "year": "2025", "result_headline": "Resume creation became consistent",
        }
    )

    assert (form.role, form.stack, form.year) == ("Creator & Developer", "Next.js, SQL", "2025")
    assert form.result_headline == "Resume creation became consistent"
    assert form.validate()


def test_project_form_rejects_overlong_glance_fields():
    form = ProjectForm.from_mapping({"title": "T", "slug": "t", "version": "1", "role": "x" * 121})

    assert not form.validate()
    assert "role" in form.errors
```

`tests/integration/content/test_set_profile_cli.py`:

```python
from __future__ import annotations

from sqlalchemy import select

from portfolio.content.models import SiteProfile


def test_set_profile_updates_only_given_fields(app, db_session):
    db_session.add(SiteProfile(email="a@example.test"))
    db_session.commit()

    result = app.test_cli_runner().invoke(
        args=["content", "set-profile", "--linkedin", "https://www.linkedin.com/in/x", "--availability", "Open to roles"]
    )

    assert result.exit_code == 0, result.output
    profile = db_session.scalar(select(SiteProfile))
    db_session.refresh(profile)
    assert profile.linkedin_url == "https://www.linkedin.com/in/x"
    assert profile.availability_text == "Open to roles"
    assert profile.github_url is None
    assert profile.email == "a@example.test"


def test_set_profile_rejects_non_https_links(app, db_session):
    db_session.add(SiteProfile())
    db_session.commit()

    result = app.test_cli_runner().invoke(args=["content", "set-profile", "--github", "javascript:alert(1)"])

    assert result.exit_code != 0
```

- [ ] **Step 2:** run both → FAIL.

- [ ] **Step 3: Implement.**

`models.py`: in `SiteProfile` add
```python
    linkedin_url: Mapped[str | None] = mapped_column(String(300))
    github_url: Mapped[str | None] = mapped_column(String(300))
    availability_text: Mapped[str | None] = mapped_column(String(240))
```
In `Project` (after `seo_last_reviewed_at`) add
```python
    role: Mapped[str | None] = mapped_column(String(120))
    stack: Mapped[str | None] = mapped_column(String(240))
    year: Mapped[str | None] = mapped_column(String(20))
    result_headline: Mapped[str | None] = mapped_column(String(240))

    @property
    def stack_list(self) -> list[str]:
        return [part.strip() for part in (self.stack or "").split(",") if part.strip()]
```

`0009_profile_project_fields.py`:

```python
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_profile_project_fields"
down_revision = "0008_content_fixes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_profiles", sa.Column("linkedin_url", sa.String(300), nullable=True))
    op.add_column("site_profiles", sa.Column("github_url", sa.String(300), nullable=True))
    op.add_column("site_profiles", sa.Column("availability_text", sa.String(240), nullable=True))
    op.add_column("projects", sa.Column("role", sa.String(120), nullable=True))
    op.add_column("projects", sa.Column("stack", sa.String(240), nullable=True))
    op.add_column("projects", sa.Column("year", sa.String(20), nullable=True))
    op.add_column("projects", sa.Column("result_headline", sa.String(240), nullable=True))


def downgrade() -> None:
    for column in ("result_headline", "year", "stack", "role"):
        op.drop_column("projects", column)
    for column in ("availability_text", "github_url", "linkedin_url"):
        op.drop_column("site_profiles", column)
```

`admin/forms.py` `ProjectForm`: add dataclass fields `role: str = ""`, `stack: str = ""`, `year: str = ""`, `result_headline: str = ""` (before `order`), read them in `from_mapping` with `.strip()`, and add to `validate()`:

```python
        for name, limit in (("role", 120), ("stack", 240), ("year", 20), ("result_headline", 240)):
            if len(getattr(self, name)) > limit:
                self.add_error(name, f"{name.replace('_', ' ').title()} must be {limit} characters or fewer")
```
`project_form_for` also sets `role=entity.role or ""`, etc.

`admin/routes.py`: add helper above `create_project`:

```python
def _apply_glance_fields(project: Project, form: ProjectForm) -> None:
    project.role = form.role or None
    project.stack = form.stack or None
    project.year = form.year or None
    project.result_headline = form.result_headline or None
```
and call `_apply_glance_fields(project, form)` immediately before each `save_draft(project, form.to_command(), ...)` in `create_project` and `update_project`.

`templates/admin/content/edit.html`: after the summary `<label>` add

```html
      <fieldset>
        <legend>At a glance (shown on the public case study and project cards)</legend>
        <div class="field-row">
          <label>Role <input name="role" value="{{ form.role }}" maxlength="120"></label>
          <label>Year <input name="year" value="{{ form.year }}" maxlength="20"></label>
        </div>
        <label>Stack (comma separated) <input name="stack" value="{{ form.stack }}" maxlength="240"></label>
        <label>Main result (one line) <input name="result_headline" value="{{ form.result_headline }}" maxlength="240"></label>
      </fieldset>
```

`content/seed.py`: add the CLI command (below `seed_initial_command`):

```python
@content_cli.command("set-profile")
@click.option("--linkedin", default=None)
@click.option("--github", default=None)
@click.option("--availability", default=None)
@click.option("--email", default=None)
def set_profile_command(
    linkedin: str | None, github: str | None, availability: str | None, email: str | None
) -> None:
    profile = db.session.query(SiteProfile).first()
    if profile is None:
        raise click.ClickException("No profile exists yet; run seed-initial first.")
    for label, value in (("linkedin", linkedin), ("github", github)):
        if value is not None and not value.startswith("https://"):
            raise click.BadParameter("must start with https://", param_hint=f"--{label}")
    if linkedin is not None:
        profile.linkedin_url = linkedin or None
    if github is not None:
        profile.github_url = github or None
    if availability is not None:
        profile.availability_text = availability or None
    if email is not None:
        profile.email = email or None
    db.session.commit()
    click.echo("profile updated")
```
(An empty string clears a field; empty `--linkedin ""` passes the https check only if you treat it as clear: change the check to `if value and not value.startswith("https://")`.)

- [ ] **Step 4:** `uv run pytest -q` → PASS. Also run `uv run flask --app portfolio db upgrade` against a scratch SQLite: `DATABASE_URL=sqlite:////tmp/x.db uv run flask --app portfolio db upgrade` (use the scratchpad dir) → no errors, then `downgrade -1` → no errors.

- [ ] **Step 5: Commit** (`feat: profile social/availability fields and project at-a-glance fields`) including migration, models, forms, routes, template, seed, tests.

### Task 7: Self-host fonts

**Files:**
- Create: `src/portfolio/static/assets/fonts/{poppins-600.woff2,poppins-700.woff2,open-sans-var.woff2,README.md}`, `src/portfolio/static/assets/fonts.css`, `tests/unit/test_fonts.py`
- Modify: `src/portfolio/templates/public/base.html`, `src/portfolio/static/assets/site.css`

- [ ] **Step 1: Failing test** `tests/unit/test_fonts.py`

```python
from __future__ import annotations

from pathlib import Path

ASSETS = Path("src/portfolio/static/assets")


def test_font_files_are_real_woff2():
    for name in ("poppins-600", "poppins-700", "open-sans-var"):
        data = (ASSETS / "fonts" / f"{name}.woff2").read_bytes()
        assert data[:4] == b"wOF2" and len(data) > 8000, name


def test_font_css_declares_faces_with_swap():
    css = (ASSETS / "fonts.css").read_text()

    assert css.count("@font-face") == 3
    assert css.count("font-display: swap") == 3
    assert "https://" not in css


def test_site_css_no_longer_references_geist():
    assert "Geist" not in (ASSETS / "site.css").read_text()


def test_base_template_loads_font_css_and_preloads_body_font(client):
    html = client.get("/").get_data(as_text=True)

    assert "assets/fonts.css" in html
    assert 'rel="preload"' in html and "open-sans-var.woff2" in html
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** Download (all SIL OFL):

```bash
cd src/portfolio/static/assets && mkdir -p fonts && cd fonts
curl -fL -o poppins-600.woff2 https://cdn.jsdelivr.net/fontsource/fonts/poppins@latest/latin-600-normal.woff2
curl -fL -o poppins-700.woff2 https://cdn.jsdelivr.net/fontsource/fonts/poppins@latest/latin-700-normal.woff2
curl -fL -o open-sans-var.woff2 https://cdn.jsdelivr.net/fontsource/fonts/open-sans:vf@latest/latin-wght-normal.woff2
```
Run `file *.woff2` (expect "Web Open Font Format (Version 2)"). If a URL 404s, fetch the equivalent latin subset from `https://fonts.google.com` download and convert with `uvx fonttools`. Create `fonts/README.md`: "Poppins and Open Sans, SIL Open Font License 1.1, latin subset, via Fontsource."

`fonts.css`:

```css
@font-face {
  font-family: "Poppins";
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url("fonts/poppins-600.woff2") format("woff2");
}

@font-face {
  font-family: "Poppins";
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url("fonts/poppins-700.woff2") format("woff2");
}

@font-face {
  font-family: "Open Sans";
  font-style: normal;
  font-weight: 300 800;
  font-display: swap;
  src: url("fonts/open-sans-var.woff2") format("woff2");
}
```

`site.css`: replace every `"Geist", ` occurrence with nothing (`sed -i 's/"Geist", //g'`); the stacks become `"Open Sans", ui-sans-serif, ...` and `"Poppins", ui-sans-serif, ...`.

`base.html` `<head>`: before the site.css link add

```html
    <link rel="preload" href="{{ url_for('static', filename='assets/fonts/open-sans-var.woff2') }}" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="{{ url_for('static', filename='assets/fonts.css') }}">
```

- [ ] **Step 4:** tests → PASS; start the app (`uv run flask --app portfolio run --port 5000`) and `curl -s -o /dev/null -w "%{http_code} %{content_type}\n" http://127.0.0.1:5000/static/assets/fonts/poppins-700.woff2` → `200 font/woff2` (if the type is wrong, add `app.add_url_rule` mimetypes via `mimetypes.add_type("font/woff2", ".woff2")` in `create_app`).

- [ ] **Step 5: Commit** (`feat: self-host Poppins and Open Sans`).

### Task 8: Content-hashed static URLs and cache headers

**Files:**
- Create: `src/portfolio/assets.py`, `tests/integration/test_static_caching.py`
- Modify: `src/portfolio/__init__.py`, `src/portfolio/public/routes.py` (media route), `src/portfolio/templates/public/base.html`

**Interfaces:**
- Produces: Jinja global `static_url(filename: str) -> str` (returns `/static/<filename>?v=<10 hex chars of sha256>`; unchanged URL if the file is missing); `apply_cache_headers(response)` after-request hook.

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

import re


def test_css_link_carries_content_hash(client):
    html = client.get("/").get_data(as_text=True)

    assert re.search(r'href="/static/assets/site\.css\?v=[0-9a-f]{10}"', html)


def test_hashed_static_urls_are_immutable_forever(client):
    html = client.get("/").get_data(as_text=True)
    href = re.search(r'href="(/static/assets/site\.css\?v=[0-9a-f]{10})"', html).group(1)

    assert "immutable" in client.get(href).headers["Cache-Control"]
    assert "max-age=31536000" in client.get(href).headers["Cache-Control"]


def test_unhashed_static_urls_get_short_cache(client):
    cache = client.get("/static/assets/site.css").headers["Cache-Control"]

    assert "max-age=3600" in cache
    assert "immutable" not in cache


def test_html_pages_are_not_given_long_cache(client):
    assert "max-age=31536000" not in client.get("/").headers.get("Cache-Control", "")


def test_static_url_for_missing_file_does_not_crash(app):
    from portfolio.assets import static_url

    with app.test_request_context():
        assert static_url("assets/nope.css") == "/static/assets/nope.css"
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement** `src/portfolio/assets.py`:

```python
from __future__ import annotations

import hashlib
from pathlib import Path

from flask import Flask, Response, current_app, request, url_for

_cache: dict[tuple[str, float], str] = {}


def _digest(path: Path) -> str | None:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), stamp)
    if key not in _cache:
        _cache[key] = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    return _cache[key]


def static_url(filename: str) -> str:
    digest = _digest(Path(current_app.static_folder or "") / filename)
    if digest is None:
        return url_for("static", filename=filename)
    return url_for("static", filename=filename, v=digest)


def apply_cache_headers(response: Response) -> Response:
    if request.endpoint == "static" and response.status_code == 200:
        if request.args.get("v"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"
    return response


def init_assets(app: Flask) -> None:
    app.jinja_env.globals["static_url"] = static_url
    app.after_request(apply_cache_headers)
```

`__init__.py`: after the security-headers hook: `from .assets import init_assets` / `init_assets(app)`.

`base.html`: replace the four `url_for('static', filename=...)` usages with `static_url('...')` (site.css, fonts.css, preload, site.js). Also `public/routes.py` media route: `send_from_directory(media_root(), filename, max_age=2592000)`.

- [ ] **Step 4:** tests + full suite → PASS.

- [ ] **Step 5: Commit** (`perf: content-hash static URLs and add long-lived cache headers`).

### Task 9: Brand assets (favicon, social card, WebP backgrounds, portrait)

**Files:**
- Create: `scripts/make_brand_assets.py`, `tests/unit/test_brand_assets.py`, generated files in `src/portfolio/static/assets/img/` (`favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`, `og-default.png`, `header-background.webp`, `header-background-960.webp`)
- Modify: `src/portfolio/templates/public/base.html`, `src/portfolio/public/routes.py`, `src/portfolio/static/assets/site.css`, `src/portfolio/templates/public/home.html` (portrait)
- Delete: `src/portfolio/static/assets/img/header-background.jpg` (via `git rm -f`)

- [ ] **Step 1: Failing tests** `tests/unit/test_brand_assets.py`

```python
from __future__ import annotations

from pathlib import Path

from PIL import Image

IMG = Path("src/portfolio/static/assets/img")


def test_social_card_is_1200_by_630():
    with Image.open(IMG / "og-default.png") as image:
        assert image.size == (1200, 630)


def test_icons_have_expected_sizes():
    with Image.open(IMG / "favicon-32.png") as small:
        assert small.size == (32, 32)
    with Image.open(IMG / "apple-touch-icon.png") as touch:
        assert touch.size == (180, 180)
    assert (IMG / "favicon.svg").read_text().startswith("<svg")


def test_hero_background_is_webp_and_much_smaller_than_old_jpg():
    assert (IMG / "header-background.webp").stat().st_size < 200_000
    assert (IMG / "header-background-960.webp").stat().st_size < 90_000


def test_head_declares_icons_and_theme_color(client):
    html = client.get("/").get_data(as_text=True)

    assert 'rel="icon"' in html and "favicon.svg" in html
    assert 'rel="apple-touch-icon"' in html
    assert 'name="theme-color"' in html


def test_favicon_ico_route_serves_png(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_homepage_without_portrait_file_renders_no_broken_image(client):
    html = client.get("/").get_data(as_text=True)

    assert "jeremyguill_profile.jpg" not in html
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** Download fonts for drawing (scratch only, not committed):

```bash
SCRATCH=/tmp/claude-1000/-mnt-storage-docker-jeremyguill-me/2ff49fec-5bf3-4d3c-b9ba-b4e121de09ff/scratchpad/fonts && mkdir -p $SCRATCH
curl -fL -o $SCRATCH/Poppins-Bold.ttf https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf
curl -fL -o $SCRATCH/Poppins-Regular.ttf https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf
```

`scripts/make_brand_assets.py`:

```python
"""Generate favicon, social card, optimized backgrounds and portrait variants.

uv run python scripts/make_brand_assets.py --fonts DIR [--portrait PHOTO.jpg]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG = Path("src/portfolio/static/assets/img")
INK = (36, 38, 42)
BLUE = (34, 89, 236)
WHITE = (255, 255, 255)
MUTED = (190, 196, 206)

FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#24262a"/>'
    '<text x="32" y="43" text-anchor="middle" font-family="Poppins, Arial, sans-serif" '
    'font-size="28" font-weight="700" fill="#ffffff">JG</text></svg>\n'
)


def icon(font_path: Path, size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), INK)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), int(size * 0.44))
    draw.text((size / 2, size / 2), "JG", font=font, fill=WHITE, anchor="mm")
    return image


def social_card(bold: Path, regular: Path) -> Image.Image:
    image = Image.new("RGB", (1200, 630), INK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 24, 630), fill=BLUE)
    draw.text((90, 210), "Jeremy Guill", font=ImageFont.truetype(str(bold), 112), fill=WHITE)
    draw.text(
        (94, 355),
        "Practical software for real-world workflows",
        font=ImageFont.truetype(str(regular), 46),
        fill=MUTED,
    )
    draw.text((94, 520), "jeremyguill.me", font=ImageFont.truetype(str(bold), 34), fill=BLUE)
    return image


def webp_background(source: Path) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        for width, name, quality in ((1920, "header-background.webp", 72), (960, "header-background-960.webp", 70)):
            copy = image.copy()
            if copy.width > width:
                copy = copy.resize((width, round(copy.height * width / copy.width)), Image.LANCZOS)
            copy.save(IMG / name, "WEBP", quality=quality, method=6)


def portrait(source: Path) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        for width, suffix in ((1200, ""), (600, "-600")):
            copy = image.copy()
            if copy.width > width:
                copy = copy.resize((width, round(copy.height * width / copy.width)), Image.LANCZOS)
            copy.save(IMG / f"jeremyguill_profile{suffix}.webp", "WEBP", quality=80, method=6)
            print(f"portrait{suffix}: {copy.size}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, required=True)
    parser.add_argument("--portrait", type=Path)
    args = parser.parse_args()
    bold, regular = args.fonts / "Poppins-Bold.ttf", args.fonts / "Poppins-Regular.ttf"
    (IMG / "favicon.svg").write_text(FAVICON_SVG)
    icon(bold, 32).save(IMG / "favicon-32.png")
    icon(bold, 180).save(IMG / "apple-touch-icon.png")
    social_card(bold, regular).save(IMG / "og-default.png", optimize=True)
    jpg = IMG / "header-background.jpg"
    if jpg.exists():
        webp_background(jpg)
    if args.portrait:
        portrait(args.portrait)


if __name__ == "__main__":
    main()
```

Run: `uv run python scripts/make_brand_assets.py --fonts $SCRATCH`. Then open `og-default.png` with the Read tool and confirm it looks right (text not clipped).

`site.css` hero background line 142: change `url("img/header-background.jpg")` to `url("img/header-background.webp")`. Then `git rm -f src/portfolio/static/assets/img/header-background.jpg`. Append to `components.css` (created in Task 10; if executing this task first, create the file with this block) a small-screen swap:

```css
@media (max-width: 48rem) {
  .mark-hero {
    background:
      linear-gradient(rgba(0, 0, 0, .1), rgba(0, 0, 0, .1)),
      url("img/header-background-960.webp") center center / cover no-repeat;
  }
}
```
(Create `components.css` here as an empty-commented file if Task 10 has not run: `/* New component styles. */` and link it in base.html: `<link rel="stylesheet" href="{{ static_url('assets/components.css') }}">` after site.css.)

`base.html` `<head>` additions (after `<title>`):

```html
    <meta name="theme-color" content="#24262a">
    <link rel="icon" href="{{ static_url('assets/img/favicon.svg') }}" type="image/svg+xml">
    <link rel="icon" href="{{ static_url('assets/img/favicon-32.png') }}" type="image/png" sizes="32x32">
    <link rel="apple-touch-icon" href="{{ static_url('assets/img/apple-touch-icon.png') }}">
```

`public/routes.py`: add

```python
@public_bp.get("/favicon.ico")
def favicon():
    return send_from_directory(
        current_app.static_folder, "assets/img/favicon-32.png", mimetype="image/png", max_age=86400
    )
```
(import `current_app` from flask).

Homepage portrait in `home.html`: replace `<div class="split-detail__image" aria-label="Jeremy Guill portrait"></div>` with

```html
  {% if site.has_portrait %}
    <img class="split-detail__image" src="{{ static_url('assets/img/jeremyguill_profile.webp') }}"
         srcset="{{ static_url('assets/img/jeremyguill_profile-600.webp') }} 600w, {{ static_url('assets/img/jeremyguill_profile.webp') }} 1200w"
         sizes="(max-width: 62rem) 100vw, 50vw" width="1200" height="1400"
         alt="Jeremy Guill" loading="lazy">
  {% endif %}
```
and in `site.css` replace the `.split-detail__image` block (lines ~341-347) with:

```css
.split-detail__image {
  width: 100%;
  min-height: 28rem;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}
```
Add to `components.css`: `.split-detail:not(:has(.split-detail__image)) { grid-template-columns: 1fr; }`.

(The portrait file itself is an owner task; the template hides the image until `jeremyguill_profile.webp` exists. After the owner supplies the photo, run `uv run python scripts/make_brand_assets.py --fonts $SCRATCH --portrait <their photo>` and adjust the `width`/`height` attributes to the printed size.)

- [ ] **Step 4:** tests + full suite → PASS.

- [ ] **Step 5: Commit** script, generated images, templates, css, route, tests, and the deletion (`git add -u` is NOT allowed; list the deleted path explicitly in both `git add` and `-- paths`).

---

# Phase 2: Layout and UX

### Task 10: Accessible responsive header

**Files:**
- Create: `src/portfolio/static/assets/components.css` (if not yet created), `tests/integration/public/test_navigation.py`
- Modify: `src/portfolio/templates/components/navigation.html`, `src/portfolio/static/assets/site.js`, `src/portfolio/templates/public/base.html` (link components.css if needed)

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

import re
from pathlib import Path


def _nav(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'<header class="site-header">.*?</header>', html, re.DOTALL).group(0)


def test_work_link_is_current_on_work_pages(client):
    nav = _nav(client, "/work")

    assert re.search(r'<a href="/work"[^>]*aria-current="page"', nav)
    assert nav.count('aria-current="page"') == 1


def test_current_page_not_marked_on_home_for_other_links(client):
    assert 'aria-current="page"' not in _nav(client, "/")


def test_nav_has_toggle_button_wired_to_nav(client):
    nav = _nav(client, "/")

    assert 'class="nav-toggle"' in nav and 'aria-expanded="false"' in nav
    assert 'aria-controls="primary-nav"' in nav and 'id="primary-nav"' in nav
    assert "hidden" in re.search(r'<button class="nav-toggle"[^>]*>', nav).group(0)


def test_contact_is_styled_as_call_to_action(client):
    assert 'class="nav-cta"' in _nav(client, "/")


def test_capabilities_anchor_is_gone_from_nav(client):
    assert "#capabilities" not in _nav(client, "/")


def test_script_wires_menu_toggle_and_escape():
    js = Path("src/portfolio/static/assets/site.js").read_text()

    assert "nav-toggle" in js and "aria-expanded" in js and "Escape" in js
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** `navigation.html`:

```html
<header class="site-header">
  <div class="site-header__inner">
    <a class="brand" href="/" aria-label="Jeremy Guill home">Jeremy Guill</a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="primary-nav" hidden>
      <span class="nav-toggle__label">Menu</span>
    </button>
    <nav id="primary-nav" class="primary-nav" aria-label="Primary navigation">
      <a href="/#about">About</a>
      <a href="/work"{% if request.path.startswith('/work') %} aria-current="page"{% endif %}>Work</a>
      <a href="/experience"{% if request.path == '/experience' %} aria-current="page"{% endif %}>Experience</a>
      {% if site.show_blog %}<a href="/blog"{% if request.path.startswith('/blog') %} aria-current="page"{% endif %}>Blog</a>{% endif %}
      <a class="nav-cta" href="/contact"{% if request.path == '/contact' %} aria-current="page"{% endif %}>Contact</a>
    </nav>
  </div>
</header>
```

`site.js` (append):

```js
const navToggle = document.querySelector(".nav-toggle");
const primaryNav = document.getElementById("primary-nav");

if (navToggle && primaryNav) {
  navToggle.hidden = false;
  const setOpen = (open) => {
    navToggle.setAttribute("aria-expanded", String(open));
    primaryNav.classList.toggle("is-open", open);
  };
  navToggle.addEventListener("click", () => setOpen(navToggle.getAttribute("aria-expanded") !== "true"));
  primaryNav.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) setOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setOpen(false);
      navToggle.focus();
    }
  });
}
```

`components.css`:

```css
/* Header */
.nav-toggle {
  display: none;
  background: transparent;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, .5);
  border-radius: .35rem;
  padding: .45rem .8rem;
  font: 700 .75rem/1 "Poppins", ui-sans-serif, system-ui, sans-serif;
  letter-spacing: .08em;
  text-transform: uppercase;
  cursor: pointer;
}

.primary-nav a[aria-current="page"] { color: #fff; box-shadow: 0 2px 0 var(--blue-bright); }

.primary-nav .nav-cta {
  background: var(--blue-bright);
  padding: .55rem 1rem;
  border-radius: .35rem;
}

.primary-nav .nav-cta:hover { color: #fff; filter: brightness(1.12); }

@media (max-width: 62rem) {
  .js .site-header__inner {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    padding: .75rem 0;
  }

  .js .nav-toggle { display: inline-flex; }

  .js .primary-nav {
    display: none;
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    gap: 0;
  }

  .js .primary-nav.is-open { display: flex; }

  .js .primary-nav a { padding: .85rem 0; border-top: 1px solid rgba(255, 255, 255, .15); }

  .js .primary-nav .nav-cta { margin-top: .5rem; text-align: center; }
}
```
Link `components.css` in `base.html` after `site.css`: `<link rel="stylesheet" href="{{ static_url('assets/components.css') }}">` (skip if Task 9 already added it).

- [ ] **Step 4:** tests → PASS. Manual: run the app; at 360px width the menu button appears and toggles (use the `run` skill); with JS disabled the full nav stays visible (no `.js` class).

- [ ] **Step 5: Commit** (`feat: accessible responsive header with active state and CTA`).

### Task 11: Footer with contact, social, résumé, copyright

**Files:**
- Create: `src/portfolio/templates/components/footer.html`, `tests/integration/public/test_footer.py`
- Modify: `src/portfolio/templates/public/base.html`, `src/portfolio/static/assets/components.css`, `src/portfolio/public/blog_routes.py`

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

from sqlalchemy import select

from portfolio.content.models import SiteProfile


def _footer(client):
    import re

    html = client.get("/").get_data(as_text=True)
    return re.search(r'<footer class="site-footer">.*?</footer>', html, re.DOTALL).group(0)


def test_footer_shows_social_links_when_configured(client, db_session):
    db_session.add(SiteProfile(linkedin_url="https://www.linkedin.com/in/x", github_url="https://github.com/x"))
    db_session.commit()

    footer = _footer(client)

    assert 'href="https://www.linkedin.com/in/x"' in footer and 'rel="noopener' in footer
    assert 'href="https://github.com/x"' in footer


def test_footer_hides_unconfigured_links(client):
    footer = _footer(client)

    assert "linkedin" not in footer.lower() and "github" not in footer.lower()
    assert 'href="/resume"' not in footer


def test_footer_has_copyright_and_site_links(client):
    footer = _footer(client)

    assert "©" in footer and 'href="/work"' in footer and 'href="/contact"' in footer


def test_footer_resume_link_when_pdf_exists(client, app, tmp_path):
    (tmp_path / "resume").mkdir()
    (tmp_path / "resume" / "Resume2026.pdf").write_bytes(b"%PDF-1.4")
    app.static_folder = str(tmp_path)

    assert 'href="/resume"' in _footer(client)


def test_resume_route_404s_without_file_and_serves_pdf_with_it(client, app, tmp_path):
    app.static_folder = str(tmp_path)
    assert client.get("/resume").status_code == 404
    (tmp_path / "resume").mkdir()
    (tmp_path / "resume" / "Resume2026.pdf").write_bytes(b"%PDF-1.4")

    response = client.get("/resume")

    assert response.status_code == 200 and response.mimetype == "application/pdf"
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** `components/footer.html`:

```html
<footer class="site-footer">
  <div class="site-footer__about">
    <p class="site-footer__title">Jeremy Guill</p>
    <p>Practical software, database workflows, and implementation work built across real operational settings.</p>
    {% if site.profile.availability_text %}<p class="site-footer__availability">{{ site.profile.availability_text }}</p>{% endif %}
  </div>
  <nav class="site-footer__links" aria-label="Footer">
    <a href="/work">Work</a>
    <a href="/experience">Experience</a>
    {% if site.show_blog %}<a href="/blog">Blog</a>{% endif %}
    <a href="/contact">Contact</a>
    {% if site.has_resume %}<a href="/resume" data-umami-event="resume-download">Résumé (PDF)</a>{% endif %}
    {% if site.profile.linkedin_url %}<a href="{{ site.profile.linkedin_url }}" rel="noopener noreferrer me" target="_blank">LinkedIn</a>{% endif %}
    {% if site.profile.github_url %}<a href="{{ site.profile.github_url }}" rel="noopener noreferrer me" target="_blank">GitHub</a>{% endif %}
  </nav>
  <p class="site-footer__legal">© {{ site.year }} Jeremy Guill</p>
</footer>
```
`base.html`: replace the inline `<footer>...</footer>` with `{% include "components/footer.html" %}`.

`components.css` append:

```css
/* Footer */
.site-footer { flex-wrap: wrap; }
.site-footer__about { flex: 2 1 20rem; }
.site-footer__availability { color: var(--blue); font-weight: 700; }
.site-footer__links { display: flex; flex-wrap: wrap; gap: .6rem 1.4rem; flex: 1 1 14rem; align-content: flex-start; }
.site-footer__links a { color: var(--blue-bright); font-weight: 700; text-decoration: none; }
.site-footer__links a:hover { text-decoration: underline; }
.site-footer__legal { flex-basis: 100%; margin: 0; font-size: .85rem; }
```

`blog_routes.py` `resume()`:

```python
@blog_bp.get("/resume")
def resume():
    path = Path(current_app.static_folder or "") / "resume"
    if not (path / "Resume2026.pdf").is_file():
        abort(404)
    return send_from_directory(path, "Resume2026.pdf", mimetype="application/pdf", max_age=3600)
```
(imports: `from pathlib import Path`, `current_app, send_from_directory` from flask; remove unused `redirect` import only if nothing else uses it: the file's other routes do not.)

- [ ] **Step 4:** `uv run pytest -q` → PASS.

- [ ] **Step 5: Commit** (`feat: footer with social links, availability, resume and copyright; fix /resume 404 redirect`).

### Task 12: Project cards, homepage restructure, availability, blog-section rule

**Files:**
- Modify: `src/portfolio/public/view_models.py`, `src/portfolio/public/routes.py`, `src/portfolio/templates/components/project_card.html`, `src/portfolio/templates/public/home.html`, `src/portfolio/templates/public/work.html`, `src/portfolio/static/assets/components.css`
- Create: `tests/integration/public/test_cards_and_home.py`

**Interfaces:**
- Produces: `ProjectCardView(slug, title, summary, year, stack, result_headline, hero_media_id, hero_alt)`; `build_project_cards(projects: list[Project]) -> list[ProjectCardView]`; `HomeView.home_project_cards: list[ProjectCardView]`; `HomeView.show_blog_section: bool` (true only with ≥3 published posts). Both new `HomeView` fields have defaults so existing constructions keep working.

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile
from portfolio.media.models import MediaAsset
from portfolio.public.view_models import build_project_cards


def _project(**kw):
    defaults = dict(title="P", slug="p", summary="Does a thing.", state=PublicationState.PUBLISHED)
    defaults.update(kw)
    return Project(**defaults)


def test_card_without_hero_stack_or_year_renders_cleanly(client, db_session):
    db_session.add(SiteProfile())
    db_session.add(_project())
    db_session.commit()

    html = client.get("/").get_data(as_text=True)

    assert 'href="/work/p"' in html and "Does a thing." in html
    assert 'class="tag-list"' not in html
    assert "<img" not in html.split('id="work"')[1].split("</section>")[0]


def test_card_shows_stack_tags_year_result_and_alt_from_media(client, db_session):
    asset = MediaAsset(original_filename="a.png", storage_key="k/a", mime_type="image/png", byte_size=1, alt_text="Dashboard of trips", private=False)
    db_session.add_all([SiteProfile(), asset])
    db_session.flush()
    db_session.add(_project(stack="Flask, SQL", year="2025", result_headline="4h to 30m", hero_media_id=asset.id))
    db_session.commit()

    html = client.get("/").get_data(as_text=True)

    assert 'alt="Dashboard of trips"' in html
    assert '<li>Flask</li>' in html and '<li>SQL</li>' in html
    assert "2025" in html and "4h to 30m" in html


def test_build_project_cards_falls_back_to_title_alt(db_session):
    asset = MediaAsset(original_filename="a.png", storage_key="k/a", mime_type="image/png", byte_size=1, alt_text="", private=False)
    db_session.add(asset)
    db_session.flush()
    db_session.add(_project(hero_media_id=asset.id))
    db_session.commit()

    cards = build_project_cards(db_session.query(Project).all())

    assert cards[0].hero_alt == "P project preview"


def test_work_index_shows_thumbnails_like_home(client, db_session):
    asset = MediaAsset(original_filename="a.png", storage_key="k/a", mime_type="image/png", byte_size=1, alt_text="Alt", private=False)
    db_session.add(asset)
    db_session.flush()
    db_session.add(_project(hero_media_id=asset.id))
    db_session.commit()

    html = client.get("/work").get_data(as_text=True)

    assert f"/media/public/{asset.id}/hero_desktop.webp" in html and 'width="' in html


def test_latest_writing_hidden_until_three_posts(client, db_session):
    for index in range(2):
        db_session.add(BlogPost(title=f"T{index}", slug=f"t{index}", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()
    assert 'id="writing"' not in client.get("/").get_data(as_text=True)

    db_session.add(BlogPost(title="T3", slug="t3", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()
    assert 'id="writing"' in client.get("/").get_data(as_text=True)


def test_availability_statement_and_single_h1(client, db_session):
    db_session.add(SiteProfile(availability_text="Open to full-time roles and select contract projects."))
    db_session.commit()

    html = client.get("/").get_data(as_text=True)

    assert "Open to full-time roles and select contract projects." in html
    assert html.count("<h1") == 1


def test_homepage_has_no_testimonial_blockquote_attributed_to_owner(client):
    assert "<blockquote" not in client.get("/").get_data(as_text=True)


def test_empty_site_home_and_work_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/work").status_code == 200
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.**

`view_models.py`: add imports `import uuid`, `from sqlalchemy import func, select`, `from portfolio.media.models import MediaAsset`; add

```python
@dataclass(frozen=True)
class ProjectCardView:
    slug: str
    title: str
    summary: str
    year: str | None
    stack: list[str]
    result_headline: str | None
    hero_media_id: uuid.UUID | None
    hero_alt: str


def build_project_cards(projects: list[Project]) -> list[ProjectCardView]:
    ids = [p.hero_media_id for p in projects if p.hero_media_id]
    alts: dict[uuid.UUID, str] = {}
    if ids:
        rows = db.session.execute(
            select(MediaAsset.id, MediaAsset.alt_text).where(MediaAsset.id.in_(ids))
        ).all()
        alts = {row.id: row.alt_text for row in rows}
    return [
        ProjectCardView(
            slug=p.slug,
            title=p.title,
            summary=p.summary,
            year=p.year,
            stack=p.stack_list,
            result_headline=p.result_headline,
            hero_media_id=p.hero_media_id,
            hero_alt=(alts.get(p.hero_media_id) if p.hero_media_id else None) or f"{p.title} project preview",
        )
        for p in projects
    ]
```
`HomeView`: append fields `home_project_cards: list[ProjectCardView] = field(default_factory=list)` and `show_blog_section: bool = False` (import `field`). In `build_home_view` before `return`, compute

```python
    published_posts = db.session.scalar(
        select(func.count()).select_from(BlogPost).where(BlogPost.state == PublicationState.PUBLISHED)
    ) or 0
```
and pass `home_project_cards=build_project_cards(list(home_projects)),` and `show_blog_section=published_posts >= 3,` in the `HomeView(...)` call.

`public/routes.py` `work_index`: import `build_project_cards`; pass `cards=build_project_cards(projects)` to `render_template`.

`components/project_card.html` (a card taking a `card` variable):

```html
<article class="project-card2 reveal">
  <a class="project-card2__media" href="/work/{{ card.slug }}" aria-label="Open {{ card.title }}" tabindex="-1">
    {% if card.hero_media_id %}
      <img src="/media/public/{{ card.hero_media_id }}/hero_desktop.webp"
           srcset="/media/public/{{ card.hero_media_id }}/hero_mobile.webp 900w, /media/public/{{ card.hero_media_id }}/hero_desktop.webp 1600w"
           sizes="(max-width: 48rem) 100vw, 24rem" width="1600" height="900"
           alt="{{ card.hero_alt }}" loading="lazy">
    {% endif %}
  </a>
  <div class="project-card2__body">
    {% if card.year %}<p class="project-card2__meta">{{ card.year }}</p>{% endif %}
    <h3><a href="/work/{{ card.slug }}">{{ card.title }}</a></h3>
    <p>{{ card.summary }}</p>
    {% if card.result_headline %}<p class="project-card2__result"><strong>Result:</strong> {{ card.result_headline }}</p>{% endif %}
    {% if card.stack %}<ul class="tag-list" aria-label="Technologies">{% for tag in card.stack %}<li>{{ tag }}</li>{% endfor %}</ul>{% endif %}
    <a class="blue-link" href="/work/{{ card.slug }}">Read the case study<span class="visually-hidden">: {{ card.title }}</span></a>
  </div>
</article>
```

`work.html` body: replace the `{% for project in projects %}` loop with `{% for card in cards %}{% include "components/project_card.html" %}{% else %}...` keeping the empty-state paragraph.

`home.html` (full replacement of the content block; keep `{% extends %}` and `{% block title %}` lines):

```html
<section id="header" class="header mark-hero">
  <div class="container">
    <div class="mark-hero__copy reveal">
      {% if site.profile.availability_text %}<p class="availability-pill">{{ site.profile.availability_text }}</p>{% endif %}
      <h1>{{ view.profile.headline }}</h1>
      <p>{{ view.profile.summary or "A portfolio of practical software, database, automation, and support work built around real problems and measurable workflow improvements." }}</p>
      <div class="hero-actions">
        <a class="button button-primary" href="#work" data-umami-event="cta-view-work">View my work</a>
        <a class="button button-outline" href="/contact" data-umami-event="cta-connect-hero">Connect with me</a>
      </div>
    </div>
  </div>
</section>

<section id="about" class="services-section">
  <div class="container narrow-heading reveal">
    <h2>Hi, I'm Jeremy.</h2>
    <p>I build the software, databases, and automation that make day-to-day operations easier to run, then train and support the people who use them. This site is a working record of that work.</p>
  </div>
  <div class="container service-grid">
    {% for capability in view.capabilities %}
      <article class="service-card reveal">
        <span class="service-icon" aria-hidden="true">{{ loop.index }}</span>
        <h3>{{ capability.title }}</h3>
        <p>{{ capability.body }}</p>
      </article>
    {% endfor %}
  </div>
</section>

<section class="split-detail">
  {% if site.has_portrait %}
    <img class="split-detail__image" src="{{ static_url('assets/img/jeremyguill_profile.webp') }}"
         srcset="{{ static_url('assets/img/jeremyguill_profile-600.webp') }} 600w, {{ static_url('assets/img/jeremyguill_profile.webp') }} 1200w"
         sizes="(max-width: 62rem) 100vw, 50vw" width="1200" height="1400" alt="Jeremy Guill" loading="lazy">
  {% endif %}
  <div class="split-detail__copy bg-gray reveal">
    <div>
      <h2>How I approach technical work</h2>
      <p>I take time to understand what is actually happening before proposing software, so the tools I build fit the environment, earn trust, and stay maintainable after launch.</p>
      <h3>Process first</h3>
      <p>Map the current workflow, clarify the pain points, and build around the reality of the job instead of forcing people into generic tools.</p>
      <h3>Reliable implementation</h3>
      <p>Requirements, database structure, testing, rollout support, user training, troubleshooting, and iteration stay connected from start to finish.</p>
    </div>
  </div>
</section>

<section id="work" class="projects-section">
  <div class="container narrow-heading reveal">
    <h2>Selected work</h2>
    <p>Representative projects across scheduling automation, lending-library systems, FileMaker workflows, and database-backed operations.</p>
  </div>
  <div class="container card-grid">
    {% for card in view.home_project_cards %}
      {% include "components/project_card.html" %}
    {% else %}
      <p>Selected projects will appear here after they are published.</p>
    {% endfor %}
  </div>
  {% if view.has_more_projects %}
    <div class="container work-cta">
      <a class="button button-primary" href="/work">View all work</a>
    </div>
  {% endif %}
</section>

<section class="principle-section">
  <div class="container reveal">
    <h2>Built for people who need software to make work clearer.</h2>
    <p class="principle">The strongest work starts with understanding the people, the process, and the constraints before writing the solution.</p>
  </div>
</section>

{% if view.show_blog_section %}
<section id="writing" class="blog-section">
  <div class="container narrow-heading reveal">
    <h2>Latest writing</h2>
    <p>Notes on practical software, workflow systems, and the craft of building tools that fit real work.</p>
  </div>
  <div class="container blog-grid">
    {% for post in view.blog_posts %}
      <article class="blog-card reveal">
        <h3><a href="/blog/{{ post.slug }}">{{ post.title }}</a></h3>
        <p>{{ post.summary }}</p>
        <a class="blue-link" href="/blog/{{ post.slug }}">Read the post</a>
      </article>
    {% endfor %}
  </div>
  <div class="container work-cta">
    <a class="button button-primary" href="/blog">View all posts</a>
  </div>
</section>
{% endif %}

<section class="contact-cta bg-gray">
  <div class="container reveal">
    <h2>Hiring, or have a workflow that needs fixing?</h2>
    <p>Whether you are filling a role or looking for someone to build or improve a system, I'm glad to talk through the work shown here and the problems behind it.</p>
    <a class="button button-primary" href="/contact" data-umami-event="cta-connect-footer">Connect with me</a>
  </div>
</section>
```
The `<blockquote>` and the self-attribution are gone. The `{% block title %}` line stays as is.

`components.css` append:

```css
/* Cards, pills, principle block */
.card-grid { display: grid; gap: 2rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
.project-card2 { display: flex; flex-direction: column; background: var(--paper); border: 1px solid var(--line); border-radius: .6rem; overflow: hidden; transition: transform .2s ease, box-shadow .2s ease; }
.project-card2:hover, .project-card2:focus-within { transform: translateY(-4px); box-shadow: 0 1.2rem 2.4rem rgba(0, 0, 0, .12); }
.project-card2__media { display: block; aspect-ratio: 16 / 9; background: var(--gray); }
.project-card2__media img { width: 100%; height: 100%; object-fit: cover; display: block; }
.project-card2__body { padding: 1.4rem; display: grid; gap: .7rem; align-content: start; }
.project-card2__body h3 a { text-decoration: none; }
.project-card2__body h3 a::after { content: ""; position: absolute; inset: 0; }
.project-card2 { position: relative; }
.project-card2__meta { margin: 0; font-size: .8rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--blue); }
.project-card2__result { margin: 0; color: var(--ink); }
.tag-list { display: flex; flex-wrap: wrap; gap: .4rem; list-style: none; margin: 0; padding: 0; }
.tag-list li { background: var(--gray); border: 1px solid var(--line); border-radius: 999px; padding: .15rem .65rem; font-size: .78rem; color: var(--ink); }
.availability-pill { display: inline-block; margin: 0 0 1.2rem; padding: .35rem .9rem; border-radius: 999px; background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .45); color: #fff; font-weight: 700; font-size: .85rem; }
.principle-section { padding: 5rem 0; text-align: center; background: var(--gray); }
.principle { max-width: 44rem; margin: 1.5rem auto 0; font-size: 1.35rem; line-height: 2rem; color: var(--ink); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
```
(`.visually-hidden` already exists in site.css; omit if so — check with grep.)

- [ ] **Step 4:** `uv run pytest -q` → PASS. The existing `.project-row`, `.testimonial-section` CSS may now be unused; leave it.

- [ ] **Step 5: Commit** (`feat: project cards, merged homepage sections, availability, blog section rule`).

### Task 13: Case-study template

**Files:**
- Create: `src/portfolio/content/toc.py`, `tests/unit/content/test_toc.py`, `tests/integration/public/test_case_study.py`
- Modify: `src/portfolio/public/routes.py` (`project_detail`), `src/portfolio/templates/public/project.html`, `src/portfolio/static/assets/components.css`

**Interfaces:**
- Produces: `TocItem(id: str, text: str)`; `enhance_case_study_html(html: str) -> tuple[str, list[TocItem]]` (adds ids to `<h2>`, wraps tables in `<div class="table-scroll">`); `reading_minutes(html: str) -> int`.

- [ ] **Step 1: Failing tests**

`tests/unit/content/test_toc.py`:

```python
from __future__ import annotations

from portfolio.content.toc import enhance_case_study_html, reading_minutes


def test_adds_unique_ids_and_builds_toc():
    html, items = enhance_case_study_html("<h2>The Problem</h2><p>x</p><h2>The Problem</h2><h2>What I Built &amp; Why</h2>")

    assert [i.id for i in items] == ["the-problem", "the-problem-2", "what-i-built-why"]
    assert '<h2 id="the-problem">' in html and '<h2 id="the-problem-2">' in html
    assert items[2].text == "What I Built & Why"


def test_no_headings_gives_empty_toc_and_untouched_html():
    html, items = enhance_case_study_html("<p>Just text.</p>")

    assert items == [] and html == "<p>Just text.</p>"


def test_tables_are_wrapped_for_horizontal_scroll():
    html, _ = enhance_case_study_html("<table><tr><td>a</td></tr></table>")

    assert html == '<div class="table-scroll"><table><tr><td>a</td></tr></table></div>'


def test_heading_with_only_symbols_gets_fallback_id():
    _, items = enhance_case_study_html("<h2>???</h2>")

    assert items[0].id == "section"


def test_reading_minutes_has_floor_of_one():
    assert reading_minutes("<p>short</p>") == 1
    assert reading_minutes("<p>" + "word " * 650 + "</p>") == 3
```

`tests/integration/public/test_case_study.py`:

```python
from __future__ import annotations

from portfolio.content.enums import PublicationState
from portfolio.content.models import Project


def _add(db_session, slug, position, html="<h2>A</h2><h2>B</h2><h2>C</h2><p>x</p>", **kw):
    project = Project(title=slug.title(), slug=slug, summary="Sum.", rendered_html=html,
                      state=PublicationState.PUBLISHED, sort_position=position, **kw)
    db_session.add(project)
    return project


def test_case_study_has_glance_toc_breadcrumb_and_single_h1(client, db_session):
    _add(db_session, "one", 1, role="Creator", stack="Flask, SQL", year="2025", result_headline="Faster")
    db_session.commit()

    html = client.get("/work/one").get_data(as_text=True)

    assert html.count("<h1") == 1
    assert 'aria-label="Breadcrumb"' in html and 'href="/work"' in html
    assert "Creator" in html and "Flask" in html and "2025" in html and "Faster" in html
    assert 'aria-label="On this page"' in html and 'href="#a"' in html
    assert "min read" in html


def test_case_study_without_glance_or_headings_omits_those_blocks(client, db_session):
    _add(db_session, "bare", 1, html="<p>Just text.</p>")
    db_session.commit()

    html = client.get("/work/bare").get_data(as_text=True)

    assert 'class="glance"' not in html and 'aria-label="On this page"' not in html


def test_previous_and_next_project_links(client, db_session):
    for index, slug in enumerate(("a", "b", "c"), start=1):
        _add(db_session, slug, index)
    db_session.commit()

    middle = client.get("/work/b").get_data(as_text=True)
    first = client.get("/work/a").get_data(as_text=True)

    assert 'href="/work/a"' in middle and 'href="/work/c"' in middle
    assert 'rel="prev"' not in first and 'rel="next"' in first


def test_case_study_ends_with_call_to_action(client, db_session):
    _add(db_session, "one", 1)
    db_session.commit()

    assert 'href="/contact"' in client.get("/work/one").get_data(as_text=True).split("</article>")[1]
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement** `src/portfolio/content/toc.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

_H2 = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class TocItem:
    id: str
    text: str


def _slug(text: str) -> str:
    return _NON_SLUG.sub("-", text.lower()).strip("-") or "section"


def enhance_case_study_html(html: str) -> tuple[str, list[TocItem]]:
    """Add ids to h2 headings, collect a TOC, and make tables scroll on small screens.

    Input is already sanitized by nh3; ids are derived from visible text only.
    """
    items: list[TocItem] = []
    used: set[str] = set()

    def add_id(match: re.Match[str]) -> str:
        text = unescape(_TAG.sub("", match.group(1))).strip()
        base = _slug(text)
        slug, count = base, 2
        while slug in used:
            slug, count = f"{base}-{count}", count + 1
        used.add(slug)
        items.append(TocItem(slug, text))
        return f'<h2 id="{slug}">{match.group(1)}</h2>'

    out = _H2.sub(add_id, html)
    out = out.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )
    return out, items


def reading_minutes(html: str) -> int:
    words = len(unescape(_TAG.sub(" ", html)).split())
    return max(1, round(words / 250))
```

`routes.py` `project_detail`: import `from portfolio.content.toc import enhance_case_study_html, reading_minutes` and compute after the project lookup:

```python
    body_html, toc = enhance_case_study_html(project.rendered_html)
    all_projects = published_projects()
    index = next((i for i, p in enumerate(all_projects) if p.id == project.id), 0)
    previous_project = all_projects[index - 1] if index > 0 else None
    next_project = all_projects[index + 1] if index + 1 < len(all_projects) else None
```
and pass `body_html=body_html, toc=toc, minutes=reading_minutes(project.rendered_html), previous_project=previous_project, next_project=next_project` to `render_template`.

`project.html` (replace; keep gallery block):

```html
{% extends "public/base.html" %}
{% block title %}{{ metadata.title }}{% endblock %}
{% block content %}
<article class="project-detail">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/">Home</a> <span aria-hidden="true">/</span> <a href="/work">Work</a> <span aria-hidden="true">/</span> <span aria-current="page">{{ project.title }}</span>
  </nav>
  <p class="eyebrow">Case study · {{ minutes }} min read</p>
  <h1>{{ project.title }}</h1>
  <p class="lede">{{ project.summary }}</p>
  {% if project.role or project.stack_list or project.year or project.result_headline %}
    <dl class="glance">
      {% if project.role %}<div><dt>Role</dt><dd>{{ project.role }}</dd></div>{% endif %}
      {% if project.year %}<div><dt>Year</dt><dd>{{ project.year }}</dd></div>{% endif %}
      {% if project.stack_list %}<div><dt>Stack</dt><dd>{{ project.stack_list|join(' · ') }}</dd></div>{% endif %}
      {% if project.result_headline %}<div><dt>Result</dt><dd>{{ project.result_headline }}</dd></div>{% endif %}
    </dl>
  {% endif %}
  {% if hero_asset %}
    <img class="project-hero" src="/media/public/{{ hero_asset.id }}/hero_desktop.webp"
         srcset="/media/public/{{ hero_asset.id }}/hero_mobile.webp 900w, /media/public/{{ hero_asset.id }}/hero_desktop.webp 1600w"
         sizes="(max-width: 54rem) 100vw, 54rem" width="1600" height="900"
         alt="{{ hero_asset.alt_text or project.title ~ ' project preview' }}" loading="eager" fetchpriority="high">
  {% endif %}
  {% if toc|length >= 3 %}
    <nav class="toc" aria-label="On this page">
      <p class="toc__title">On this page</p>
      <ol>{% for item in toc %}<li><a href="#{{ item.id }}">{{ item.text }}</a></li>{% endfor %}</ol>
    </nav>
  {% endif %}
  <div class="prose">{{ body_html | safe }}</div>
  {% if gallery %}
    <section class="project-gallery" aria-label="Project gallery">
      <h2>Gallery</h2>
      <div class="gallery-grid">
        {% for asset in gallery %}
          <img src="/media/public/{{ asset.id }}/hero_desktop.webp" width="1600" height="900" alt="{{ asset.alt_text or project.title ~ ' gallery image' }}" loading="lazy">
        {% endfor %}
      </div>
    </section>
  {% endif %}
</article>
<section class="case-cta">
  <h2>Have a similar problem?</h2>
  <p>I'm happy to talk through how I'd approach it.</p>
  <a class="button button-primary" href="/contact" data-umami-event="cta-connect-case-study">Connect with me</a>
</section>
{% if previous_project or next_project %}
<nav class="project-pager" aria-label="More case studies">
  {% if previous_project %}<a rel="prev" href="/work/{{ previous_project.slug }}"><span>Previous</span>{{ previous_project.title }}</a>{% endif %}
  {% if next_project %}<a rel="next" href="/work/{{ next_project.slug }}"><span>Next</span>{{ next_project.title }}</a>{% endif %}
</nav>
{% endif %}
{% endblock %}
```
(The test `split("</article>")[1]` expects the CTA to follow the article: it does.)

`components.css` append:

```css
/* Case study */
.breadcrumb { font-size: .85rem; margin-bottom: 1rem; }
.breadcrumb a { color: var(--blue-bright); }
.glance { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 1rem 1.5rem; margin: 1.5rem 0; padding: 1.2rem 1.4rem; background: var(--gray); border: 1px solid var(--line); border-radius: .5rem; }
.glance div { min-width: 0; }
.glance dt { font-size: .72rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--blue); }
.glance dd { margin: .2rem 0 0; color: var(--ink); }
.toc { margin: 2rem 0; padding: 1.2rem 1.4rem; border-left: 4px solid var(--blue-bright); background: var(--gray); }
.toc__title { margin: 0 0 .5rem; font-weight: 700; color: var(--ink); }
.toc ol { margin: 0; padding-left: 1.2rem; display: grid; gap: .25rem; }
.prose h2 { scroll-margin-top: 6rem; }
.table-scroll { overflow-x: auto; margin: 1.5rem 0; }
.table-scroll table { min-width: 32rem; }
.prose pre { overflow-x: auto; max-width: 100%; }
.case-cta { max-width: 54rem; margin: 4rem auto 0; padding: 2rem; text-align: center; background: var(--gray); border-radius: .6rem; }
.project-pager { max-width: 54rem; margin: 2rem auto 4rem; display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
.project-pager a { display: block; text-decoration: none; font-weight: 700; color: var(--ink); max-width: 24rem; }
.project-pager a span { display: block; font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; color: var(--blue); }
.project-pager a[rel="next"] { margin-left: auto; text-align: right; }
```

- [ ] **Step 4:** `uv run pytest -q` → PASS; existing `test_published_project_has_public_page` still passes.

- [ ] **Step 5: Commit** (`feat: case-study template with at-a-glance, TOC, pager and CTA`).

### Task 14: Contact page

**Files:**
- Modify: `src/portfolio/templates/public/contact.html`, `src/portfolio/contact/routes.py`, `src/portfolio/static/assets/site.js`, `src/portfolio/static/assets/components.css`
- Create: `tests/integration/contact/test_contact_page.py`

(First read `src/portfolio/contact/forms.py` and the existing `tests/integration/contact/*` to reuse their payload helpers; the messages below must match `ContactForm`'s real field names `name`, `email`, `subject`, `message`, `form_started_at`, `company_website`.)

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

from sqlalchemy import select

from portfolio.content.models import SiteProfile


def test_contact_page_has_no_hardcoded_fallback_email_or_plain_mailto(client, db_session):
    db_session.add(SiteProfile(email=None))
    db_session.commit()

    html = client.get("/contact").get_data(as_text=True)

    assert "rbtm2006@me.com" not in html and "mailto:" not in html


def test_email_is_not_in_plain_text_when_configured(client, db_session):
    db_session.add(SiteProfile(email="hello@example.test"))
    db_session.commit()

    html = client.get("/contact").get_data(as_text=True)

    assert "hello@example.test" not in html
    assert 'data-email-user="hello"' in html and 'data-email-domain="example.test"' in html


def test_form_has_autocomplete_and_reply_promise(client):
    html = client.get("/contact").get_data(as_text=True)

    assert 'autocomplete="name"' in html and 'autocomplete="email"' in html
    assert "usually reply within" in html


def test_success_banner_only_with_sent_flag(client):
    assert 'role="status"' not in client.get("/contact").get_data(as_text=True)
    assert 'role="status"' in client.get("/contact?sent=1").get_data(as_text=True)


def test_valid_submission_redirects_with_sent_flag(client):
    import time

    response = client.post(
        "/contact",
        data={"name": "A", "email": "a@example.test", "subject": "Hi", "message": "Hello there friend",
              "form_started_at": str(time.time() - 30), "company_website": ""},
    )

    assert response.status_code == 302 and response.headers["Location"].endswith("/contact?sent=1")


def test_invalid_submission_shows_field_error_and_keeps_input(client):
    response = client.post("/contact", data={"name": "A", "email": "not-an-email", "subject": "", "message": ""})
    html = response.get_data(as_text=True)

    assert response.status_code == 422
    assert 'role="alert"' in html and 'value="A"' in html
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** `contact/routes.py`: both `redirect(url_for("public.contact"))` calls become `redirect(url_for("public.contact", sent=1))`. `public/routes.py` `contact()` passes `sent=request.args.get("sent") == "1"` (import `request`).

`contact.html` (replace):

```html
{% extends "public/base.html" %}
{% block title %}Contact | Jeremy Guill{% endblock %}
{% block content %}
<section class="page-section">
  <p class="eyebrow">Contact</p>
  <h1>Let's talk about your project or role.</h1>
  <p class="lede">If you are hiring, collaborating, or want to ask about a project in this portfolio, send a note. I usually reply within two business days.</p>
  {% set email_parts = (site.profile.email or '').split('@') %}
  {% if email_parts|length == 2 %}
    <p>Prefer email? <span class="obfuscated-email" data-email-user="{{ email_parts[0] }}" data-email-domain="{{ email_parts[1] }}">Use the form below.</span></p>
  {% endif %}
  {% if site.profile.linkedin_url %}<p>Or find me on <a href="{{ site.profile.linkedin_url }}" rel="noopener noreferrer me" target="_blank">LinkedIn</a>.</p>{% endif %}
  {% if sent %}
    <div class="notice" role="status" tabindex="-1"><p>Thanks, your message is on its way. I'll reply soon.</p></div>
  {% endif %}
  {% if form and form.errors %}
    <div class="alert" role="alert">
      {% for messages in form.errors.values() %}
        {% for message in messages %}<p>{{ message }}</p>{% endfor %}
      {% endfor %}
    </div>
  {% endif %}
  <form method="post" action="/contact" class="contact-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <input type="hidden" name="form_started_at" value="{{ form.command.form_started_at if form else form_started_at }}">
    <label>Name <input name="name" autocomplete="name" value="{{ form.command.name if form else '' }}" required></label>
    <label>Email <input name="email" type="email" autocomplete="email" value="{{ form.command.email if form else '' }}" required></label>
    <label>Subject <input name="subject" autocomplete="off" value="{{ form.command.subject if form else '' }}" required></label>
    <label class="visually-hidden">Company website <input name="company_website" tabindex="-1" autocomplete="off"></label>
    <label>Message <textarea name="message" rows="8" maxlength="5000" placeholder="Tell me what caught your attention, what role or collaboration you have in mind, or what question you have about the work." required>{{ form.command.message if form else '' }}</textarea></label>
    <button class="button" type="submit" data-umami-event="contact-submit">Send message</button>
  </form>
</section>
{% endblock %}
```
`site.js` append:

```js
document.querySelectorAll(".obfuscated-email").forEach((node) => {
  const user = node.getAttribute("data-email-user");
  const domain = node.getAttribute("data-email-domain");
  if (!user || !domain) return;
  const link = document.createElement("a");
  link.href = `mailto:${user}@${domain}`;
  link.textContent = `${user}@${domain}`;
  node.replaceChildren(link);
});

const statusBanner = document.querySelector('.notice[role="status"]');
if (statusBanner instanceof HTMLElement) statusBanner.focus();
```
`components.css` append:

```css
.notice { padding: 1rem 1.2rem; border-left: 4px solid #1a7f4b; background: #eaf7f0; color: #14472b; border-radius: .3rem; margin: 1.5rem 0; }
.notice p { margin: 0; }
.contact-form { display: grid; gap: 1.1rem; margin-top: 1.5rem; }
```

- [ ] **Step 4:** tests → PASS (fix any existing contact test that asserted the old redirect target `/contact`).

- [ ] **Step 5: Commit** (`feat: contact page success state, autocomplete, reply promise, obfuscated email`).

### Task 15: Dark mode, print, contrast, no-JS-safe reveal

**Files:**
- Create: `src/portfolio/static/assets/theme.css`, `tests/unit/test_theme_contrast.py`
- Modify: `src/portfolio/templates/public/base.html`

- [ ] **Step 1: Failing tests** `tests/unit/test_theme_contrast.py`

```python
from __future__ import annotations

import re
from pathlib import Path

ASSETS = Path("src/portfolio/static/assets")


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _lum(rgb: tuple[int, int, int]) -> float:
    channels = []
    for c in rgb:
        s = c / 255
        channels.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(_hex(a)), _lum(_hex(b))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", block))


LIGHT = _tokens((ASSETS / "site.css").read_text().split("}", 1)[0])
DARK_BLOCK = re.search(
    r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{(.*?)\}", (ASSETS / "theme.css").read_text(), re.DOTALL
).group(1)
DARK = _tokens(DARK_BLOCK)

PAIRS = [("ink", "paper"), ("ink-soft", "paper"), ("ink-soft", "gray"), ("blue-bright", "paper"), ("blue-bright", "gray"), ("blue", "paper")]


def test_light_theme_meets_wcag_aa():
    for fg, bg in PAIRS:
        assert ratio(LIGHT[fg], LIGHT[bg]) >= 4.5, (fg, bg, LIGHT[fg], LIGHT[bg])


def test_dark_theme_meets_wcag_aa():
    merged = {**LIGHT, **DARK}
    for fg, bg in PAIRS:
        assert ratio(merged[fg], merged[bg]) >= 4.5, (fg, bg, merged[fg], merged[bg])


def test_reveal_is_only_hidden_when_js_class_present():
    css = (ASSETS / "site.css").read_text()

    assert re.search(r"\.js \.reveal\s*\{\s*opacity:\s*0", css)
    assert not re.search(r"(^|\n)\.reveal\s*\{[^}]*opacity:\s*0", css)


def test_print_stylesheet_reveals_content_and_hides_chrome():
    css = (ASSETS / "theme.css").read_text()
    print_block = css.split("@media print", 1)[1]

    assert ".site-header" in print_block and "display: none" in print_block
    assert "opacity: 1" in print_block


def test_theme_is_linked_after_other_styles(client):
    html = client.get("/").get_data(as_text=True)

    assert html.index("components.css") < html.index("theme.css")
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement** `theme.css`:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --ink: #eef1f6;
    --ink-soft: #c2c8d2;
    --paper: #14161a;
    --gray: #1c1f25;
    --line: #333a44;
    --blue: #9db8ff;
    --blue-bright: #86a8ff;
    color-scheme: dark;
  }

  .project-card2,
  .tag-list li,
  .glance,
  .toc,
  .case-cta { background: var(--gray); border-color: var(--line); }

  .notice { background: #12301f; color: #bfe8d0; border-color: #2fae6b; }

  img { filter: brightness(.92); }
}

@media print {
  .site-header,
  .site-footer__links,
  .nav-toggle,
  .hero-actions,
  .case-cta,
  .project-pager,
  .skip-link { display: none !important; }

  .reveal,
  .js .reveal {
    opacity: 1 !important;
    transform: none !important;
  }

  body { background: #fff; color: #000; font-size: 11pt; }
  a { color: #000; text-decoration: underline; }
  .prose a[href^="http"]::after { content: " (" attr(href) ")"; font-size: .85em; }
  .site-main { padding-top: 0; }
}
```
`base.html`: link after components.css: `<link rel="stylesheet" href="{{ static_url('assets/theme.css') }}">`.

- [ ] **Step 4:** tests → PASS. If a light pair fails (for example `blue` on `gray`), darken that token in `site.css` `:root` by the smallest amount that passes; re-run. Then render the site in dark mode (`run` skill; emulate with browser devtools or a Playwright `color_scheme="dark"` screenshot of `/`, `/work`, a case study, `/contact`) and `grep -nE '#[0-9a-fA-F]{3,6}\b' src/portfolio/static/assets/site.css` for hard-coded light colours that look wrong; override them in `theme.css`'s dark block.

- [ ] **Step 5: Commit** (`feat: dark mode, print stylesheet and AA-verified contrast tokens`).

---

# Phase 3: SEO and discoverability

### Task 16: JSON-LD, breadcrumbs, RSS, security.txt

**Files:**
- Modify: `src/portfolio/seo/schemas.py`, `src/portfolio/seo/services.py`, `src/portfolio/seo/routes.py`, `src/portfolio/public/routes.py`, `src/portfolio/public/blog_routes.py`, `src/portfolio/templates/public/base.html`
- Create: `src/portfolio/templates/rss.xml`, `tests/integration/seo/test_rich_seo.py`

**Interfaces:**
- Produces: `SeoPage.extra: dict[str, object] | None`, merged into the JSON-LD by `build_json_ld`; routes `/rss.xml` and `/.well-known/security.txt`.

- [ ] **Step 1: Failing tests**

```python
from __future__ import annotations

import json
import re

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project, SiteProfile


def _ld(html: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)]


def test_person_json_ld_has_same_as_when_links_configured(client, db_session):
    db_session.add(SiteProfile(linkedin_url="https://www.linkedin.com/in/x", github_url="https://github.com/x"))
    db_session.commit()

    person = _ld(client.get("/").get_data(as_text=True))[0]

    assert person["@type"] == "Person" and person["name"] == "Jeremy Guill"
    assert person["sameAs"] == ["https://www.linkedin.com/in/x", "https://github.com/x"]


def test_person_json_ld_omits_same_as_when_none(client):
    assert "sameAs" not in _ld(client.get("/").get_data(as_text=True))[0]


def test_project_page_emits_breadcrumb_list(client, db_session):
    db_session.add(Project(title="One", slug="one", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()

    blocks = _ld(client.get("/work/one").get_data(as_text=True))
    crumbs = next(b for b in blocks if b["@type"] == "BreadcrumbList")

    assert [i["name"] for i in crumbs["itemListElement"]] == ["Home", "Work", "One"]


def test_blog_post_json_ld_has_dates_and_author(client, db_session):
    from datetime import UTC, datetime

    db_session.add(BlogPost(title="P", slug="p", summary="s", state=PublicationState.PUBLISHED,
                            published_at=datetime(2026, 5, 1, tzinfo=UTC)))
    db_session.commit()

    post = _ld(client.get("/blog/p").get_data(as_text=True))[0]

    assert post["@type"] == "BlogPosting" and post["datePublished"].startswith("2026-05-01")
    assert post["author"]["name"] == "Jeremy Guill"


def test_rss_is_valid_on_empty_site_and_lists_posts(client, db_session, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    empty = client.get("/rss.xml")
    assert empty.status_code == 200 and empty.mimetype == "application/rss+xml" and "<item>" not in empty.get_data(as_text=True)

    db_session.add(BlogPost(title="Hello & <World>", slug="p", summary="s", state=PublicationState.PUBLISHED))
    db_session.commit()
    body = client.get("/rss.xml").get_data(as_text=True)

    assert "<link>https://example.test/blog/p</link>" in body and "Hello &amp; &lt;World&gt;" in body


def test_pages_advertise_rss_feed(client):
    assert 'rel="alternate" type="application/rss+xml"' in client.get("/").get_data(as_text=True)


def test_security_txt(client, app):
    app.config["PUBLIC_ORIGIN"] = "https://example.test"
    response = client.get("/.well-known/security.txt")
    body = response.get_data(as_text=True)

    assert response.mimetype == "text/plain"
    assert "Contact: https://example.test/contact" in body and "Expires: " in body
    assert "Canonical: https://example.test/.well-known/security.txt" in body


def test_project_title_uses_seo_title_when_set(client, db_session):
    db_session.add(Project(title="One", slug="one", summary="s", seo_title="One: a descriptor | Jeremy Guill", state=PublicationState.PUBLISHED))
    db_session.commit()

    assert "<title>One: a descriptor | Jeremy Guill</title>" in client.get("/work/one").get_data(as_text=True)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.**

`schemas.py` `SeoPage`: add `extra: dict[str, object] | None = None`.
`services.py` `build_json_ld`: before `return data` add `if page.extra: data.update(page.extra)`; add function

```python
def breadcrumb_json_ld(crumbs: list[tuple[str, str]]) -> dict[str, object]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute_url(path)}
            for i, (name, path) in enumerate(crumbs, start=1)
        ],
    }
```
Add `breadcrumbs: dict[str, object] | None = None` handling: simplest is to let `PageMetadata.json_ld` stay a single dict and render breadcrumbs as a second `<script>`. So: `PageMetadata` gets `extra_json_ld: list[dict[str, object]]` (default via `field(default_factory=list)`, declared last), and `SeoPage` gets `breadcrumbs: list[tuple[str, str]] | None = None`; `build_metadata` sets `extra_json_ld=[breadcrumb_json_ld(page.breadcrumbs)] if page.breadcrumbs else []`. `metadata.html` after the first script: `{% for block in metadata.extra_json_ld %}<script type="application/ld+json">{{ block|tojson }}</script>{% endfor %}`.

Routes:
- `home()`: build `same_as = [u for u in (view.profile.linkedin_url, view.profile.github_url) if u]` and pass `extra={"sameAs": same_as} if same_as else None`.
- `project_detail`: `breadcrumbs=[("Home", "/"), ("Work", "/work"), (project.title, f"/work/{project.slug}")]`, and `extra={"author": {"@type": "Person", "name": "Jeremy Guill"}}`.
- `blog_routes.detail`: `extra={"datePublished": post.published_at.isoformat() if post.published_at else None ...}`: build dict only with non-None values:

```python
    extra: dict[str, object] = {"author": {"@type": "Person", "name": "Jeremy Guill"}}
    if post.published_at:
        extra["datePublished"] = post.published_at.isoformat()
    extra["dateModified"] = post.updated_at.isoformat()
```
and pass `extra=extra`.

`project.html` already uses `metadata.title` for `<title>`. For blog post/other templates leave.

`seo/routes.py` append:

```python
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime


@seo_bp.get("/rss.xml")
def rss():
    posts = list(
        db.session.execute(
            select(BlogPost)
            .where(BlogPost.state == PublicationState.PUBLISHED)
            .order_by(BlogPost.published_at.desc(), BlogPost.title)
            .limit(20)
        ).scalars()
    )
    items = [
        {
            "title": p.title,
            "link": absolute_url(f"/blog/{p.slug}"),
            "summary": p.summary,
            "date": format_datetime(p.published_at or p.updated_at) if (p.published_at or p.updated_at).tzinfo else format_datetime((p.published_at or p.updated_at).replace(tzinfo=UTC)),
        }
        for p in posts
    ]
    return Response(
        render_template("rss.xml", items=items, site_url=absolute_url("/"), feed_url=absolute_url("/rss.xml")),
        mimetype="application/rss+xml",
    )


@seo_bp.get("/.well-known/security.txt")
def security_txt():
    expires = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = (
        f"Contact: {absolute_url('/contact')}\n"
        f"Expires: {expires}\n"
        f"Canonical: {absolute_url('/.well-known/security.txt')}\n"
        "Preferred-Languages: en\n"
    )
    return Response(body, mimetype="text/plain")
```
(add `BlogPost` import already present from Task 3). Simplify the `date` expression into a small helper `_rfc822(value: datetime) -> str` that attaches UTC when naive; use it in the dict.

`templates/rss.xml` (autoescape applies to `.xml` templates in Flask; confirm with the test's `&amp;` assertion):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Jeremy Guill: Notes on practical software work</title>
    <link>{{ site_url }}</link>
    <description>Notes on practical software, workflow systems, and building tools that fit real work.</description>
    <language>en-us</language>
    <atom:link href="{{ feed_url }}" rel="self" type="application/rss+xml"/>
    {% for item in items %}
    <item>
      <title>{{ item.title }}</title>
      <link>{{ item.link }}</link>
      <guid isPermaLink="true">{{ item.link }}</guid>
      <description>{{ item.summary }}</description>
      <pubDate>{{ item.date }}</pubDate>
    </item>
    {% endfor %}
  </channel>
</rss>
```
`base.html` head: `<link rel="alternate" type="application/rss+xml" title="Jeremy Guill: Notes" href="/rss.xml">`.

- [ ] **Step 4:** `uv run pytest -q` → PASS.

- [ ] **Step 5: Commit** (`feat: rich JSON-LD, breadcrumbs, RSS feed and security.txt`).

---

# Phase 5: Security headers

### Task 17: Scope CSP per path, add COOP, allow the analytics origin only when configured

**Files:**
- Modify: `src/portfolio/security/headers.py`, `tests/security/test_headers.py`

**Interfaces:**
- Produces: `content_security_policy(path: str, analytics_origin: str | None) -> str`. Reads `current_app.config.get("ANALYTICS_SCRIPT_URL")` (set in Task 18) to derive `analytics_origin` (scheme + host).

- [ ] **Step 1: Failing tests** (append to `tests/security/test_headers.py`)

```python
from portfolio.security.headers import content_security_policy


def test_public_pages_do_not_allow_openai_connections(client):
    csp = client.get("/").headers["Content-Security-Policy"]

    assert "api.openai.com" not in csp
    assert "connect-src 'self'" in csp


def test_admin_pages_still_allow_openai_connections(client):
    assert "https://api.openai.com" in client.get("/admin/sign-in").headers["Content-Security-Policy"]


def test_cross_origin_opener_policy_is_set(client):
    assert client.get("/").headers["Cross-Origin-Opener-Policy"] == "same-origin"


def test_analytics_origin_is_added_to_public_script_and_connect_src_only_when_given():
    with_origin = content_security_policy("/", "https://stats.example.test")
    without = content_security_policy("/", None)

    assert "script-src 'self' https://stats.example.test" in with_origin
    assert "connect-src 'self' https://stats.example.test" in with_origin
    assert "stats.example.test" not in without


def test_admin_csp_never_includes_analytics_origin():
    assert "stats.example.test" not in content_security_policy("/admin/projects", "https://stats.example.test")


def test_csp_never_allows_inline_or_wildcards():
    csp = content_security_policy("/", "https://stats.example.test")

    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp and " * " not in csp
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement** `headers.py`:

```python
from __future__ import annotations

from urllib.parse import urlparse

from flask import Response, current_app, request

STATIC_HEADERS = {
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

NO_STORE_PREFIXES = ("/admin/sign-in", "/admin/bootstrap", "/admin/auth/")


def content_security_policy(path: str, analytics_origin: str | None) -> str:
    is_admin = path.startswith("/admin")
    script_src = "'self'"
    connect_src = "'self'"
    if is_admin:
        connect_src += " https://api.openai.com"
    elif analytics_origin:
        script_src += f" {analytics_origin}"
        connect_src += f" {analytics_origin}"
    return (
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        f"img-src 'self' data:; font-src 'self'; object-src 'none'; script-src {script_src}; "
        f"style-src 'self'; connect-src {connect_src}"
    )


def _analytics_origin() -> str | None:
    url = current_app.config.get("ANALYTICS_SCRIPT_URL") or ""
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def apply_security_headers(response: Response) -> Response:
    response.headers.setdefault(
        "Content-Security-Policy", content_security_policy(request.path, _analytics_origin())
    )
    for name, value in STATIC_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.path.startswith(NO_STORE_PREFIXES):
        response.headers["Cache-Control"] = "no-store"
    return response
```
Search for other importers of `SECURITY_HEADERS` (`grep -rn SECURITY_HEADERS src tests`) and update them.

- [ ] **Step 4:** `uv run pytest tests/security -q` and full suite → PASS. Manually verify the admin AI feature still works in the admin pages (it calls the OpenAI API from the browser only if the editor does so; if the admin JS calls only same-origin routes, the allowance is harmless).

- [ ] **Step 5: Commit** (`security: scope CSP connect-src per path, add COOP`).

---

# Phase 7: Analytics

### Task 18: Analytics script tag, events, config

**Files:**
- Modify: `src/portfolio/config.py`, `src/portfolio/__init__.py`, `src/portfolio/public/chrome.py`, `src/portfolio/templates/public/base.html`, `.env.example`, `compose.yaml` (web + worker env pass-through), `tests/unit/test_config.py`
- Create: `tests/integration/public/test_analytics_tag.py`

**Interfaces:**
- Consumes: Task 5 `SiteChrome`; Task 17 CSP (reads `ANALYTICS_SCRIPT_URL`).
- Produces: `Settings.analytics_script_url: str`, `Settings.analytics_website_id: str` → `app.config["ANALYTICS_SCRIPT_URL"]`, `["ANALYTICS_WEBSITE_ID"]`; `SiteChrome.analytics -> dict[str, str] | None` (`script_url`, `website_id`).

- [ ] **Step 1: Failing tests**

`tests/integration/public/test_analytics_tag.py`:

```python
from __future__ import annotations

import re


def _configure(app, url="https://stats.example.test/script.js", site_id="11111111-2222-3333-4444-555555555555"):
    app.config["ANALYTICS_SCRIPT_URL"] = url
    app.config["ANALYTICS_WEBSITE_ID"] = site_id


def test_no_tag_when_unconfigured(client):
    assert "data-website-id" not in client.get("/").get_data(as_text=True)


def test_tag_rendered_when_configured_and_honours_do_not_track(client, app):
    _configure(app)

    html = client.get("/").get_data(as_text=True)

    assert re.search(r'<script defer src="https://stats\.example\.test/script\.js" data-website-id="11111111-2222-3333-4444-555555555555"', html)
    assert 'data-do-not-track="true"' in html


def test_tag_requires_both_settings(client, app):
    app.config["ANALYTICS_SCRIPT_URL"] = "https://stats.example.test/script.js"

    assert "data-website-id" not in client.get("/").get_data(as_text=True)


def test_non_https_script_url_is_ignored(client, app):
    _configure(app, url="http://stats.example.test/script.js")

    assert "data-website-id" not in client.get("/").get_data(as_text=True)


def test_csp_allows_only_the_analytics_origin(client, app):
    _configure(app)

    csp = client.get("/").headers["Content-Security-Policy"]

    assert "script-src 'self' https://stats.example.test" in csp
    assert "https://stats.example.test/script.js" not in csp


def test_admin_pages_never_load_tracker(client, app):
    _configure(app)

    html = client.get("/admin/sign-in").get_data(as_text=True)

    assert "data-website-id" not in html and "stats.example.test" not in client.get("/admin/sign-in").headers["Content-Security-Policy"]


def test_cta_events_are_declared(client):
    html = client.get("/").get_data(as_text=True)

    assert 'data-umami-event="cta-view-work"' in html and 'data-umami-event="cta-connect-hero"' in html
```
Append to `tests/unit/test_config.py`:

```python
def test_analytics_settings_default_to_empty_and_read_env(monkeypatch):
    monkeypatch.delenv("ANALYTICS_SCRIPT_URL", raising=False)
    monkeypatch.delenv("ANALYTICS_WEBSITE_ID", raising=False)
    assert Settings.from_env().analytics_script_url == ""

    monkeypatch.setenv("ANALYTICS_SCRIPT_URL", "https://stats.example.test/script.js")
    monkeypatch.setenv("ANALYTICS_WEBSITE_ID", "abc")
    settings = Settings.from_env()
    assert (settings.analytics_script_url, settings.analytics_website_id) == ("https://stats.example.test/script.js", "abc")
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** `config.py`: add dataclass fields `analytics_script_url: str` and `analytics_website_id: str`; in `from_env` set `analytics_script_url=os.getenv("ANALYTICS_SCRIPT_URL", "").strip(), analytics_website_id=os.getenv("ANALYTICS_WEBSITE_ID", "").strip(),`. `__init__.py` `app.config.from_mapping(...)`: add `ANALYTICS_SCRIPT_URL=settings.analytics_script_url, ANALYTICS_WEBSITE_ID=settings.analytics_website_id,`.

`chrome.py`: add

```python
    @cached_property
    def analytics(self) -> dict[str, str] | None:
        url = (current_app.config.get("ANALYTICS_SCRIPT_URL") or "").strip()
        site_id = (current_app.config.get("ANALYTICS_WEBSITE_ID") or "").strip()
        if not url.startswith("https://") or not site_id:
            return None
        return {"script_url": url, "website_id": site_id}
```
`base.html`, before `</head>`:

```html
    {% if site.analytics %}<script defer src="{{ site.analytics.script_url }}" data-website-id="{{ site.analytics.website_id }}" data-do-not-track="true"></script>{% endif %}
```
`headers.py` `_analytics_origin` already requires https; make it use the same rule: require `site_id` too by also checking `current_app.config.get("ANALYTICS_WEBSITE_ID")` (return None if empty), so a half-configured site never widens the CSP. (Add that check, and a test: `test_csp_unchanged_when_website_id_missing`.)

`.env.example`: add

```
# Optional visitor analytics (self-hosted Umami). Leave empty to disable.
ANALYTICS_SCRIPT_URL=
ANALYTICS_WEBSITE_ID=
```
`compose.yaml`: under both `web` and `worker` `environment:` add `ANALYTICS_SCRIPT_URL: ${ANALYTICS_SCRIPT_URL:-}` and `ANALYTICS_WEBSITE_ID: ${ANALYTICS_WEBSITE_ID:-}` (worker does not need them; add only to `web`).

Event attributes were added to hero/CTA links in Tasks 11, 12, 13, 14; add `data-umami-event="outbound-career-groove"`-style attributes for outbound project links is a content concern; skip.

- [ ] **Step 4:** `uv run pytest -q` → PASS.

- [ ] **Step 5: Commit** (`feat: optional cookie-less analytics script with scoped CSP and CTA events`).

### Task 19: Self-hosted Umami service, docs, production verification

**Files:**
- Modify: `compose.yaml`, `scripts/verify-production.sh`, `tests/operations/test_compose_config.py`, `.env.example`, `docker/backup.sh` (only if it lists databases explicitly; inspect first)
- Create: `docs/analytics.md`

**Interfaces:** Umami listens on container port 3000; compose binds it to `127.0.0.1:3001` and joins `nginx-proxy-manager_default` so the proxy can reach it as `analytics:3000`.

- [ ] **Step 1: Failing tests** (append to `tests/operations/test_compose_config.py`)

```python
def test_analytics_service_is_private_and_hardened():
    compose = Path("compose.yaml").read_text()
    section = compose.split("  analytics:", 1)[1].split("\n  backup:", 1)[0]

    assert '"127.0.0.1:3001:3000"' in section
    assert "image: ghcr.io/umami-software/umami:postgresql-" in section
    assert "restart: unless-stopped" in section and "mem_limit:" in section
    assert "APP_SECRET: ${UMAMI_APP_SECRET:?" in section
    assert "DATABASE_URL: postgresql://umami:" in section
    assert "nginx-proxy-manager_default" in section


def test_umami_has_its_own_database_not_the_portfolio_one():
    section = Path("compose.yaml").read_text().split("  analytics:", 1)[1]

    assert "/umami" in section.split("\n  backup:", 1)[0]
    assert "/portfolio" not in section.split("\n  backup:", 1)[0]
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement.** Pin an exact Umami tag: run `docker pull ghcr.io/umami-software/umami:postgresql-latest` is NOT allowed to float; instead check https://github.com/umami-software/umami/releases for the latest stable and use the matching `postgresql-vX.Y.Z` tag (e.g. `ghcr.io/umami-software/umami:postgresql-v2.19.0`; confirm the tag exists with `docker manifest inspect` before committing).

Add to `compose.yaml` before `backup:`:

```yaml
  analytics:
    image: ghcr.io/umami-software/umami:postgresql-v2.19.0
    environment:
      DATABASE_URL: postgresql://umami:${UMAMI_DB_PASSWORD:?set UMAMI_DB_PASSWORD}@db:5432/umami
      APP_SECRET: ${UMAMI_APP_SECRET:?set UMAMI_APP_SECRET}
      DISABLE_TELEMETRY: "1"
    ports:
      - "127.0.0.1:3001:3000"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - default
      - nginx-proxy-manager_default
    mem_limit: 384m
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    restart: unless-stopped
```
`.env.example` append (documented placeholders, no real secrets):

```
# Umami (analytics). Generate each with: openssl rand -hex 32
UMAMI_DB_PASSWORD=change-me
UMAMI_APP_SECRET=change-me
```
The `${VAR:?}` form would make `docker compose config` (used by existing tests/CI, e.g. `tests/operations`) fail when unset. Check how `test_compose_config.py` and any CI invoke compose; if `docker compose config` is run without those vars, use `${UMAMI_DB_PASSWORD:-}` for the DB password and keep `:?` only for `APP_SECRET`, or update the test fixture environment. Decide by running `UMAMI_DB_PASSWORD= docker compose config >/dev/null` locally.

`docs/analytics.md` documents the owner steps (copied from "Owner Checklist" section 5 below) plus: creating the DB (`docker compose exec db psql -U portfolio -d portfolio -c "CREATE ROLE umami LOGIN PASSWORD '...'; "` and `CREATE DATABASE umami OWNER umami;`), first login (`admin` / `umami`, change immediately), adding the website with domain `jeremyguill.me`, copying the Website ID, and setting `ANALYTICS_SCRIPT_URL=https://stats.jeremyguill.me/script.js` + `ANALYTICS_WEBSITE_ID=<id>`.

`scripts/verify-production.sh` (append; keep `set -eu` semantics):

```sh
body="$(curl --fail --silent --show-error "$origin/")"
if printf '%s' "$body" | grep -qi 'localhost'; then echo "FAIL: localhost found in homepage"; exit 1; fi
printf '%s' "$body" | grep -q 'rel="canonical" href="'"$origin"'/"' || { echo "FAIL: canonical does not match $origin"; exit 1; }
printf '%s' "$body" | grep -q 'property="og:image"' || { echo "FAIL: og:image missing"; exit 1; }
printf '%s' "$body" | grep -q 'rel="icon"' || { echo "FAIL: favicon link missing"; exit 1; }
curl --fail --silent --show-error "$origin/sitemap.xml" | grep -qi 'localhost' && { echo "FAIL: localhost in sitemap"; exit 1; }
curl --fail --silent --show-error "$origin/robots.txt" | grep -qi 'localhost' && { echo "FAIL: localhost in robots.txt"; exit 1; }
curl --fail --silent --show-error "$origin/rss.xml" | grep -q '<rss' || { echo "FAIL: rss feed"; exit 1; }
curl --fail --silent --show-error "$origin/.well-known/security.txt" | grep -q '^Contact:' || { echo "FAIL: security.txt"; exit 1; }
curl --fail --silent --show-error --output /dev/null "$origin/favicon.ico"
if [ -n "${STATS_ORIGIN:-}" ]; then
  printf '%s' "$body" | grep -q 'data-website-id=' || { echo "FAIL: analytics tag missing"; exit 1; }
  curl --fail --silent --show-error --output /dev/null "$STATS_ORIGIN/script.js"
fi
echo "verify-production: OK"
```
Add a test in `tests/operations/` that runs the script's grep logic against a local test-server? Not practical; instead add `tests/operations/test_verify_script.py` asserting the script contains each check string (`localhost`, `canonical`, `og:image`, `rss`, `security.txt`) and `sh -n scripts/verify-production.sh` exits 0 via `subprocess.run(["sh", "-n", ...])`.

- [ ] **Step 4:** `uv run pytest tests/operations -q` (the pre-existing `binds_web_to_localhost_only` failure remains; everything else passes) and `docker compose config >/dev/null` with dummy env values (`UMAMI_DB_PASSWORD=x UMAMI_APP_SECRET=y docker compose config`).

- [ ] **Step 5: Commit** (`ops: add self-hosted Umami analytics service, docs, and production verification checks`).

---

# Phase 4: Content (interview-driven)

### Task 20: `apply-copy` command (reviewed Markdown → database)

**Files:**
- Create: `src/portfolio/content/copy.py`, `tests/unit/content/test_copy.py`, `tests/integration/content/test_apply_copy_cli.py`, `src/portfolio/content/copy/` (directory for `.md` files, created with a `README.md`)
- Modify: `src/portfolio/content/seed.py` (register the command)

**Interfaces:**
- Produces: `parse_copy_file(text: str) -> CopyDoc`; `apply_copy_doc(doc: CopyDoc) -> str` (returns a human-readable result line); CLI `flask --app portfolio content apply-copy [--dry-run] [PATH ...]` (defaults to every `*.md` in `src/portfolio/content/copy/` except `README.md`).

File format:

```
---
type: project            # project | blog | experience
match: pollywog-scheduling-automation     # project/blog: slug; experience: "Organization | Role"
title: Pollywog scheduling automation     # optional (project/blog)
summary: One-sentence summary under 320 chars   # optional
role: Developer           # optional, project only
stack: Microsoft Access, TripLink CSV    # optional, project only
year: 2012–2014           # optional, project only
result_headline: Prep time 4 h → 30 min   # optional, project only
seo_title: ...            # optional
seo_description: ...      # optional
---
Markdown body here (becomes source_markdown; rendered with render_markdown / render_experience_markdown).
```

- [ ] **Step 1: Failing tests**

`tests/unit/content/test_copy.py`:

```python
from __future__ import annotations

import pytest

from portfolio.content.copy import CopyError, parse_copy_file

SAMPLE = """---
type: project
match: pollywog
summary: Short.
stack: Access, CSV
---
## The Problem

Text.
"""


def test_parse_front_matter_and_body():
    doc = parse_copy_file(SAMPLE)

    assert doc.kind == "project" and doc.match == "pollywog"
    assert doc.fields == {"summary": "Short.", "stack": "Access, CSV"}
    assert doc.body.startswith("## The Problem")


def test_missing_front_matter_is_an_error():
    with pytest.raises(CopyError, match="front matter"):
        parse_copy_file("no front matter")


def test_unknown_field_is_an_error():
    with pytest.raises(CopyError, match="unknown field"):
        parse_copy_file("---\ntype: project\nmatch: x\nbogus: 1\n---\nbody")


def test_type_must_be_known():
    with pytest.raises(CopyError, match="type"):
        parse_copy_file("---\ntype: page\nmatch: x\n---\nbody")


def test_summary_longer_than_320_is_an_error():
    with pytest.raises(CopyError, match="320"):
        parse_copy_file("---\ntype: project\nmatch: x\nsummary: " + "a" * 321 + "\n---\nbody")
```

`tests/integration/content/test_apply_copy_cli.py`:

```python
from __future__ import annotations

from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Experience, Project

DOC = """---
type: project
match: pollywog
summary: New summary.
stack: Access, CSV
year: 2012
---
## The Problem

Nightly prep took hours.
"""


def _write(tmp_path, text, name="p.md"):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_apply_updates_project_and_renders_html(app, db_session, tmp_path):
    db_session.add(Project(title="Pollywog", slug="pollywog", summary="old", state=PublicationState.PUBLISHED))
    db_session.commit()

    result = app.test_cli_runner().invoke(args=["content", "apply-copy", _write(tmp_path, DOC)])

    assert result.exit_code == 0, result.output
    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert project.summary == "New summary." and project.stack == "Access, CSV" and project.year == "2012"
    assert "<h2>The Problem</h2>" in project.rendered_html
    assert project.source_markdown.startswith("## The Problem")


def test_dry_run_changes_nothing(app, db_session, tmp_path):
    db_session.add(Project(title="Pollywog", slug="pollywog", summary="old", state=PublicationState.PUBLISHED))
    db_session.commit()

    result = app.test_cli_runner().invoke(args=["content", "apply-copy", "--dry-run", _write(tmp_path, DOC)])

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert result.exit_code == 0 and project.summary == "old" and "dry run" in result.output.lower()


def test_unknown_slug_fails_with_clear_message(app, db_session, tmp_path):
    result = app.test_cli_runner().invoke(args=["content", "apply-copy", _write(tmp_path, DOC)])

    assert result.exit_code != 0 and "no project with slug 'pollywog'" in result.output


def test_apply_is_idempotent(app, db_session, tmp_path):
    db_session.add(Project(title="Pollywog", slug="pollywog", summary="old", state=PublicationState.PUBLISHED))
    db_session.commit()
    path = _write(tmp_path, DOC)

    first = app.test_cli_runner().invoke(args=["content", "apply-copy", path])
    second = app.test_cli_runner().invoke(args=["content", "apply-copy", path])

    assert first.exit_code == 0 and second.exit_code == 0 and "unchanged" in second.output


def test_experience_doc_matches_by_organization_and_role(app, db_session, tmp_path):
    db_session.add(Experience(organization="Dudefish Printing", role="Owner Operator", start_date="2024", sort_position=1))
    db_session.commit()
    doc = "---\ntype: experience\nmatch: Dudefish Printing | Owner Operator\nsummary: Ran the business.\n---\n- Built custom software\n- Managed finances\n"

    result = app.test_cli_runner().invoke(args=["content", "apply-copy", _write(tmp_path, doc, "e.md")])

    exp = db_session.scalar(select(Experience))
    db_session.refresh(exp)
    assert result.exit_code == 0, result.output
    assert exp.summary == "Ran the business." and "<li>Built custom software</li>" in exp.rendered_html
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: Implement** `src/portfolio/content/copy.py`:

```python
"""Apply owner-reviewed Markdown copy files to projects, blog posts and experience entries."""

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
    "project": {"title", "summary", "role", "stack", "year", "result_headline", "seo_title", "seo_description"},
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
    return CopyDoc(kind=kind, match=match, fields=meta, body=body.strip("\n") + "\n" if body.strip() else "")


def _find(doc: CopyDoc):
    if doc.kind == "project":
        entity = db.session.scalar(select(Project).where(Project.slug == doc.match))
    elif doc.kind == "blog":
        entity = db.session.scalar(select(BlogPost).where(BlogPost.slug == doc.match))
    else:
        organization, _, role = (part.strip() for part in doc.match.partition("|"))
        entity = db.session.scalar(
            select(Experience).where(Experience.organization == organization, Experience.role == role)
        )
    if entity is None:
        raise CopyError(f"no {doc.kind} with slug {doc.match!r}" if doc.kind != "experience" else f"no experience entry {doc.match!r}")
    return entity


def apply_copy_doc(doc: CopyDoc, *, dry_run: bool = False) -> str:
    entity = _find(doc)
    changes: dict[str, str] = dict(doc.fields)
    if doc.body:
        changes["source_markdown"] = doc.body
        changes["rendered_html"] = (
            render_experience_markdown(doc.body) if doc.kind == "experience" else render_markdown(doc.body)
        )
    changed = [name for name, value in changes.items() if (getattr(entity, name, None) or "") != value]
    if not changed:
        return f"{doc.kind} {doc.match}: unchanged"
    if not dry_run:
        for name in changed:
            setattr(entity, name, changes[name])
        if hasattr(entity, "version"):
            entity.version = (entity.version or 0) + 1
    prefix = "would update" if dry_run else "updated"
    return f"{doc.kind} {doc.match}: {prefix} {', '.join(sorted(changed))}"
```
Note: `Experience` stores bullets in `source_markdown`/`rendered_html` (migration 0006) and `summary`; confirm the attribute names on the model with `grep -n "class Experience" -A25 src/portfolio/content/models.py` and adjust `FIELDS`/setattr if they differ.

`seed.py`: add

```python
@content_cli.command("apply-copy")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, dir_okay=False))
def apply_copy_command(dry_run: bool, paths: tuple[str, ...]) -> None:
    from pathlib import Path

    from portfolio.content.copy import COPY_DIR, CopyError, apply_copy_doc, parse_copy_file

    files = [Path(p) for p in paths] or sorted(
        p for p in COPY_DIR.glob("*.md") if p.name.lower() != "readme.md"
    )
    try:
        for file in files:
            click.echo(apply_copy_doc(parse_copy_file(file.read_text()), dry_run=dry_run))
        if dry_run:
            click.echo("dry run: no changes written")
        else:
            db.session.commit()
    except CopyError as exc:
        db.session.rollback()
        raise click.ClickException(str(exc)) from exc
```
Create `src/portfolio/content/copy/README.md` documenting the file format above and the rule "every file is reviewed by the owner before it is applied; run with `--dry-run` first".

Ensure the copy directory ships in the Docker image (check `Dockerfile`/`.dockerignore` copy `src/` entirely; if `*.md` is excluded by `.dockerignore`, add `!src/portfolio/content/copy/*.md`).

- [ ] **Step 4:** `uv run pytest -q` → PASS.

- [ ] **Step 5: Commit** (`feat: apply-copy command for owner-reviewed Markdown content`).

### Task 21: Owner interviews and case-study copy (interactive, owner-approved)

This task has no code-first test; its "test" is the owner approving each file, then `apply-copy --dry-run` succeeding. Do it **after Tasks 1 to 20 are merged**, with the owner present.

**Files:** create `src/portfolio/content/copy/project-<slug>.md` for each of: `trio-lending-library-system`, `pollywog-scheduling-automation`, `payment-authorization-workflow`, `medical-mileage`; `blog-why-slapping-a-jet-engine-on-a-unicycle-isnt-a-tech-strategy.md`; `experience-*.md` for each role.

- [ ] **Step 1: Project interviews.** For each project, ask the owner these questions (use AskUserQuestion with open "Other" text, one project at a time). Write nothing that is not an answer, or a fact already on the site (Pollywog: ~4 h → ~30 min nightly prep; ~75% → ~93% placement accuracy over three years; Experience page text for TRIO, Willamette Valley, payment authorization):
  1. Who used it and what was the situation before? (the problem)
  2. What was your role, and what was the timeframe (year or range)?
  3. What tools/stack did you use?
  4. How did you approach it? Two or three decisions you are proud of.
  5. What was the measurable result, even if approximate? (time saved, errors reduced, adoption). If none, say "no number" and I will describe the qualitative outcome only.
  6. What was hard, and what did you learn?
  7. Do you have screenshots, or a short description of what each screen showed (for alt text)?
- [ ] **Step 2: Draft** one file per project in the Career Groove structure: `## The Problem`, `## What I Built`, `## How It Works` (only if answered), `## Result`, `## What I Learned`, each H2 with 1 to 3 short paragraphs in first person, plain voice. Front matter sets `summary` (≤320 chars), `role`, `stack`, `year`, `result_headline`, and a `seo_title` of the form `<Name>: <what it is> | Jeremy Guill` plus a one-sentence `seo_description`. Every sentence not taken verbatim from an owner answer or the existing site text is marked in the draft with an HTML comment `<!-- REVIEW -->` (nh3 strips comments when rendering). Also fill `role/stack/year/result_headline` for **Career Groove** (`project-career-groove.md`, body omitted so the existing text is kept; the owner supplied Role "Creator & Developer", Stack "Next.js · Node.js · SQL" on the page already) and **Dudefish Printing OS** (`project-dfp-os.md`), asking questions 2 and 5 only.
- [ ] **Step 3: Blog post.** Draft `blog-...md` front matter with a `summary` (the migration already set one; only change if the owner wants), and ask the owner: keep the tone as is, or soften "contractually obligated"/"hostage negotiation"? Do not rewrite the body unless asked; if the post calls itself "my first post", ask whether to keep it.
- [ ] **Step 4: Experience trimming.** For each role show the owner the current bullets and propose 4 to 5 outcome-first bullets using only facts already present (for example for Willamette Valley Transportation lead with the Pollywog result). Unify bullets as Markdown `- ` lists. The owner approves each before the file is saved.
- [ ] **Step 5: Owner review gate.** Present all files; the owner edits or approves each. Remove every `<!-- REVIEW -->` marker only after approval.
- [ ] **Step 6: Verify and commit.** Run `uv run flask --app portfolio content apply-copy --dry-run` against a local database seeded with the production slugs (`flask --app portfolio content seed-initial` plus `data_fixes`) and confirm no `CopyError`. Then:

```bash
git add src/portfolio/content/copy
git commit -m "content: reviewed case-study, experience and blog copy" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- src/portfolio/content/copy
```
Production application is an owner step (checklist step 7).

---

# Phase 6: Repo hygiene and final verification

### Task 22: Remove clutter (inspect, confirm, then delete)

**Files:** see list below; separate, reversible commit.

- [ ] **Step 1: Inspect, change nothing yet.**

```bash
git ls-files | grep -E '(^|/)\._|^orig_template/|^MASTER_IMPLEMENTATION_PROMPT.md|^test/|^node_modules/|^reference/' 
find . -name '._*' -not -path './node_modules/*' -not -path './.venv/*' | head
git grep -n "orig_template\|MASTER_IMPLEMENTATION_PROMPT\|casestudies/career-groove-flowchart" -- . ':!docs' | head
ls -la test orig_template reference 2>/dev/null
```
- [ ] **Step 2: Ask the owner** (AskUserQuestion, multi-select) which of the listed items to remove, showing what each is. Defaults: delete the `._*` AppleDouble files (certain junk); delete `orig_template/*.zip` and `MASTER_IMPLEMENTATION_PROMPT.md` only if nothing references them (step 1 grep is empty); keep `reference/` (already git-ignored; do not touch the owner's local files); remove the empty/duplicate `test/` directory only if it holds no tracked files that tests need; leave `node_modules/` (ignored, owner's local disk).
- [ ] **Step 3: Convert the 1 MB flowchart.** If `static/assets/img/casestudies/career-groove-flowchart.png` is referenced by Career Groove's content, upload an optimised copy through the admin media library and update the content; if nothing references it, remove it with the owner's approval. Check with `grep -rn "career-groove-flowchart" src content`.
- [ ] **Step 4: Delete approved items** with `git rm -r --cached` for tracked files and `rm` for untracked, add `._*` is already ignored (`.gitignore` line 2). Add to `.gitignore` anything newly ignored (for example `orig_template/` if kept locally).
- [ ] **Step 5: Verify** `uv run pytest -q` → no new failures (the compose-port failure is pre-existing).
- [ ] **Step 6: Commit** only the removals, one commit `chore: remove unused template zips, AppleDouble files and stray prompt`, listing the removed paths in the body.

### Task 23: README, docs, and final verification

**Files:** `README.md`, `docs/release-checklist.md`

- [ ] **Step 1:** Extend `README.md`: a short "What this is" (CMS-backed portfolio, features list), a screenshot (`docs/img/home.png`, captured with the `run` skill at 1280px), a one-paragraph architecture overview (Flask, Postgres, worker, Docker, nginx proxy), the asset pipeline (`scripts/make_brand_assets.py`, no JS build), the content workflow (`flask content set-profile`, `apply-copy`), analytics pointer to `docs/analytics.md`, and the verification command.
- [ ] **Step 2:** Add to `docs/release-checklist.md`: set `PUBLIC_ORIGIN`; run `verify-production.sh`; run Lighthouse and axe on `/`, `/work`, a case study and `/contact`.
- [ ] **Step 3: Full verification (superpowers:verification-before-completion).** Run and read the real output of:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
docker compose config >/dev/null
```
Expected: all green except the one known compose-port test. Then start the stack (`run` skill) and, for `/`, `/work`, `/work/<each slug>`, `/experience`, `/blog`, `/contact`, a 404: take screenshots at 360px and 1280px in light and dark, confirm no horizontal scroll, one `<h1>`, nav usable with JS on and off. If Node/Chrome is available run `npx lighthouse http://127.0.0.1:7777/ --only-categories=accessibility,performance,seo,best-practices --chrome-flags="--headless"` and record scores in the PR description; fix any accessibility finding below 100 or SEO below 100 that is within scope.
- [ ] **Step 4: Commit** `docs: README, release checklist` (explicit paths).

---

## Owner Checklist (things only you can do, in order)

**A. Before I start Phase 1 (quick, unblocks the biggest bug)**
1. SSH to the production server and open the deployment `.env` (the file next to `compose.yaml`).
2. Set `PUBLIC_ORIGIN=https://jeremyguill.me` (exactly, no trailing path). Save.
3. After the code from Task 1 to 4 is deployed (step C), the app will refuse to start if this value is wrong; that is intentional.

**B. Information and files I need from you (put them in a folder or paste them into the chat)**
1. A portrait photo (JPG or PNG, at least 1200 px wide). Tell me where it is on disk, e.g. `~/Pictures/jeremy.jpg`.
2. Your LinkedIn URL and GitHub URL (must start with `https://`), or tell me to skip either.
3. A one-line availability statement, e.g. "Open to full-time roles and select contract projects." (I'll show the exact wording before it goes live.)
4. Your résumé as a PDF, if you want it public. It will be named `Resume2026.pdf` in `src/portfolio/static/resume/` and **committed to the repo**; remove phone numbers or home address first if you don't want them public. If not, skip it, and the link simply won't appear.
5. Screenshots for each project (PNG/JPG), or "none".
6. Answers to the project interview questions in Task 21 (I'll ask in chat).
7. Optional: a real testimonial from a colleague/client with their permission and name/title. Without one, the homepage shows the "principle" block.

**C. Deploying each phase (repeat after each batch of commits you approve)**
1. On your dev machine: `cd /mnt/storage/docker/jeremyguill-me && git status` (confirm the branch you want to ship).
2. Push the branch and merge it (or tell me to open a PR), then on the production server `git pull`.
3. Rebuild and restart: `docker compose up --build -d` (migrations run automatically because `RUN_MIGRATIONS=1`).
4. Check logs for errors: `docker compose logs --tail=100 web`.
5. Verify: `scripts/verify-production.sh https://jeremyguill.me` (it must print `verify-production: OK`).
6. Open the site on your phone and laptop and tell me anything that looks wrong.

**D. One-time server settings**
1. Compression: in your openresty / nginx-proxy-manager proxy host for jeremyguill.me, "Advanced" tab, add `gzip on; gzip_types text/css application/javascript image/svg+xml application/xml; gzip_min_length 1024;` (brotli if your build supports it). Then `curl -sI -H 'Accept-Encoding: gzip' https://jeremyguill.me/static/assets/site.css | grep -i content-encoding` should print `content-encoding: gzip`.
2. Set the profile links after the Task 6 deploy: `docker compose exec web flask --app portfolio content set-profile --linkedin https://www.linkedin.com/in/YOU --github https://github.com/YOU --availability "Open to full-time roles and select contract projects."`

**E. Analytics setup (after Task 19 is deployed)**
1. DNS: at your DNS provider add an `A` (or `CNAME`) record `stats.jeremyguill.me` pointing to the same server as `jeremyguill.me`.
2. Generate secrets on the server: `openssl rand -hex 32` twice; put them in the production `.env` as `UMAMI_DB_PASSWORD=<first>` and `UMAMI_APP_SECRET=<second>`.
3. Create Umami's database (use the same `<first>` password): `docker compose exec db psql -U portfolio -d portfolio -c "CREATE ROLE umami LOGIN PASSWORD '<first>';" -c "CREATE DATABASE umami OWNER umami;"`
4. Start it: `docker compose up -d analytics` and check `docker compose logs --tail=50 analytics`.
5. nginx-proxy-manager: Proxy Hosts, Add: domain `stats.jeremyguill.me`, scheme `http`, forward host `analytics`, port `3000`, enable "Block Common Exploits", SSL tab: request a Let's Encrypt certificate and enable "Force SSL" and "HTTP/2".
6. Open `https://stats.jeremyguill.me`, sign in with `admin` / `umami`, and immediately change the password (Settings, Profile).
7. Settings, Websites, Add website: Name `jeremyguill.me`, Domain `jeremyguill.me`. Click Edit and copy the **Website ID**.
8. In the production `.env` add `ANALYTICS_SCRIPT_URL=https://stats.jeremyguill.me/script.js` and `ANALYTICS_WEBSITE_ID=<the id>`, then `docker compose up -d web`.
9. Visit your site in a private window, then check Umami's Realtime tab: you should see one visitor. Run `STATS_ORIGIN=https://stats.jeremyguill.me scripts/verify-production.sh https://jeremyguill.me`.
10. Optional: in Umami, Settings, Websites, Share URL to get a read-only public dashboard link.

**F. Applying the reviewed copy (after Task 21)**
1. `docker compose exec web flask --app portfolio content apply-copy --dry-run` and read the output.
2. If it looks right: `docker compose exec web flask --app portfolio content apply-copy`.
3. Reload the case-study pages and confirm they read the way you approved.

**G. Decisions I'm leaving to you**
1. The failing test `test_compose_binds_web_to_localhost_only`: `compose.yaml` publishes port `7777` on all interfaces. If your proxy reaches the app over the Docker network, change it to `"127.0.0.1:7777:7777"` and update the test; tell me if you want me to.
2. Whether to keep `reference/` and `node_modules/` on disk (they're git-ignored; I won't touch them).
