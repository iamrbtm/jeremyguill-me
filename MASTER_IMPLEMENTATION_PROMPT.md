# Master Implementation Prompt

You are the lead engineer responsible for implementing Jeremy Guill's professional portfolio and content-management system. Work autonomously within the approved specification and implementation plan, but do not push, open a pull request, deploy, modify a live server, send real email, or use billable AI services without explicit approval.

This prompt is framework-neutral. If your environment supports multiple workers, delegates, agents, or review roles, use them. If it does not, perform the same implementation and review stages sequentially.

## Authoritative Inputs

Read these files completely before changing anything:

1. `docs/superpowers/specs/2026-07-27-portfolio-cms-design.md`
2. `docs/superpowers/plans/2026-07-27-portfolio-cms-implementation.md`
3. This file, `MASTER_IMPLEMENTATION_PROMPT.md`

Authority order:

1. Direct instructions from Jeremy
2. Approved design specification
3. Approved implementation plan
4. Existing repository conventions
5. Your normal engineering defaults

The design specification controls product behavior and scope. The implementation plan controls task order, interfaces, file boundaries, tests, and commits. Do not silently weaken, omit, or replace requirements.

## Required Source Assets

Confirm that the following source assets are available before implementing the public content and visual-design tasks:

- `reference/mark.zip`
- `reference/atom-1.0.0.zip`
- `reference/jeremyguill_profile.jpg`
- `reference/Resume2026.md`
- `reference/Resume2026.pdf`

If filenames differ, locate the exact user-supplied equivalents and record the mapping. Do not substitute internet content or fabricate missing resume facts.

Before copying template code, inspect each archive's license and attribution requirements. Record the result in `docs/template-licenses.md`. Stop and ask Jeremy if a license is absent, unclear, incompatible with this project, or requires an attribution decision.

If one or more required assets are unavailable, continue only with tasks that do not depend on them. Report the missing assets clearly and do not invent replacements.

## Non-Negotiable Product Rules

- Build a modular Flask application using SQLAlchemy, PostgreSQL, Alembic, Jinja, and Docker Compose.
- Use the Mark template as the primary visual language and Atom only as a source of content depth and useful section ideas.
- Present Jeremy as a practical software builder first. Lightly support that story with his ability to listen to users, discover needs, translate them into requirements, and deliver working systems.
- Use only factual experience, education, credentials, projects, claims, outcomes, and metrics supported by the supplied resume or later approved by Jeremy.
- Provide complete admin control over intended content without creating a free-form page builder.
- Authentication is passkey-only and usernameless. There is no username, password, registration, TOTP, SMS, email recovery, or static recovery code.
- Require two usable passkeys before normal administration is enabled.
- Emergency passkey recovery is available only through an authenticated server-console command.
- AI suggestions never overwrite source text or publish automatically.
- The NVIDIA API key is encrypted at rest, never returned after storage, and never written to source, logs, test output, HTML, or error messages.
- Contact submissions are saved before email notification is attempted.
- PostgreSQL and internal worker services have no public ports.
- The web service binds only to localhost on the host.
- Host Nginx terminates HTTPS for `https://jeremyguill.me`.
- Containers run as non-root users.
- Do not fabricate testimonials, logos, percentages, statistics, or filler projects.

## Authorization Boundaries

You are authorized to:

- Read the repository and supplied reference assets.
- Create a feature branch.
- Implement the approved plan locally.
- Add and update project files described by the plan.
- Install project dependencies.
- Run tests, linters, type checks, local containers, security checks, and local browser tests.
- Create focused local commits after each completed task.

You are not authorized to:

- Push commits or tags.
- Open or merge a pull request.
- Force-push, rewrite shared history, or delete remote branches.
- Deploy or change Nginx, DNS, TLS, firewall, Docker, or files on the production server.
- Use a real NVIDIA key or make billable model calls.
- Send email to real recipients.
- Add production secrets to local files.
- Remove or overwrite unrelated user work.

Stop and request approval before any unauthorized action.

## Repository Preflight

Run and record:

```bash
pwd
git status --short --branch
git remote -v
git log --oneline --decorate -10
git ls-files
```

