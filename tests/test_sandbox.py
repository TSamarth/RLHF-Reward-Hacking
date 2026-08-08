"""One runnable check: the sandbox seals, runs as non-root, and enforces the
per-exec timeout. Requires a built redactor-sandbox:latest image and a
working container binary — skips if either is unavailable.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from harness.config import CONTAINER_BIN
from harness.sandbox import Sandbox

pytestmark = pytest.mark.skipif(
    shutil.which(CONTAINER_BIN) is None,
    reason=f"{CONTAINER_BIN} not on PATH",
)


def test_sandbox_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        with Sandbox(workspace) as sandbox:
            container_id = sandbox.container_id

            # non-root
            code, out, _ = sandbox.exec("id -u")
            assert code == 0
            assert out.strip() != "0"

            # host sees a file the container writes into the mount
            code, _, err = sandbox.exec("echo hi > /work/probe.txt")
            assert code == 0, err
            assert (workspace / "probe.txt").read_text().strip() == "hi"

            # network is sealed
            code, _, _ = sandbox.exec(
                "python -c \"import socket; socket.setdefaulttimeout(3); "
                "socket.gethostbyname('example.com')\""
            )
            assert code != 0

            # per-exec timeout is enforced
            with pytest.raises(TimeoutError):
                sandbox.exec("sleep 5", timeout=1)

            # sanity: the filter finds the container while it's still alive
            # (otherwise the post-teardown "finds nothing" check below is vacuous)
            result = subprocess.run(
                [CONTAINER_BIN, "ps", "-a", "--filter", f"id={container_id}", "--format", "{{.ID}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.stdout.strip() != ""

        # teardown removed the container
        result = subprocess.run(
            [CONTAINER_BIN, "ps", "-a", "--filter", f"id={container_id}", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stdout.strip() == ""
