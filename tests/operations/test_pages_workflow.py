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
    assert re.search(r"^name: Build and publish one-page site$", text, re.M)
    on_block = re.search(r"^on:\n((?:[ \t]+.*\n|\n)+)", text, re.M)
    assert on_block is not None
    body = on_block.group(1)
    top_keys = re.findall(r"^  (\w+):", body, re.M)
    assert top_keys == ["push", "schedule", "workflow_dispatch"]
    assert re.search(r"branches: \[main\]|branches:\n\s+- main", body)
    assert "paths" not in body
    assert re.findall(r"cron: (.+)", body) == ['"23 */6 * * *"']
    assert re.search(r"^  workflow_dispatch:\s*$", body, re.M)
    assert "inputs" not in body


def test_timeout_and_setup_uv_pinned(text: str) -> None:
    m = re.search(r"timeout-minutes: (\d+)", text)
    assert m and int(m.group(1)) <= 15
    assert re.search(r"uses: astral-sh/setup-uv@v\d+$", text, re.M)
    assert 'python-version: "3.14"' in text


def test_build_steps(text: str) -> None:
    assert "uv sync --frozen --no-dev" in text
    assert "run: sh scripts/ci_build_one_page.sh" in text
    build = re.search(r"- name: Build one-page site\n\s+id: build\n", text)
    assert build is not None
    # Every publish step is skipped when the build reported production not ready.
    for name in ("Check one-page build", "Checkout Pages repo", "Copy index.html only",
                 "Commit and push"):
        block = re.search(rf"- name: {name}\n((?:\s{{8}}.*\n)+)", text)
        assert block and "if: steps.build.outputs.skip != 'true'" in block.group(1), name
    order = [text.index(x) for x in ("scripts/ci_build_one_page.sh", "scripts/check_one_page.sh",
                                     "Checkout Pages repo")]
    assert order == sorted(order)


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


def test_first_checkout_does_not_persist_credentials(text: str) -> None:
    first = text.split("Checkout Pages repo")[0]
    assert "persist-credentials: false" in first


def test_actions_pinned_to_major(text: str) -> None:
    uses = re.findall(r"uses: (\S+)", text)
    assert uses and all(re.fullmatch(r"[\w./-]+@v\d+", u) for u in uses)
    assert uses.count("actions/checkout@v4") == 2


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


def test_publish_job_only_runs_on_main(text: str) -> None:
    assert re.search(
        r"^  publish:\n(?:    #.*\n)*    if: github\.ref == 'refs/heads/main'\n", text, re.M
    )


def test_workflow_uses_guard_script(text: str) -> None:
    assert "sh scripts/check_one_page.sh" in text


CI_BUILD = ROOT / "scripts" / "ci_build_one_page.sh"


def _run_ci(tmp_path: Path, code: int) -> tuple[subprocess.CompletedProcess[str], str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(f"#!/bin/sh\necho fake-uv \"$@\"\nexit {code}\n", encoding="utf-8")
    fake.chmod(0o755)
    out = tmp_path / "gh_output"
    out.write_text("", encoding="utf-8")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "GITHUB_OUTPUT": str(out)}
    r = subprocess.run(
        ["sh", str(CI_BUILD)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    return r, out.read_text(encoding="utf-8")


def test_ci_build_script_is_executable_posix_sh() -> None:
    assert CI_BUILD.stat().st_mode & 0o111
    assert CI_BUILD.read_text(encoding="utf-8").splitlines()[0] == "#!/bin/sh"


def test_ci_build_success(tmp_path: Path) -> None:
    r, out = _run_ci(tmp_path, 0)
    assert r.returncode == 0
    assert "skip=true" not in out
    assert "run python scripts/build_one_page.py --output one_page/index.html" in r.stdout


def test_ci_build_exit_3_skips_quietly(tmp_path: Path) -> None:
    r, out = _run_ci(tmp_path, 3)
    assert r.returncode == 0
    assert "skip=true" in out
    assert "::notice::" in r.stdout


@pytest.mark.parametrize("code", [1, 2, 7])
def test_ci_build_other_failures_propagate(tmp_path: Path, code: int) -> None:
    r, out = _run_ci(tmp_path, code)
    assert r.returncode == code
    assert "skip=true" not in out


def _run(tmp_path: Path, content: str | None) -> subprocess.CompletedProcess[str]:
    if content is not None:
        (tmp_path / "one_page").mkdir()
        (tmp_path / "one_page" / "index.html").write_text(content, encoding="utf-8")
    return subprocess.run(
        ["sh", str(GUARD)], cwd=tmp_path, capture_output=True, text=True, check=False
    )


def _good_page(doctype: str = "<!doctype html>") -> str:
    return (
        f"{doctype}<html><head>"
        "<!-- generated by scripts/build_one_page.py from https://jeremyguill.me/x"
        " -->"
        '<link rel="canonical" href="https://jeremyguill.me/">'
        "</head><body>https://jeremyguill.me</body></html>"
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


@pytest.mark.parametrize("bad", ["localhost:8000", "127.0.0.1", "0.0.0.0"])
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
    r = _run(tmp_path, _good_page(doctype))
    assert r.returncode == 0, r.stdout + r.stderr


def test_guard_rejects_wrong_origin_page(tmp_path: Path) -> None:
    page = _good_page().replace("https://jeremyguill.me/", "https://example.test/")
    r = _run(tmp_path, page)
    assert r.returncode != 0
    assert "::error::" in r.stdout + r.stderr


def test_guard_rejects_missing_generator_comment(tmp_path: Path) -> None:
    r = _run(tmp_path, _good_page().replace("generated by scripts/build_one_page.py", "hand made"))
    assert r.returncode != 0
    assert "::error::" in r.stdout + r.stderr


def test_guard_rejects_symlink(tmp_path: Path) -> None:
    (tmp_path / "one_page").mkdir()
    real = tmp_path / "real.html"
    real.write_text(_good_page(), encoding="utf-8")
    (tmp_path / "one_page" / "index.html").symlink_to(real)
    r = _run(tmp_path, None)
    assert r.returncode != 0
    assert "::error::" in r.stdout + r.stderr
