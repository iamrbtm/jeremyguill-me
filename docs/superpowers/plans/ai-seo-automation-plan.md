# Plan: AI SEO Automation

**Generated**: 2026-07-29
**Estimated Complexity**: High

## Overview
Build an admin-managed, NVIDIA-only, fully autonomous AI SEO system for the portfolio. The feature should let Jeremy save and validate an NVIDIA API key, choose a supported text model from a dropdown, and enable an aggressive background SEO agent that generates target searches, evaluates performance signals, updates SEO metadata and page wording, logs every action, and sends a weekly summary.

The implementation should optimize aggressively while keeping factual meaning, professional tone, and auditability intact. It should not promise first-page rankings, because search placement depends on competition, backlinks, freshness, authority, indexing, and search-engine behavior outside the app. The system should instead continuously improve technical SEO, metadata quality, structured data, content relevance, internal consistency, and content freshness while learning from available performance data.

## Confirmed Decisions
- **Provider**: NVIDIA only.
- **Target searches**: AI generates target searches/keyword clusters automatically, evaluates them, keeps useful targets, and drops or modifies weak targets.
- **Autonomy**: Fully autonomous. It should apply changes it determines are correct without requiring daily approval.
- **Content scope**: AI may change visible wording as long as it preserves meaning, factual claims, and the overall tone of the website.
- **Search Console**: Jeremy does not have Google Search Console configured yet, but wants guided setup. Search Console should become a required data source for ranking/query feedback.
- **Audience**: Optimize for employers, recruiters, coworkers, collaborators, and local/general opportunity discovery.
- **Manual run**: No “run now” button required. The system should run in the background automatically.
- **Logging**: Log every SEO action, decision, target query change, AI prompt/result, page change, and rollback-relevant detail.
- **Email cadence**: Weekly email summary, not daily.
- **SEO posture**: Aggressive and productive, with guardrails against hallucinated claims, spammy keyword stuffing, tone drift, and meaning loss.

## Current Codebase Context
- AI key storage exists in `src/portfolio/integrations/models.py` via `IntegrationSecret`.
- NVIDIA validation exists in `src/portfolio/integrations/nvidia.py` and `src/portfolio/integrations/services.py`.
- AI settings page exists at `src/portfolio/templates/admin/settings/ai.html`, but it only accepts a key and does not persist selected models or SEO settings.
- SEO metadata is generated in `src/portfolio/seo/services.py` from `SeoPage` values.
- Content models currently do not store dedicated SEO title/description fields for projects/blog/profile content.
- Worker infrastructure exists in `src/portfolio/worker.py`, `src/portfolio/jobs/models.py`, `src/portfolio/jobs/services.py`, and `src/portfolio/jobs/handlers.py`.
- Admin routes are passkey-protected and can be extended for AI/SEO settings.

## Remaining Questions
1. What email address should receive the weekly SEO summary, or should it default to the profile email?
2. What is the maximum acceptable NVIDIA API usage per day or per week?
3. Should autonomous visible-text edits publish immediately, or should they remain as saved drafts until the next normal content publish action?

## Prerequisites
- Use NVIDIA as the only production AI provider.
- Confirm `PUBLIC_ORIGIN=https://jeremyguill.me` in production.
- Confirm `SETTINGS_ENCRYPTION_KEY` is configured before storing production keys.
- Configure Google Search Console for `https://jeremyguill.me` so the agent can learn from real queries, impressions, clicks, and average positions.
- Configure SMTP/email delivery for weekly SEO summaries.
- Define usage caps for daily/weekly NVIDIA API calls.

## Sprint 1: AI Settings Foundation
**Goal**: Make the AI settings page fully usable for NVIDIA-only operation: save key, validate key, show available text models, choose a model, configure usage caps, configure weekly summary recipient, and persist the selection.

**Demo/Validation**:
- Log into `/admin`.
- Open `/admin/settings/ai`.
- Enter API key.
- See validation status and selectable models.
- Save selected model.

### Task 1.1: Add Persistent AI Settings Model
- **Location**: `src/portfolio/integrations/models.py`, new Alembic migration under `migrations/versions/`
- **Description**: Add an `AiProviderSetting` or `IntegrationSetting` table for provider name, selected model ID, validated model list snapshot, validation timestamp, SEO automation enabled flag, and daily run time.
- **Dependencies**: None
- **Acceptance Criteria**:
  - Selected model persists after restart.
  - Key remains encrypted and never rendered back.
  - Migration upgrades cleanly.
