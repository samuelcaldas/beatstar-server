"""Regression coverage for aggregate inventory resource limits."""
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from scripts import inspect_music_assets


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/inspect_music_assets.py"


def run_inventory(root, *arguments):
    """Run the real isolated CLI with bounded process lifetime."""
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(root),
         "--unity-version", "2022.3.50f1", *arguments],
        capture_output=True, text=True, timeout=30,
    )


def test_non_candidate_entries_count_toward_traversal_budget(tmp_path):
    (tmp_path / "one.txt").write_text("one")
    (tmp_path / "two.txt").write_text("two")
    result = run_inventory(tmp_path, "--max-entries", "1")
    assert result.returncode == 2
    assert "directory entry limit" in result.stderr


def test_individually_small_files_cannot_exceed_total_byte_budget(tmp_path):
    (tmp_path / "one.bundle").write_bytes(b"ab")
    (tmp_path / "two.bundle").write_bytes(b"cd")
    result = run_inventory(tmp_path, "--max-total-bytes", "3")
    assert result.returncode == 2
    assert "total byte limit" in result.stderr


def test_expired_inventory_deadline_does_not_start_another_parser(tmp_path):
    source = tmp_path / "expired.bundle"
    source.write_bytes(b"abc")
    arguments = SimpleNamespace(source=tmp_path, timeout=30)
    record = inspect_music_assets.inspect_file(source, arguments, deadline=0)
    assert record["status"] == "error"
    assert record["error"] == "TimeoutError"
    assert record["path"] == "expired.bundle"
