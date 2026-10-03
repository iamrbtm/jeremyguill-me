# Jeremy Guill Portfolio CMS

Professional portfolio and single-owner CMS for Jeremy Guill.

## Local Setup

1. Install Python 3.14, `uv`, and Docker.
2. Install dependencies with `uv sync --locked`.
3. Run tests with `uv run pytest -v`.
4. Start the local stack with `docker compose up --build -d`.

Open `http://127.0.0.1:7777/` locally.

## Useful Commands

- `uv run flask --app portfolio db upgrade`
- `uv run flask --app portfolio content seed-initial`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pip-audit`
- `docker compose config`
- `docker compose logs -f web worker`

## Production Verification

After deployment and HTTPS termination, run:

```bash
scripts/verify-production.sh https://jeremyguill.me
```
