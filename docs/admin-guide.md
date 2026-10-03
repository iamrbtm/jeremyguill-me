# Admin Guide

## Access

Sign in at `/admin/sign-in`. You can authenticate with a username and password or with an enrolled passkey. Bootstrap and recovery are console-only flows.

### Password login

Set the `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` environment variables. Generate the hash from the console:

```
docker compose exec web flask --app portfolio admin set-password
```

The command prints `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` values to place in your environment. Set both before password login is available; otherwise sign-in falls back to passkeys only.

## Content

Projects, blog posts, experience, credentials, and profile content are stored as structured records. Markdown source is sanitized and rendered before publication.

## Editor And AI

The visual editor syncs Markdown back to the source field on save. AI revisions are side-by-side suggestions and never overwrite content without explicit acceptance.

## Media

Uploads are signature-validated images. Originals are private; public variants are generated for hero, profile, mobile, and Open Graph use.

## SEO

Canonical metadata, JSON-LD, sitemap, robots, and redirects are deterministic. AI availability does not affect canonical SEO output.

## Contacts

Contact submissions are stored before notification delivery. Honeypot and timing checks silently discard obvious automated submissions.

## Backups

Use `docker compose run --rm backup` for backups. See `docs/backup-and-restore.md` for restore confirmation requirements.
