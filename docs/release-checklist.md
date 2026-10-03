# Release Checklist

- Confirm `uv run pytest --cov=portfolio --cov-report=term-missing` passes.
- Confirm `uv run ruff check .`, `uv run mypy src`, `uv run pip-audit`, and `npm run build` pass.
- Confirm `docker compose config` and `docker build -t jeremyguill-portfolio:acceptance .` pass.
- Preview migrations with `docker compose run --rm web flask --app portfolio db upgrade` against a staging database.
- Confirm two production passkeys are enrolled.
- Confirm PostgreSQL and worker services expose no host ports.
- Confirm Nginx config passes `nginx -t` on the host.
- Confirm `scripts/verify-production.sh https://jeremyguill.me` passes after deployment.
- Run and record an encrypted backup identifier.
- Restore the backup into a new named database before final acceptance.
- Record deployed commit SHA, backup identifier, and rollback command.