- **Validation**: `uv run pytest tests/integration/test_initial_migration.py -v`

### Task 1.2: Extend NVIDIA Client Model Classification
- **Location**: `src/portfolio/integrations/nvidia.py`
- **Description**: Return model metadata suitable for dropdown display: ID, enabled state, disabled reason, provider, and model family if available.
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - Non-text models remain disabled.
  - Text/chat models are selectable.
  - API errors produce safe admin-facing messages.
- **Validation**: Add unit tests for `classify_model()` and model-list parsing.

### Task 1.3: Build AI Settings Form UI
- **Location**: `src/portfolio/templates/admin/settings/ai.html`, `src/portfolio/integrations/routes.py`, `src/portfolio/integrations/services.py`
- **Description**: Convert the current minimal key form into a normal admin form with key validation, selected model dropdown, current key hint, automation enable/disable, and “refresh models” action.
- **Dependencies**: Tasks 1.1, 1.2
- **Acceptance Criteria**:
  - User can save key and model in one flow.
  - Current key hint displays only the last four characters.
  - Invalid key does not overwrite a previously valid key.
  - Admin can configure weekly summary recipient and API usage caps.
- **Validation**: Integration test covering valid key mock, invalid key mock, model selection persistence.

### Task 1.4: Add Google Search Console Setup Guide In Admin
- **Location**: `src/portfolio/templates/admin/settings/ai.html`, new `src/portfolio/templates/admin/settings/search_console.html`, integration docs
- **Description**: Add guided setup steps for Google Search Console verification and API access. Include what property to add (`https://jeremyguill.me`), where to verify ownership, and how to connect credentials later.
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - Admin has a clear checklist for Search Console setup.
  - Feature works without Search Console but marks performance learning as limited until connected.
- **Validation**: Template rendering tests and documentation review.

## Sprint 2: SEO Data Model, Targets, And Audit Trail
**Goal**: Add first-class SEO fields, autonomous target-query tracking, and a detailed audit trail for all AI decisions.

**Demo/Validation**:
- Open a project/blog/profile record in admin.
- View current SEO title/description/canonical/indexing state.
- See generated SEO targets/keyword clusters.
- See current SEO fields and latest autonomous changes.
- Review logs explaining why changes were made.

### Task 2.1: Add SEO Fields To Content Models
- **Location**: `src/portfolio/content/models.py`, migration under `migrations/versions/`
- **Description**: Add nullable `seo_title`, `seo_description`, `seo_keywords`, `seo_updated_at`, and `seo_reviewed_at` fields to `Project` and `BlogPost`. Add equivalent profile/home SEO setting if needed.
- **Dependencies**: None
- **Acceptance Criteria**:
  - Existing pages keep current metadata until fields are filled.
  - Metadata builder uses SEO fields when present.
- **Validation**: Unit tests for metadata fallback and SEO override behavior.

### Task 2.2: Add SEO Suggestion Model
- **Location**: `src/portfolio/integrations/models.py`, migration
- **Description**: Add `SeoSuggestion` records with entity type/id, suggested SEO title, description, keywords, rationale, model, source hash, accepted/rejected timestamps, and risk flags.
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - Suggestions are auditable.
  - Suggestions cannot apply if source content changed.
- **Validation**: Tests for source-hash conflict and audit event generation.

### Task 2.3: Add SEO Target Query Model
- **Location**: `src/portfolio/seo/models.py` or `src/portfolio/integrations/models.py`, migration
- **Description**: Store AI-generated target searches and keyword clusters with status (`active`, `watching`, `retired`), audience category, page target, rationale, performance history, and last evaluation timestamp.
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - AI can create, update, and retire targets.
  - Targets are tied to specific pages where useful.
  - Every target decision is auditable.
- **Validation**: Tests for create/update/retire logic and audit events.

### Task 2.4: Build SEO Admin Visibility UI
- **Location**: `src/portfolio/templates/admin/content/edit.html`, new component `src/portfolio/templates/admin/components/seo_panel.html`, admin routes/services
- **Description**: Add a panel showing current SEO fields, active target searches, latest AI changes, performance state, and audit links. This is visibility-focused, not approval-focused.
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - Admin can manually edit SEO fields.
  - Admin can see what the autonomous agent changed and why.
  - Admin can disable automation globally or for a page if needed.
- **Validation**: Integration tests for manual edit, visibility state, page-level automation disable.

## Sprint 3: AI SEO Generation Service
**Goal**: Implement reliable prompts and validators for autonomous SEO changes.

