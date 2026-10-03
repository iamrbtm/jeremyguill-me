from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path("scripts/verify-production.sh").resolve()
ORIGIN = "https://example.test"

FAKE_CURL = """#!/bin/sh
# Fake curl: serves canned files from $FAKE_SITE by URL path.
url=""
head=0
for arg in "$@"; do
  case "$arg" in
    --head) head=1 ;;
    http*) url="$arg" ;;
  esac
done
path="${url#https://example.test}"
if [ "$head" = 1 ]; then
  printf 'HTTP/2 200\\r\\ncontent-security-policy: x\\r\\nstrict-transport-security: y\\r\\n'
  exit 0
fi
case "$path" in
  /) f=index ;;
  /health/live|/health/ready) printf ok; exit 0 ;;
  /sitemap.xml) f=sitemap ;;
  /robots.txt) f=robots ;;
  /rss.xml) f=rss ;;
  /.well-known/security.txt) f=security ;;
  /favicon.ico) printf icon; exit 0 ;;
  *) exit 22 ;;
esac
cat "$FAKE_SITE/$f"
"""

CLEAN = {
    "index": (
        '<link rel="canonical" href="https://example.test/">'
        '<link rel="icon" href="/favicon.ico">'
        '<meta property="og:image" content="https://example.test/og.png">'
    ),
    "sitemap": "<urlset><url><loc>https://example.test/</loc></url></urlset>",
    "robots": "Sitemap: https://example.test/sitemap.xml\n",
    "rss": "<rss version='2.0'></rss>",
    "security": "Contact: mailto:a@example.test\n",
}


def run_script(tmp_path: Path, pages: dict[str, str]):
    bindir = tmp_path / "bin"
    site = tmp_path / "site"
    bindir.mkdir()
    site.mkdir()
    curl = bindir / "curl"
    curl.write_text(FAKE_CURL)
    curl.chmod(curl.stat().st_mode | stat.S_IEXEC)
    for name, body in pages.items():
        (site / name).write_text(body)
    env = {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "FAKE_SITE": str(site),
    }
    return subprocess.run(
        ["sh", str(SCRIPT), ORIGIN], env=env, capture_output=True, text=True, timeout=30
    )


def test_script_has_valid_shell_syntax():
    assert subprocess.run(["sh", "-n", str(SCRIPT)]).returncode == 0


def test_script_contains_each_check():
    text = SCRIPT.read_text()
    for needle in (
        "localhost",
        "canonical",
        "og:image",
        'rel="icon"',
        "rss.xml",
        "security.txt",
        "favicon.ico",
        "STATS_ORIGIN",
        "data-website-id=",
        "verify-production: OK",
    ):
        assert needle in text, needle


def test_clean_site_passes(tmp_path):
    result = run_script(tmp_path, CLEAN)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "verify-production: OK" in result.stdout


def test_localhost_in_homepage_fails(tmp_path):
    pages = {**CLEAN, "index": CLEAN["index"] + "<a href='http://localhost:7777'>x</a>"}
    result = run_script(tmp_path, pages)

    assert result.returncode != 0
    assert "FAIL: localhost found in homepage" in result.stdout


def test_localhost_in_sitemap_fails(tmp_path):
    pages = {**CLEAN, "sitemap": CLEAN["sitemap"] + "http://localhost/"}
    result = run_script(tmp_path, pages)

    assert result.returncode != 0
    assert "FAIL: localhost in sitemap" in result.stdout


def test_missing_canonical_fails(tmp_path):
    pages = {**CLEAN, "index": '<link rel="icon" href="/f"><meta property="og:image" content="x">'}
    result = run_script(tmp_path, pages)

    assert result.returncode != 0
    assert "FAIL: canonical" in result.stdout
