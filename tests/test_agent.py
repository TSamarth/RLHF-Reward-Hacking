"""Regression test: an unexpected exception from tool dispatch (harness-side,
not a model mistake) must be recorded as an `error` transcript event plus a
`trial_end` with `stop_reason == "error"`, then re-raised — never swallowed.

Uses a real, never-started `Sandbox` to trigger a real `RuntimeError` from
`Sandbox.exec` (no mocking, no container needed) and a minimal fake
`Provider` that always returns one `run_bash` tool call.
"""

import json
from pathlib import Path

import pytest

from harness.agent import run_agent
from harness.providers.base import Message, Provider, Response, ToolCall, ToolDef
from harness.sandbox import Sandbox
from harness.transcript import Transcript


class _OneToolCallProvider(Provider):
    name = "fake"
    model_id = "fake"

    def call(self, system: str, messages: list[Message], tools: list[ToolDef]) -> Response:
        return Response(
            text="",
            reasoning=None,
            tool_calls=[ToolCall(id="1", name="run_bash", arguments={"command": "echo hi"})],
            stop_reason="tool_calls",
            input_tokens=0,
            output_tokens=0,
        )


def test_unexpected_dispatch_exception_writes_error_event_and_reraises(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sandbox = Sandbox(workspace)  # never start()ed: Sandbox.exec() raises RuntimeError

    transcript_path = tmp_path / "t.jsonl"

    with (
        pytest.raises(RuntimeError, match="sandbox not started"),
        Transcript(transcript_path) as transcript,
    ):
        run_agent(
            trial_id="t1",
            system="sys",
            user_prompt="go",
            workspace=workspace,
            sandbox=sandbox,
            provider=_OneToolCallProvider(),
            transcript=transcript,
        )

    events = [json.loads(line) for line in transcript_path.read_text(encoding="utf-8").splitlines()]

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "sandbox not started" in error_events[0]["detail"]

    end_events = [e for e in events if e["type"] == "trial_end"]
    assert len(end_events) == 1
    assert end_events[0]["stop_reason"] == "error"
