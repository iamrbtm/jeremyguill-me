# Implementation Status

## Preflight

- Branch: `feat/portfolio-cms`
- Remote: `git@github.com:iamrbtm/jeremyguill-me.git`
- Authoritative files reviewed:
  - `MASTER_IMPLEMENTATION_PROMPT.md`
  - `docs/superpowers/specs/2026-07-27-portfolio-cms-design.md`
  - `docs/superpowers/plans/2026-07-27-portfolio-cms-implementation.md`
- Required assets available:
  - `reference/mark.zip`
  - `reference/atom-1.0.0.zip`
  - `reference/jeremyguill_profile.jpg`
  - `reference/Resume2026.md`
  - `reference/Resume2026.pdf`
- Template license status: no explicit LICENSE files found in template archives; Jeremy approved proceeding on 2026-07-28. Templates are references only unless compatible license terms are later confirmed.
- Toolchain available: Python 3.14.4, uv 0.11.28, Node 22.22.1, npm 9.2.0, Docker 29.1.3.

## Task 1: Reproducible Application Foundation

- Deliverable: Flask application factory, validated settings, liveness endpoint, Python/browser dependency locks, Vite build foundation, and initial app-factory tests.
- Affected files:
  - `.env.example`
  - `.gitignore`
  - `LICENSE`
  - `README.md`
  - `package.json`
  - `package-lock.json`
  - `pyproject.toml`
  - `uv.lock`
  - `vite.config.ts`
  - `src/portfolio/__init__.py`
  - `src/portfolio/config.py`
  - `src/portfolio/extensions.py`
  - `src/portfolio/public/routes.py`
  - `src/portfolio/static_src/css/site.css`
  - `src/portfolio/static_src/ts/site.ts`
  - `src/portfolio/templates/errors/404.html`
  - `src/portfolio/templates/errors/500.html`
  - `tests/conftest.py`
  - `tests/unit/test_app_factory.py`
- Tests and verification:
  - `uv lock`: passed
  - `uv sync --locked`: passed
  - `npm ci`: passed
  - `npm audit --omit=dev`: passed, 0 vulnerabilities
  - `npm run build`: passed
  - `uv run pytest tests/unit/test_app_factory.py -v`: passed, 3 tests
  - `uv run ruff check .`: passed
- Dependency decision: added an npm override for `dompurify@3.4.12` because the planned `@toast-ui/editor@3.2.2` dependency resolved to vulnerable `dompurify@2.5.9`. This preserves the planned editor package while removing known DOMPurify advisories.
- Review result: self-review completed against Task 1 and the design specification. No secrets or private reference assets are staged intentionally.
- Commit SHA: `0d278c3`

## Task 2: PostgreSQL, Migrations, and Core Records

- Deliverable: core SQLAlchemy domain schema, publication-state enum, initial Alembic migration, database test fixtures, and schema tests.
- Affected files:
  - `migrations/env.py`
  - `migrations/versions/0001_initial_schema.py`
  - `src/portfolio/__init__.py`
  - `src/portfolio/extensions.py`
  - `src/portfolio/audit/models.py`
  - `src/portfolio/auth/models.py`
  - `src/portfolio/contact/models.py`
  - `src/portfolio/content/enums.py`
  - `src/portfolio/content/models.py`
  - `src/portfolio/integrations/models.py`
  - `src/portfolio/jobs/models.py`
  - `src/portfolio/media/models.py`
  - `tests/conftest.py`
  - `tests/integration/test_initial_migration.py`
  - `tests/unit/content/test_models.py`
- Tests and verification:
  - `uv run pytest tests/integration/test_initial_migration.py tests/unit/content/test_models.py -v`: passed, 4 tests
  - `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task2-migration.sqlite" uv run flask --app portfolio db upgrade`: passed
  - `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task2-migration.sqlite" uv run flask --app portfolio db downgrade base`: passed
  - second `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task2-migration.sqlite" uv run flask --app portfolio db upgrade`: passed
  - `uv run pytest -v`: passed, 7 tests
  - `uv run ruff check .`: passed
- Limitation: PostgreSQL server tooling (`initdb`, `pg_ctl`, `psql`) is not available in this workspace yet, so Task 2 migration upgrade/downgrade was smoke-tested against SQLite only. PostgreSQL migration verification remains required before production readiness.
- Implementation note: `Job` is stored in `src/portfolio/jobs/models.py` to preserve the domain-module boundary even though the Task 2 file list omitted that path while requiring a `Job` model.
- Review result: self-review completed against Task 2 and the design specification. No secrets or private reference assets are staged intentionally.
- Commit SHA: `91cd21c`

