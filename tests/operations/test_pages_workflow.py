"""Tests for the one-page Pages publish workflow (text based; PyYAML is not a dependency)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
GUARD = ROOT / "scripts" / "check_one_page.sh"


@pytest.fixture(scope="module")
def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _code_lines(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def test_name_and_triggers(text: str) -> None:
    assert re.search(r"^name: Publish one-page site$", text, re.M)
    on_block = re.search(r"^on:\n((?:[ \t]+.*\n|\n)+)", text, re.M)
    assert on_block is not None
    body = on_block.group(1)
    top_keys = re.findall(r"^  (\w+):", body, re.M)
    assert top_keys == ["push", "workflow_dispatch"]
    assert re.search(r"branches: \[main\]|branches:\n\s+- main", body)
    assert re.search(
        r'paths: \["one_page/index\.html"\]|paths:\n\s+- "?one_page/index\.html"?', body
    )


def test_no_pull_request(text: str) -> None:
    assert "pull_request" not in _code_lines(text)


def test_permissions_read_only_and_concurrency(text: str) -> None:
    assert re.search(r"^permissions:\n  contents: read\n", text, re.M)
    assert not re.search(r"contents: write", text)
    assert re.search(r"group: pages-publish", text)
    assert re.search(r"cancel-in-progress: false", text)


def test_no_destructive_or_npm(text: str) -> None:
    code = _code_lines(text)
    assert "rm -rf" not in code
    assert not re.search(r"\bfind\b[^\n]*(-exec\s+rm|-delete)", code)
    assert not re.search(r"\bnpm\b", code)
    assert "git add -A" not in code
    assert "git rm" not in code


def test_tokens(text: str) -> None:
    code = _code_lines(text)
    assert code.count("secrets.DEPLOY_TOKEN") == 1
    assert "secrets.GITHUB_TOKEN" not in code
    assert not re.search(r"https://[^\s]*@github\.com", code)
    assert "remote set-url" not in code
    # DEPLOY_TOKEN belongs to the Pages repo checkout step.
    pages = re.search(
        r"repository: iamrbtm/iamrbtm\.github\.io\n\s+token: \$\{\{ secrets\.DEPLOY_TOKEN \}\}"
        r"\n\s+path: pages-repo",
        text,
    )
    assert pages is not None
    assert "ref:" not in code
    assert "master" not in code


def test_actions_pinned_to_major(text: str) -> None:
    uses = re.findall(r"uses: (\S+)", text)
    assert uses and all(u == "actions/checkout@v4" for u in uses)


def test_copies_only_one_page_index(text: str) -> None:
    code = _code_lines(text)
    cps = re.findall(r"^\s*cp\b.*$", code, re.M)
    assert cps == ["          cp one_page/index.html pages-repo/index.html"]
    assert not re.search(r"\b(rsync|mv)\b", code)
    assert "git status --porcelain" in code
    assert "No changes" in code
    assert "git push" in code
    assert not re.search(r"git push\s+\S", code)
    assert "github-actions[bot]" in code
    assert "41898282+github-actions[bot]@users.noreply.github.com" in code
    assert "Publish one-page site from ${GITHUB_SHA::7}" in code


def test_workflow_uses_guard_script(text: str) -> None:
    assert "sh scripts/check_one_page.sh" in text


def _run(tmp_path: Path, content: str | None) -> subprocess.CompletedProcess[str]:
    if content is not None:
        (tmp_path / "one_page").mkdir()
        (tmp_path / "one_page" / "index.html").write_text(content, encoding="utf-8")
    return subprocess.run(
        ["sh", str(GUARD)], cwd=tmp_path, capture_output=True, text=True, check=False
    )


def test_guard_is_executable_posix_sh() -> None:
    assert GUARD.stat().st_mode & 0o111
    first = GUARD.read_text(encoding="utf-8").splitlines()[0]
    assert first == "#!/bin/sh"
    assert "set -eu" in GUARD.read_text(encoding="utf-8")


def test_guard_missing_file(tmp_path: Path) -> None:
    r = _run(tmp_path, None)
    assert r.returncode != 0
    assert "::error::" in r.stdout + r.stderr


@pytest.mark.parametrize("bad", ["localhost:8000", "127.0.0.1"])
def test_guard_rejects_local_hosts(tmp_path: Path, bad: str) -> None:
    r = _run(tmp_path, f"<!DOCTYPE html><html><a href='http://{bad}/'>x</a></html>")
    assert r.returncode != 0
    assert "::error::" in r.stdout + r.stderr


def test_guard_rejects_missing_doctype(tmp_path: Path) -> None:
    r = _run(tmp_path, "<html><body>hi</body></html>")
    assert r.returncode != 0
    assert "::error::" in r.stdout + r.stderr


@pytest.mark.parametrize("doctype", ["<!doctype html>", "<!DOCTYPE html>"])
def test_guard_accepts_good_file(tmp_path: Path, doctype: str) -> None:
    r = _run(tmp_path, f"{doctype}<html><body>https://jeremyguill.me</body></html>")
    assert r.returncode == 0, r.stdout + r.stderr
