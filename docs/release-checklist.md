# Release Checklist

- Confirm `uv run pytest --cov=portfolio --cov-report=term-missing` passes.
- Confirm `uv run ruff check .`, `uv run mypy src`, and `uv run pip-audit` pass (there is no JS build).
- Confirm `docker compose config` and `docker build -t jeremyguill-portfolio:acceptance .` pass.
- Preview migrations with `docker compose run --rm web flask --app portfolio db upgrade` against a staging database.
- Confirm two production passkeys are enrolled.
- Confirm PostgreSQL and worker services expose no host ports.
- Confirm Nginx config passes `nginx -t` on the host.
- Confirm `PUBLIC_ORIGIN=https://jeremyguill.me` is set in the production `.env` (the app refuses to boot with a localhost or non-https value).
- Confirm `scripts/verify-production.sh https://jeremyguill.me` passes after deployment and prints `verify-production: OK`. If analytics is enabled, run it with `STATS_ORIGIN=https://stats.jeremyguill.me` as well.
- Run Lighthouse and axe on `/`, `/work`, one case study and `/contact`; fix any accessibility or SEO score below 100.
- Resume: the PDF is intentionally not published. The `/resume` link stays hidden until a redacted PDF (no home address or phone) is added as `src/portfolio/static/resume/Resume2026.pdf`.
- Run and record an encrypted backup identifier.
- Restore the backup into a new named database before final acceptance.
- Record deployed commit SHA, backup identifier, and rollback command.
