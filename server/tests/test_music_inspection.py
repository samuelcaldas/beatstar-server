"""Exercise the inventory CLI without proprietary fixtures or host data."""
import json
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/inspect_music_assets.py"


def run_inventory(root, *arguments):
    """Run the isolated CLI and return its captured process result."""
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(root),
         "--unity-version", "2022.3.50f1", *arguments],
        capture_output=True, text=True, timeout=30,
    )


def test_empty_inventory_is_not_evidence_of_compatibility(tmp_path):
    result = run_inventory(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["files"] == []
    assert report["android_compatible"] is False
    assert report["schema_version"] == 1


def test_missing_source_directory_is_rejected(tmp_path):
    result = run_inventory(tmp_path / "missing")
    assert result.returncode == 2
    assert "source must be a real directory" in result.stderr


def test_symlinked_bundle_cannot_escape_inventory_root(tmp_path):
    source = tmp_path / "assets"
    source.mkdir()
    outside = tmp_path / "outside.bundle"
    outside.write_bytes(b"private")
    (source / "escape.bundle").symlink_to(outside)
    result = run_inventory(source)
    assert result.returncode == 2
    assert "symlink" in result.stderr
    assert "private" not in result.stdout


def test_inventory_rejects_oversized_file_before_parsing(tmp_path):
    (tmp_path / "large.bundle").write_bytes(b"a" * 1025)
    result = run_inventory(tmp_path, "--max-file-bytes", "1024")
    assert result.returncode == 2
    assert "size limit" in result.stderr


def test_inventory_bounds_file_count(tmp_path):
    (tmp_path / "one.bundle").write_bytes(b"a")
    (tmp_path / "two.bundle").write_bytes(b"b")
    result = run_inventory(tmp_path, "--max-files", "1")
    assert result.returncode == 2
    assert "file count" in result.stderr


def test_invalid_bundle_is_fingerprinted_but_not_verified(tmp_path):
    source = tmp_path / "invalid.bundle"
    source.write_bytes(b"abc")
    result = run_inventory(tmp_path)
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    record = report["files"][0]
    assert record["path"] == "invalid.bundle"
    assert record["bytes"] == 3
    assert record["sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert record["status"] == "error"
    assert report["android_compatible"] is False
    assert source.read_bytes() == b"abc"
