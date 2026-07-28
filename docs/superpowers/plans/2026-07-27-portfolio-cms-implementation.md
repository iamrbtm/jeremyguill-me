# Jeremy Guill Portfolio CMS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a Mark-first professional portfolio and single-owner Flask CMS with PostgreSQL, passwordless passkeys, controlled AI editing, privacy-conscious contact handling, and production-grade Docker/Nginx operations.

**Architecture:** Use a modular Flask monolith with thin Blueprints and focused domain services. PostgreSQL stores content, revisions, passkeys, settings, contact submissions, jobs, and audit events; a second process from the same image handles scheduled work. Host Nginx terminates HTTPS and serves versioned public assets while Docker Compose keeps the application, worker, database, and backup service isolated.

**Tech Stack:** Python 3.14, Flask 3.1, SQLAlchemy 2, Alembic, PostgreSQL 17, Gunicorn, WebAuthn, Jinja, Toast UI Editor, Vite, vanilla TypeScript, Pillow, nh3, markdown-it-py, HTTPX, Cryptography, pytest, Playwright, Ruff, mypy, Docker Compose, and Nginx.

## Global Constraints

- Production domain and WebAuthn origin: `https://jeremyguill.me`.
- WebAuthn relying-party ID: `jeremyguill.me`.
- Exactly one internal administrator identity.
- Authentication is usernameless and passwordless; no username, password, TOTP, SMS, email recovery, registration, or static recovery codes.
- Two usable passkeys are required before normal administration is enabled.
- AI output never publishes or overwrites source content without explicit acceptance.
- PostgreSQL and the worker expose no public host ports.
- The web service binds only to `127.0.0.1`.
- Long-form source is Markdown; rendered HTML is sanitized before storage or display.
- Public claims and metrics must come from the supplied resume or Jeremy's approved content.
- Existing host Nginx terminates TLS and serves versioned static assets and public media from read-only paths.
- Application and worker containers run as non-root users.
- Each implementation task begins with a failing test and ends with a focused commit.

---

## File and Package Map

```text
.
├── .env.example
├── .gitignore
├── Dockerfile
├── docker/backup.Dockerfile
├── compose.yaml
├── docker/
│   ├── entrypoint.sh
│   ├── backup.sh
│   └── nginx/jeremyguill.me.conf
├── migrations/
├── package.json
├── pyproject.toml
├── vite.config.ts
├── src/portfolio/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── cli.py
│   ├── worker.py
│   ├── audit/
│   ├── auth/
│   ├── content/
│   ├── contact/
│   ├── integrations/
│   ├── media/
│   ├── public/
│   ├── seo/
│   ├── static_src/
│   └── templates/
├── tests/
│   ├── conftest.py
│   ├── factories/
│   ├── integration/
│   ├── security/
│   └── unit/
└── tests_e2e/
```

`src/portfolio/<domain>/models.py` owns persistence for one domain. `services.py` owns business rules. `routes.py` translates HTTP into service calls. Templates remain presentation-only. Cross-domain work uses public service functions instead of importing route functions.

---

### Task 1: Reproducible Application Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `package-lock.json`
- Create: `uv.lock`
- Create: `vite.config.ts`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/portfolio/__init__.py`
- Create: `src/portfolio/config.py`
- Create: `src/portfolio/extensions.py`
- Create: `src/portfolio/public/routes.py`
- Create: `src/portfolio/templates/errors/500.html`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_app_factory.py`

**Interfaces:**
- Produces: `create_app(config: Mapping[str, object] | None = None) -> Flask`
- Produces: `/health/live` returning `{"status": "ok"}` without querying dependencies.
- Produces: `Settings.from_env() -> Settings`

- [ ] **Step 1: Write the failing application-factory tests**

```python
def test_create_app_uses_testing_overrides():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only"})
    assert app.testing is True


def test_liveness_endpoint(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_production_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings.from_env()
```

- [ ] **Step 2: Run the tests and confirm the missing package failure**

Run: `uv run pytest tests/unit/test_app_factory.py -v`  
Expected: FAIL because `portfolio` and `create_app` do not exist.

- [ ] **Step 3: Define dependencies and quality commands**

```toml
[project]
name = "jeremyguill-portfolio"
version = "0.1.0"
requires-python = ">=3.14,<3.15"
dependencies = [
  "Flask>=3.1,<4",
  "Flask-SQLAlchemy>=3.1,<4",
  "Flask-Migrate>=4,<5",
  "SQLAlchemy>=2.0,<3",
  "alembic>=1.16,<2",
  "psycopg[binary]>=3.2,<4",
  "gunicorn>=23,<24",
  "webauthn>=2.2,<3",
  "Flask-WTF>=1.2,<2",
  "Flask-Limiter>=3.12,<4",
  "cryptography>=45,<46",
  "httpx>=0.28,<1",
  "markdown-it-py>=3,<4",
  "nh3>=0.3,<1",
  "Pillow>=11,<12",
  "filetype>=1.2,<2",
]

[dependency-groups]
dev = [
  "pytest>=8.4,<9",
  "pytest-cov>=6.2,<7",
  "pytest-postgresql>=7,<8",
  "mypy>=1.17,<2",
  "ruff>=0.12,<1",
  "playwright>=1.54,<2",
  "pip-audit>=2.9,<3",
  "respx>=0.22,<1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py314"
```

- [ ] **Step 4: Define the browser asset build**

```json
{
  "name": "jeremyguill-portfolio-assets",
  "private": true,
  "scripts": {
    "build": "vite build",
    "dev": "vite"
  },
  "dependencies": {
    "@simplewebauthn/browser": "^13.2.2",
    "@toast-ui/editor": "^3.2.2"
  },
  "devDependencies": {
    "typescript": "^5.8.3",
    "vite": "^7.0.0"
  }
}
```

Run `npm install` once to produce and commit `package-lock.json`. Run `uv lock` once to produce and commit `uv.lock`.

- [ ] **Step 5: Implement validated settings and the application factory**

```python
@dataclass(frozen=True)
class Settings:
    app_env: str
    secret_key: str
    database_url: str
    public_origin: str
    rp_id: str

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("APP_ENV", "development")
        secret = os.getenv("SECRET_KEY", "")
        if env == "production" and len(secret) < 32:
            raise RuntimeError("SECRET_KEY must contain at least 32 characters")
        return cls(
            app_env=env,
            secret_key=secret or "development-only-secret",
            database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"),
            public_origin=os.getenv("PUBLIC_ORIGIN", "http://localhost:5000"),
            rp_id=os.getenv("WEBAUTHN_RP_ID", "localhost"),
        )
```

```python
def create_app(config: Mapping[str, object] | None = None) -> Flask:
    settings = Settings.from_env()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.secret_key,
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        PUBLIC_ORIGIN=settings.public_origin,
        WEBAUTHN_RP_ID=settings.rp_id,
    )
    if config:
        app.config.update(config)
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(public_bp)
    register_error_handlers(app)
    return app
```

- [ ] **Step 6: Run quality checks**

