# Analytics (self-hosted Umami)

Cookie-less visitor analytics served from `stats.jeremyguill.me`. The Umami container
listens on port 3000, is bound to `127.0.0.1:3001` on the host, and joins
`nginx-proxy-manager_default` so the proxy reaches it as `analytics:3000`. It uses its
own `umami` database (and role) inside the existing Postgres container, separate from
the `portfolio` database.

## One-time setup

1. **DNS.** Add an `A` (or `CNAME`) record `stats.jeremyguill.me` pointing to the same
   server as `jeremyguill.me`.
2. **Secrets.** On the server run `openssl rand -hex 32` twice. In the production `.env`
   set `UMAMI_DB_PASSWORD=<first>` and `UMAMI_APP_SECRET=<second>`. Both default to
   empty in `compose.yaml` so `docker compose config` works without them; Umami will not
   work until they are set.
3. **Create the database** (use the same `<first>` password):
   ```sh
   docker compose exec db psql -U portfolio -d portfolio \
     -c "CREATE ROLE umami LOGIN PASSWORD '<first>';" \
     -c "CREATE DATABASE umami OWNER umami;"
   ```
4. **Start it:** `docker compose up -d analytics`, then
   `docker compose logs --tail=50 analytics`.
5. **nginx-proxy-manager.** Proxy Hosts, Add: domain `stats.jeremyguill.me`, scheme
   `http`, forward host `analytics`, port `3000`, enable "Block Common Exploits". SSL
   tab: request a Let's Encrypt certificate, enable "Force SSL" and "HTTP/2".
6. **First login.** Open `https://stats.jeremyguill.me`, sign in with `admin` / `umami`,
   and immediately change the password (Settings, Profile).
7. **Add the website.** Settings, Websites, Add website: Name `jeremyguill.me`, Domain
   `jeremyguill.me`. Click Edit and copy the **Website ID**.
8. **Wire the site.** In the production `.env` add
   `ANALYTICS_SCRIPT_URL=https://stats.jeremyguill.me/script.js` and
   `ANALYTICS_WEBSITE_ID=<the id>`, then `docker compose up -d web`.
9. **Verify.** Visit the site in a private window; Umami's Realtime tab should show one
   visitor. Then run:
   ```sh
   STATS_ORIGIN=https://stats.jeremyguill.me scripts/verify-production.sh https://jeremyguill.me
   ```
10. Optional: Settings, Websites, Share URL gives a read-only public dashboard link.

## Notes

- The image is pinned (`postgresql-v2.20.2`); upgrade deliberately by changing the tag
  and checking Umami's release notes for migrations.
- Backups: `docker/backup.sh` dumps the `umami` database into the same archive
  (`umami.dump`) when that database exists, and skips it otherwise. The backup job must
  be rebuilt (`docker compose build backup`) to pick up the change.
- Leaving `ANALYTICS_SCRIPT_URL` / `ANALYTICS_WEBSITE_ID` empty disables the tracking tag.
