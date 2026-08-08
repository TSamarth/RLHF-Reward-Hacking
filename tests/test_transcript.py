"""The transcript is the source of truth for every trial — a crashed run
must leave a readable partial file. No mocking: real file I/O against tmp_path.
"""

import json
from pathlib import Path

import pytest

from harness.transcript import Transcript


def test_write_appends_one_json_line_per_event(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    with Transcript(path) as t:
        t.write("trial-1", 0, "trial_start")
        t.write("trial-1", 1, "tool_result", tool="run_bash", args={}, result="ok", exit_code=0)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    events = [json.loads(line) for line in lines]
    assert events[0]["type"] == "trial_start"
    assert events[1]["type"] == "tool_result"
    assert events[1]["exit_code"] == 0
    assert all({"ts", "trial_id", "step", "type"} <= e.keys() for e in events)


def test_write_rejects_unknown_event_type(tmp_path: Path) -> None:
    with Transcript(tmp_path / "t.jsonl") as t, pytest.raises(ValueError):
        t.write("trial-1", 0, "not_a_real_event")


def test_partial_transcript_is_readable_line_by_line(tmp_path: Path) -> None:
    """Simulates a crash mid-run: never call close(), just write and drop
    the handle. Every line written so far must still parse as JSON."""
    path = tmp_path / "t.jsonl"
    t = Transcript(path)
    t.write("trial-1", 0, "trial_start")
    t.write("trial-1", 0, "system_prompt", text="be helpful")
    # no close() / __exit__ — mimics an abrupt kill after the flush+fsync

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # raises if not valid JSON
