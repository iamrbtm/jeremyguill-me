#!/bin/sh
set -eu

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="/backups/portfolio-${timestamp}.dump"
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

pg_dump --format=custom --host=db --username=portfolio --dbname=portfolio --file="$destination"
printf 'backup written: %s\n' "$destination"
