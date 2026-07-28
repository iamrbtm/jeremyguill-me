# Jeremy Guill Portfolio and CMS Design

**Status:** Approved by Jeremy Guill on 2026-07-27
**Domain:** `https://jeremyguill.me`  
**Primary audience:** Employers and hiring teams seeking software, implementation, application support, database, and technical customer-success talent

## 1. Purpose and Success Criteria

Build a polished professional portfolio that presents Jeremy as a practical software builder who can understand real-world needs and turn them into dependable working systems. The technical work leads the story. Jeremy's ability to listen, gather requirements, communicate with people, and train users appears as a supporting strength rather than the main theme.

The finished system succeeds when:

1. An employer can understand Jeremy's value, capabilities, and strongest work within a few minutes.
2. Jeremy can change public content, projects, experience, media, resume files, navigation, and site settings without editing code.
3. Jeremy can draft and revise posts and portfolio content with AI assistance, while retaining final editorial control.
4. The public site is fast, accessible, responsive, privacy-conscious, and visually cohesive.
5. The administrative interface is protected by passwordless passkeys, has no public registration, and exposes no database or internal service directly to the internet.
6. The application can be deployed predictably on Jeremy's personal server using Docker Compose behind the server's existing Nginx installation.

## 2. Scope

### Included

- Public portfolio, project case studies, experience, education, credentials, resume, blog, and contact pages
- A private single-owner content-management interface
- Passwordless WebAuthn/passkey authentication
- Rich-text editing with an optional Markdown/source view
- NVIDIA-hosted AI assistance for editorial revision and SEO suggestions
- Media and document management
- Contact submissions saved in the admin area with email notifications
- Revision history, drafts, previews, publishing, scheduling, and rollback
- Technical SEO, structured metadata, sitemap, redirects, and social-sharing metadata
- PostgreSQL persistence, Alembic migrations, Docker Compose, Gunicorn, and host Nginx integration
- Automated tests, security controls, backups, health checks, and production documentation

### Excluded

- Public registration or multiple administrative users
- Public comments
- Ecommerce, payments, subscriptions, or analytics that profile individual visitors
- A free-form page builder or editable design system
- AI-generated content that publishes without Jeremy's explicit approval
- Fabricated testimonials, client logos, statistics, experience, or credentials

## 3. Visual and Editorial Direction

The site uses a **Mark-first hybrid**. Mark supplies the dominant visual language: editorial scale, generous spacing, charcoal and white surfaces, restrained blue accents, strong typography, and an image-led project presentation. Atom contributes content depth and useful section ideas, not its visual styling.

### Visual rules

- Large editorial hero with Jeremy's name and the headline, “I build practical software for real-world problems.”
- Jeremy's portrait appears on the right side of the hero with a dark, controlled monochrome treatment that preserves a natural and approachable expression.
- The palette is charcoal, white, light gray, and a restrained accessible blue.
- Motion is subtle and respects `prefers-reduced-motion`.
- Decorative effects never interfere with readability, keyboard use, or load performance.
- No fake percentage skill bars, maps, corporate-logo walls, vanity counters, or filler statistics.
- The administrator can change content and media, but not arbitrarily break typography, spacing, or responsive layout.

### Public information architecture

1. Hero
2. About
3. Capabilities
4. How I Work
5. Selected Work
6. Technical Experience
7. Education and Credentials
8. Blog, hidden automatically when no published posts exist
9. Contact
10. Footer

Long-form projects and blog posts receive their own canonical pages. Navigation is concise on desktop and accessible on mobile.

## 4. Content Strategy

The resume is the factual baseline. Public content is curated rather than copied wholesale, while the CMS retains complete records so Jeremy can expose or hide individual entries whenever needed.

The initial story emphasizes:

- DFPos as an end-to-end business-management platform
- Pollywog and other substantial software work supported by the resume
- Salem Communications FileMaker automation work
- The TRIO lending-library system
- Canvas Grade Parser
- Python, Flask, SQL, database design, Docker, Linux, APIs, cloud foundations, implementation, and technical communication

The “How I Work” section briefly shows that Jeremy can talk with users, identify the actual problem, translate it into requirements, build a solution, and help people use it. This is presented as part of delivering software successfully, not as a substitute for technical ability.

Only genuine testimonials, outcomes, links, and metrics may be published. Unknown values remain omitted until Jeremy supplies them.

## 5. Application Architecture

The application is a modular Flask monolith. This keeps deployment and maintenance reasonable for one owner while maintaining clear internal boundaries.

### Core platform

- Python and Flask application factory
- Focused Flask Blueprints for public pages, admin, authentication, content, media, AI, contact, and system operations
- SQLAlchemy ORM with PostgreSQL
- Alembic database migrations
- Jinja templates with server-rendered public pages
- Progressive JavaScript only where it improves editing, previews, uploads, and passkey ceremonies
- Gunicorn as the application server
- A small database-backed worker process, built from the same application image, for scheduled publishing, email retries, and deferred media work

