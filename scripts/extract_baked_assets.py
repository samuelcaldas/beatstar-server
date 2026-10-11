#!/usr/bin/env python3
"""Offline extraction into a NEW private directory; requires a sandbox and python -I."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import re
import resource
import shutil
import struct
import sys
import tempfile
TARGET_CONFIGS = {"SongConfig", "AssetsConfig", "AudioConfig", "GameConfig", "BeatmapsConfig"}
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 * 1024


def read_exact(stream, length):
    """Read a bounded serialized field, raising ValueError on truncation."""
    if length > MAX_FILE_BYTES:
        raise ValueError("TextAsset exceeds payload limit")
    result = stream.read(length)
    if len(result) != length:
        raise ValueError("Truncated TextAsset")
    return result


def parse_text_asset_payload(raw_data: bytes) -> tuple[str, bytes]:
    """Decode a TextAsset, rejecting truncated data and unsafe filesystem names."""
    stream = io.BytesIO(raw_data)
    name_length = struct.unpack("<I", read_exact(stream, 4))[0]
    name = read_exact(stream, name_length).decode("utf-8")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", name):
        raise ValueError("Unsafe TextAsset name")
    read_exact(stream, -name_length % 4)
    data_length = struct.unpack("<I", read_exact(stream, 4))[0]
    return name, read_exact(stream, data_length)


MAX_SOURCE_ENTRIES = 4096


def validate_source(source: Path, output: Path) -> list[Path]:
    """Validate immutable bounded inputs before creating output directories.

    Entries are counted as they are yielded to avoid materializing an
    unbounded list before the limit can be enforced.  Non-regular files
    (FIFOs, sockets, devices) are rejected before any further inspection.
    """
    if output.exists() or output.is_symlink():
        raise ValueError("Output must be a new directory; existing data is never overwritten")
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Asset source directory is missing or unsafe")

    paths: list[Path] = []
    for count, path in enumerate(source.rglob("*"), start=1):
        if count > MAX_SOURCE_ENTRIES:
            raise ValueError("Source exceeds directory entry limit")
        if path.is_symlink():
            raise ValueError("Symlink inputs are not permitted")
        if path.exists() and not path.is_dir() and not path.is_file():
            raise ValueError("Source contains a non-regular file")
        paths.append(path)

    files = [path for path in paths if path.is_file()]
    if any(path.stat().st_size > MAX_FILE_BYTES for path in files):
        raise ValueError("Source file exceeds size limit")
    if sum(path.stat().st_size for path in files) > MAX_INPUT_BYTES:
        raise ValueError("Source exceeds total size limit")
    if not (source / "bin/Data/data.unity3d").is_file():
        raise ValueError("Missing core Unity archive")
    return sorted((source / "AssetBundles").glob("*.bundle"))


def write_unique(path: Path, payload: bytes) -> None:
    """Write a unique staged artifact; reject collisions instead of silently replacing."""
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise ValueError("Conflicting extracted asset names")
    path.write_bytes(payload)


def text_assets(path):
    """Yield parsed TextAssets; parser failures propagate and abort publication."""
    import UnityPy

    environment = UnityPy.load(str(path))
    for item in environment.objects:
        if item.type.name == "TextAsset":
            yield item


def extract_configs(source, output):
    """Extract required configs, failing if any required config is absent."""
    found = set()
    for item in text_assets(source / "bin/Data/data.unity3d"):
        if item.peek_name() not in TARGET_CONFIGS:
            continue
        name, payload = parse_text_asset_payload(item.get_raw_data())
        write_unique(output / "configs" / f"{name}.bin", payload)
        found.add(name)
    if found != TARGET_CONFIGS:
        raise ValueError("Required baked configuration is missing")
    return len(found)


def extract_bundle(path, output, stats):
    """Copy one bundle and extract candidate charts/banks without asserting linkage."""
    shutil.copyfile(path, output / "bundles" / path.name)
    stats["bundles"] += 1
    for item in text_assets(path):
        name, payload = parse_text_asset_payload(item.get_raw_data())
        if payload.startswith(b"BKHD"):
            write_unique(output / "extracted" / f"{name}.bnk.bytes", payload)
            stats["audio_banks"] += 1
            continue
        if len(payload) > 4 and payload[0] == 8:
            write_unique(output / "extracted" / f"{name}.chart.bytes", payload)
            stats["charts"] += 1


def stage_extraction(source, output, bundles):
    """Build a private inventory; all candidate metadata remains unverified natively."""
    for name in ("configs", "bundles", "extracted", "catalog"):
        (output / name).mkdir()
    stats = {"configs": extract_configs(source, output), "bundles": 0, "charts": 0, "audio_banks": 0}
    for path in bundles:
        extract_bundle(path, output, stats)
    catalog = {"client_version": "36.1.4.9545", "unity_version": "2022.3.50f1",
               "android_compatible": False, "counts": stats}
    (output / "catalog/asset_catalog.json").write_text(json.dumps(catalog, indent=2))
    return stats


def extract_assets(assets_dir: Path, output_dir: Path) -> dict[str, int]:
    """Stage validated extraction and atomically create a new output; never overwrite."""
    import UnityPy

    bundles = validate_source(assets_dir, output_dir)
    UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.50f1"
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".extract-", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "result"
        staging.mkdir()
        stats = stage_extraction(assets_dir, staging, bundles)
        if output_dir.exists():
            raise ValueError("Output appeared during extraction")
        staging.rename(output_dir)
    return stats


def main() -> None:
    """Run a resource-limited offline extractor in an operator-provided sandbox."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = parser.parse_args()
    if not sys.flags.isolated:
        parser.error("Run with python -I inside the documented sandbox")
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
    print(json.dumps(extract_assets(arguments.assets_dir, arguments.output_dir)))


if __name__ == "__main__":
    main()