## Task 3: Append-Oriented Audit Service

- Deliverable: recursive metadata redaction and append-only audit event creation service.
- Affected files:
  - `src/portfolio/audit/services.py`
  - `src/portfolio/audit/types.py`
  - `tests/unit/audit/test_audit_service.py`
- Tests and verification:
  - `uv run pytest tests/unit/audit/test_audit_service.py -v`: passed, 3 tests
  - `uv run pytest -v`: passed, 10 tests
  - `uv run ruff check .`: passed
- Review result: self-review completed against Task 3 and the design specification. Secret-bearing metadata keys are recursively redacted before persistence; no update service was added.
- Commit SHA: `c261d14`

## Task 4: Passkey Bootstrap, Sign-In, and Session Security

- Deliverable: passkey policy primitives, challenge/session persistence, bootstrap/recovery console commands, sign-in routes, admin guard decorator, initial passkey browser bundle, templates, and replay/origin tests.
- Affected files:
  - `migrations/versions/0002_auth_challenges.py`
  - `src/portfolio/__init__.py`
  - `src/portfolio/auth/cli.py`
  - `src/portfolio/auth/decorators.py`
  - `src/portfolio/auth/models.py`
  - `src/portfolio/auth/routes.py`
  - `src/portfolio/auth/services.py`
  - `src/portfolio/auth/webauthn.py`
  - `src/portfolio/static_src/ts/passkeys.ts`
  - `src/portfolio/templates/admin/security.html`
  - `src/portfolio/templates/auth/bootstrap.html`
  - `src/portfolio/templates/auth/sign_in.html`
  - `tests/conftest.py`
  - `tests/integration/auth/test_passkey_routes.py`
  - `tests/security/test_webauthn_replay.py`
  - `tests/unit/auth/test_passkey_policy.py`
  - `vite.config.ts`
- Tests and verification:
  - `uv run pytest tests/unit/auth tests/integration/auth tests/security/test_webauthn_replay.py -v`: passed, 6 tests
  - `uv run pytest -v`: passed, 16 tests
  - `npm run build`: passed
  - `uv run ruff check .`: passed
  - `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task4-migration.sqlite" uv run flask --app portfolio db upgrade`: passed
  - `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task4-migration.sqlite" uv run flask --app portfolio db downgrade base`: passed
  - second `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task4-migration.sqlite" uv run flask --app portfolio db upgrade`: passed
- Limitation: route tests use deterministic credential dictionaries to verify origin, RP ID, user verification, and single-use challenge behavior. Real WebAuthn cryptographic attestation/assertion verification and browser ceremony coverage remain required before production acceptance.
- Review result: self-review completed against Task 4. No username, password, TOTP, SMS, email recovery, or registration route was added.
- Commit SHA: `8e67abc`

## Checkpoint After Task 4

- Completed tasks and commits:
  - Task 1: `0d278c3`
  - Task 2: `91cd21c`
  - Task 3: `c261d14`
  - Task 4: `8e67abc`
- Verification commands run:
  - `uv sync --locked`
  - `npm ci`
  - `npm audit --omit=dev`
  - `npm run build`
  - `uv run pytest -v`
  - `uv run ruff check .`
  - SQLite migration upgrade/downgrade smoke checks through current head
- Security controls added or verified:
  - Production rejects weak/missing `SECRET_KEY`
  - npm production audit is clean after DOMPurify override
  - audit metadata redaction is recursive
  - passkey challenge replay is rejected
  - wrong WebAuthn origin is rejected
  - no alternate password/recovery route exists
- Deviations and limitations:
  - PostgreSQL migration verification remains blocked by missing local PostgreSQL tooling.
  - Real WebAuthn cryptographic verification remains to be completed before production acceptance.
  - Screenshots are not available yet because public/admin interfaces are skeletal.
- Next task: Task 5 content services, sanitization, revisions, and publishing.

## Task 5: Content Services, Sanitization, Revisions, and Publishing