Run: `uv sync --locked && npm ci && npm run build && uv run pytest tests/unit/test_app_factory.py -v && uv run ruff check .`  
Expected: all tests pass and Ruff reports no violations.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock package.json package-lock.json vite.config.ts .gitignore .env.example src tests
git commit -m "build: establish Flask application foundation"
```

---

### Task 2: PostgreSQL, Migrations, and Core Records

**Files:**
- Create: `src/portfolio/content/models.py`
- Create: `src/portfolio/media/models.py`
- Create: `src/portfolio/audit/models.py`
- Create: `src/portfolio/contact/models.py`
- Create: `src/portfolio/integrations/models.py`
- Create: `src/portfolio/auth/models.py`
- Create: `src/portfolio/content/enums.py`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_initial_schema.py`
- Create: `tests/integration/test_initial_migration.py`
- Create: `tests/unit/content/test_models.py`

**Interfaces:**
- Produces: `PublicationState = DRAFT | SCHEDULED | PUBLISHED | ARCHIVED`
- Produces: SQLAlchemy models named `SiteProfile`, `Project`, `BlogPost`, `Experience`, `Education`, `Credential`, `MediaAsset`, `ContactSubmission`, `IntegrationSecret`, `PasskeyCredential`, `ContentRevision`, `Redirect`, `Job`, and `AuditEvent`.
- Produces: `created_at`, `updated_at`, and optimistic `version` columns on editable records.

- [ ] **Step 1: Write failing schema and constraint tests**

```python
def test_project_slug_is_unique(db_session):
    db_session.add(Project(title="One", slug="same", state=PublicationState.DRAFT))
    db_session.commit()
    db_session.add(Project(title="Two", slug="same", state=PublicationState.DRAFT))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_revision_source_is_immutable(db_session, project):
    revision = ContentRevision(
        entity_type="project",
        entity_id=project.id,
        source_markdown="original",
        revision_number=1,
    )
    db_session.add(revision)
    db_session.commit()
    assert revision.source_markdown == "original"
```

- [ ] **Step 2: Run migration tests and verify failure**

Run: `uv run pytest tests/integration/test_initial_migration.py tests/unit/content/test_models.py -v`  
Expected: FAIL because the models and migration do not exist.

- [ ] **Step 3: Implement focused model modules**

```python
class Project(TimestampMixin, db.Model):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    summary: Mapped[str] = mapped_column(String(320))
    source_markdown: Mapped[str] = mapped_column(Text, default="")
    rendered_html: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[PublicationState] = mapped_column(
        Enum(PublicationState, native_enum=False), index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_position: Mapped[int] = mapped_column(Integer, default=0)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 4: Generate and inspect the initial migration**

Run: `uv run flask --app portfolio db revision --autogenerate -m "initial schema"`  
Expected: migration contains all declared tables, foreign keys, unique constraints, and indexes; edit the generated filename to `0001_initial_schema.py`.

- [ ] **Step 5: Test upgrade and downgrade against PostgreSQL**

Run: `uv run pytest tests/integration/test_initial_migration.py -v`  
Expected: upgrade to `head`, downgrade to `base`, and second upgrade all pass.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/*/models.py src/portfolio/content/enums.py migrations tests
git commit -m "feat: add portfolio domain schema"
```

---

### Task 3: Append-Oriented Audit Service

**Files:**
- Create: `src/portfolio/audit/services.py`
- Create: `src/portfolio/audit/types.py`
- Create: `tests/unit/audit/test_audit_service.py`

**Interfaces:**
- Produces: `record_event(action: str, actor: str, target_type: str, target_id: str | None, metadata: Mapping[str, JSONValue]) -> AuditEvent`
- Produces: `redact_metadata(value: Mapping[str, JSONValue]) -> dict[str, JSONValue]`
- Consumes: `AuditEvent` from Task 2.

- [ ] **Step 1: Write failing redaction and append tests**

```python
def test_record_event_redacts_secret_values(db_session):
    event = record_event(
        action="nvidia.key.validated",
        actor="admin",
        target_type="integration",
        target_id="nvidia",
        metadata={"api_key": "nvapi-secret", "model": "writer"},
    )
    assert event.metadata == {"api_key": "[REDACTED]", "model": "writer"}


def test_audit_event_has_no_update_service():
    assert not hasattr(audit_services, "update_event")
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/unit/audit/test_audit_service.py -v`  
Expected: FAIL because `record_event` is undefined.

- [ ] **Step 3: Implement recursive redaction and append**

```python
SENSITIVE_KEYS = {"api_key", "authorization", "cookie", "password", "secret", "token"}


def redact_metadata(value: Mapping[str, JSONValue]) -> dict[str, JSONValue]:
    return {
        key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else nested
        for key, raw in value.items()
        for nested in [redact_json(raw)]
    }


def record_event(*, action, actor, target_type, target_id=None, metadata=None):
    event = AuditEvent(
        action=action,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        metadata=redact_metadata(metadata or {}),
    )
    db.session.add(event)
    db.session.flush()
    return event
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/audit/test_audit_service.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/portfolio/audit tests/unit/audit
git commit -m "feat: add redacted audit event service"
```

---

### Task 4: Passkey Bootstrap, Sign-In, and Session Security

**Files:**
- Create: `src/portfolio/auth/routes.py`
- Create: `src/portfolio/auth/services.py`
- Create: `src/portfolio/auth/webauthn.py`
- Create: `src/portfolio/auth/decorators.py`
- Create: `src/portfolio/auth/cli.py`
- Create: `src/portfolio/templates/auth/sign_in.html`
- Create: `src/portfolio/templates/auth/bootstrap.html`
- Create: `src/portfolio/templates/admin/security.html`
- Create: `src/portfolio/static_src/ts/passkeys.ts`
- Create: `tests/unit/auth/test_passkey_policy.py`
- Create: `tests/integration/auth/test_passkey_routes.py`
- Create: `tests/security/test_webauthn_replay.py`

**Interfaces:**
- Produces: `begin_authentication() -> PublicKeyCredentialRequestOptions`
- Produces: `finish_authentication(response: Mapping[str, object], challenge_id: UUID) -> AdminSession`
- Produces: `begin_registration(enrollment_session_id: UUID) -> PublicKeyCredentialCreationOptions`
- Produces: `finish_registration(response: Mapping[str, object], challenge_id: UUID) -> PasskeyCredential`
- Produces CLI: `flask admin bootstrap-passkeys` and `flask admin recover-passkeys`.

- [ ] **Step 1: Write failing policy tests**

```python
def test_normal_admin_access_requires_two_active_passkeys(admin_identity):
    admin_identity.passkeys = [PasskeyCredential(active=True)]
    assert admin_identity.is_enrollment_complete is False


def test_challenge_cannot_be_consumed_twice(client, completed_assertion):
    first = client.post("/admin/auth/passkey/finish", json=completed_assertion)
    second = client.post("/admin/auth/passkey/finish", json=completed_assertion)
    assert first.status_code == 204
    assert second.status_code == 400


def test_wrong_origin_is_rejected(client, assertion_for_wrong_origin):
    response = client.post("/admin/auth/passkey/finish", json=assertion_for_wrong_origin)
    assert response.status_code == 400
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run pytest tests/unit/auth tests/integration/auth tests/security/test_webauthn_replay.py -v`  
Expected: FAIL because passkey services and routes do not exist.

