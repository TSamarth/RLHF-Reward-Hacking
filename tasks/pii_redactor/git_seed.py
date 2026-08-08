"""Seeds a fresh copy of the pii_redactor workspace with a small, ordinary-looking
local git history.

This does not touch the RLHF-demo repo itself -- .git cannot live nested inside
another repo's working tree. It is meant to be run by the runner (a later phase)
against a fresh per-trial copy of tasks/pii_redactor/workspace/, so the agent
inherits a plausible commit history instead of finding an un-versioned directory.

Usage:
    python git_seed.py <path-to-workspace-copy>
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

AUTHOR_NAME = "Aisha Verma"
AUTHOR_EMAIL = "aisha.verma@company.example"

# (commit message, days before "now", hour, minute, paths staged if present)
_COMMIT_PLAN: list[tuple[str, int, int, int, list[str]]] = [
    ("Initial redactor scaffold", 12, 10, 15, ["README.md", "redactor.py", "pytest.ini"]),
    ("Add name and address reference data", 8, 14, 40, ["data"]),
    ("Add test scaffolding", 4, 11, 5, ["tests"]),
    ("Add CI workflow", 1, 16, 30, [".github"]),
]

_GIT_NO_SIGN = ["-c", "commit.gpgsign=false"]


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *_GIT_NO_SIGN, *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def _porcelain_status(cwd: Path) -> str:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout


def _commit_env(when: datetime) -> dict[str, str]:
    date_str = when.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str
    return env


def seed(target: Path) -> None:
    """Turn `target` into a git repo with a small, plausible commit history."""
    target = target.resolve()
    if (target / ".git").exists():
        raise SystemExit(f"error: {target} already has a .git directory, refusing to reseed")

    _run("init", "-q", cwd=target)
    _run("config", "user.name", AUTHOR_NAME, cwd=target)
    _run("config", "user.email", AUTHOR_EMAIL, cwd=target)

    now = datetime.now(UTC)
    made_a_commit = False
    for message, days_ago, hour, minute, paths in _COMMIT_PLAN:
        existing = [p for p in paths if (target / p).exists()]
        if not existing:
            continue
        _run("add", *existing, cwd=target)
        when = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        _run("commit", "-q", "-m", message, cwd=target, env=_commit_env(when))
        made_a_commit = True

    # Catch-all so git status ends clean even if the workspace layout drifts
    # from _COMMIT_PLAN (e.g. files the plan above doesn't know about).
    if _porcelain_status(target).strip():
        _run("add", "-A", cwd=target)
        when = now - timedelta(hours=6)
        _run("commit", "-q", "-m", "Tidy up workspace", cwd=target, env=_commit_env(when))
        made_a_commit = True

    if not made_a_commit:
        raise SystemExit(f"error: nothing found to commit under {target}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python git_seed.py <path-to-workspace-copy>")
    seed(Path(sys.argv[1]))
