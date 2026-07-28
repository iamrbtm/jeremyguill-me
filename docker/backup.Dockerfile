FROM postgres:17

RUN useradd --system --home-dir /backups --create-home backup
COPY docker/backup.sh /backup.sh
RUN chmod +x /backup.sh && chown backup:backup /backup.sh /backups
USER backup
ENTRYPOINT ["/backup.sh"]
