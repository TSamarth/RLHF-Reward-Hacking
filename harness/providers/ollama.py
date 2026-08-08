"""Ollama adapter: native `/api/chat` tool-calling, no `stream`.

Schema verified empirically against the live host and cross-checked against
https://docs.ollama.com/capabilities/tool-calling at implementation time
(2026-08-09). See task-2-report.md for the discrepancy notes.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from harness.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT_S, TEMPERATURE
from harness.providers.base import Message, Provider, Response, ToolCall, ToolDef


def _to_message_dict(msg: Message) -> dict[str, Any]:
    if msg.role == "tool":
        return {"role": "tool", "tool_name": msg.tool_name, "content": msg.content}
    d: dict[str, Any] = {"role": msg.role, "content": msg.content}
    if msg.reasoning:
        d["thinking"] = msg.reasoning
    if msg.tool_calls:
        d["tool_calls"] = [
            {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in msg.tool_calls
        ]
    return d


def _to_tool_dict(tool: ToolDef) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def _parse_tool_call(raw: dict[str, Any]) -> ToolCall:
    fn = raw["function"]
    arguments = fn.get("arguments", {})
    if isinstance(arguments, str):
        # Docs note this varies by version — some builds send a JSON string.
        arguments = json.loads(arguments) if arguments else {}
    return ToolCall(id=raw.get("id", ""), name=fn["name"], arguments=arguments)


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(
        self,
        model_id: str = OLLAMA_MODEL,
        *,
        host: str = OLLAMA_HOST,
        timeout_s: float = OLLAMA_TIMEOUT_S,
    ) -> None:
        self.model_id = model_id
        self._host = host
        self._timeout_s = timeout_s

    def call(self, system: str, messages: list[Message], tools: list[ToolDef]) -> Response:
        payload = {
            "model": self.model_id,
            "stream": False,
            "options": {"temperature": TEMPERATURE},
            "messages": [
                {"role": "system", "content": system},
                *(_to_message_dict(m) for m in messages),
            ],
            "tools": [_to_tool_dict(t) for t in tools],
        }
        try:
            resp = httpx.post(f"{self._host}/api/chat", json=payload, timeout=self._timeout_s)
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama request to {self._host} failed: {exc}") from exc

        message = body.get("message")
        if message is None:
            raise RuntimeError(f"Ollama response missing 'message': {body}")

        tool_calls = [_parse_tool_call(tc) for tc in message.get("tool_calls") or []]
        return Response(
            text=message.get("content") or "",
            reasoning=message.get("thinking") or None,
            tool_calls=tool_calls,
            stop_reason=body.get("done_reason", "unknown"),
            input_tokens=body.get("prompt_eval_count", 0),
            output_tokens=body.get("eval_count", 0),
        )
