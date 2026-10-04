#!/bin/sh
# Guard for the one-page publish workflow: refuse to publish a broken or dev-only page.
set -eu

f="one_page/index.html"

if [ ! -f "$f" ]; then
  echo "::error::$f is missing"
  exit 1
fi
if ! grep -qi '<!doctype html>' "$f"; then
  echo "::error::$f does not contain <!doctype html>"
  exit 1
fi
if grep -qE 'localhost|127\.0\.0\.1' "$f"; then
  echo "::error::$f references localhost or 127.0.0.1"
  exit 1
fi
echo "$f passed pre-publish checks"
