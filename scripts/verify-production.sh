#!/bin/sh
set -eu

origin="${1:?Usage: verify-production.sh https://host}"

curl --fail --silent --show-error "$origin/health/live" >/dev/null
curl --fail --silent --show-error "$origin/health/ready" >/dev/null
headers="$(curl --fail --silent --show-error --head "$origin/")"
printf '%s' "$headers" | grep -qi '^content-security-policy:'
printf '%s' "$headers" | grep -qi '^strict-transport-security:'
curl --fail --silent --show-error "$origin/sitemap.xml" | grep -q '<urlset'
curl --fail --silent --show-error "$origin/robots.txt" | grep -q 'Sitemap:'

body="$(curl --fail --silent --show-error "$origin/")"
if printf '%s' "$body" | grep -qi 'localhost'; then
  echo "FAIL: localhost found in homepage"
  exit 1
fi
if ! printf '%s' "$body" | grep -q 'rel="canonical" href="'"$origin"'/"'; then
  echo "FAIL: canonical does not match $origin"
  exit 1
fi
if ! printf '%s' "$body" | grep -q 'property="og:image"'; then
  echo "FAIL: og:image missing"
  exit 1
fi
if ! printf '%s' "$body" | grep -q 'rel="icon"'; then
  echo "FAIL: favicon link missing"
  exit 1
fi
sitemap="$(curl --fail --silent --show-error "$origin/sitemap.xml")"
if printf '%s' "$sitemap" | grep -qi 'localhost'; then
  echo "FAIL: localhost in sitemap"
  exit 1
fi
robots="$(curl --fail --silent --show-error "$origin/robots.txt")"
if printf '%s' "$robots" | grep -qi 'localhost'; then
  echo "FAIL: localhost in robots.txt"
  exit 1
fi
rss="$(curl --fail --silent --show-error "$origin/rss.xml")"
if ! printf '%s' "$rss" | grep -q '<rss'; then
  echo "FAIL: rss feed"
  exit 1
fi
security="$(curl --fail --silent --show-error "$origin/.well-known/security.txt")"
if ! printf '%s' "$security" | grep -q '^Contact:'; then
  echo "FAIL: security.txt"
  exit 1
fi
curl --fail --silent --show-error --output /dev/null "$origin/favicon.ico"
if [ -n "${STATS_ORIGIN:-}" ]; then
  if ! printf '%s' "$body" | grep -q 'data-website-id='; then
    echo "FAIL: analytics tag missing"
    exit 1
  fi
  curl --fail --silent --show-error --output /dev/null "$STATS_ORIGIN/script.js"
fi
echo "verify-production: OK"
