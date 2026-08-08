"""Throwaway smoke test: run the ReAct loop end to end against the live
Ollama host, on a toy task (fix a bug so a failing test passes). Not the PII
task — no runner, no conditions. Proves harness/agent.py, tools.py,
transcript.py and providers/ollama.py work together.

Usage:
    uv run python scripts/smoke_agent.py [--step-cap N] [--wall-clock-s S]
"""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path

from harness.agent import run_agent
from harness.config import STEP_CAP, WALL_CLOCK_S
from harness.providers.ollama import OllamaProvider
from harness.sandbox import Sandbox
from harness.transcript import Transcript

SYSTEM_PROMPT = (
    "You are a software engineer working in a Python repository. You have "
    "tools to read and write files, run shell commands, and run the test "
    "suite.\n\nWork through the task, then call finish() with a short "
    "summary of what you did."
)
USER_PROMPT = (
    "There is a bug in add.py that makes tests/test_add.py fail. "
    "Fix the bug so the test passes, then finish."
)

TOY_MODULE = "def add(a, b):\n    return a - b  # bug: should add, not subtract\n"
TOY_TEST = "from add import add\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n"


def _build_workspace(root: Path) -> None:
    (root / "tests").mkdir(parents=True)
    (root / "add.py").write_text(TOY_MODULE)
    (root / "tests" / "test_add.py").write_text(TOY_TEST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step-cap", type=int, default=STEP_CAP)
    parser.add_argument("--wall-clock-s", type=float, default=WALL_CLOCK_S)
    args = parser.parse_args()

    trial_id = f"smoke-{uuid.uuid4().hex[:8]}"
    workspace = Path("runs") / trial_id / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    _build_workspace(workspace)

    transcript_path = Path("results") / "transcripts" / f"{trial_id}.jsonl"
    provider = OllamaProvider()

    with Sandbox(workspace) as sandbox, Transcript(transcript_path) as transcript:
        stop_reason = run_agent(
            trial_id=trial_id,
            system=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
            workspace=workspace,
            sandbox=sandbox,
            provider=provider,
            transcript=transcript,
            step_cap=args.step_cap,
            wall_clock_s=args.wall_clock_s,
        )

    print(f"trial_id: {trial_id}")
    print(f"stop_reason: {stop_reason}")
    print(f"transcript: {transcript_path}")

    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["type"] == "finish":
            print(f"finish summary: {event['summary']}")


if __name__ == "__main__":
    main()
