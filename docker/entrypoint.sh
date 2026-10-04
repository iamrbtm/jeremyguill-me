#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  flask --app portfolio db upgrade
fi

if [ "${SEED_INITIAL_CONTENT:-0}" = "1" ]; then
  flask --app portfolio content seed-initial
fi

exec "$@"
