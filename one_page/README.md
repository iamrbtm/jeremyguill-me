# One-page site (github.io)

This folder holds the generated one-page version of jeremyguill.me for GitHub Pages.
`index.html` is **generated**, never edited by hand.

## Publish (order matters)

1. **Deploy the main site first.** It adds `/api/site-content.json` and the font CORS header.
   (At the time of review production returned 404 and had no `Access-Control-Allow-Origin`.)
2. **Verify production:**
   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' https://jeremyguill.me/api/site-content.json   # 200
   curl -sI https://jeremyguill.me/static/assets/fonts/open-sans-var.woff2 \
     | grep -i access-control-allow-origin                                                 # *
   ```
3. **Generate and review:** `uv run python scripts/build_one_page.py` (defaults to production).
   Options: `--source URL_OR_FILE`, `--origin ORIGIN`, `--output PATH`, `--no-copy-overrides`,
   `--allow-origin-mismatch`. The generator exits non-zero and writes nothing if the source cannot
   be fetched or parsed, if the export's origin differs from `--origin`, or if a URL field is
   off-origin. Bodies are re-sanitised with the site allowlist.
4. **Commit `one_page/index.html` and push to `main`.** `.github/workflows/deploy.yml` (push to
   `main` touching `one_page/index.html`, or `workflow_dispatch` from `main` only) runs
   `scripts/check_one_page.sh` and copies ONLY `index.html` to `iamrbtm/iamrbtm.github.io`
   (default branch `master`). The repo secret `DEPLOY_TOKEN` needs write access to it.
5. **One-time manual cleanup:** the Pages repo still holds files from the OLD workflow
   (`assets/index-*.js`, `passkeys-*.js`, `site-*.js`, `site-*.css`; the old 813-byte
   `index.html` is overwritten). The new workflow never deletes anything, so delete `assets/`
   from `iamrbtm.github.io` once by hand.

Source of the page: `scripts/one_page/template.html`, `style.css` and `app.js` (inlined into
one file).

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
