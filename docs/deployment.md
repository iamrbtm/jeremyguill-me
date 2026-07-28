# Deployment

1. Create `/srv/jeremyguill-me/shared/static`, `/srv/jeremyguill-me/shared/media`, and `/srv/jeremyguill-me/backups` with ownership matching the container user.
2. Provide production environment values for `SECRET_KEY`, `DATABASE_URL`, `PUBLIC_ORIGIN`, `WEBAUTHN_RP_ID`, `SETTINGS_ENCRYPTION_KEY`, and SMTP/NVIDIA settings as needed.
3. Run `docker compose run --rm web flask --app portfolio db upgrade` before starting the web and worker services.
4. Start with `docker compose up --build -d` and verify `/health/live` and `/health/ready`.
5. Install `docker/nginx/jeremyguill.me.conf` into host Nginx after Certbot has issued certificates for `jeremyguill.me`.

PostgreSQL and worker services publish no host ports. The web service binds to `127.0.0.1:7777` for host Nginx proxying.
