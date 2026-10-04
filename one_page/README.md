# One-page site (github.io)

This folder holds the generated one-page version of jeremyguill.me for GitHub Pages.
`index.html` is **generated**, never edited by hand.

## Regenerate

```bash
uv run python scripts/build_one_page.py
```

Defaults: reads `https://jeremyguill.me/api/site-content.json`, applies the reviewed copy files
in `src/portfolio/content/copy/project-*.md` as overrides, and writes `one_page/index.html`.
Options: `--source URL_OR_FILE`, `--origin ORIGIN`, `--output PATH`, `--no-copy-overrides`.
The generator exits non-zero and writes nothing if the source cannot be fetched or parsed.

Source of the page: `scripts/one_page/template.html`, `style.css` and `app.js` (inlined into
one file).

## Deploy

A GitHub Actions workflow (added in a later task) publishes this folder to GitHub Pages.
Commit `index.html` only after production serves `/api/site-content.json`, so the generated
page reflects live published content.

## Notes

- Images and fonts are linked from `https://jeremyguill.me`, not copied here.
- No analytics, frameworks or third-party hosts.
- The case-study overlay deep-links with `#work/<slug>`; without JavaScript the cards link to
  the full case study on jeremyguill.me.
