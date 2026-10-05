#!/bin/sh
# CI build step: generate one_page/index.html from the live site.
# Exit 3 from the generator means production is not ready yet: skip publishing quietly.
set +e
uv run python scripts/build_one_page.py --output one_page/index.html
code=$?
if [ "$code" -eq 3 ]; then
  echo "::notice::Production does not serve /api/site-content.json yet; skipping publish (deploy the main site first)."
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 0
fi
exit "$code"