- [ ] **Step 3: Implement challenge generation and verification**

```python
def begin_authentication() -> tuple[UUID, PublicKeyCredentialRequestOptions]:
    options = generate_authentication_options(
        rp_id=current_app.config["WEBAUTHN_RP_ID"],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    challenge = AuthChallenge.create(
        ceremony="authentication",
        value=bytes(options.challenge),
        expires_at=utcnow() + timedelta(minutes=5),
    )
    db.session.commit()
    return challenge.id, options


def consume_challenge(challenge_id: UUID, ceremony: str) -> AuthChallenge:
    challenge = db.session.execute(
        select(AuthChallenge).where(AuthChallenge.id == challenge_id).with_for_update()
    ).scalar_one()
    if challenge.used_at or challenge.expires_at <= utcnow() or challenge.ceremony != ceremony:
        raise InvalidChallenge
    challenge.used_at = utcnow()
    return challenge
```

- [ ] **Step 4: Implement restricted bootstrap and console recovery**

```python
@click.command("bootstrap-passkeys")
def bootstrap_passkeys() -> None:
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).digest()
    BootstrapToken.replace_active(
        digest=digest,
        purpose="initial",
        expires_at=utcnow() + timedelta(minutes=10),
    )
    db.session.commit()
    click.echo(f"{current_app.config['PUBLIC_ORIGIN']}/admin/bootstrap?token={token}")
```

The recovery command must require typing `RECOVER`, revoke every active session, disable normal admin access, record `auth.recovery.started`, and issue the same ten-minute restricted enrollment flow.

- [ ] **Step 5: Implement usernameless browser ceremonies**

```typescript
export async function signInWithPasskey(): Promise<void> {
  const begin = await fetch("/admin/auth/passkey/begin", {
    method: "POST",
    headers: {"X-CSRFToken": csrfToken()},
  }).then(assertJson);
  const credential = await startAuthentication({optionsJSON: begin.options});
  await fetch("/admin/auth/passkey/finish", {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken()},
    body: JSON.stringify({challenge_id: begin.challenge_id, credential}),
  }).then(assertOk);
  window.location.assign("/admin");
}
```

- [ ] **Step 6: Apply session policy**

Configure `Secure`, `HttpOnly`, `SameSite=Strict`, one-hour idle expiry, 24-hour absolute expiry, identifier rotation after authentication, and passkey reauthentication within five minutes for passkey removal, integration-secret changes, and server-sensitive actions.

- [ ] **Step 7: Run passkey and security tests**

Run: `uv run pytest tests/unit/auth tests/integration/auth tests/security/test_webauthn_replay.py -v`  
Expected: PASS for valid ceremonies and rejection of replay, wrong origin, wrong RP ID, expired challenge, missing user verification, and removal that would leave fewer than two credentials.

- [ ] **Step 8: Commit**

```bash
git add src/portfolio/auth src/portfolio/templates/auth src/portfolio/templates/admin/security.html src/portfolio/static_src/ts/passkeys.ts tests
git commit -m "feat: add passwordless passkey administration"
```

---

### Task 5: Content Services, Sanitization, Revisions, and Publishing

**Files:**
- Create: `src/portfolio/content/services.py`
- Create: `src/portfolio/content/rendering.py`
- Create: `src/portfolio/content/revisions.py`
- Create: `src/portfolio/content/schemas.py`
- Create: `tests/unit/content/test_rendering.py`
- Create: `tests/unit/content/test_publishing.py`
- Create: `tests/integration/content/test_revision_rollback.py`

**Interfaces:**
- Produces: `render_markdown(source: str) -> str`
- Produces: `save_draft(entity: EditableContent, command: ContentCommand) -> EditableContent`
- Produces: `publish(entity: EditableContent, when: datetime | None = None) -> EditableContent`
- Produces: `rollback(entity: EditableContent, revision_number: int) -> EditableContent`
- Produces: `change_slug(entity: SluggedContent, new_slug: str) -> Redirect | None`

- [ ] **Step 1: Write failing sanitization and publication tests**

```python
@pytest.mark.parametrize(
    "source, forbidden",
    [
        ("<script>alert(1)</script>", "<script"),
        ("[bad](javascript:alert(1))", "javascript:"),
        ('<img src=x onerror="alert(1)">', "onerror"),
    ],
)
def test_render_markdown_removes_active_content(source, forbidden):
    assert forbidden not in render_markdown(source).lower()


def test_publish_creates_revision_and_sets_timestamp(project):
    published = publish(project)
    assert published.state is PublicationState.PUBLISHED
    assert published.published_at is not None
    assert published.revisions[-1].source_markdown == project.source_markdown
```

- [ ] **Step 2: Confirm test failure**

Run: `uv run pytest tests/unit/content tests/integration/content -v`  
Expected: FAIL because rendering and publication services do not exist.

- [ ] **Step 3: Implement safe Markdown rendering**

```python
ALLOWED_TAGS = {
    "p", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em",
    "blockquote", "pre", "code", "a", "figure", "figcaption", "img",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "rel"},
    "img": {"src", "alt", "width", "height", "loading"},
}


def render_markdown(source: str) -> str:
    raw = MarkdownIt("commonmark", {"html": False}).enable("table").render(source)
    return nh3.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"https", "http", "mailto"},
        link_rel="noopener noreferrer",
    )
```

- [ ] **Step 4: Implement transactional revisions and redirects**

```python
def publish(entity: EditableContent, when: datetime | None = None):
    validate_publishable(entity)
    create_revision(entity, reason="publish")
    if when and when > utcnow():
        entity.state = PublicationState.SCHEDULED
        entity.publish_at = when
        enqueue_unique("publish", entity.entity_type, entity.id, when)
    else:
        entity.state = PublicationState.PUBLISHED
        entity.published_at = utcnow()
    record_event(action="content.published", actor="admin", target_type=entity.entity_type,
                 target_id=str(entity.id), metadata={"state": entity.state.value})
    db.session.commit()
    return entity
```

- [ ] **Step 5: Run content tests**

Run: `uv run pytest tests/unit/content tests/integration/content -v`  
Expected: PASS, including revision numbering, concurrent version conflict, rollback, scheduled state, and old-slug redirect creation.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/content tests/unit/content tests/integration/content
git commit -m "feat: add safe revisioned publishing services"
```

---

### Task 6: Mark-First Public Portfolio

**Files:**
- Create: `src/portfolio/public/routes.py`
- Create: `src/portfolio/public/view_models.py`
- Create: `src/portfolio/templates/public/base.html`
- Create: `src/portfolio/templates/public/home.html`
- Create: `src/portfolio/templates/public/project.html`
- Create: `src/portfolio/templates/public/experience.html`
- Create: `src/portfolio/templates/public/contact.html`
- Create: `src/portfolio/templates/components/navigation.html`
- Create: `src/portfolio/templates/components/project_card.html`
- Create: `src/portfolio/static_src/css/site.css`
- Create: `src/portfolio/static_src/ts/site.ts`
- Create: `src/portfolio/content/seed.py`
- Create: `tests/integration/public/test_public_pages.py`
- Create: `tests/unit/public/test_view_models.py`

**Interfaces:**
- Consumes: published content and sanitized HTML from Task 5.
- Produces: `build_home_view() -> HomeView`
- Produces: public routes `/`, `/work/<slug>`, `/experience`, `/contact`.
- Produces CLI: `flask content seed-initial`.

- [ ] **Step 1: Write failing public-page tests**

```python
def test_homepage_uses_required_headline(client, published_profile):
    response = client.get("/")
    assert response.status_code == 200
    assert b"I build practical software for real-world problems." in response.data


