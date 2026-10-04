#!/bin/sh
set -eu

command="${BACKUP_COMMAND:-backup}"
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

backup_now() {
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  workdir="$(mktemp -d)"
  dump_path="${workdir}/portfolio.dump"
  media_archive="${workdir}/media.tar"
  archive="/backups/portfolio-${timestamp}.tar"
  encrypted="${archive}.age"

  pg_dump --format=custom --host=db --username=portfolio --dbname=portfolio --file="$dump_path"
  members="portfolio.dump media.tar"
  # Umami's database is created manually (docs/analytics.md); only dump it if it exists.
  if psql --host=db --username=portfolio --dbname=portfolio -tAc "select 1 from pg_database where datname = 'umami'" | grep -q 1; then
    # Best-effort: an analytics problem must never block the portfolio backup.
    if pg_dump --format=custom --host=db --username=portfolio --dbname=umami --file="${workdir}/umami.dump"; then
      members="$members umami.dump"
    else
      rm -f "${workdir}/umami.dump"
      printf 'umami dump failed; skipping\n' >&2
    fi
  else
    printf 'umami database not found; skipping its dump\n'
  fi
  tar -C /source -cf "$media_archive" media
  # shellcheck disable=SC2086
  tar -C "$workdir" -cf "$archive" $members

  recipient_file="${AGE_RECIPIENT_FILE:-/run/secrets/age_recipient}"
  if [ -f "$recipient_file" ]; then
    age --recipient "$(cat "$recipient_file")" --output "$encrypted" "$archive"
    test -s "$encrypted"
    rm -f "$archive"
    printf 'encrypted backup written: %s\n' "$encrypted"
  else
    printf 'backup written without age recipient: %s\n' "$archive"
  fi
  rm -rf "$workdir"
  find /backups -type f -name 'portfolio-*' -mtime +35 -delete
}

restore_backup() {
  target="${RESTORE_DATABASE:-}"
  archive="${RESTORE_ARCHIVE:-}"
  confirmation="${RESTORE_CONFIRM:-}"
  if [ -z "$target" ] || [ -z "$archive" ] || [ "$confirmation" != "restore-to-${target}" ]; then
    printf 'Refusing restore: set RESTORE_DATABASE, RESTORE_ARCHIVE, and RESTORE_CONFIRM=restore-to-$RESTORE_DATABASE\n' >&2
    exit 2
  fi
  pg_restore --clean --if-exists --host=db --username=portfolio --dbname="$target" "$archive"
}

case "$command" in
  backup|backup-now) backup_now ;;
  restore|restore-backup) restore_backup ;;
  *) printf 'unknown backup command: %s\n' "$command" >&2; exit 2 ;;
esac