### Module boundaries

| Module | Responsibility | Main dependencies |
|---|---|---|
| Public | Render published portfolio, project, blog, resume, and contact pages | Content, media, SEO |
| Admin | Dashboards and controlled content-management workflows | Auth, content, revisions |
| Auth | Passkey enrollment, authentication, session lifecycle, and recovery events | WebAuthn, audit |
| Content | Structured records, drafts, publication state, ordering, and slugs | Database, revisions |
| Editor | Rich text, Markdown source, sanitization, and preview | Content, AI |
| Media | Validation, storage, variants, metadata, and reference tracking | Filesystem volume, database |
| AI | NVIDIA key validation, model discovery, revision requests, and suggestions | NVIDIA API, encrypted settings |
| SEO | Deterministic metadata delivery plus AI-assisted editorial suggestions | Content, AI |
| Contact | Public form, spam controls, stored submissions, and email notification | Database, SMTP |
| Operations | Health checks, backup hooks, audit records, and maintenance commands | Database, storage |

Modules communicate through explicit service interfaces rather than importing route internals. Routes remain thin; business behavior belongs in focused services.

## 6. Data Model

The data model uses structured fields where order, filtering, relationships, or validation matter. Long-form content is stored as Markdown source and rendered to sanitized HTML.

### Main entities

- Site settings and profile
- Navigation items and homepage sections
- Capabilities and skills
- Experience entries
- Education and credentials
- Projects, technologies, outcomes, project links, and case-study sections
- Blog posts and categories
- Media assets and derived variants
- Resume documents
- Social and contact links
- Contact submissions
- SEO metadata and redirects
- Integration settings
- Passkey credentials and authentication events
- Content revisions and publication events
- Audit events

Every editable record includes timestamps and publication state where relevant. Ordered public collections use explicit sort positions. Slugs are unique, normalized, and protected by redirect creation when changed.

## 7. Admin Experience

The admin interface is intentionally task-oriented rather than a generic database console.

### Dashboard

- Drafts awaiting attention
- Scheduled and recently published content
- New contact submissions
- Missing image alternative text or SEO fields
- Integration status
- Recent security and content activity

### Editing

- Visual rich-text editor for normal writing
- Optional Markdown/source view that preserves a safe, documented subset of formatting
- Structured side panels for slug, status, dates, categories, featured state, ordering, SEO, and social-preview data
- Full-page preview using the real public templates
- Responsive preview sizes
- Save draft, schedule, publish, unpublish, duplicate, archive, and restore controls

The editor supports headings, paragraphs, lists, links, emphasis, quotes, code blocks, and approved media embeds. Unsupported or unsafe markup is removed during sanitization.

### Publishing workflow

1. Create or edit a draft.
2. Optionally request AI revision or SEO suggestions.
3. Compare the original and suggestion side by side.
4. Accept, reject, or regenerate the suggestion.
5. Preview the complete public page.
6. Publish immediately or schedule publication.
7. Create an immutable revision snapshot and audit event.

Published records can be rolled back to a prior revision. Changing a published slug creates a permanent redirect from the old URL.

## 8. AI Integration

AI is an editorial assistant, not an autonomous publisher.

### NVIDIA settings

- Admin settings page accepts an NVIDIA API key.
- The key is validated against NVIDIA's fixed API endpoint before it is saved.
- A successful validation retrieves the currently available models.
- Models appear in a searchable dropdown.
- Models unsuitable for text editing are labeled and disabled for editorial actions rather than silently hidden.
- Jeremy selects the default editorial model and may override it per request.
- The API key is encrypted at rest using an application master key supplied outside the database.
- The full key is never redisplayed, logged, included in an error, or sent to the browser after storage.

### Editorial actions

- Correct grammar and spelling
- Professional rewrite
- Improve clarity
- Shorten
- Expand
- Reformat
- Adjust voice or audience
- Generate SEO suggestions
- Apply custom instructions

The application sends only the content and context necessary for the chosen action. Results are treated as untrusted input, sanitized, and shown beside the original. AI cannot publish, delete, run commands, retrieve arbitrary URLs, alter settings, or overwrite source content automatically.

Timeouts, bounded retries, useful errors, and request correlation IDs prevent failed requests from damaging drafts. The application does not log prompts containing private contact submissions or secret values.

## 9. SEO and Discoverability

AI handles editorial SEO assistance. Deterministic application code handles the parts that must always be correct.

### AI-assisted

- Suggested page titles and descriptions
- Alternative text suggestions
- Keyword and topic suggestions
- Internal-link suggestions
- Heading and content-structure feedback
- Social-sharing copy

### Deterministic

