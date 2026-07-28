FROM postgres:17

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends age ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN id -u backup >/dev/null 2>&1 || useradd --system --home-dir /backups --create-home backup
COPY docker/backup.sh /backup.sh
RUN mkdir -p /backups && chmod +x /backup.sh && chown backup:backup /backup.sh /backups
USER backup
ENTRYPOINT ["/backup.sh"]
