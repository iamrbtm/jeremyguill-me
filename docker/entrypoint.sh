#!/bin/sh
set -eu

if [ -d /app/bundled_static ]; then
  mkdir -p /app/var/static
  cp -R /app/bundled_static/. /app/var/static/
fi

exec "$@"
