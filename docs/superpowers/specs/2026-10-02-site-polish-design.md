# jeremyguill.me Site Polish: Design Spec

Date: 2026-10-02 · Branch: `feat/portfolio-cms` · Status: approved 2026-10-02 (analytics added)

## 1. Intent

Make jeremyguill.me look and perform like a polished professional portfolio, and fix what is
actually broken. The site serves **two audiences equally**: hiring managers/recruiters and
freelance/contract clients. Source: the 64-item audit (groups A–G) done on 2026-10-02.

**Success criteria**
- No `localhost` URL appears in any public HTML, sitemap, or robots output; the app refuses to
  boot in production with a localhost `PUBLIC_ORIGIN`.
- Shared links (LinkedIn/Slack/iMessage) render a proper card; the site has a favicon set.
- Portrait, fonts, and hero images load; no layout shift; static assets are cacheable.
- Every public page works at 360px width, has one `<h1>`, passes axe with zero serious/critical
  issues, and meets WCAG AA contrast.
- All six case studies share one structure and include the owner's real outcomes.
- Full test suite, `ruff`, and `mypy` pass; `scripts/verify-production.sh` passes against prod.

**Out of scope (YAGNI):** visual-identity redesign, new CMS features beyond the fields listed, a
comment system, multi-language support.

## 2. Constraints discovered in the code

- Public content lives in the **database** (CMS), not in templates. Copy and metadata changes
  reach production through (a) Alembic **data migrations** (run on deploy via `RUN_MIGRATIONS=1`) or
  (b) the owner editing in `/admin`. `seed_initial_content()` is a no-op once a profile exists,
  so editing the seed does not change production.
- CSP is strict (`script-src 'self'`, `style-src 'self'`, `font-src 'self'`): no inline
  JS/CSS, no third-party fonts/scripts. Fonts must be self-hosted.
- Production runs behind openresty/nginx-proxy-manager, so `PUBLIC_ORIGIN` is set in the
  server's `.env` (copied from `.env.example`, which defaults to localhost). **Only the owner can
  change the production `.env` and deploy.**
- `docker/nginx/jeremyguill.me.conf` already sets long-lived caching for `/static/`, but the live
  response is `no-cache`, so that config is not in the live path. Cache busting must therefore
  work at the app level.
- The working tree has 113 staged-but-uncommitted changes from earlier work. Implementation
  commits will use explicit pathspecs so unrelated staged work is not swept in.

## 3. Approach (chosen over alternatives)

Three delivery shapes were considered: (1) one big branch, (2) ordered phases each ending in a
green test run and one commit, (3) per-item PRs. **Chosen: (2)**. It gives reviewable
checkpoints and lets the highest-impact fixes ship first without the overhead of 60 PRs.

## 4. Phases

### Phase 0, Hotfixes (ship first)
| # | Change | Notes |
|---|---|---|
| 0.1 | `PUBLIC_ORIGIN` guard in `config.py`: in production, reject empty/`localhost`/`127.*`/non-https values at startup | Test: settings unit test |
| 0.2 | `.env.example` uses `https://jeremyguill.me`-style placeholder with a comment; `compose.yaml` already defaults correctly | |
| 0.3 | `verify-production.sh`: fail on any `localhost` in `/`, `/sitemap.xml`, `/robots.txt`; check `og:image`, favicon, canonical host | |
| 0.4 | Sitemap includes `/work`, `/blog`, and published blog posts | `seo/routes.py` + template |
| 0.5 | Homepage `og:title`/JSON-LD `name` fixed: Person `name` = "Jeremy Guill"; page `og:title` uses the page title | `seo/services.py` |
| 0.6 | Slug typo `medial-mileage` → `medical-mileage` via data migration **plus** a `Redirect` row (308) from the old path | migration `0008` |
| 0.7 | Data migration: fix blog summary, give every project hero/gallery image a descriptive `alt_text` | Alt text written from page content, flagged for review |

### Phase 1, Assets and performance
- Self-host two WOFF2 fonts (heading + body) with `@font-face`, `font-display: swap`, preload
  of the body font; remove the unused Geist/Open Sans references. License: OFL fonts only.
- Portrait: replace the CSS-background with `<img>` + `alt`, `srcset` (WebP), explicit
  `width`/`height`. **Needs the owner's photo file.**
- Favicon set (SVG + 32px + apple-touch-icon 180px) and a default 1200×630 `og:image`
  (generated from a template; owner can swap). Per-project `og:image` falls back to the project
  hero.