- Canonical URLs
- XML sitemap
- `robots.txt`
- Open Graph and social metadata placement
- JSON-LD structured data
- Redirects after slug changes
- Semantic HTML
- Accessible heading order
- Stable URL generation

All AI suggestions require preview and acceptance. SEO output cannot introduce false claims or hidden keyword stuffing.

## 10. Contact and Privacy

The public site displays a general location, professional email address, GitHub, LinkedIn, and a contact form. It does not publish a street address or telephone number.

The contact form:

- Saves each valid submission in PostgreSQL
- Sends Jeremy an email notification through configurable SMTP
- Supports unread, read, replied, archived, and spam states
- Uses server-side validation, a honeypot, rate limiting, timing checks, and bounded message sizes
- Avoids invasive third-party tracking or fingerprinting
- Does not expose SMTP errors, addresses, or internal details to the visitor

SMTP credentials are encrypted at rest. The admin settings page includes a test-email function. A failed notification does not discard the saved submission; it records the delivery failure for retry and displays it in the admin area.

## 11. Passwordless Administrator Authentication

There is exactly one internal administrator identity and no public registration, username field, password, password reset, or email-based account recovery.

### Passkey policy

- Authentication uses WebAuthn discoverable credentials for a usernameless sign-in.
- User verification is required for every authentication ceremony.
- The production relying-party ID is `jeremyguill.me`.
- The production origin is `https://jeremyguill.me`.
- At least two registered passkeys are required before normal administration is enabled.
- The recommended enrollment is one synced platform passkey and one independent hardware security key or second-device passkey.
- Passkeys can be named, viewed, added, and revoked from the admin security page.
- Adding or revoking a passkey requires recent authentication with an existing passkey.
- The last two usable passkeys cannot be removed through the web interface.
- Authentication challenges are random, single-use, short-lived, and bound to the current ceremony.

### Initial enrollment

A server-console command creates a single-use, short-lived bootstrap token. The token can be exchanged once for a restricted enrollment session and does not permit normal administration. The enrollment session expires after ten minutes. The administrator must enroll two passkeys before the bootstrap state can be completed.

### Emergency recovery

Recovery is available only from the authenticated server console. The recovery command:

1. Requires explicit confirmation.
2. Revokes all active browser sessions.
3. Records a recovery audit event.
4. Creates a ten-minute single-use enrollment token.
5. Requires two usable passkeys before restoring normal admin access.

There is no TOTP, SMS, email-link, password, or static recovery-code fallback. This avoids creating a weaker alternate entrance.

### Sessions

- Cookies are `Secure`, `HttpOnly`, and `SameSite=Strict`.
- Session identifiers rotate after authentication and sensitive security changes.
- Sessions expire after one hour of inactivity and no later than 24 hours after authentication.
- Sensitive actions require recent passkey reauthentication.
- The admin can inspect and revoke active sessions.

## 12. Security Design

No system can guarantee that it will never be compromised. The design uses layered controls to block common automated attacks, reduce exploit impact, and make suspicious activity visible.

### Application controls

- SQLAlchemy ORM and bound parameters only; unparameterized SQL string construction is prohibited.
- The application database role has only the permissions it needs.
- Jinja autoescaping remains enabled.
- Rich text, Markdown output, AI output, SVG handling, and user-supplied links are sanitized through explicit allowlists.
- CSRF protection covers every state-changing browser request.
- A restrictive Content Security Policy and standard security headers are supplied at the application and Nginx layers.
- Redirect targets, filenames, slugs, paths, MIME types, file signatures, file sizes, and form inputs are validated.
- User-controlled values are never passed to a shell.
- NVIDIA and SMTP integrations use fixed or allowlisted destinations. The application does not provide an arbitrary URL-fetching feature.
- Public and authentication endpoints have separate rate limits.
- Public error pages never expose stack traces, SQL, filesystem paths, environment variables, or secret values.

### Upload controls

- Allowlisted formats only
- File-signature and MIME verification
- Random server-generated storage names
- Maximum dimensions and sizes
- Image decoding and re-encoding to remove active content and unnecessary metadata
- No executable uploads
- Public assets served from a non-executable media location
- Reference checks prevent deleting media still used by published content
- Atomic writes prevent partial files

### Infrastructure controls

- Existing host Nginx terminates HTTPS and proxies only to a localhost-bound application port.
- PostgreSQL and backup services remain on a private Docker network with no public host ports.
- Containers run as non-root users with only required writable volumes.
- Production secrets enter through protected environment or secret files and never enter the image or repository.
- Dependencies and base images are pinned and updated through a documented maintenance process.
- Health checks distinguish application readiness, database connectivity, and worker health.
- Security-relevant authentication, settings, publication, integration, and recovery actions enter an append-oriented audit log.

### Verification baseline

