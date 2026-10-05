# One-page site (github.io)

The one-page version of jeremyguill.me for GitHub Pages is **generated and published
automatically**. Nothing in this folder is committed: `one_page/index.html` is built on the
CI runner and is git-ignored. Never commit it.

## How it publishes

`.github/workflows/deploy.yml` ("Build and publish one-page site") runs:

- on every push to `main`,
- every 6 hours (cron `23 */6 * * *`),
- manually via **Run workflow** (`workflow_dispatch`, `main` only).

It runs `scripts/build_one_page.py` against production, checks the result with
`scripts/check_one_page.sh`, and copies ONLY `index.html` to `iamrbtm/iamrbtm.github.io`
(default branch `master`). If the generated file is unchanged there is no commit.

Requirements: the repo secret `DEPLOY_TOKEN` needs write access to the Pages repo.

### Quiet skip

If production does not serve `/api/site-content.json` yet (HTTP 404) the generator exits 3.
The workflow then prints a notice, skips every publish step and finishes green. Any other
failure (500, network, invalid JSON, off-origin data) fails the run and publishes nothing.

## Deploy-order checklist for the main site

Deploy the main site BEFORE expecting a publish. Verify:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://jeremyguill.me/api/site-content.json   # 200
curl -sI https://jeremyguill.me/static/assets/fonts/open-sans-var.woff2 \
  | grep -i access-control-allow-origin                                                 # *
```

## One-time manual cleanup

The Pages repo still holds files from the OLD workflow (`assets/index-*.js`,
`passkeys-*.js`, `site-*.js`, `site-*.css`). The workflow never deletes anything, so delete
`assets/` from `iamrbtm.github.io` once by hand.

## Local preview

```bash
uv run python scripts/build_one_page.py --output /tmp/preview.html
```

Options: `--source URL_OR_FILE`, `--origin ORIGIN`, `--output PATH`, `--no-copy-overrides`,
`--allow-origin-mismatch`. Exit codes: 0 success, 3 production not ready (404), 1 any other
failure; nothing is written on failure. Do not write the preview to `one_page/index.html`
and never commit it.

Source of the page: `scripts/one_page/template.html`, `style.css` and `app.js` (inlined into
one file). The generated comment carries no date, so identical content gives an identical file.

Copy files in `src/portfolio/content/copy/project-*.md` are applied as overrides and WIN over
production data in the generated page (applied slugs are printed to stderr).

## Notes

- Images and fonts are linked from `https://jeremyguill.me`, not copied here.
- No analytics, frameworks or third-party hosts.
- The case-study overlay deep-links with `#work/<slug>`; without JavaScript the cards link to
  the full case study on jeremyguill.me.
- nginx caveat: `docker/nginx/jeremyguill.me.conf` serves `/static/` straight from disk, which
  would bypass the Flask font-CORS header. Production currently routes static through Flask; if
  static is ever served by the proxy, add `add_header Access-Control-Allow-Origin *;` for
  `/static/assets/fonts/`.