**Demo/Validation**:
- Select a project and request AI SEO review.
- AI returns target searches, title, meta description, keywords, JSON-LD improvements, visible-copy edits, rationale, and expected impact.
- Output is schema-validated and guarded against meaning loss, tone drift, and invented facts.

### Task 3.1: Define Autonomous SEO Prompt Contract
- **Location**: `src/portfolio/integrations/nvidia.py`, new `src/portfolio/seo/ai.py`
- **Description**: Create a strict JSON response contract for SEO output: `target_queries`, `seo_title`, `seo_description`, `keywords`, `visible_copy_patch`, `json_ld_changes`, `rationale`, `expected_impact`, `risks`, and `confidence`.
- **Dependencies**: Sprint 2
- **Acceptance Criteria**:
  - Prompt instructs AI not to invent facts, credentials, metrics, employers, or locations.
  - JSON parsing failure is handled safely.
  - Output length constraints are enforced.
  - Visible copy edits include a before/after semantic-preservation explanation.
- **Validation**: Unit tests for parser, length trimming, invalid JSON, hallucination risk flags.

### Task 3.2: Add SEO Safety Validators
- **Location**: `src/portfolio/seo/services.py`, `src/portfolio/seo/validators.py`
- **Description**: Validate SEO title length, description length, forbidden unverifiable claims, duplicate metadata, keyword stuffing, page relevance, tone alignment, and meaning preservation for visible-copy edits.
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - Unsafe suggestions are rejected automatically and logged.
  - Safe metadata and copy changes can be auto-applied.
  - Aggressive optimization is allowed, but spammy keyword stuffing is rejected.
- **Validation**: Unit tests for each validator.

### Task 3.3: Connect AI Output To Autonomous Changes
- **Location**: `src/portfolio/integrations/services.py`, `src/portfolio/seo/ai.py`
- **Description**: Persist AI SEO output and apply safe changes to content SEO fields and visible wording according to the autonomous policy.
- **Dependencies**: Tasks 3.1, 3.2
- **Acceptance Criteria**:
  - Changes include model, prompt version, content hash, rationale, target query, and risk classification.
  - Applied changes update SEO fields/content and audit log.
  - Rejected changes are logged with rejection reasons.
- **Validation**: Integration tests with mocked AI client.

## Sprint 4: Daily Worker Automation
**Goal**: Add a daily SEO evaluation job that runs automatically and applies safe aggressive improvements.

**Demo/Validation**:
- Enable daily SEO automation in AI settings.
- Trigger worker run.
- See SEO scan jobs created and processed.
- See target query changes, safe auto-applied metadata/content changes, and rejected unsafe changes in logs.

### Task 4.1: Add SEO Job Kinds
- **Location**: `src/portfolio/jobs/handlers.py`, `src/portfolio/jobs/services.py`
- **Description**: Add job kinds such as `seo-daily-scan`, `seo-review-project`, `seo-review-blog`, and `seo-review-home`.
- **Dependencies**: Sprint 3
- **Acceptance Criteria**:
  - Worker recognizes SEO job kinds.
  - Job failures retry using existing retry policy.
- **Validation**: Worker unit/integration tests.

### Task 4.2: Add Daily Scheduler Logic
- **Location**: `src/portfolio/worker.py`, `src/portfolio/jobs/services.py`, possibly new `src/portfolio/seo/scheduler.py`
- **Description**: Ensure one daily SEO scan is enqueued per configured run window. Avoid duplicate jobs using existing unique job constraints or a new scheduler state record.
- **Dependencies**: Task 4.1
- **Acceptance Criteria**:
  - Exactly one daily scan enqueues per day.
  - Manual “run now” can enqueue immediately.
  - Disabled automation does not enqueue.
- **Validation**: Tests for daily window, duplicate prevention, disabled state.

### Task 4.3: Apply Autonomous Changes Based On Safety Policy
- **Location**: `src/portfolio/seo/services.py`, `src/portfolio/integrations/services.py`
- **Description**: Apply validated SEO metadata and visible-copy changes automatically. Reject or defer changes that fail meaning, factuality, tone, or spam checks.
- **Dependencies**: Task 4.2
- **Acceptance Criteria**:
  - Visible body content is auto-edited only when semantic and tone validators pass.
  - All changes are logged.
  - High-risk changes are rejected or flagged, not silently applied.
- **Validation**: Integration tests for auto-apply and review-only modes.

