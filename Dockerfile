FROM node:24-alpine AS assets
WORKDIR /build
COPY package.json package-lock.json vite.config.ts ./
RUN npm ci
COPY src/portfolio/static_src ./src/portfolio/static_src
RUN npm run build

FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system portfolio \
    && useradd --system --gid portfolio --home-dir /app --create-home portfolio

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY migrations ./migrations
RUN uv sync --frozen --no-dev \
    && mkdir -p /app/var/static /app/var/media \
    && chown -R portfolio:portfolio /app

COPY --from=assets /build/src/portfolio/static /app/bundled_static
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

USER portfolio
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "portfolio:create_app()"]