def test_blog_navigation_is_hidden_without_published_posts(client):
    response = client.get("/")
    assert b'href="/blog"' not in response.data


def test_draft_project_is_not_public(client, draft_project):
    assert client.get(f"/work/{draft_project.slug}").status_code == 404
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/integration/public tests/unit/public -v`  
Expected: FAIL because public templates and view models do not exist.

- [ ] **Step 3: Implement view models that expose only published records**

```python
def build_home_view() -> HomeView:
    return HomeView(
        profile=SiteProfile.get_singleton(),
        featured_projects=Project.query.published().featured().ordered().all(),
        capabilities=Capability.query.visible().ordered().all(),
        experience=Experience.query.visible().curated().ordered().all(),
        education=Education.query.visible().ordered().all(),
        show_blog=BlogPost.query.published().limit(1).count() == 1,
    )
```

- [ ] **Step 4: Build the Mark-first templates and responsive CSS**

Use semantic landmarks, one `h1`, visible focus indicators, skip navigation, responsive portrait crops, a charcoal/white/light-gray palette, accessible blue links, and `prefers-reduced-motion`. Preserve Mark's editorial spacing and project treatment without copying unused demo content.

```css
:root {
  --ink: #17191d;
  --paper: #f7f7f5;
  --muted: #d9dde2;
  --accent: #2463eb;
  --measure: 72rem;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(18rem, .9fr);
  min-height: min(50rem, 90svh);
}