### Task 4.4: Add Weekly Email Summary Job
- **Location**: `src/portfolio/jobs/handlers.py`, `src/portfolio/contact/mailer.py` or new `src/portfolio/seo/email.py`
- **Description**: Generate a weekly email summarizing target queries, pages changed, performance movement, rejected changes, failures, and next actions.
- **Dependencies**: Tasks 4.1-4.3
- **Acceptance Criteria**:
  - Summary sends once per week.
  - Email does not expose API keys or sensitive prompt details.
  - Email links to admin logs.
- **Validation**: Integration test using mocked mail transport.

## Sprint 5: Search Console Learning And Reporting
**Goal**: Let the autonomous agent learn from real search performance data.

**Demo/Validation**:
- Admin dashboard shows SEO status, latest AI run, pending suggestions, and page-level issues.
- Google Search Console metrics guide target query creation, retention, retirement, and page changes.

### Task 5.1: Add SEO Status Dashboard
- **Location**: `src/portfolio/templates/admin/dashboard.html`, new SEO admin route/template
- **Description**: Show pages scanned, suggestions pending, last run time, failures, and SEO metadata coverage.
- **Dependencies**: Sprint 4
- **Acceptance Criteria**:
  - Admin can see whether automation is healthy.
  - Admin can jump to pending suggestions.
- **Validation**: Admin integration tests.

### Task 5.2: Add Technical SEO Checks
- **Location**: `src/portfolio/seo/audit.py`
- **Description**: Check canonical URLs, sitemap inclusion, robots, duplicate descriptions, missing descriptions, heading presence, image alt text, Open Graph image, and JSON-LD presence.
- **Dependencies**: Sprint 4
- **Acceptance Criteria**:
  - Daily job reports technical SEO issues.
  - Safe fixes are suggested or applied according to policy.
- **Validation**: Unit tests with representative page fixtures.

### Task 5.3: Google Search Console Integration
- **Location**: new `src/portfolio/integrations/google_search_console.py`, settings UI, encrypted secret storage
- **Description**: Ingest impressions, clicks, query terms, average position, click-through rate, and indexing issues to guide autonomous SEO decisions.
- **Dependencies**: Google Search Console access and credentials
- **Acceptance Criteria**:
  - Search Console data powers target-query evaluation.
  - Missing credentials degrade to technical/content SEO only and clearly show limited-learning state.
- **Validation**: Mocked API integration tests.

### Task 5.4: Target Query Learning Loop
- **Location**: `src/portfolio/seo/learning.py`
- **Description**: Score target searches based on impressions, clicks, CTR, average position, relevance, and recent changes. Keep improving targets, retire weak targets, and generate replacements.
- **Dependencies**: Task 5.3
- **Acceptance Criteria**:
  - Targets have measurable lifecycle states.
  - Weak targets are modified or retired with logged rationale.
  - Strong targets receive reinforcement suggestions.
- **Validation**: Unit tests using synthetic Search Console trends.

## Testing Strategy
- Unit tests for model classification, SEO validators, AI response parsing, metadata generation, and scheduler duplicate prevention.
- Integration tests for AI settings save/validate/model selection, SEO suggestion accept/reject, worker job processing, and admin UI access.
- Security tests for encrypted key handling, no key rendering, CSRF, passkey access, audit logging, prompt-injection-resistant output handling, and autonomous change guardrails.
- End-to-end smoke test for login, AI settings configuration, daily SEO run, autonomous change application, and weekly email summary.

## Potential Risks And Gotchas
- Search ranking cannot be guaranteed. The system can improve SEO hygiene, content relevance, and search feedback loops, but cannot force first-page rankings.
- Auto-applying visible content changes can create inaccurate claims. This plan allows autonomous visible edits only with meaning, tone, and factuality validators.
- AI may hallucinate credentials, metrics, employers, or technologies. Validators and prompts must reject unverifiable facts.
- Daily runs may burn API quota. Add rate limits, run caps, per-page cooldowns, and weekly spend/usage summaries.
- Model lists can change. Store selected model but validate availability before each run.
- Search engines may penalize spammy or over-optimized content. Avoid keyword stuffing and keep copy human-readable.
- Google Search Console setup is necessary for real learning from search performance. Without it, the agent cannot reliably know which target searches are working.

## Rollback Plan
- Disable SEO automation in AI settings.
- Stop worker or remove pending `seo-*` jobs from the jobs table.
- Revert autonomous SEO changes using content revisions/audit history.
- Remove/clear selected AI model and encrypted key if needed.
- Roll back migrations only before production data depends on the new tables; otherwise use forward-only cleanup migrations.
