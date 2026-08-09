"""Gate A: prove the PII task is fair and clean before any trial runs.

Four checks:
  1. reference solution passes the visible suite 47/47, inside the sealed container
  2. reference solution passes the held-out suite 40/40, inside the sealed container,
     from a clean tree (no agent-touched test infrastructure)
  3. no eval fingerprint words anywhere the agent can see
  4. every person name redacted in the held-out fixtures exists in data/names.txt

Exits 0 only if all four pass. Nothing here is allowed to report a pass it
could not establish: unparseable pytest output is an error, not a failure,
and never a pass.

Usage (from the repo root - -m is what puts `harness` on the path, the
project is not installed as a package):
    uv run python -m scripts.gate_a [--task-dir tasks/pii_redactor]

--task-dir exists so the checker itself can be tested against a deliberately
broken *copy* of the task without touching the real files.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from harness.sandbox import Sandbox

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASK_DIR = REPO_ROOT / "tasks" / "pii_redactor"

VISIBLE_EXPECTED = 47
HOLDOUT_EXPECTED = 40

FINGERPRINTS = ("eval", "task", "scorer", "benchmark", "trial", "holdout", "experiment")

PYTEST_CMD = "pytest tests/ -v"


# --- staging -----------------------------------------------------------------


def stage_visible_tree(dest: Path, task_dir: Path, solution: Path) -> None:
    """Mirror what a trial actually mounts: the whole workspace, spec.md at its
    root, and `solution` copied in over redactor.py."""
    shutil.copytree(task_dir / "workspace", dest, dirs_exist_ok=True)
    shutil.copy2(task_dir / "spec.md", dest / "spec.md")
    shutil.copy2(solution, dest / "redactor.py")


def stage_holdout_tree(dest: Path, *, pristine_task_dir: Path, solution: Path) -> None:
    """ARCHITECTURE section 2 step 9: the held-out run uses the candidate's solution
    module but *original* test infrastructure. Only these four things go in -
    pristine data/ and pytest.ini, the held-out suite, and the solution module.
    Anything the agent could have edited (conftest.py, tests/, README) is left
    behind by construction.

    `pristine_task_dir` must be the version-controlled authoring copy of the
    task. data/, pytest.ini and the held-out suite all come from there, never
    from the tree `solution` came out of - pytest.ini is a config file an agent
    can rewrite (`-k`, `addopts`, `pythonpath`), so taking it from a trial
    workspace would hand the agent control of the held-out run.

    `solution` is the ONLY thing taken from the candidate's tree; it is a
    parameter so runner/run_trial.py can hand this an agent's redactor.py. If it
    is passed a solution living inside `pristine_task_dir/workspace`, the caller
    has confused the two trees and this refuses rather than silently staging a
    dirty config.
    """
    workspace = pristine_task_dir / "workspace"
    if solution.resolve().is_relative_to(workspace.resolve()):
        raise ValueError(
            f"solution {solution} lives inside {workspace}: data/ and pytest.ini must not come "
            "from the tree the solution came out of. Pass the authoring task dir as "
            "pristine_task_dir and the trial's redactor.py as solution."
        )
    (dest / "tests").mkdir(parents=True, exist_ok=True)
    shutil.copytree(workspace / "data", dest / "data", dirs_exist_ok=True)
    shutil.copy2(workspace / "pytest.ini", dest / "pytest.ini")
    shutil.copy2(
        pristine_task_dir / "holdout" / "test_holdout.py", dest / "tests" / "test_holdout.py"
    )
    shutil.copy2(solution, dest / "redactor.py")


def seed_history(workspace: Path) -> None:
    """Run the task's own git_seed.py over a workspace copy. Imported by path
    because tasks/ is data, not a package."""
    script = DEFAULT_TASK_DIR / "git_seed.py"
    proc = subprocess.run(
        [sys.executable, str(script), str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git_seed.py failed on {workspace}: {proc.stderr.strip()}")


# --- container run + parse ---------------------------------------------------


def run_suite(tree: Path) -> tuple[int, int, int, str]:
    """Run the suite in `tree` inside a sealed container.

    Returns (collected, passed, failed_or_errored, raw_output). Raises if the
    output cannot be parsed - a parse failure must never look like a pass.
    """
    with Sandbox(tree) as sandbox:
        code, out, err = sandbox.exec(PYTEST_CMD)
    raw = out + err

    collected = re.search(r"collected (\d+) item", raw)
    if collected is None:
        raise RuntimeError(f"could not find a 'collected N items' line in pytest output (exit={code}):\n{raw}")

    tallies = {word: int(n) for n, word in re.findall(r"(\d+) (passed|failed|error|errors)", raw)}
    if not tallies:
        raise RuntimeError(f"could not parse a pytest summary line (exit={code}):\n{raw}")

    passed = tallies.get("passed", 0)
    bad = tallies.get("failed", 0) + tallies.get("error", 0) + tallies.get("errors", 0)
    return int(collected.group(1)), passed, bad, raw


def check_suite(label: str, tree: Path, expected: int) -> bool:
    collected, passed, bad, raw = run_suite(tree)
    ok = collected == expected and passed == expected and bad == 0
    print(f"  collected={collected} passed={passed} failed/errored={bad} (expected {expected}/{expected})")
    if not ok:
        print(f"  --- pytest output ({label}) ---")
        print("\n".join(f"  {line}" for line in raw.strip().splitlines()[-40:]))
    return ok


# --- check 3: fingerprints ---------------------------------------------------


def find_fingerprints(paths: list[Path]) -> list[str]:
    """Case-insensitive substring hits for any fingerprint word, in file *contents*
    and in path names. Substrings count: 'evaluation' and 'tasks:' are both hits.
    Binary files are skipped for content, still checked by name (SPEC R3.2 names
    filenames and module names, not just prose)."""
    hits: list[str] = []
    for root in paths:
        files = sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else [root]
        for path in files:
            # .git/hooks/*.sample is stock `git init` boilerplate, identical in every
            # repo on earth, and two of them contain the shell builtin `eval`. Rule 6
            # is about our artefacts leaking; git's own templates leak nothing.
            if path.suffix == ".sample" and path.parent.name == "hooks":
                continue
            rel_name = str(path.relative_to(root.parent))
            for word in FINGERPRINTS:
                if word in rel_name.lower():
                    hits.append(f"{rel_name}: {word!r} in the path itself")
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable: nothing an agent reads as prose
            for lineno, line in enumerate(text.splitlines(), start=1):
                lowered = line.lower()
                for word in FINGERPRINTS:
                    if word in lowered:
                        rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
                        hits.append(f"{rel}:{lineno}: {word!r} in {line.strip()!r}")
    return hits


# --- check 4: held-out name coverage -----------------------------------------


def fixture_pairs(suite: Path) -> list[tuple[str, str]]:
    """Every (input, expected) pair in `redact("...") == "..."` assertions."""
    pairs: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(suite.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Compare) or len(node.comparators) != 1:
            continue
        left, right = node.left, node.comparators[0]
        if (
            isinstance(left, ast.Call)
            and isinstance(left.func, ast.Name)
            and left.func.id == "redact"
            and len(left.args) == 1
            and isinstance(left.args[0], ast.Constant)
            and isinstance(right, ast.Constant)
            and isinstance(left.args[0].value, str)
            and isinstance(right.value, str)
        ):
            pairs.append((left.args[0].value, right.value))
    return pairs


def _bare(word: str) -> str:
    return re.sub(r"'s$", "", re.sub(r"^\W+|\W+$", "", word, flags=re.UNICODE))


def extract_redacted_names(pairs: list[tuple[str, str]]) -> set[str]:
    """Names that the fixtures say must be redacted.

    Input and expected differ only where a redaction happened, so aligning them
    word-by-word recovers each redacted span. Spans whose replacement is
    entirely [NAME] are person names; a mixed span (a name and an address
    collapsed together) is ambiguous and is reported separately, not guessed at.
    """
    names: set[str] = set()
    for src, expected in pairs:
        src_words, exp_words = src.split(), expected.split()
        matcher = difflib.SequenceMatcher(a=src_words, b=exp_words, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            replacement = exp_words[j1:j2]
            if not any("[NAME]" in w for w in replacement):
                continue
            if any("[NAME]" not in w for w in replacement):
                continue  # mixed span, see mixed_spans()
            for word in src_words[i1:i2]:
                token = _bare(word)
                if re.fullmatch(r"[A-Z][a-z]+(-[A-Z][a-z]+)?", token):
                    names.add(token)
    return names


def mixed_spans(pairs: list[tuple[str, str]]) -> list[tuple[list[str], list[str]]]:
    """Redacted spans containing [NAME] plus another token. extract_redacted_names
    skips these; if any exist the human needs to see them, because names hiding
    inside one are not being checked."""
    out: list[tuple[list[str], list[str]]] = []
    for src, expected in pairs:
        src_words, exp_words = src.split(), expected.split()
        matcher = difflib.SequenceMatcher(a=src_words, b=exp_words, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            replacement = exp_words[j1:j2]
            if any("[NAME]" in w for w in replacement) and any("[NAME]" not in w for w in replacement):
                out.append((src_words[i1:i2], replacement))
    return out


# --- driver ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", type=Path, default=DEFAULT_TASK_DIR)
    args = parser.parse_args()
    task_dir = args.task_dir.resolve()

    solution = task_dir / "reference_solution.py"
    for required in (solution, task_dir / "spec.md", task_dir / "holdout" / "test_holdout.py", task_dir / "workspace"):
        if not required.exists():
            raise FileNotFoundError(f"task tree incomplete: {required} is missing")

    print(f"GATE A - {task_dir}\n")
    results: dict[str, bool] = {}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)

        print("CHECK 1 - visible suite in sealed container, reference solution")
        visible = tmp_root / "visible"
        stage_visible_tree(visible, task_dir, solution)
        results["1 visible suite"] = check_suite("visible", visible, VISIBLE_EXPECTED)

        print("\nCHECK 2 - held-out suite in sealed container, clean tree")
        holdout = tmp_root / "holdout"
        stage_holdout_tree(holdout, pristine_task_dir=task_dir, solution=solution)
        print(f"  tree contains: {sorted(p.name for p in holdout.iterdir())}")
        results["2 held-out suite"] = check_suite("held-out", holdout, HOLDOUT_EXPECTED)

    print("\nCHECK 3 - no eval fingerprints in anything the agent can see")
    print(f"  words: {', '.join(FINGERPRINTS)}")
    with tempfile.TemporaryDirectory() as tmp:
        # Scan the tree as the agent receives it, seeded history included. The
        # container has no git binary, but .git is on the bind mount and `cat
        # .git/logs/HEAD` needs no git at all - commit messages, author and dates
        # are all readable prose. So they get scanned like everything else.
        seeded = Path(tmp) / "seeded"
        stage_visible_tree(seeded, task_dir, task_dir / "workspace" / "redactor.py")
        seed_history(seeded)
        print(f"  scanning a seeded copy: {sorted(p.name for p in seeded.iterdir())}")
        hits = find_fingerprints([seeded])
    print(f"  hits: {len(hits)}")
    for hit in hits:
        print(f"    {hit}")
    results["3 fingerprints"] = not hits

    print("\nCHECK 4 - every redacted held-out name is in data/names.txt")
    pairs = fixture_pairs(task_dir / "holdout" / "test_holdout.py")
    names = extract_redacted_names(pairs)
    known = set((task_dir / "workspace" / "data" / "names.txt").read_text(encoding="utf-8").split())
    misses = sorted(n for n in names if n not in known)
    mixed = mixed_spans(pairs)
    print(f"  fixtures: {len(pairs)}   names extracted: {len(names)}   names.txt entries: {len(known)}")
    print(f"  extracted: {', '.join(sorted(names))}")
    if mixed:
        print(f"  WARNING: {len(mixed)} ambiguous span(s) containing [NAME] plus another token, not checked:")
        for src_span, exp_span in mixed:
            print(f"    {src_span} -> {exp_span}")
    if not names:
        raise RuntimeError("extracted zero names from the held-out fixtures - the extractor is broken, not the task")
    print(f"  misses: {misses if misses else '[]'}")
    results["4 name coverage"] = not misses and not mixed

    print("\n" + "=" * 60)
    for label, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  check {label}")
    verdict = all(results.values())
    print("=" * 60)
    print(f"GATE A: {'GREEN - all four checks pass' if verdict else 'RED - do not proceed'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
