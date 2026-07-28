FROM postgres:17

RUN id -u backup >/dev/null 2>&1 || useradd --system --home-dir /backups --create-home backup
COPY docker/backup.sh /backup.sh
RUN mkdir -p /backups && chmod +x /backup.sh && chown backup:backup /backup.sh /backups
USER backup
ENTRYPOINT ["/backup.sh"]
