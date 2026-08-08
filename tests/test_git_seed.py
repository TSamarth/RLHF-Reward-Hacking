"""One runnable check for tasks/pii_redactor/git_seed.py: seeding a workspace
copy produces a clean, non-empty commit history, and reseeding an already-seeded
copy refuses loudly instead of silently doing something to it.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tasks" / "pii_redactor"))

import pytest
from git_seed import seed

WORKSPACE = Path(__file__).resolve().parent.parent / "tasks" / "pii_redactor" / "workspace"


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout


def test_seed_produces_clean_history_and_refuses_to_reseed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "workspace"
        shutil.copytree(WORKSPACE, copy)

        seed(copy)

        # 3-4 plausible commits, working tree clean afterward.
        log = _git("log", "--pretty=%s", cwd=copy)
        commits = [line for line in log.splitlines() if line.strip()]
        assert 3 <= len(commits) <= 4, commits
        assert _git("status", "--porcelain", cwd=copy).strip() == ""

        # Idempotent-safe: refuses loudly rather than reseeding on top.
        with pytest.raises(SystemExit, match="already has a .git directory"):
            seed(copy)
