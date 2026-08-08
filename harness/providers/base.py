"""Shared provider interface. Anthropic and Gemini adapters (later phases)
implement `Provider` against these same dataclasses without changing this
file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolDef:
    """A tool exposed to the model, normalised into a JSON Schema shape
    every provider's native tool-calling API can consume."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object


@dataclass
class ToolCall:
    """A tool invocation the model asked for."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """One turn in the conversation sent back to the provider. `system` is
    passed separately to `Provider.call` and is not a `Message`."""

    role: Literal["user", "assistant", "tool"]
    content: str = ""
    reasoning: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_name: str | None = None  # set when role == "tool": which tool this result is for


@dataclass
class Response:
    """A normalised model turn. `stop_reason` is the provider's own reason
    the turn ended (e.g. "stop", "tool_calls", "length") — not the agent
    loop's trial-level stop reason."""

    text: str
    reasoning: str | None
    tool_calls: list[ToolCall]
    stop_reason: str
    input_tokens: int
    output_tokens: int


class Provider(ABC):
    name: str
    model_id: str

    @abstractmethod
    def call(
        self,
        system: str,
        messages: list[Message],
        tools: list[ToolDef],
    ) -> Response: ...