- `og:image`, `twitter:card=summary_large_image`, `og:type`, `og:site_name`,
  `og:locale` added to `metadata.html`.
- Cache busting: `static_url()` helper appends a content hash (`?v=<sha8>`); Flask sends
  `Cache-Control: public, max-age=31536000, immutable` for hashed static URLs; media
  variants (UUID-addressed) get `max-age=31536000, immutable`.
- Convert `header-background.jpg` and the 1 MB flowchart PNG to WebP/AVIF with responsive
  sizes; add `width`/`height` to every `<img>`; hero image `fetchpriority="high"`, the rest lazy.
- Confirm compression at the proxy; if absent, document the one-line change for the owner.

### Phase 2, Layout and UX
- **Header:** accessible mobile menu (button, `aria-expanded`, JS in `site.js`, works without JS
  via a CSS fallback), `aria-current="page"`, sticky header with a Contact button, in-page
  anchors work from any page (`/#about` already; verified).
- **Footer:** email, LinkedIn, GitHub, résumé link (rendered only if configured), copyright,
  short sitemap. New `SiteProfile` fields: `linkedin_url`, `github_url`, `resume_path`,
  `availability_text` (migration `0009`, admin form fields).
- **Homepage:** merge the overlapping "What this portfolio shows / How I approach" sections;
  rebuild project rows into cards (title, one-line outcome, stack tags, year, whole card
  clickable); add an availability statement serving both audiences; hide the "Latest writing"
  block until ≥3 published posts (blog stays in nav/sitemap); replace the self-attributed
  pull-quote with a restyled "principle" block unless the owner supplies a real testimonial.
- **`/work`:** same card component with thumbnails (parity with the homepage).
- **Case-study template** (`project.html`): "At a glance" block (role, stack, year, result),
  breadcrumb, reading-time, auto-generated table of contents for long pages, previous/next project
  links, closing call to action. New `Project` fields: `role`, `stack` (list), `year`,
  `result_headline` (migration `0009`, admin form). Dudefish OS: collapsible long sections,
  tables made scrollable, ASCII diagram replaced by an SVG.
- **Contact:** success/failed states, field-level errors, `autocomplete` attributes, reply-time
  promise, LinkedIn alternative, email obfuscated from scrapers (rendered via data attributes +
  JS, with a plain form fallback), removal of the hardcoded fallback address from the template.
- **404/500:** branded, with navigation and links to Work/Contact.
- **Theming:** `prefers-color-scheme` dark mode via CSS custom properties (no toggle, to
  avoid inline script), print stylesheet, contrast fixes for `bg-gray` and `blue-link`.
- Reveal animations: content stays visible without JS and in print/find-in-page.

### Phase 3, SEO and discoverability
- Unique `<title>` + meta description per page; case-study titles become
  "Name: short descriptor | Jeremy Guill".
- JSON-LD: `Person` with `sameAs`, `jobTitle`, `knowsAbout`; `SoftwareApplication`/`CreativeWork`
  for projects; `BlogPosting` with `datePublished`/`author`; `BreadcrumbList` on case studies.
- RSS feed `/rss.xml` + `<link rel="alternate">`.
- `/.well-known/security.txt` (contact + policy link to `SECURITY.md`).
- Internal links: Experience roles ↔ related projects, blog post ↔ case studies.
- `robots.txt` correct host; `lastmod` in sitemap.

### Phase 4, Content (interview-driven)
Structure ships in Phases 2–3; wording comes from the owner. For each stub case study (TRIO,
Pollywog, Payment Authorization) and Medical Mileage, I interview the owner (problem, role,
approach, result, learning, screenshots) and write the Career Groove-style narrative **only from
the owner's answers and facts already on the site. No invented metrics.** Also: trim Experience
bullets to 4–5 outcome-first items per role and unify bullet styling, add skills/education
summary, align voice (first person, plain, light humour), and rewrite the blog post's summary and
"first post" framing. Content is delivered as a data migration or admin entries, each flagged
for owner review.

### Phase 5, Security headers
- Scope `connect-src https://api.openai.com` to `/admin*` only; public pages get
  `connect-src 'self'`.
- Add `Cross-Origin-Opener-Policy: same-origin`; add header tests.
- Contact form: keep CSRF/honeypot/timing; add visible rate-limit message.

