#!/bin/sh
set -eu

if [ -d /app/bundled_static ]; then
  mkdir -p /app/var/static
  cp -R /app/bundled_static/. /app/var/static/
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  flask db upgrade
fi

if [ "${SEED_INITIAL_CONTENT:-0}" = "1" ]; then
  flask content seed-initial
fi

exec "$@"