- Deliverable: safe Markdown rendering, content command schema, revision creation and rollback, draft saving, immediate/scheduled publishing, idempotent publish job enqueue, and slug redirect creation.
- Affected files:
  - `src/portfolio/content/rendering.py`
  - `src/portfolio/content/revisions.py`
  - `src/portfolio/content/schemas.py`
  - `src/portfolio/content/services.py`
  - `src/portfolio/jobs/models.py`
  - `tests/integration/content/test_revision_rollback.py`
  - `tests/unit/content/test_publishing.py`
  - `tests/unit/content/test_rendering.py`
- Tests and verification:
  - `uv run pytest tests/unit/content tests/integration/content -v`: passed, 11 tests
  - `uv run pytest -v`: passed, 25 tests
  - `uv run ruff check .`: passed
  - `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task5-migration.sqlite" uv run flask --app portfolio db upgrade`: passed
  - `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task5-migration.sqlite" uv run flask --app portfolio db downgrade base`: passed
  - second `DATABASE_URL="sqlite+pysqlite:////tmp/opencode/task5-migration.sqlite" uv run flask --app portfolio db upgrade`: passed
- Security controls verified:
  - raw HTML is stripped before Markdown rendering
  - unsafe URL schemes including `javascript:`, `data:`, and `vbscript:` are removed
  - rendered HTML is sanitized through an explicit tag/attribute allowlist
  - external links receive `rel="noopener noreferrer"`
- Review result: self-review completed against Task 5 and the design specification. AI output and editor input will consume the same sanitizer in later tasks.
- Commit SHA: `db5fbae`

## Pre-Task 6 Dockerization Foundation

- Deliverable: buildable Docker image, local Compose services for `web`, `worker`, `db`, and `backup`, non-root runtime container, static asset build stage, entrypoint static copy, private reference asset exclusion, and initial Compose safety tests.
- Affected files:
  - `.dockerignore`
  - `Dockerfile`
  - `compose.yaml`
  - `docker/backup.Dockerfile`
  - `docker/backup.sh`
  - `docker/entrypoint.sh`
  - `src/portfolio/worker.py`
  - `tests/operations/test_compose_config.py`
- Verification:
  - `uv run pytest tests/operations/test_compose_config.py -v`: passed, 3 tests
  - `uv run pytest -v`: passed, 28 tests
  - `uv run ruff check .`: passed
  - `docker compose config`: passed
  - `docker build -t jeremyguill-portfolio:local .`: passed
- Limitation: local Compose currently uses development environment defaults so it can validate and build without production secret files. Task 15 must replace this with production secret-file handling before deployment.
- Review result: self-review completed. The database service exposes no host ports, the web service binds to `127.0.0.1:7777`, private `reference/` assets are excluded from Docker build context, and the runtime image runs as the non-root `portfolio` user.
- Commit SHA: `06cc837`

## Task 6: Mark-First Public Portfolio

- Deliverable: Mark-first public homepage, project detail, experience, contact routes/templates, public view models, responsive CSS, stable Vite asset names, and idempotent initial content seed command using factual resume-supported content.
- Affected files:
  - `compose.yaml`
  - `docker/entrypoint.sh`
  - `src/portfolio/__init__.py`
  - `src/portfolio/config.py`
  - `src/portfolio/content/seed.py`
  - `src/portfolio/public/routes.py`
  - `src/portfolio/public/view_models.py`
  - `src/portfolio/static_src/css/site.css`
  - `src/portfolio/templates/components/navigation.html`
  - `src/portfolio/templates/components/project_card.html`
  - `src/portfolio/templates/public/base.html`
  - `src/portfolio/templates/public/contact.html`
  - `src/portfolio/templates/public/experience.html`
  - `src/portfolio/templates/public/home.html`
  - `src/portfolio/templates/public/project.html`
  - `tests/integration/public/test_public_pages.py`
  - `tests/unit/public/test_view_models.py`
  - `tests/unit/test_app_factory.py`
  - `vite.config.ts`
- Tests and verification:
  - `uv run pytest tests/integration/public tests/unit/public -v`: passed, 8 tests
  - `uv run pytest -v`: passed, 38 tests
  - `uv run ruff check .`: passed
  - `npm run build`: passed
  - `docker compose config`: passed
  - `docker compose build`: passed
- Docker/local run note: local Compose now runs migrations and `flask content seed-initial` automatically for the web service so the homepage is usable after `docker compose up --build -d`.
- Review result: self-review completed against Task 6 and the design specification. Blog navigation hides unless a published blog post exists; draft projects return 404; public claims are sourced from `reference/Resume2026.md`.
- Commit SHA: `4c0cf85`
