# One-Page github.io Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Produce `one_page/index.html`, a single self-contained HTML/CSS/JS page (everything except the blog) that can be hosted on `iamrbtm.github.io`, generated from the live CMS content, with images and fonts linked back to `https://jeremyguill.me`.

**Architecture:** The Flask app gains a read-only public JSON export of published content (`/api/site-content.json`, also available as `flask content export-site`). A generator script (`scripts/build_one_page.py`) reads that JSON (URL or file), applies reviewed copy files from `src/portfolio/content/copy/`, and renders a Jinja template (`scripts/one_page/`) into one `index.html` with inline CSS and JS. Case studies open in a native `<dialog>` overlay with deep links. A new GitHub Actions workflow publishes only `one_page/` to the Pages repo.

**Tech Stack:** Python 3.14, Flask, Jinja2 (already a dependency), httpx (already a dependency), plain CSS/JS (no build, no frameworks), GitHub Actions.

**Design decisions (owner-approved 2026-10-04):** contact = button linking to `https://jeremyguill.me/contact` + LinkedIn/GitHub links (never the email address); case studies = overlay with deep links `#work/<slug>`, falling back to plain links to the main-site case study without JS; fonts = loaded from jeremyguill.me, so the main site serves font files with `Access-Control-Allow-Origin: *`; content source = generator script, rerunnable; canonical link points to `https://jeremyguill.me/`; blog excluded; no analytics tag on the one-pager.

## Global Constraints

- Run Python via `uv run` from `/mnt/storage/docker/jeremyguill-me`. Gates after each task: `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`. Baselines: ONE known pytest failure (`tests/operations/test_compose_config.py::test_compose_binds_web_to_localhost_only`, leave it); `ruff check .` has 14 pre-existing errors (add none; wrap new lines to <=100 cols); mypy clean.
- Work on branch `main` in the existing checkout (tree is clean at start). Never `git add -A`/`commit -a`; commit with explicit paths: `git add <paths> && git commit -m "<msg>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- <paths>`. Do NOT push; the controller pushes.
- Never put the owner's email address, phone number or home address in any export, page or test fixture. The export must contain only published/visible content.
- The one-pager must be CSP-agnostic (github.io) but still avoid third-party hosts: only `https://jeremyguill.me` assets. No frameworks, no CDN scripts, no analytics.
- Every image has `alt`, `width`/`height`; one `<h1>`; keyboard accessible; works at 360px with no horizontal scroll; honours `prefers-color-scheme` and `prefers-reduced-motion`.
- Do not invent facts or copy; all text comes from the export JSON or from the main site's existing homepage copy (see Task 2).

## File Structure

| File | Responsibility |
|---|---|
| `src/portfolio/public/site_export.py` (new) | `build_site_export() -> dict` shared by route and CLI |
| `src/portfolio/public/export_routes.py` (new) | `GET /api/site-content.json` |
| `src/portfolio/assets.py` | add CORS header for font files |
| `src/portfolio/content/seed.py` | add `export-site` CLI command |
| `scripts/build_one_page.py` (new) | generator CLI |
| `scripts/one_page/template.html`, `style.css`, `app.js` (new) | page template, styles, behaviour |
| `one_page/README.md` (new), `one_page/index.html` (generated; committed only after production has the export) | output |
| `.github/workflows/deploy.yml` | replaced: publish `one_page/` only |

---

### Task 1: Site-content export and font CORS

**Files:**
- Create: `src/portfolio/public/site_export.py`, `src/portfolio/public/export_routes.py`, `tests/integration/public/test_site_export.py`
- Modify: `src/portfolio/__init__.py` (register blueprint), `src/portfolio/assets.py`, `src/portfolio/content/seed.py`, `tests/integration/test_static_caching.py` (or a new test) for the CORS header

**Interfaces:**
- Produces: `build_site_export() -> dict[str, object]` with exactly this shape:

