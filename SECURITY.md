# Security Policy

## Supported Versions

Only the current `feat/portfolio-cms` deployment branch is supported until the first production release tag.

## Reporting

Report security issues privately to Jeremy Guill before public disclosure. Do not include secrets, API keys, passkey material, or contact-message bodies in issue trackers.

## Operational Requirements

- Production requires a strong `SECRET_KEY` and `SETTINGS_ENCRYPTION_KEY`.
- Two usable passkeys must be enrolled before normal administration.
- PostgreSQL and worker services must not publish host ports.
- Backups should be encrypted with an age recipient and restore-tested before release.
- NVIDIA and SMTP credentials must be supplied through deployment secrets or environment, never committed.