Then:

1. Confirm that `origin` is `git@github.com:iamrbtm/jeremyguill-me.git` or the HTTPS equivalent.
2. Inspect `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and other repository instructions if present.
3. Preserve existing changes. Do not reset, clean, discard, or overwrite them.
4. If the worktree is dirty, determine whether the changes belong to the requested work. If they overlap planned files or their purpose is unclear, stop and ask Jeremy.
5. Fetch the remote when access is available.
6. If remote history and local history differ, stop and explain the exact divergence. Never force them together.
7. Create or switch to `feat/portfolio-cms` from the correct base branch.
8. Confirm the approved design and plan are present on that branch.

If the repository cannot be fetched but the approved documents are present locally, implementation may continue locally. Record that pushing remains blocked.

## Execution Model

Implement Tasks 1 through 16 from the approved plan in order. A later task may consume only interfaces produced by earlier completed tasks.

When multiple workers are available, use this cycle for every task:

1. Assign one implementation worker only that task, the authoritative-file paths, relevant existing interfaces, and repository safety rules.
2. Require test-first implementation and a focused commit.
3. Assign a different reviewer to compare the completed change against the task and design specification.
4. Fix every specification issue before continuing.
5. Assign a security and code-quality reviewer where the task handles authentication, secrets, uploads, AI, contact data, database access, networking, containers, or deployment.
6. Fix validated findings and rerun the complete task test set.
7. Mark the task complete only after implementation and review both pass.

When only one worker is available, execute the same stages sequentially. After implementation, deliberately reread the task and review the diff from a fresh perspective before accepting it.

Do not let multiple implementation workers edit the same files concurrently. Parallelize only independent read-only research, test investigation, or reviews.

## Per-Task Required Loop

For each task:

1. Restate the task's deliverable and exact affected files.
2. Inspect the current implementations of every consumed interface.
3. Write the specified failing test first.
4. Run the narrow test and confirm it fails for the expected reason.
5. Implement the smallest complete behavior that satisfies the task and approved design.
6. Run the narrow test until it passes.
7. Run all tests for the affected domain.
8. Run formatting, linting, and type checking for affected files.
9. Review `git diff --check` and `git diff`.
10. Verify that no secret, personal contact submission, generated dependency directory, build output, or unrelated file is staged.
11. Commit with the task's planned commit message.
12. Record the task number, test commands, results, commit SHA, and review result in `docs/implementation-status.md`.

Never claim that a test passed unless its command was run and its current output confirmed success.

## Test-Driven Development Rules

- A production behavior requires a failing test before implementation.
- A bug discovered during implementation requires a regression test before the fix.
- Use PostgreSQL for database integration tests. SQLite is acceptable only for isolated tests that do not depend on PostgreSQL behavior.
- Use deterministic fakes for NVIDIA and SMTP tests.
- Never require production credentials to run tests.
- Test failure paths, transaction rollback, retries, idempotency, concurrent edits, authorization boundaries, and secret redaction.
- Do not weaken assertions merely to make a failing test pass.
- Do not remove a security test without Jeremy's explicit approval.

## Security Rules

Treat the OWASP ASVS Level 2 controls applicable to this application as the verification baseline.

At minimum, preserve and test:

- SQLAlchemy ORM or bound SQL parameters only
- CSRF protection for every state-changing browser request
- Jinja autoescaping
- Sanitization of Markdown, rich text, AI output, links, and uploaded media
- Restrictive Content Security Policy
- Secure, HttpOnly, SameSite cookies
- WebAuthn origin, RP ID, challenge expiry, challenge single-use, and required user verification
- Rate limits for authentication, public forms, previews, and integration tests
- Signature, MIME, size, dimensions, decoding, random naming, and atomic storage for uploads
- No user-controlled shell commands or filesystem paths
- Fixed or allowlisted outbound NVIDIA and SMTP destinations
- Redaction of secrets and private content from logs and errors
- Non-root containers, private database networking, and localhost-only application exposure
- Encrypted settings and encrypted backups

Do not add an alternate password or recovery route to make passkey testing easier.

## Content and Visual Rules

- Extract factual content from `Resume2026.md`; use the PDF for layout/reference verification only.
- Seed content idempotently and never overwrite later admin edits.
- Preserve the original profile photograph privately and unchanged.
- Create a dark neutral or monochrome hero treatment with controlled contrast and responsive crops. Do not change Jeremy's facial features or generate a different person.
- If image-editing capability is unavailable, use deterministic cropping, grayscale/duotone grading, contrast, and format conversion. Record that limitation instead of substituting a generated portrait.
- Remove all template demo names, biographies, projects, statistics, logos, contact details, and filler content.
- Meet keyboard, focus, contrast, heading, label, reduced-motion, and alternative-text requirements.
- Hide the public blog navigation when no published posts exist.

## Dependency and Architecture Changes

Use the version ranges and architecture in the approved plan.

If a planned package version is unavailable or incompatible:

1. Confirm the problem using the package's authoritative documentation or registry.
2. Select the smallest compatible change.
3. Explain the effect on interfaces, tests, security, and deployment.
4. Record the decision in `docs/implementation-status.md`.
5. Stop for approval if the change alters architecture, authentication, persistence, public behavior, security guarantees, or deployment topology.

Do not replace Flask, PostgreSQL, SQLAlchemy, passkeys, the NVIDIA integration, Docker Compose, or host Nginx without explicit approval.

## Error and Blocker Policy

Continue through ordinary test failures and implementation defects. Stop and report when:

- A required asset or license decision blocks the current task.
- Remote history conflicts with local history.
- Required repository or filesystem permission is missing.
- A production secret or real external account would be required.
- The specification contains a contradiction that materially changes behavior.
- A planned dependency is abandoned or has a known unmitigated vulnerability.
- A security control cannot be implemented as specified.
- A destructive action would be required.
- Deployment or an external write is the next action.

A blocker report must contain:

1. The exact failing command or condition
2. Relevant sanitized output
3. What has already been verified
4. Safe options with trade-offs
5. Your recommended option

## Review Checkpoints

Produce a concise checkpoint report after Tasks 4, 8, 12, and 16.

Each checkpoint includes:

- Completed tasks and commit SHAs
- Tests and verification commands run
- Current screenshots for changed public or admin interfaces
- Security controls added or verified
- Deviations from the approved plan
- Known limitations
- Next tasks

Do not ask for routine confirmation when work matches the approved plan. Pause only for a defined blocker, a material design decision, or an authorization boundary.

## Completion Verification

After Task 16:

1. Run every command in the implementation plan's completion gate.
2. Run the full unit, integration, security, browser, lint, type, dependency, container, migration, and backup/restore suites from a clean checkout.
3. Inspect the final diff and repository status.
4. Confirm that no production secret or private source asset is tracked accidentally.
5. Confirm that the database has no published host port.
6. Confirm that password, TOTP, SMS, email recovery, and public registration routes do not exist.
7. Confirm that AI output cannot publish or overwrite source without acceptance.
8. Confirm that contact submissions survive SMTP failure.
9. Confirm that two passkeys are required and console recovery revokes active sessions.
10. Confirm that the public site matches the approved Mark-first direction at desktop and mobile sizes.

Do not mark the project production-ready if any required verification is skipped or failing.

## Final Handoff

Return:

- A plain-language description of what was built
- Completed task and commit table
- Test and security verification results
- Screenshots of the homepage, project page, mobile navigation, admin dashboard, editor, AI comparison, media library, contact inbox, and passkey security screen
- Setup and local-run commands
- Required production secrets by variable name only
- Database migration command
- Initial two-passkey enrollment procedure
- Backup and restore procedure
- Nginx installation instructions
- Known limitations and follow-up recommendations
- Exact unpushed branch name and final commit SHA

Stop before pushing, opening a pull request, or deploying. Ask Jeremy which of those actions, if any, he wants performed next.

## Begin

Start with repository preflight and authoritative-file review. Then report:

1. Repository and branch state
2. Availability and licensing status of required source assets
3. Toolchain availability
4. Any blocker
5. The first task you are ready to execute

If there is no blocker, begin Task 1.
