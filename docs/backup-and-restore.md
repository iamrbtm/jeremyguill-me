# Backup And Restore

Run a backup with `docker compose run --rm backup` or `BACKUP_COMMAND=backup-now docker compose run --rm backup`.

When `/run/secrets/age_recipient` exists, backups are encrypted with `age` and written as `.age` files. Without a recipient, local development writes an unencrypted archive and prints that fact.

Restore requires explicit target confirmation:

```bash
BACKUP_COMMAND=restore-backup \
RESTORE_DATABASE=portfolio_restore \
RESTORE_ARCHIVE=/backups/portfolio-example.dump \
RESTORE_CONFIRM=restore-to-portfolio_restore \
docker compose run --rm backup
```

The restore command refuses to run without `RESTORE_CONFIRM=restore-to-$RESTORE_DATABASE`.