The security checklist follows OWASP ASVS Level 2 where applicable. Tests include SQL-injection payloads, stored and reflected XSS attempts, CSRF failure, malicious uploads, path traversal, unsafe redirects, rate-limit behavior, WebAuthn replay and challenge-expiration cases, authorization boundaries, secret redaction, and AI-output sanitization.

## 13. Media Processing

The supplied portrait is adapted to the Mark-first visual language while preserving Jeremy's recognizable appearance. The treatment uses a dark neutral or monochrome grade, controlled contrast, responsive crops, and focal-point metadata. The original remains private and unchanged.

Generated variants include:

- Hero desktop
- Hero mobile
- Profile/about crop
- Open Graph image crop where suitable
- Modern web formats with an appropriate fallback

Every public media record supports alternative text, caption, credit, focal point, visibility, and replacement without breaking references.

## 14. Deployment and Operations

### Docker Compose services

| Service | Purpose | Exposure |
|---|---|---|
| Web | Flask application served by Gunicorn | Bound to localhost only |
| Worker | Scheduled publishing, email retries, and deferred media work | Private Docker network only |
| Database | PostgreSQL | Private Docker network only |
| Backup | Scheduled encrypted database and media backups | No public port |

The existing host Nginx configuration owns TLS certificates, redirects HTTP to HTTPS, applies proxy and upload limits, and forwards dynamic requests to the localhost application port. Nginx serves versioned static assets and public media from explicit read-only host paths. Private originals and non-public documents are delivered only through authorized application routes.

### Configuration

Separate development, test, and production settings validate required values at startup. Production refuses to start with development defaults, a missing encryption key, an unsafe origin, or a weak Flask secret.

### Backups

- Automated PostgreSQL and media backups
- Encryption before off-server transfer
- Configurable daily and weekly retention
- Integrity checks
- Documented restoration command and periodic restore test
- Backup failure visible in health status and logs

### Observability

- Structured logs with secret and personal-data redaction
- Request correlation IDs
- Health and readiness endpoints restricted to appropriate consumers
- Log rotation
- Clear notification of backup, email, migration, and integration failures

## 15. Error Handling and Data Integrity

- Database changes that must succeed together use transactions.
- Failed media processing removes temporary files and leaves the previous public asset intact.
- Failed AI requests never alter the stored source.
- Failed email delivery never discards a contact submission.
- Publishing validates required content, slug uniqueness, media references, and renderability before changing public state.
- Scheduled publishing is idempotent, so retries cannot publish duplicate records.
- Destructive admin actions require confirmation and create audit events.
- Referenced records are archived when deletion would break published content.

## 16. Testing Strategy

### Automated tests

- Unit tests for content rules, sanitization, slugging, redirects, encryption boundaries, and service behavior
- Database integration tests against PostgreSQL
- Route and form tests for public and admin flows
- WebAuthn ceremony tests, including replay, origin, RP ID, expiry, user-verification, and credential-revocation cases
- AI client contract tests using deterministic fakes
- SMTP delivery and failure-path tests
- Upload and image-processing tests
- Accessibility checks on representative pages
- Security regression tests described in Section 12
- Migration upgrade tests from an empty database

### Browser tests

Critical end-to-end coverage includes:

1. Initial passkey enrollment
2. Passkey sign-in and reauthentication
3. Draft, AI comparison, preview, and publish
4. Project and blog media upload
5. Slug change and redirect
6. Contact submission and admin notification state
7. Responsive navigation and keyboard operation

### Production verification

Before deployment, the release process runs tests, builds containers, scans dependencies and images, applies migrations in a controlled step, verifies health checks, confirms HTTPS and security headers, checks that PostgreSQL has no public port, and performs a backup/restore smoke test.

## 17. Delivery Sequence

The implementation plan will divide the work into reviewable phases:

1. Repository, quality tooling, Docker, PostgreSQL, migrations, and configuration
2. Core content model and seed content from the resume
3. Mark-first public templates and processed portrait
4. Passkey authentication and security controls
5. Admin CMS, revisions, preview, and publishing
6. Media library
7. NVIDIA AI integration and rich-text/Markdown editing
8. Blog, SEO, redirects, resume, and contact workflow
9. Backups, Nginx example configuration, hardening, testing, and deployment documentation

Each phase must pass its relevant tests before the next phase is treated as complete.

## 18. Final Acceptance

The portfolio is ready for production when:

- All approved public sections render correctly with factual content.
- Jeremy can manage every intended content type without editing source files.
- Two passkeys are enrolled and password-based entry does not exist.
- AI actions always require human acceptance before changing content.
- Contact submissions survive email failures and remain manageable in admin.
- Database, media, and integration secrets are not publicly exposed.
- Automated tests and production security checks pass.
- A fresh installation and a backup restoration both work from the documentation.
- The deployed site operates correctly behind Nginx at `https://jeremyguill.me`.