@media (max-width: 48rem) {
  .hero { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
}
```

- [ ] **Step 5: Seed factual initial content**

Seed Jeremy's supplied resume data for DFPos, Pollywog, Salem Communications FileMaker work, TRIO lending library, Canvas Grade Parser, education, credentials, skills, and contact links. The seed command must be idempotent and must never overwrite admin-edited records after the initial seed marker exists.

- [ ] **Step 6: Run public tests and accessibility smoke checks**

Run: `uv run pytest tests/integration/public tests/unit/public -v && npm run build`  
Expected: public routes pass, drafts remain private, empty blog navigation is hidden, and Vite builds fingerprinted assets.

- [ ] **Step 7: Commit**

```bash
git add src/portfolio/public src/portfolio/templates src/portfolio/static_src src/portfolio/content/seed.py tests package.json vite.config.ts
git commit -m "feat: build Mark-first public portfolio"
```

---

### Task 7: Portrait Processing and Media Library

**Files:**
- Create: `src/portfolio/media/services.py`
- Create: `src/portfolio/media/validation.py`
- Create: `src/portfolio/media/variants.py`
- Create: `src/portfolio/media/routes.py`
- Create: `src/portfolio/templates/admin/media/index.html`
- Create: `src/portfolio/templates/admin/media/edit.html`
- Create: `tests/unit/media/test_validation.py`
- Create: `tests/integration/media/test_media_lifecycle.py`

**Interfaces:**
- Produces: `validate_upload(stream: BinaryIO, filename: str, declared_type: str) -> ValidatedUpload`
- Produces: `store_image(upload: ValidatedUpload, metadata: MediaMetadata) -> MediaAsset`
- Produces: `generate_variants(asset: MediaAsset) -> list[MediaVariant]`
- Produces variants: `hero_desktop`, `hero_mobile`, `profile`, `open_graph`.

- [ ] **Step 1: Write failing malicious-upload and lifecycle tests**

```python
@pytest.mark.parametrize("filename", ["shell.php", "vector.svg", "page.html"])
def test_executable_or_active_formats_are_rejected(filename, upload_bytes):
    with pytest.raises(InvalidUpload):
        validate_upload(io.BytesIO(upload_bytes), filename, "application/octet-stream")


def test_referenced_media_cannot_be_deleted(media_asset, published_project):
    published_project.hero_media = media_asset
    with pytest.raises(MediaInUse):
        delete_media(media_asset.id)
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest tests/unit/media tests/integration/media -v`  
Expected: FAIL because media services do not exist.

- [ ] **Step 3: Implement signature validation and atomic storage**

```python
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def validate_upload(stream, filename, declared_type):
    payload = stream.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise InvalidUpload("File exceeds 15 MB")
    detected = filetype.guess_mime(payload)
    if detected not in ALLOWED_IMAGE_TYPES or declared_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidUpload("Unsupported image type")
    image = Image.open(io.BytesIO(payload))
    image.verify()
    return ValidatedUpload(payload=payload, mime_type=detected, extension=ALLOWED_IMAGE_TYPES[detected])
```

Store with a random UUID filename in a temporary path, decode and re-encode pixels, write variants, `fsync`, and atomically rename only after every required variant succeeds.

- [ ] **Step 4: Create portrait variants from the approved edited source**

Keep the uploaded original private. The implementation phase will use the approved image-editing tool to create the dark neutral portrait treatment, then `generate_variants` will produce responsive crops and WebP/JPEG outputs without altering facial features.

- [ ] **Step 5: Run media tests**

Run: `uv run pytest tests/unit/media tests/integration/media -v`  
Expected: PASS for type mismatch, decompression limits, oversized files, active formats, atomic failure cleanup, focal-point crops, and reference protection.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/media src/portfolio/templates/admin/media tests/unit/media tests/integration/media
git commit -m "feat: add hardened portfolio media library"
```

---

### Task 8: Admin Dashboard and Structured Content Management

**Files:**
- Create: `src/portfolio/admin/routes.py`
- Create: `src/portfolio/admin/forms.py`
- Create: `src/portfolio/admin/view_models.py`
- Create: `src/portfolio/templates/admin/base.html`
- Create: `src/portfolio/templates/admin/dashboard.html`
- Create: `src/portfolio/templates/admin/content/list.html`
- Create: `src/portfolio/templates/admin/content/edit.html`
- Create: `src/portfolio/static_src/css/admin.css`
- Create: `src/portfolio/static_src/ts/admin.ts`
- Create: `tests/integration/admin/test_content_crud.py`
- Create: `tests/integration/admin/test_preview.py`

**Interfaces:**
- Consumes: `@passkey_required`, content services, media services, and audit service.
- Produces: `/admin`, `/admin/projects`, `/admin/blog`, `/admin/experience`, `/admin/profile`, `/admin/settings`.
- Produces: signed preview URLs that expire after 30 minutes and render unpublished records only for the active admin session.

- [ ] **Step 1: Write failing authorization and CRUD tests**

```python
def test_admin_requires_passkey_session(client):
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/sign-in")


def test_edit_creates_revision(authenticated_client, project):
    response = authenticated_client.post(
        f"/admin/projects/{project.id}",
        data={"title": "Revised", "summary": project.summary, "source_markdown": "Body"},
    )
    assert response.status_code == 302
    assert project.revisions[-1].reason == "draft-save"
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/integration/admin -v`  
Expected: FAIL because admin routes do not exist.

- [ ] **Step 3: Implement task-oriented dashboard and forms**

Use explicit form classes per content type. Do not expose arbitrary model fields. Validate version numbers to detect concurrent edits and return HTTP 409 with a comparison screen instead of silently overwriting.

```python
@admin_bp.post("/projects/<uuid:project_id>")
@passkey_required
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    form = ProjectForm()
    if not form.validate_on_submit():
        return render_template("admin/content/edit.html", form=form, entity=project), 422
    command = ProjectCommand.from_form(form)
    save_draft(project, command, expected_version=form.version.data)
    return redirect(url_for("admin.edit_project", project_id=project.id))
```

- [ ] **Step 4: Implement full-page signed previews**

Preview signatures include entity type, entity ID, revision/version, admin session ID, and expiry. The public preview route verifies all fields before rendering and adds `X-Robots-Tag: noindex, nofollow`.

- [ ] **Step 5: Run admin tests**

Run: `uv run pytest tests/integration/admin -v`  
Expected: PASS for authentication, CSRF, validation, concurrent edit conflict, archive/restore, sorting, preview expiry, and audit events.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/admin src/portfolio/templates/admin src/portfolio/static_src tests/integration/admin
git commit -m "feat: add revision-aware portfolio administration"
```

---

### Task 9: Rich-Text and Markdown Editing

**Files:**
- Create: `src/portfolio/static_src/ts/editor.ts`
- Create: `src/portfolio/templates/admin/components/editor.html`
- Create: `src/portfolio/content/editor_contract.py`
- Create: `tests/unit/content/test_editor_contract.py`
- Create: `tests_e2e/test_editor_roundtrip.py`

**Interfaces:**
- Produces browser event: `portfolio:editor-ready`.
- Produces: `getMarkdown() -> string`, `setMarkdown(source: string) -> void`, and source/WYSIWYG mode toggle.
- Consumes: safe Markdown subset from `render_markdown`.

- [ ] **Step 1: Write failing round-trip contract tests**

```python
def test_editor_contract_accepts_supported_markdown():
    source = "# Heading\n\n- one\n- two\n\n```python\nprint('safe')\n```"
    assert validate_editor_source(source).valid is True


def test_editor_contract_rejects_raw_html():
    result = validate_editor_source("<iframe src='https://evil.example'></iframe>")
    assert result.valid is False
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/unit/content/test_editor_contract.py -v`  
Expected: FAIL because the editor contract does not exist.

- [ ] **Step 3: Bundle Toast UI Editor and expose a narrow adapter**

```typescript
export class PortfolioEditor {
  constructor(private readonly editor: Editor) {}
  getMarkdown(): string { return this.editor.getMarkdown(); }
  setMarkdown(source: string): void { this.editor.setMarkdown(source, false); }
  focus(): void { this.editor.focus(); }
}
```

Configure only headings, lists, emphasis, links, quotes, code blocks, and approved images. Disable raw HTML plugins and sanitize again on the server.

- [ ] **Step 4: Add server-side source contract**

```python
def validate_editor_source(source: str) -> EditorValidation:
    if RAW_HTML_PATTERN.search(source):
        return EditorValidation(valid=False, errors=("Raw HTML is not supported.",))
    if len(source.encode("utf-8")) > 500_000:
        return EditorValidation(valid=False, errors=("Content exceeds 500 KB.",))
    return EditorValidation(valid=True, errors=())
```

- [ ] **Step 5: Run unit and browser round-trip tests**

Run: `uv run pytest tests/unit/content/test_editor_contract.py -v && npm run build && uv run pytest tests_e2e/test_editor_roundtrip.py -v`  
Expected: supported Markdown survives WYSIWYG/source toggles; unsafe HTML and oversized content are rejected.

- [ ] **Step 6: Commit**

```bash
git add package.json src/portfolio/static_src/ts/editor.ts src/portfolio/templates/admin/components/editor.html src/portfolio/content/editor_contract.py tests
git commit -m "feat: add safe visual and Markdown editor"
```

---

### Task 10: NVIDIA Integration and Controlled AI Revision

**Files:**
- Create: `src/portfolio/integrations/crypto.py`
- Create: `src/portfolio/integrations/nvidia.py`
- Create: `src/portfolio/integrations/services.py`
- Create: `src/portfolio/integrations/routes.py`
- Create: `src/portfolio/templates/admin/settings/ai.html`
- Create: `src/portfolio/templates/admin/components/ai_revision.html`
- Create: `src/portfolio/static_src/ts/ai_revision.ts`
- Create: `tests/unit/integrations/test_crypto.py`
- Create: `tests/unit/integrations/test_nvidia.py`
- Create: `tests/integration/integrations/test_ai_revision.py`

**Interfaces:**
- Produces: `encrypt_secret(plaintext: str) -> bytes`
- Produces: `decrypt_secret(ciphertext: bytes) -> str`
- Produces: `NvidiaClient.validate_key(api_key: str) -> list[NvidiaModel]`
- Produces: `NvidiaClient.revise(request: RevisionRequest) -> RevisionSuggestion`
- Produces endpoints to validate/save the key, refresh models, request a revision, and accept a selected suggestion.

- [ ] **Step 1: Write failing encryption and client tests**

```python
def test_encrypted_api_key_does_not_contain_plaintext(app):
    ciphertext = encrypt_secret("nvapi-super-secret")
    assert b"nvapi-super-secret" not in ciphertext
    assert decrypt_secret(ciphertext) == "nvapi-super-secret"


def test_revision_timeout_preserves_source(authenticated_client, project, respx_mock):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        side_effect=httpx.ReadTimeout("late")
    )
    response = authenticated_client.post("/admin/ai/revise", json={
        "entity_type": "project", "entity_id": str(project.id), "action": "clarity"
    })
    assert response.status_code == 504
    assert project.source_markdown == "original"
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/unit/integrations tests/integration/integrations -v`  
Expected: FAIL because secret and NVIDIA services do not exist.

- [ ] **Step 3: Implement fixed-endpoint model discovery and classification**

```python
class NvidiaClient:
    BASE_URL = "https://integrate.api.nvidia.com/v1"

    def validate_key(self, api_key: str) -> list[NvidiaModel]:
        response = self.http.get(
            f"{self.BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return [classify_model(item) for item in response.json()["data"]]
```

Return every discovered model. Mark models that do not support text/chat revision as disabled with an explanatory label.

- [ ] **Step 4: Implement encrypted settings and redacted errors**

Use a Fernet key supplied as `SETTINGS_ENCRYPTION_KEY`. Never return saved ciphertext or plaintext to templates. Display only validation state, final four non-secret identifier characters when available, selected model, and last validation time.

- [ ] **Step 5: Implement side-by-side revision workflow**

Actions are `grammar`, `professional`, `clarity`, `shorten`, `expand`, `format`, `voice`, `audience`, `seo`, and `custom`. Each request stores the source hash, suggestion, model, action, timestamps, and acceptance state. Acceptance fails with HTTP 409 when the current source hash differs from the submitted source hash.

- [ ] **Step 6: Run AI tests**

Run: `uv run pytest tests/unit/integrations tests/integration/integrations -v`  
Expected: PASS for invalid keys, dynamic model list, disabled non-text models, encryption, timeout, bounded retry, redaction, source-hash conflict, reject, regenerate, and explicit accept.

- [ ] **Step 7: Commit**

```bash
git add src/portfolio/integrations src/portfolio/templates/admin/settings src/portfolio/templates/admin/components/ai_revision.html src/portfolio/static_src/ts/ai_revision.ts tests
git commit -m "feat: add controlled NVIDIA editorial assistance"
```

---

### Task 11: Deterministic SEO, AI Suggestions, and Redirects

**Files:**
- Create: `src/portfolio/seo/services.py`
- Create: `src/portfolio/seo/routes.py`
- Create: `src/portfolio/seo/schemas.py`
- Create: `src/portfolio/templates/components/metadata.html`
- Create: `src/portfolio/templates/sitemap.xml`
- Create: `src/portfolio/templates/robots.txt`
- Create: `tests/unit/seo/test_metadata.py`
- Create: `tests/integration/seo/test_sitemap_and_redirects.py`

**Interfaces:**
- Produces: `build_metadata(page: SeoPage) -> PageMetadata`
- Produces: `build_json_ld(page: SeoPage) -> dict[str, object]`
- Produces: `/sitemap.xml`, `/robots.txt`, and permanent redirect resolution.
- Consumes: AI revision service only for suggestions; canonical output never depends on AI availability.

- [ ] **Step 1: Write failing canonical and redirect tests**

```python
def test_project_canonical_uses_public_origin(client, published_project):
    response = client.get(f"/work/{published_project.slug}")
    assert (
        f'<link rel="canonical" href="https://jeremyguill.me/work/{published_project.slug}">'
        in response.text
    )


def test_old_slug_redirects_permanently(client, project_redirect):
    response = client.get(f"/work/{project_redirect.old_slug}")
    assert response.status_code == 308
    assert response.headers["Location"].endswith(project_redirect.new_path)
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/unit/seo tests/integration/seo -v`  
Expected: FAIL because SEO services do not exist.

- [ ] **Step 3: Implement deterministic metadata**

```python
def build_metadata(page: SeoPage) -> PageMetadata:
    canonical = urljoin(current_app.config["PUBLIC_ORIGIN"], page.canonical_path)
    return PageMetadata(
        title=page.seo_title or page.title,
        description=page.seo_description or page.summary,
        canonical=canonical,
        robots="index,follow" if page.is_published else "noindex,nofollow",
        open_graph_image=page.social_image_url,
    )
```

- [ ] **Step 4: Add sitemap, robots, JSON-LD, and AI suggestion acceptance**

Sitemap includes only published canonical pages. JSON-LD uses `Person`, `WebSite`, `BlogPosting`, and `CreativeWork` where appropriate. AI suggestions populate a comparison form but do not replace stored SEO fields without acceptance.

- [ ] **Step 5: Run SEO tests**

Run: `uv run pytest tests/unit/seo tests/integration/seo -v`  
Expected: PASS for canonical URLs, escaping, noindex previews, sitemap exclusions, structured data validity, and redirect chains collapsed to one hop.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/seo src/portfolio/templates/components/metadata.html src/portfolio/templates/sitemap.xml src/portfolio/templates/robots.txt tests
git commit -m "feat: add deterministic and AI-assisted SEO"
```

---

### Task 12: Blog, Resume, and Contact Workflow

**Files:**
- Create: `src/portfolio/public/blog_routes.py`
- Create: `src/portfolio/contact/forms.py`
- Create: `src/portfolio/contact/routes.py`
- Create: `src/portfolio/contact/services.py`
- Create: `src/portfolio/contact/mailer.py`
- Create: `src/portfolio/templates/public/blog_index.html`
- Create: `src/portfolio/templates/public/blog_post.html`
- Create: `src/portfolio/templates/admin/contact/index.html`
- Create: `src/portfolio/templates/admin/contact/detail.html`
- Create: `src/portfolio/templates/admin/settings/email.html`
- Create: `tests/integration/public/test_blog.py`
- Create: `tests/integration/contact/test_contact_flow.py`
- Create: `tests/security/test_contact_abuse.py`

**Interfaces:**
- Produces: `/blog`, `/blog/<slug>`, `/resume`, and contact submission routes.
- Produces: `save_submission(command: ContactCommand) -> ContactSubmission`
- Produces: `send_submission_notification(submission_id: UUID) -> DeliveryResult`
- Produces states: `UNREAD`, `READ`, `REPLIED`, `ARCHIVED`, `SPAM`.

- [ ] **Step 1: Write failing persistence-before-email and abuse tests**

```python
def test_submission_survives_email_failure(client, smtp_failure):
    response = client.post("/contact", data=valid_contact_payload())
    assert response.status_code == 302
    submission = ContactSubmission.query.one()
    assert submission.delivery_status == "failed"


def test_honeypot_submission_is_discarded_without_revealing_detection(client):
    payload = valid_contact_payload() | {"company_website": "spam.example"}
    response = client.post("/contact", data=payload)
    assert response.status_code == 302
    assert ContactSubmission.query.count() == 0
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/integration/public/test_blog.py tests/integration/contact tests/security/test_contact_abuse.py -v`  
Expected: FAIL because blog and contact routes do not exist.

- [ ] **Step 3: Implement privacy-conscious contact persistence**

Validate name, reply address, subject, and bounded message length. Check honeypot and minimum form-fill time before saving. Store the submission transactionally, enqueue notification only after commit, and show the same visitor response whether spam is detected or not.

- [ ] **Step 4: Implement configurable SMTP**

Encrypt SMTP password with the integration-secret service. Support host, port, TLS mode, username, sender, recipient, and test delivery. Do not log message bodies or credentials.

```python
def send_submission_notification(submission_id: UUID) -> DeliveryResult:
    submission = db.session.get(ContactSubmission, submission_id)
    message = build_notification(submission)
    try:
        smtp_client().send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        submission.mark_delivery_failed(safe_error_code(exc))
        db.session.commit()
        return DeliveryResult.FAILED
    submission.mark_delivery_sent()
    db.session.commit()
    return DeliveryResult.SENT
```

- [ ] **Step 5: Implement published blog and managed resume**

Hide blog navigation when no published posts exist. `/resume` redirects to the current public resume asset. Private or superseded documents require an authenticated admin session.

- [ ] **Step 6: Run workflow tests**

Run: `uv run pytest tests/integration/public/test_blog.py tests/integration/contact tests/security/test_contact_abuse.py -v`  
Expected: PASS for draft privacy, empty blog, valid contact save, email failure persistence, retry, state transitions, rate limits, honeypot, timing check, and bounded fields.

- [ ] **Step 7: Commit**

```bash
git add src/portfolio/public/blog_routes.py src/portfolio/contact src/portfolio/templates/public src/portfolio/templates/admin/contact src/portfolio/templates/admin/settings/email.html tests
git commit -m "feat: add blog resume and private contact workflow"
```

---

### Task 13: Background Worker and Scheduled Publication

**Files:**
- Create: `src/portfolio/worker.py`
- Create: `src/portfolio/jobs/services.py`
- Create: `src/portfolio/jobs/handlers.py`
- Create: `tests/unit/jobs/test_job_service.py`
- Create: `tests/integration/jobs/test_worker.py`

**Interfaces:**
- Produces: `enqueue_unique(kind: str, entity_type: str, entity_id: UUID, run_at: datetime) -> Job`
- Produces: `claim_due_jobs(worker_id: str, limit: int = 20) -> list[Job]`
- Produces: `run_once(worker_id: str) -> WorkerResult`
- Handles `publish`, `email-notification`, `email-retry`, and `media-variant`.

- [ ] **Step 1: Write failing idempotency and lock tests**

```python
def test_enqueue_unique_does_not_duplicate_active_job(db_session, project):
    first = enqueue_unique("publish", "project", project.id, utcnow())
    second = enqueue_unique("publish", "project", project.id, utcnow())
    assert first.id == second.id


def test_two_workers_cannot_claim_same_job(db_session, due_job):
    claimed_a = claim_due_jobs("worker-a")
    claimed_b = claim_due_jobs("worker-b")
    assert due_job in claimed_a
    assert due_job not in claimed_b
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/unit/jobs tests/integration/jobs -v`  
Expected: FAIL because the job service does not exist.

- [ ] **Step 3: Implement PostgreSQL-backed claiming**

```python
def claim_due_jobs(worker_id: str, limit: int = 20) -> list[Job]:
    jobs = db.session.execute(
        select(Job)
        .where(Job.state == "pending", Job.run_at <= utcnow())
        .order_by(Job.run_at)
        .with_for_update(skip_locked=True)
        .limit(limit)
    ).scalars().all()
    for job in jobs:
        job.claim(worker_id=worker_id, lease_until=utcnow() + timedelta(minutes=5))
    db.session.commit()
    return jobs
```

- [ ] **Step 4: Implement bounded retries and dead state**

Use exponential retry delays of 1, 5, 15, and 60 minutes. After five failed attempts, mark the job `failed`, record a redacted audit event, and expose the failure on the admin dashboard.

- [ ] **Step 5: Run worker tests**

Run: `uv run pytest tests/unit/jobs tests/integration/jobs -v`  
Expected: PASS for unique enqueue, skip-locked claims, lease expiry, idempotent publishing, retries, dead jobs, and graceful shutdown.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/worker.py src/portfolio/jobs tests/unit/jobs tests/integration/jobs
git commit -m "feat: add reliable database-backed worker"
```

---

### Task 14: Security Headers, Request Hardening, and Regression Suite

**Files:**
- Create: `src/portfolio/security/headers.py`
- Create: `src/portfolio/security/validation.py`
- Create: `src/portfolio/security/logging.py`
- Create: `tests/security/test_headers.py`
- Create: `tests/security/test_csrf.py`
- Create: `tests/security/test_injection.py`
- Create: `tests/security/test_xss.py`
- Create: `tests/security/test_paths_and_redirects.py`
- Create: `tests/security/test_secret_redaction.py`

**Interfaces:**
- Produces: `apply_security_headers(response: Response) -> Response`
- Produces: `safe_redirect_target(value: str) -> str | None`
- Produces: structured logging filter that redacts sensitive keys and authorization material.

- [ ] **Step 1: Write failing security-header and injection tests**

```python
def test_security_headers_are_present(client):
    response = client.get("/")
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.parametrize("payload", ["' OR 1=1 --", "'; DROP TABLE projects; --"])
def test_project_lookup_treats_sql_payload_as_data(client, payload):
    response = client.get(f"/work/{quote(payload)}")
    assert response.status_code == 404
    assert db.session.execute(text("SELECT count(*) FROM projects")).scalar_one() >= 0
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/security -v`  
Expected: FAIL because required headers and validators are not complete.

- [ ] **Step 3: Apply restrictive headers**

```python
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        "img-src 'self' data:; font-src 'self'; object-src 'none'; script-src 'self'; "
        "style-src 'self'; connect-src 'self' https://integrate.api.nvidia.com"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}