### Phase 6, Repo hygiene (separate, reversible commit)
Inspect, then handle each: `static/assets/img/casestudies/._*` (delete), `orig_template/` (tracked
zips: confirm unused, then remove), `MASTER_IMPLEMENTATION_PROMPT.md`, `test/` (empty duplicate),
`node_modules/` (already ignored; confirm untracked), `reference/` (ignored). Document the asset
build flow and expand `README.md` (screenshot, architecture, features). Convert the 1 MB flowchart
as above. Nothing is deleted without being listed first in the commit message.

### Phase 7, Analytics (visitor counts)
Goal: see how many people visit, which pages and projects they read, and where they come from,
without cookies or a consent banner.
- **Tool:** self-hosted **Umami** (cookie-less, GDPR-friendly, simple dashboard) as a new
  `analytics` service in `compose.yaml` using its own database on the existing Postgres
  container (separate DB and user), on a private port behind the proxy at
  `stats.jeremyguill.me`. Chosen over Plausible (needs ClickHouse, heavier) and a home-grown
  Flask page-view log (no dashboard, would need building).
- **Site integration:** one `<script defer src="https://stats.jeremyguill.me/script.js"
  data-website-id="...">` rendered in `base.html` **only when** `ANALYTICS_SCRIPT_URL` and
  `ANALYTICS_WEBSITE_ID` are set (so dev/test and the admin are never tracked). The CSP is
  extended for that single origin (`script-src`, `connect-src`) via config, not hardcoded.
  Do Not Track is honoured (`data-do-not-track="true"`); admin pages never load it.
- **Events:** page views by default, plus data-attribute events for "View my work", "Connect with
  me", contact-form submit, résumé download, and outbound project links.
- **Ops:** the Umami image, DB init, secrets in `.env.example`, backup coverage (existing backup
  script extended), and a `verify-production.sh` check that the script tag is present and the
  stats host responds.
- **Tests:** script tag rendered only when configured; CSP contains the analytics origin only
  when configured; admin pages exclude it.

## 5. Components and boundaries
- `portfolio/config.py`: validation only. `portfolio/seo/*`: metadata, sitemap, feeds, JSON-LD.
- `portfolio/public/*`: routes + view models (new `ProjectCardView`, `ProjectDetailView`).
- Templates: new partials `components/{site_header,site_footer,project_card,at_a_glance,breadcrumb,toc}.html`.
- `static/assets/site.css` is split by concern if it passes ~1,200 lines (tokens, layout,
  components, themes).
- Migrations `0008` (data fixes) and `0009` (new profile/project columns), both reversible.

## 6. Error handling
Missing optional config (résumé, social links, portrait) never breaks a page: the related UI is
simply omitted. Startup fails fast only for the `PUBLIC_ORIGIN` guard. Redirects use the existing
chain resolver (loop-safe).

## 7. Testing
- TDD for every behavioural change. Unit: config guard, metadata/JSON-LD, sitemap, RSS, static
  hashing. Integration: each public route renders, canonical host, redirects, header values,
  blog-section visibility rule, contact states. Security: `tests/security/test_headers.py`
  extended. 
- Quality gates per phase: `uv run pytest`, `ruff check`, `mypy src`.
- Visual/accessibility checks: render pages locally and run axe and Lighthouse where tooling is
  available; mobile checked at 360px and 768px.
- Post-deploy: `scripts/verify-production.sh https://jeremyguill.me`.

## 8. Owner tasks (will be delivered as a step-by-step checklist with the plan)
1. Update production `.env`: `PUBLIC_ORIGIN=https://jeremyguill.me`, restart (Phase 0).
2. Provide: portrait photo, LinkedIn/GitHub URLs, résumé PDF, availability wording, optional
   testimonial, screenshots for each project.
3. Answer the per-project interview questions (Phase 4).
4. After each phase: deploy (`docker compose up --build -d`), run the verification script,
   and review the live pages.
5. Proxy: confirm gzip/brotli (one setting).
6. Analytics (Phase 7): create DNS record `stats.jeremyguill.me`, add a proxy host with SSL in
   nginx-proxy-manager pointing at the Umami container, create the Umami admin account on first
   login (change the default password), add the site there, and copy the Website ID into the
   production `.env`.
7. Review all flagged copy and alt text before it goes live.

## 9. Open items / decisions deferred
- **Dark mode toggle:** system-preference only for now.
- **Fonts:** I will propose a specific pairing (e.g. Inter + a display face, both OFL) for approval
  before downloading.
