#!/bin/sh
# CI build step: generate one_page/index.html from the live site.
# Exit 3 from the generator means production is not ready yet: skip publishing quietly.
set +e
uv run --frozen --no-dev python scripts/build_one_page.py --output one_page/index.html
code=$?
if [ "$code" -eq 3 ]; then
  msg="Production does not serve /api/site-content.json yet;"
  msg="$msg skipping publish (deploy the main site first)."
  echo "::notice::$msg"
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 0
fi
exit "$code"
