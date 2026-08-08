"""Path containment is the load-bearing logic in tools.py — a bug here lets
the agent out of the workspace. No mocking, no fixture framework: just the
functions against a real tmp_path.
"""

from pathlib import Path

from harness.tools import MAX_READ_LINES, _read_file, _write_file


def test_read_file_rejects_dotdot_escape(tmp_path: Path) -> None:
    result = _read_file(tmp_path, "../outside.txt")
    assert result.startswith("error:")
    assert "escapes" in result


def test_write_file_rejects_dotdot_escape(tmp_path: Path) -> None:
    result = _write_file(tmp_path, "../outside.txt", "pwned")
    assert result.startswith("error:")
    assert not (tmp_path.parent / "outside.txt").exists()


def test_read_file_rejects_absolute_path(tmp_path: Path) -> None:
    result = _read_file(tmp_path, "/etc/passwd")
    assert result.startswith("error:")


def test_write_file_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "symlink_target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape_link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        return  # symlinks need elevated privileges on some Windows setups
    result = _write_file(tmp_path, "escape_link/pwned.txt", "pwned")
    assert result.startswith("error:")
    assert not (outside / "pwned.txt").exists()


def test_write_file_allowed_under_tests_dir(tmp_path: Path) -> None:
    result = _write_file(tmp_path, "tests/test_new.py", "def test_x(): assert True")
    assert result.startswith("wrote")
    assert (tmp_path / "tests" / "test_new.py").read_text() == "def test_x(): assert True"


def test_read_file_truncates_over_limit(tmp_path: Path) -> None:
    content = "\n".join(f"line{i}" for i in range(MAX_READ_LINES + 100))
    (tmp_path / "big.txt").write_text(content)
    result = _read_file(tmp_path, "big.txt")
    assert "truncated" in result
    assert len(result.splitlines()) == MAX_READ_LINES + 1  # +1 for the truncation notice


def test_read_file_under_limit_not_truncated(tmp_path: Path) -> None:
    content = "\n".join(f"line{i}" for i in range(10))
    (tmp_path / "small.txt").write_text(content)
    result = _read_file(tmp_path, "small.txt")
    assert "truncated" not in result
    assert result == content