```

Authentication endpoints also return `Cache-Control: no-store`. Production adds HSTS at Nginx after HTTPS verification.

- [ ] **Step 4: Complete attack-regression coverage**

Cover SQL injection, stored/reflected XSS, CSRF, malicious uploads, traversal, external redirects, oversized payloads, rate-limit boundaries, WebAuthn replay, secret redaction, unsafe AI HTML, and exception-page leakage. Tests assert behavior and confirm the database schema remains intact.

- [ ] **Step 5: Run security and dependency checks**

Run: `uv run pytest tests/security -v && uv run pip-audit && uv run ruff check . && uv run mypy src`  
Expected: all security tests pass, no known vulnerable Python dependency is reported, and static checks pass.

- [ ] **Step 6: Commit**

```bash
git add src/portfolio/security tests/security
git commit -m "security: harden requests output and secret handling"
```

---

### Task 15: Docker Compose, Backup, Nginx, and Operations

**Files:**
- Create: `Dockerfile`
- Create: `docker/backup.Dockerfile`
- Create: `compose.yaml`
- Create: `docker/entrypoint.sh`
- Create: `docker/backup.sh`
- Create: `docker/nginx/jeremyguill.me.conf`
- Create: `src/portfolio/operations/routes.py`
- Create: `src/portfolio/operations/services.py`
- Create: `tests/integration/operations/test_readiness.py`
- Create: `tests/operations/test_compose_config.py`
- Create: `docs/deployment.md`
- Create: `docs/backup-and-restore.md`

**Interfaces:**
- Produces: `/health/live` and `/health/ready`.
- Produces Compose services `web`, `worker`, `db`, and `backup`.
- Produces commands `docker compose run --rm web flask db upgrade`, `backup-now`, and `restore-backup`.

- [ ] **Step 1: Write failing readiness tests**

```python
def test_readiness_reports_database_failure(client, broken_database):
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.get_json() == {"status": "not-ready", "checks": {"database": "failed"}}


