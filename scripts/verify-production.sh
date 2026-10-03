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
