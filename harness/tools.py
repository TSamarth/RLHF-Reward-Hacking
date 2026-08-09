"""Tool definitions and dispatch. `list_dir`/`read_file`/`write_file` operate
on the host-side workspace directory (the same directory the sandbox mounts
at /work); `run_bash`/`run_tests` go through `Sandbox.exec`.

All paths are relative to the workspace root and validated to prevent
escape. A bad path is a model mistake, not a harness failure — it comes back
as an error string in the tool result, never an exception.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness.providers.base import ToolDef
from harness.sandbox import Sandbox

MAX_READ_LINES = 2000

TOOLS: list[ToolDef] = [
    ToolDef(
        name="list_dir",
        description=(
            "List the contents of a directory, tree-style. Path is relative "
            "to the workspace root; defaults to the root itself."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to the workspace root."}
            },
            "required": [],
        },
    ),
    ToolDef(
        name="read_file",
        description="Read a file's contents. Path is relative to the workspace root.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the workspace root."}
            },
            "required": ["path"],
        },
    ),
    ToolDef(
        name="write_file",
        description=(
            "Write content to a file at the given path, relative to the "
            "workspace root. Creates parent directories as needed and "
            "overwrites any existing content."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the workspace root."},
                "content": {"type": "string", "description": "Full content to write."},
            },
            "required": ["path", "content"],
        },
    ),
    ToolDef(
        name="run_bash",
        description="Run a shell command in the workspace and return its exit code, stdout and stderr.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Shell command to run."}},
            "required": ["command"],
        },
    ),
    ToolDef(
        name="run_tests",
        description="Run the test suite and return the raw output.",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolDef(
        name="finish",
        description="Call this when you are done. Ends the session.",
        parameters={
            "type": "object",
            "properties": {"summary": {"type": "string", "description": "Short summary of what you did."}},
            "required": ["summary"],
        },
    ),
]


class PathEscapeError(Exception):
    pass


def _resolve_in_workspace(workspace: Path, path: str) -> Path:
    """Resolve `path` against `workspace` and require the result stays
    inside it. Rejects absolute paths, `..` escapes and symlinks that point
    outside — all raise `PathEscapeError`."""
    if Path(path).is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {path!r}")
    root = workspace.resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise PathEscapeError(f"path escapes the workspace: {path!r}") from None
    return candidate


def _list_dir(workspace: Path, path: str) -> str:
    try:
        root = _resolve_in_workspace(workspace, path)
    except PathEscapeError as exc:
        return f"error: {exc}"
    if not root.exists():
        return f"error: path not found: {path}"
    if not root.is_dir():
        return f"error: not a directory: {path}"

    lines: list[str] = []

    def walk(d: Path, prefix: str) -> None:
        for entry in sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name)):
            lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                walk(entry, prefix + "  ")

    walk(root, "")
    return "\n".join(lines) if lines else "(empty)"


def _read_file(workspace: Path, path: str) -> str:
    try:
        target = _resolve_in_workspace(workspace, path)
    except PathEscapeError as exc:
        return f"error: {exc}"
    if not target.exists():
        return f"error: file not found: {path}"
    if not target.is_file():
        return f"error: not a file: {path}"

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > MAX_READ_LINES:
        head = "\n".join(lines[:MAX_READ_LINES])
        return f"{head}\n... [truncated: file has {len(lines)} lines, showing first {MAX_READ_LINES}]"
    return "\n".join(lines)


def _write_file(workspace: Path, path: str, content: str) -> str:
    try:
        target = _resolve_in_workspace(workspace, path)
    except PathEscapeError as exc:
        return f"error: {exc}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {path}"


def _run_bash(sandbox: Sandbox, command: str) -> tuple[str, int | None]:
    try:
        code, out, err = sandbox.exec(command)
    except TimeoutError as exc:
        return f"error: {exc}", None
    return f"exit_code: {code}\nstdout:\n{out}\nstderr:\n{err}", code


def _run_tests(sandbox: Sandbox) -> tuple[str, int | None]:
    return _run_bash(sandbox, "pytest tests/ -v")


def _handle_list_dir(args: dict[str, Any], workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    return _list_dir(workspace, args.get("path", ".")), None


def _handle_read_file(args: dict[str, Any], workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    if "path" not in args:
        return "error: missing required argument 'path'", None
    return _read_file(workspace, args["path"]), None


def _handle_write_file(args: dict[str, Any], workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    missing = [k for k in ("path", "content") if k not in args]
    if missing:
        return f"error: missing required argument(s): {', '.join(missing)}", None
    return _write_file(workspace, args["path"], args["content"]), None


def _handle_run_bash(args: dict[str, Any], workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    if "command" not in args:
        return "error: missing required argument 'command'", None
    return _run_bash(sandbox, args["command"])


def _handle_run_tests(args: dict[str, Any], workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    return _run_tests(sandbox)


def _handle_finish(args: dict[str, Any], workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    if "summary" not in args:
        return "error: missing required argument 'summary'", None
    return args["summary"], None


_HANDLERS: dict[str, Callable[[dict[str, Any], Path, Sandbox], tuple[str, int | None]]] = {
    "list_dir": _handle_list_dir,
    "read_file": _handle_read_file,
    "write_file": _handle_write_file,
    "run_bash": _handle_run_bash,
    "run_tests": _handle_run_tests,
    "finish": _handle_finish,
}


def dispatch(name: str, args: dict[str, Any], *, workspace: Path, sandbox: Sandbox) -> tuple[str, int | None]:
    """Runs a tool call. Returns (result_text, exit_code). exit_code is None
    for tools that don't have one."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"error: unknown tool {name!r}", None
    return handler(args, workspace, sandbox)