```json
{
  "generated_at": "2026-10-04T12:00:00+00:00",
  "origin": "https://jeremyguill.me",
  "profile": {"display_name": "", "headline": "", "summary": "", "location": null,
              "availability_text": null, "linkedin_url": null, "github_url": null},
  "capabilities": [{"title": "", "body": ""}],
  "projects": [{"slug": "", "title": "", "summary": "", "role": null, "stack": ["A", "B"],
                "year": null, "result_headline": null, "body_html": "<p>…</p>",
                "url": "https://jeremyguill.me/work/<slug>",
                "hero": {"url": "https://jeremyguill.me/media/public/<id>/hero_desktop.webp",
                         "alt": "", "width": 1600, "height": 900},
                "gallery": [{"url": "…hero_desktop.webp", "alt": "", "width": 1600, "height": 900}]}],
  "experience": [{"organization": "", "role": "", "start_date": null, "end_date": null,
                  "summary": "", "body_html": "", "logo": {"url": "…/profile.webp", "alt": "<org> logo",
                  "width": 100, "height": 100}}]
}
```
`hero` and `logo` are `null` when absent. Projects ordered like the site (`sort_position`, then title; published only). Experience ordered by `sort_position`, `visible` only. `capabilities` come from `portfolio.public.view_models` (the same list the homepage shows; reuse the existing source, don't duplicate the text). The profile NEVER includes email. All URLs absolute via `portfolio.seo.services.absolute_url`.
- Route: `GET /api/site-content.json` → 200 JSON (`application/json`), `Cache-Control: public, max-age=300`. No auth (it is the same public content). CLI: `flask --app portfolio content export-site [--output PATH]` prints/writes the same JSON (indent 2).
- CORS: static font files (`/static/assets/fonts/*.woff2`) respond with `Access-Control-Allow-Origin: *`. Do NOT add CORS to anything else (pages, JSON, admin, media).

- [ ] **Step 1: Write failing tests** (`tests/integration/public/test_site_export.py`): (a) empty site → 200, keys present, `projects == []`, `experience == []`, profile has default name and no `email` key; (b) a published project with hero MediaAsset (alt set), stack "Flask, SQL", role/year/result → exact fields, `stack == ["Flask","SQL"]`, hero URL `/media/public/<id>/hero_desktop.webp` absolute under `app.config["PUBLIC_ORIGIN"]` (set to `https://example.test` in the test), `body_html` equals the stored `rendered_html`; (c) draft projects and hidden experience are excluded; (d) profile with `email="secret@example.test"` → the string `secret@example.test` and `"email"` are absent from the response text; (e) project without hero → `hero is None`; hero asset with blank alt → alt falls back to `"<title> project preview"`; (f) experience with logo → `logo.url` ends `/profile.webp` and alt `"<org> logo"`; (g) CORS: `GET /static/assets/fonts/open-sans-var.woff2` has `Access-Control-Allow-Origin: *`, while `GET /` and `GET /api/site-content.json` and a hashed CSS file do not; (h) CLI `export-site` output parses as JSON and equals the route's JSON apart from `generated_at`.
- [ ] **Step 2: Run, verify RED.**
- [ ] **Step 3: Implement** `site_export.py`, `export_routes.py` (blueprint registered in `create_app`), the CORS rule inside `apply_cache_headers`'s module (a small separate after-request function in `assets.py`: if `request.endpoint == "static"` and the requested path starts with `assets/fonts/` add the header), and the CLI command in `seed.py`.
- [ ] **Step 4: Verify GREEN + gates; commit** (`feat: public site-content JSON export and font CORS header`).

---

### Task 2: One-page generator, template, styles and behaviour

**Files:**
- Create: `scripts/build_one_page.py`, `scripts/one_page/template.html`, `scripts/one_page/style.css`, `scripts/one_page/app.js`, `one_page/README.md`, `tests/unit/test_build_one_page.py`

**Interfaces:**
- Consumes: the Task 1 JSON shape (above); `portfolio.content.copy_apply.parse_copy_file`, `portfolio.content.rendering.render_markdown` (to apply reviewed copy files as overrides).
- Produces: CLI `uv run python scripts/build_one_page.py [--source URL_OR_FILE] [--origin https://jeremyguill.me] [--output one_page/index.html] [--no-copy-overrides]`. Default `--source` is `<origin>/api/site-content.json`. Importable function `build_page(data: dict, *, origin: str, overrides: dict[str, dict] | None = None) -> str` returning the full HTML. Exits non-zero with a clear message on fetch/parse failure (never writes a partial file).

**Page requirements** (single HTML file, CSS/JS inlined from the three template files; Jinja2 with autoescape on, `body_html` marked safe because the CMS sanitizes it with nh3):
1. `<head>`: title from profile (`"<display_name> | Software and Workflow Portfolio"`), meta description (profile summary), `<link rel="canonical" href="{origin}/">`, og tags with image `{origin}/static/assets/img/og-default.png`, favicon links to `{origin}/static/assets/img/favicon.svg` and `favicon-32.png`, `theme-color`. `@font-face` rules for Poppins 600/700 and Open Sans variable with absolute URLs `{origin}/static/assets/fonts/poppins-600.woff2`, `poppins-700.woff2`, `open-sans-var.woff2` (unhashed), `font-display: swap`, system-font fallbacks.
2. Sticky header: brand, nav links (About, Work, Experience, Contact) as in-page anchors, collapsing menu button below 62rem (aria-expanded/aria-controls, Escape closes, JS-only; without JS the nav stays visible), skip link.
3. Sections, in order: `#top` hero (h1 = profile headline, summary, availability pill if set, buttons "View my work" → `#work`, "Connect with me" → `#contact`; background `{origin}/static/assets/img/header-background.webp`, small-screen `header-background-960.webp`); `#about` (heading "Hi, I'm Jeremy.", the paragraph and the capability cards from `capabilities`, then the "How I approach technical work" copy with "Process first" and "Reliable implementation" — copy the exact text from `src/portfolio/templates/public/home.html` as it is in the repo; put a comment in the template noting the source file; portrait `<img>` from `{origin}/static/assets/img/jeremyguill_profile.webp` with srcset `-600.webp 600w, .webp 1200w`, width 1200 height 797, alt "Jeremy Guill"); `#work` ("Selected work" + intro line from home.html + a card per project: hero image if any (width/height/alt, lazy), year, title, summary, result headline, stack tags, button "Read the case study" (an `<a href="{project.url}" data-case="{slug}">` — JS opens the overlay, no-JS follows the link)); the principle block (copy from home.html, no blockquote); `#experience` (h2 "Experience and technical background", timeline entries like `public/experience.html`: dates, role as h3, organization, logo, summary, `body_html`); `#contact` (h2 + the contact CTA copy from home.html, a primary button "Send me a message" → `{origin}/contact` with `rel="noopener"`, LinkedIn/GitHub links only when set, NO email address); footer (© year, name, same links). No blog anywhere.
4. Case-study overlay: one hidden `<template id="case-{slug}">` (or hidden `<article>`) per project holding: breadcrumb-less header (h2 title in the dialog, summary, at-a-glance box: role/year/stack/result when present), hero image, `body_html`, gallery images, and a "View on jeremyguill.me" link. A single native `<dialog id="case-dialog" aria-labelledby=…>`: `showModal()` on card click (preventDefault), content cloned from the template, close button, Escape (native), backdrop click closes, focus returns to the originating card, body scroll locked while open. Deep links: opening sets `location.hash = "#work/<slug>"` via `history.pushState`; loading with that hash opens it; browser Back/popstate closes/opens accordingly; unknown slug hash is ignored; closing clears the hash with `history.replaceState` without scrolling. In-case anchors must not trigger the router. Tables get a scroll wrapper (reuse `portfolio.content.toc.enhance_case_study_html` ONLY for its table wrapping — pass the HTML through it and then strip the `id` attributes it adds to `<h2>`, to avoid duplicate ids across case studies — or implement the table wrapping directly; do not emit duplicate ids).
5. Style: reuse the main site's custom properties/look (copy the `:root` tokens from `src/portfolio/static/assets/site.css`/`theme.css` dark block, cards like `.project-card2`, `.glance`, `.tag-list`, `.principle`, `.availability-pill`, timeline like `.mini-timeline`), dark mode via `prefers-color-scheme`, print styles (hide header/dialog chrome, show everything, hero text black), reduced-motion respected, no horizontal scroll at 360px, tables scroll inside their wrapper, `scroll-margin-top` for the sticky header, `color-scheme` set. WCAG AA contrast for text.
6. Overrides: `overrides` maps slug → dict of fields (`title`, `summary`, `role`, `stack`, `year`, `result_headline`, `body_html`) built from `src/portfolio/content/copy/project-*.md` (front matter + rendered body via `render_markdown`) when `--no-copy-overrides` is absent; they replace the JSON's values for matching slugs (stack as list split on commas). A copy file whose slug isn't in the data is ignored with a warning on stderr.
7. Output is deterministic apart from the footer year and a `<!-- generated … from <source> -->` comment (include the source and the UTC date).

- [ ] **Step 1: Write failing unit tests** (`tests/unit/test_build_one_page.py`) using an in-memory fixture dict (2 projects incl. one with no hero and no stack, 1 experience with logo, capabilities, profile with linkedin only, availability set): the HTML has exactly one `<h1>`; section ids `top about work experience contact` present; `blog` absent (case-insensitive check for `/blog` and "Latest writing"); every `<img>` has alt, width, height and an absolute `https://example.test/` URL (use origin `https://example.test`); font-face URLs use the origin; canonical `https://example.test/`; no `mailto:` and no `@` email-looking text; a card + a `template`/article per project with the right `data-case` slug; GitHub link absent when unset, LinkedIn present with `rel` containing `noopener`; case body HTML preserved (a `<table>` is wrapped in a scroll div; no duplicate `id=` values anywhere in the document); a project body containing `</script>` text or `<script>` tags in the fixture is NOT executed/escaped incorrectly (the CMS body is trusted, but titles/summaries are escaped: assert a title containing `<b>x</b>` is escaped); overrides replace the title/summary/body of a matching slug and ignore unknown slugs; `build_page` is pure (no network, no file writes); the CLI exits non-zero and writes no file when `--source` is a missing file or invalid JSON; the template/JS/CSS contain no `http://` and no third-party hosts other than the origin (scan the output for `https://` URLs and assert each starts with the origin, or is `https://www.linkedin.com`/`https://github.com` from the fixture, or the schema.org-free allowlist you need — list it in the test).
- [ ] **Step 2: Run, verify RED.**
- [ ] **Step 3: Implement** the generator and the three template files per the requirements above. Keep `app.js` dependency-free ES2020, wrapped in an IIFE, feature-detecting `HTMLDialogElement` (if unsupported, cards just follow their href).
- [ ] **Step 4: Generate a local preview** to the scratchpad only (never into `one_page/`): `uv run flask --app portfolio content export-site --output <scratch>/site.json` against a scratch SQLite DB with `db.create_all()` + `seed-initial` (plus the reviewed Pollywog copy override), then `uv run python scripts/build_one_page.py --source <scratch>/site.json --origin http://127.0.0.1:5055 --output <scratch>/one_page_preview.html`. (The preview origin points at a locally running copy of the main site so images/fonts resolve while testing.) Report the preview path.
- [ ] **Step 5: Write `one_page/README.md`**: what this folder is, how to regenerate (`uv run python scripts/build_one_page.py`), the deploy flow (workflow in Task 3), that `index.html` is generated and committed only after production serves `/api/site-content.json`, and that the page links images/fonts to jeremyguill.me.
- [ ] **Step 6: Verify GREEN + gates; commit** (generator, templates, README, tests; do NOT commit any generated `index.html`).

---

### Task 3: GitHub Actions workflow that publishes only `one_page/`

**Files:**
- Modify (replace): `.github/workflows/deploy.yml`
- Create: `tests/operations/test_pages_workflow.py`

The existing workflow (push/PR to `main` → npm build → wipe `iamrbtm/iamrbtm.github.io` → copy `src/portfolio/static/*` → push to `master`) is obsolete (`package.json` was removed) and dangerous (deletes everything in the Pages repo). The owner approved replacing it.

**New behaviour:** name `Publish one-page site`. Triggers: `push` to `main` with `paths: ["one_page/index.html"]`, and `workflow_dispatch`. NO `pull_request` trigger. `permissions: contents: read`. `concurrency: group: pages-publish, cancel-in-progress: false`. Steps: checkout this repo (`actions/checkout@v4`); fail with a clear error if `one_page/index.html` is missing or does not contain `<!doctype html>` (case-insensitive) or contains `localhost`/`127.0.0.1`; checkout `iamrbtm/iamrbtm.github.io` into `pages-repo` with `token: ${{ secrets.DEPLOY_TOKEN }}` (default branch; do not hardcode `master`); copy ONLY `one_page/index.html` to `pages-repo/index.html` (do NOT delete or modify any other file in the Pages repo); if `git status --porcelain` shows no change print "No changes" and exit 0; else commit as `github-actions[bot]` with message `Publish one-page site from ${GITHUB_SHA::7}` and `git push` to the checked-out branch (no remote URL rewriting with tokens in the URL). Pin actions by major version (`@v4`).

- [ ] **Step 1: Write failing tests** (`tests/operations/test_pages_workflow.py`, parse YAML with `yaml` — check `uv run python -c "import yaml"`; if PyYAML isn't available use a tolerant text-based assertion approach and say so): triggers are only push-to-main-with-paths and workflow_dispatch; no `pull_request`; no `rm -rf`/`find ... -exec rm` anywhere; no `npm`; `DEPLOY_TOKEN` used, `GITHUB_TOKEN` not embedded in a remote URL; copies only `one_page/index.html`; guards for localhost and missing file present; `permissions` is read-only.
- [ ] **Step 2: RED, then write the workflow, GREEN.** Also run a local dry-run of the shell logic where possible (e.g. extract the guard shell snippet into the test and execute it against fixture files in tmp_path: missing file → non-zero; file with localhost → non-zero; good file → zero). Gates; commit (`ci: publish only one_page/ to the Pages repo`).

---

### Task 4: Visual and accessibility QA (headless browser) and fixes

No new files unless a defect is fixed. Use the scratchpad (never the repo) for tooling: install a headless Chromium via `PLAYWRIGHT_BROWSERS_PATH=<scratch>/pw uvx --from playwright playwright install chromium` and drive it with `uvx --with playwright python <script>` (do not add playwright to pyproject). A Chromium may already exist from an earlier session in the scratchpad (`pw` dir): reuse it.

- [ ] **Step 1:** Run a local copy of the main site (scratch SQLite DB created with `create_all` + `seed-initial` + the Pollywog copy applied + `set-profile --linkedin https://www.linkedin.com/in/example --github https://github.com/example --availability "Open to full-time roles and select contract projects."`) on `127.0.0.1:5055`, and serve the generated preview from Task 2 (built with `--origin http://127.0.0.1:5055`) via `python -m http.server` on `127.0.0.1:5056` from the scratchpad. Stop both servers at the end.
- [ ] **Step 2:** Screenshots (360x800 and 1280x900, light and dark, full page) of the one-pager; open each case-study overlay at both sizes (screenshot of the open dialog); read each PNG with the Read tool and record concrete defects. Check: fonts load cross-origin from the local main site (`document.fonts` status for Poppins/Open Sans; confirms the CORS header); images load (no broken images; `img.naturalWidth > 0` for all); no horizontal scroll (`scrollWidth <= innerWidth`) at both sizes and with the overlay open; mobile menu opens/closes with Escape and updates `aria-expanded`; overlay: opens from card click, Escape closes, backdrop click closes, focus returns to the card, `#work/<slug>` deep link opens on load, Back button closes, closing clears the hash, unknown hash ignored; JS-disabled run: nav visible, card links go to the main-site URLs, all other content visible; keyboard-only run through the nav and a card; no console errors.
- [ ] **Step 3:** axe-core (from `node_modules` in scratch via `npm i axe-core` in the scratchpad, or `npx`) on the page and with an overlay open: report serious/critical violations; also check heading order. Lighthouse if it runs (CHROME_PATH to the playwright chromium).
- [ ] **Step 4:** Fix clear, small defects in the template files (CSS/JS/HTML) — each fix its own commit with a test where practical (the unit tests from Task 2 can assert markup); report anything bigger as a finding. Do NOT commit generated output.
- [ ] **Step 5:** Write the QA report (screenshots reviewed table, axe/Lighthouse numbers, fixes vs open findings).
