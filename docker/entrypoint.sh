#!/bin/sh
set -eu

if [ -d /app/bundled_static ]; then
  mkdir -p /app/var/static
  cp -R /app/bundled_static/. /app/var/static/ 2>/dev/null || true
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  flask --app portfolio db upgrade
fi

if [ "${SEED_INITIAL_CONTENT:-0}" = "1" ]; then
  flask --app portfolio content seed-initial
fi

exec "$@"
