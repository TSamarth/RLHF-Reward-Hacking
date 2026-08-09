"""ReAct loop: model -> tool call -> observation -> repeat, until `finish`,
the step cap, or the wall-clock timeout. Every model message, tool call and
tool result is written to the transcript before the next step (SPEC R1.5).
"""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from harness.config import STEP_CAP, WALL_CLOCK_S
from harness.providers.base import Message, Provider
from harness.sandbox import Sandbox
from harness.tools import TOOLS, dispatch
from harness.transcript import Transcript

NUDGE = "Use one of the available tools, or call finish when you are done."


def run_agent(
    *,
    trial_id: str,
    system: str,
    user_prompt: str,
    workspace: Path,
    sandbox: Sandbox,
    provider: Provider,
    transcript: Transcript,
    step_cap: int = STEP_CAP,
    wall_clock_s: float = WALL_CLOCK_S,
) -> str:
    """Runs the loop. Returns the stop reason: "finish" | "step_cap" | "timeout"."""
    transcript.write(trial_id, 0, "trial_start")
    transcript.write(trial_id, 0, "system_prompt", text=system)
    transcript.write(trial_id, 0, "user_prompt", text=user_prompt)

    messages: list[Message] = [Message(role="user", content=user_prompt)]
    start = time.monotonic()
    step = 0

    while step < step_cap:
        if time.monotonic() - start > wall_clock_s:
            transcript.write(trial_id, step, "trial_end", stop_reason="timeout")
            return "timeout"

        try:
            response = provider.call(system, messages, TOOLS)
        except Exception as exc:
            transcript.write(trial_id, step, "error", detail=str(exc))
            transcript.write(trial_id, step, "trial_end", stop_reason="error")
            raise

        transcript.write(
            trial_id,
            step,
            "model_response",
            text=response.text,
            reasoning=response.reasoning,
            tool_calls=[asdict(tc) for tc in response.tool_calls],
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        messages.append(
            Message(
                role="assistant",
                content=response.text,
                reasoning=response.reasoning,
                tool_calls=response.tool_calls,
            )
        )

        if not response.tool_calls:
            # A turn that calls no tool still costs a provider call, so it still costs a
            # step. Counting only tool-calling turns would leave a chatty model bounded
            # by wall clock alone, which is the expensive way to find out.
            step += 1
            messages.append(Message(role="user", content=NUDGE))
            continue

        for tool_call in response.tool_calls:
            step += 1
            try:
                result, exit_code = dispatch(
                    tool_call.name, tool_call.arguments, workspace=workspace, sandbox=sandbox
                )
            except Exception as exc:
                # dispatch() itself already turns model-caused failures (bad path, bad
                # command, tool timeout) into result strings. Getting here means something
                # unexpected broke on the harness side (e.g. Sandbox.exec called before
                # start(), a permission error writing to disk) — that's not the model's
                # mistake to observe, it's ours to record and stop on.
                transcript.write(trial_id, step, "error", detail=str(exc))
                transcript.write(trial_id, step, "trial_end", stop_reason="error")
                raise
            transcript.write(
                trial_id,
                step,
                "tool_result",
                tool=tool_call.name,
                args=tool_call.arguments,
                result=result,
                exit_code=exit_code,
            )
            messages.append(Message(role="tool", tool_name=tool_call.name, content=result))

            if tool_call.name == "finish":
                transcript.write(trial_id, step, "finish", summary=result)
                transcript.write(trial_id, step, "trial_end", stop_reason="finish")
                return "finish"
            if step >= step_cap:
                transcript.write(trial_id, step, "trial_end", stop_reason="step_cap")
                return "step_cap"

    transcript.write(trial_id, step, "trial_end", stop_reason="step_cap")
    return "step_cap"
