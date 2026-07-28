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
  tar -C /source -cf "$media_archive" media
  tar -C "$workdir" -cf "$archive" portfolio.dump media.tar

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
