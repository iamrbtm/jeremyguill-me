from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path("docker/backup.sh").resolve()

FAKES = {
    "psql": "echo 1\n",
    "pg_dump": (
        'for a in "$@"; do case "$a" in --dbname=umami) [ "${FAIL_UMAMI:-0}" = 1 ] && exit 1;; '
        "--file=*) f=${a#--file=};; esac; done\n"
        'for a in "$@"; do case "$a" in --file=*) echo dump > "${a#--file=}";; esac; done\n'
    ),
    "tar": 'echo "$@" >> "$TAR_LOG"\n',
    "find": "exit 0\n",
}


def run_backup(tmp_path: Path, fail_umami: bool):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in FAKES.items():
        f = bindir / name
        f.write_text("#!/bin/sh\n" + body)
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "tar.log"
    env = {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "POSTGRES_PASSWORD": "x",
        "AGE_RECIPIENT_FILE": str(tmp_path / "none"),
        "TAR_LOG": str(log),
        "FAIL_UMAMI": "1" if fail_umami else "0",
        "TMPDIR": str(tmp_path),
    }
    result = subprocess.run(
        ["sh", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30
    )
    return result, log.read_text() if log.exists() else ""


def test_backup_includes_umami_dump_when_it_works(tmp_path):
    result, tar_log = run_backup(tmp_path, fail_umami=False)

    assert result.returncode == 0, result.stderr
    assert "portfolio.dump media.tar umami.dump" in tar_log


def test_failing_umami_dump_does_not_block_portfolio_backup(tmp_path):
    result, tar_log = run_backup(tmp_path, fail_umami=True)

    assert result.returncode == 0, result.stderr
    assert "umami dump failed; skipping" in result.stderr
    assert "portfolio.dump media.tar" in tar_log
    assert "umami.dump" not in tar_log
