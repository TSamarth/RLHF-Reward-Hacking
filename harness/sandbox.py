"""Container lifecycle: start, exec, teardown.

Sealed (--network none), resource-capped, non-root, fresh container per
trial. Mounts a workspace directory rw at /work (read-only is a parameter,
for the held-out-suite phase). No docker-py — subprocess + the container
CLI, argument list only, never shell=True.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Self

from harness.config import CONTAINER_BIN, IMAGE_NAME

EXEC_TIMEOUT_S = 120


class Sandbox:
    """One container. start() -> exec() any number of times -> teardown()."""

    def __init__(self, workspace: Path, *, read_only: bool = False) -> None:
        self.workspace = workspace.resolve()
        self.read_only = read_only
        self.container_id: str | None = None

    def start(self) -> None:
        mount = f"{self.workspace}:/work:{'ro' if self.read_only else 'rw'}"
        cmd = [
            CONTAINER_BIN,
            "run",
            "-d",
            "--network",
            "none",
            "--cpus",
            "2",
            "--memory",
            "2g",
            "-v",
            mount,
            "-w",
            "/work",
            IMAGE_NAME,
            "sleep",
            "infinity",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"failed to start container: {result.stderr}")
        self.container_id = result.stdout.strip()

    def exec(self, command: str, timeout: int = EXEC_TIMEOUT_S) -> tuple[int, str, str]:
        """Run `command` via `sh -c` inside the container. Returns (exit_code, stdout, stderr)."""
        if self.container_id is None:
            raise RuntimeError("sandbox not started")
        cmd = [CONTAINER_BIN, "exec", self.container_id, "sh", "-c", command]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"exec timed out after {timeout}s: {command!r}") from exc
        return result.returncode, result.stdout, result.stderr

    def teardown(self) -> None:
        if self.container_id is None:
            return
        result = subprocess.run(
            [CONTAINER_BIN, "rm", "-f", self.container_id],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"failed to remove container: {result.stderr}")
        self.container_id = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.teardown()


def _smoke_test() -> None:
    """Round-trips an exec in a sealed container. Uses a throwaway workspace."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        with Sandbox(workspace) as sandbox:
            container_id = sandbox.container_id
            code, out, err = sandbox.exec("pytest --version")
            print(f"pytest --version -> exit={code} stdout={out.strip()!r} stderr={err.strip()!r}")
            assert code == 0, f"pytest --version failed: {err}"

            code, out, _ = sandbox.exec("id -u")
            print(f"id -u -> {out.strip()}")
            assert out.strip() != "0", "container is running as root"

            code, out, err = sandbox.exec(
                "python -c \"import socket; socket.setdefaulttimeout(3); "
                "socket.gethostbyname('example.com')\""
            )
            print(f"DNS probe (expect failure) -> exit={code} stderr={err.strip()!r}")
            assert code != 0, "DNS resolution succeeded — network is not sealed"

        print(f"container {container_id} torn down")
        print("sandbox round-trip OK")


if __name__ == "__main__":
    _smoke_test()