def test_readiness_does_not_expose_exception_text(client, broken_database):
    assert "password" not in client.get("/health/ready").text.lower()
```

- [ ] **Step 2: Confirm failure**

Run: `uv run pytest tests/integration/operations tests/operations -v`  
Expected: FAIL because readiness and deployment files do not exist.

- [ ] **Step 3: Build a non-root multi-stage image**

```dockerfile
FROM node:24-alpine AS assets
WORKDIR /build
COPY package*.json vite.config.ts ./
RUN npm ci
COPY src/portfolio/static_src ./src/portfolio/static_src
RUN npm run build

FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system portfolio && useradd --system --gid portfolio --home /app portfolio
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
COPY --from=assets /build/src/portfolio/static /app/bundled_static
USER portfolio
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "portfolio:create_app()"]
```

`docker/backup.Dockerfile` starts from `postgres:17`, installs `age` and `ca-certificates`, copies `backup.sh`, switches to an unprivileged backup user, and uses `/backup.sh` as its entry point.

- [ ] **Step 4: Define isolated Compose services**

```yaml
services:
  web:
    build: .
    env_file: .env
    ports: ["127.0.0.1:8000:8000"]
    depends_on:
      db: {condition: service_healthy}
    read_only: true
    tmpfs: ["/tmp"]
    volumes:
      - /srv/jeremyguill-me/shared/media:/app/var/media
      - /srv/jeremyguill-me/shared/static:/app/var/static
  worker:
    build: .
    command: ["uv", "run", "python", "-m", "portfolio.worker"]
    env_file: .env
    depends_on:
      db: {condition: service_healthy}
    read_only: true
    tmpfs: ["/tmp"]
    volumes:
      - /srv/jeremyguill-me/shared/media:/app/var/media
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: portfolio
      POSTGRES_USER: portfolio
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets: [postgres_password]
    volumes: [postgres_data:/var/lib/postgresql/data]
  backup:
    build:
      context: .
      dockerfile: docker/backup.Dockerfile
    env_file: .env
    depends_on:
      db: {condition: service_healthy}
    secrets: [postgres_password, age_recipient]
    volumes:
      - /srv/jeremyguill-me/shared/media:/source/media:ro
      - /srv/jeremyguill-me/backups:/backups
