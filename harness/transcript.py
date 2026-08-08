"""Append-only JSONL transcript writer. One event per line, flushed and
fsynced immediately — a crashed trial must leave every completed event
readable, not buffered until close.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

EVENT_TYPES = frozenset(
    {
        "trial_start",
        "system_prompt",
        "user_prompt",
        "model_response",
        "tool_result",
        "finish",
        "trial_end",
        "error",
    }
)


class Transcript:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")

    def write(self, trial_id: str, step: int, event_type: str, **fields: Any) -> None:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown transcript event type: {event_type!r}")
        event = {
            "ts": datetime.now(UTC).isoformat(),
            "trial_id": trial_id,
            "step": step,
            "type": event_type,
            **fields,
        }
        self._fh.write(json.dumps(event) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