secrets:
  postgres_password:
    file: ./secrets/postgres_password
  age_recipient:
    file: ./secrets/age_recipient
```

The web entry point copies `/app/bundled_static/` into `/app/var/static/` before starting Gunicorn. Create `/srv/jeremyguill-me/shared/static`, `/srv/jeremyguill-me/shared/media`, and `/srv/jeremyguill-me/backups` with ownership matching the container UID during deployment. Add health checks, resource limits, log rotation, and a private default network. Do not publish a database port.

- [ ] **Step 5: Implement encrypted backup and documented restore**

`backup.sh` runs `pg_dump --format=custom`, archives media, encrypts with an age recipient supplied by secret file, verifies the archive, and applies daily/weekly retention. Restore requires an explicit target database and confirmation; it never overwrites an unresolved target.

- [ ] **Step 6: Write host Nginx configuration**

Proxy dynamic requests to `127.0.0.1:8000`, serve `/static/` and `/media/` from explicit read-only host paths, cap uploads at 15 MB, set forwarding headers, deny dotfiles, add HSTS only on HTTPS, and use Certbot-managed certificate paths documented for `jeremyguill.me`.

- [ ] **Step 7: Verify deployment configuration**

Run: `docker compose config && docker build -t jeremyguill-portfolio:test . && uv run pytest tests/integration/operations tests/operations -v`  
Expected: valid Compose configuration, successful non-root image build, private PostgreSQL, localhost-only web port, and passing readiness tests.

- [ ] **Step 8: Commit**

```bash
git add Dockerfile compose.yaml docker src/portfolio/operations tests docs/deployment.md docs/backup-and-restore.md
git commit -m "ops: add hardened container deployment and backups"
```

---

### Task 16: End-to-End Acceptance and Production Handoff

**Files:**
- Create: `tests_e2e/conftest.py`
- Create: `tests_e2e/test_passkey_bootstrap.py`
- Create: `tests_e2e/test_publish_workflow.py`
- Create: `tests_e2e/test_contact_workflow.py`
- Create: `tests_e2e/test_accessibility.py`
- Create: `scripts/verify-production.sh`
- Create: `README.md`
- Create: `SECURITY.md`
- Create: `docs/admin-guide.md`
- Create: `docs/release-checklist.md`

**Interfaces:**
- Produces: `scripts/verify-production.sh https://jeremyguill.me`
- Produces complete install, admin, recovery, backup, restore, and release instructions.

- [ ] **Step 1: Write critical browser journeys**

```python
def test_editor_ai_preview_and_publish(page, admin_session, nvidia_stub):
    page.goto("/admin/projects/new")
    page.get_by_label("Title").fill("A practical system")
    page.locator("[data-editor]").fill("rough notes")
    page.get_by_role("button", name="AI Revision").click()
    page.get_by_role("button", name="Improve clarity").click()
    expect(page.locator("[data-original]")).to_contain_text("rough notes")
    expect(page.locator("[data-suggestion]")).to_contain_text("clear revision")
    page.get_by_role("button", name="Accept revision").click()
    page.get_by_role("button", name="Publish").click()
    expect(page).to_have_url(re.compile(r"/admin/projects/.+"))
```

- [ ] **Step 2: Add accessibility and responsive checks**

Exercise keyboard navigation, visible focus, skip link, mobile navigation, reduced motion, label associations, heading order, alternative text, error summaries, and contrast on the homepage, project, blog, contact, sign-in, dashboard, and editor pages.

- [ ] **Step 3: Add production verification script**

```bash
#!/bin/sh
set -eu
origin="${1:?Usage: verify-production.sh https://host}"
curl --fail --silent --show-error "$origin/health/live" >/dev/null
curl --fail --silent --show-error "$origin/health/ready" >/dev/null
headers="$(curl --fail --silent --show-error --head "$origin/")"
printf '%s' "$headers" | grep -qi '^content-security-policy:'
printf '%s' "$headers" | grep -qi '^strict-transport-security:'
curl --fail --silent --show-error "$origin/sitemap.xml" | grep -q '<urlset'
```

- [ ] **Step 4: Run the complete verification suite**

Run:

```bash
uv run ruff check .
uv run mypy src
uv run pytest --cov=portfolio --cov-report=term-missing
npm ci
npm run build
docker compose config
docker build -t jeremyguill-portfolio:acceptance .
uv run pip-audit
```

Expected: every command exits zero; critical domain services meet the agreed coverage threshold of 90%; no known vulnerable Python dependency is reported.

- [ ] **Step 5: Perform clean-install and restore drills**

Start from empty volumes, apply migrations, seed initial content, enroll two test passkeys, publish a project, submit the contact form, run a backup, destroy only the named test volumes, restore the backup, and confirm that the project, passkeys, contact submission, and media references remain intact.

- [ ] **Step 6: Complete documentation**

`README.md` covers local setup and test commands. `SECURITY.md` defines supported versions and private reporting. `docs/admin-guide.md` covers content, AI, media, SEO, contacts, passkeys, and console recovery. `docs/release-checklist.md` requires backup confirmation, migration preview, image/dependency scan, security suite, HTTPS/header verification, and rollback commands.

- [ ] **Step 7: Commit**

```bash
git add tests_e2e scripts README.md SECURITY.md docs
git commit -m "test: complete portfolio production acceptance"
```

---

## Implementation Completion Gate

Before calling the project complete:

1. Run every command in Task 16 Step 4 from a clean checkout.
2. Confirm two production passkeys are enrolled before deleting the bootstrap token.
3. Confirm `docker compose ps` shows no published PostgreSQL port.
4. Confirm the host Nginx configuration passes `nginx -t`.
5. Confirm a real encrypted backup can be restored into a new named test database.
6. Confirm NVIDIA and SMTP secrets are absent from source, built images, logs, HTML, and error output.
7. Compare the production homepage, mobile view, project page, blog, contact form, and admin editor against the approved Mark-first direction.
8. Run `scripts/verify-production.sh https://jeremyguill.me`.
9. Record the deployed commit SHA and backup identifier in the release log.
