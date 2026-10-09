"""Read-only Unity asset inventory; run with python -I in a sandbox container."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_FILES = 512
WORKER_MEMORY_BYTES = 1024 * 1024 * 1024
WORKER_CPU_SECONDS = 25


def positive_integer(value):
    """Parse a positive CLI limit, raising ArgumentTypeError for invalid limits."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("limit must be positive")
    return number


def parse_arguments():
    """Parse source/version and resource limits without loading asset data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--unity-version", required=True)
    parser.add_argument("--max-file-bytes", type=positive_integer, default=MAX_FILE_BYTES)
    parser.add_argument("--max-files", type=positive_integer, default=MAX_FILES)
    parser.add_argument("--timeout", type=positive_integer, default=30)
    parser.add_argument("--max-entries", type=positive_integer, default=4096)
    parser.add_argument("--max-total-bytes", type=positive_integer, default=512 * 1024 * 1024)
    parser.add_argument("--max-parser-seconds", type=positive_integer, default=600)
    parser.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if not sys.flags.isolated:
        parser.error("use python -I to exclude untrusted import paths")
    return parser, arguments


def validate_path(path, arguments):
    """Reject links, nonregular files and oversize inputs before hashing/parsing."""
    if path.is_symlink():
        raise ValueError("symlink inputs are not permitted")
    if not path.is_file():
        raise ValueError("input must be a regular file")
    if path.stat().st_size > arguments.max_file_bytes:
        raise ValueError("input exceeds file size limit")


def discover_files(arguments):
    """Return bounded bundle/core paths, rejecting symlinks; raise ValueError."""
    root = arguments.source
    if root.is_symlink() or not root.is_dir():
        raise ValueError("source must be a real directory, not a symlink")
    files = []
    for count, path in enumerate(root.rglob("*"), start=1):
        if count > arguments.max_entries:
            raise ValueError("input exceeds directory entry limit")
        if path.is_symlink():
            raise ValueError("symlink inputs are not permitted")
        if path.suffix == ".bundle" or path.name == "data.unity3d":
            validate_path(path, arguments)
            files.append(path)
        if len(files) > arguments.max_files:
            raise ValueError("input exceeds file count limit")
    if sum(path.stat().st_size for path in files) > arguments.max_total_bytes:
        raise ValueError("input exceeds total byte limit")
    return sorted(files)


def fingerprint(path, root):
    """Return relative path, length and SHA-256 without changing source bytes."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
            "sha256": digest}


def text_asset_metadata(item):
    """Describe a TextAsset without exporting its proprietary payload."""
    data = item.read_typetree()
    content = data["m_Script"]
    if isinstance(content, str):
        content = content.encode("utf-8", errors="surrogateescape")
    payload = bytes(content)
    return {"name": data.get("m_Name"), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "wwise_bkhd": payload.startswith(b"BKHD")}


def object_metadata(item):
    """Read type information and return metadata only for text assets."""
    if item.type.name == "TextAsset":
        return [text_asset_metadata(item)]
    item.read_typetree()
    return []


def inspect_object(item, errors):
    """Record recoverable type-tree failures without claiming a complete decode."""
    try:
        return object_metadata(item)
    except (ValueError, TypeError, KeyError, EOFError, NotImplementedError) as error:
        errors[type(error).__name__] += 1
        return []


def summarize_objects(environment):
    """Report types and text metadata, explicitly counting unreadable type trees."""
    types, errors, text_assets = Counter(), Counter(), []
    for item in environment.objects:
        types[item.type.name] += 1
        text_assets.extend(inspect_object(item, errors))
    return {"types": dict(types), "typetree_errors": dict(errors), "text_assets": text_assets}


def probe(arguments):
    """Inspect one file under OS limits; parser failures terminate the worker."""
    resource.setrlimit(resource.RLIMIT_CPU, (WORKER_CPU_SECONDS, WORKER_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (WORKER_MEMORY_BYTES, WORKER_MEMORY_BYTES))
    validate_path(arguments.source, arguments)
    import UnityPy
    UnityPy.config.FALLBACK_UNITY_VERSION = arguments.unity_version
    with redirect_stdout(sys.stderr):
        environment = UnityPy.load(str(arguments.source))
        summary = summarize_objects(environment)
    if not summary["types"]:
        raise ValueError("no serialized Unity objects found")
    summary["containers"] = sorted(environment.container.keys())
    summary["status"] = "partial" if summary["typetree_errors"] else "inspected"
    return summary


def run_probe(path, arguments, deadline):
    """Run a bounded parser, raising TimeoutError when the shared budget expires."""
    remaining = min(arguments.timeout, deadline - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("inventory parser budget expired")
    command = [sys.executable, "-I", str(Path(__file__).resolve()), str(path),
               "--unity-version", arguments.unity_version, "--probe",
               "--max-file-bytes", str(arguments.max_file_bytes)]
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=remaining, check=True)
    return json.loads(result.stdout)


def inspect_file(path, arguments, deadline):
    """Run an isolated parser; report failures instead of compatibility."""
    record = fingerprint(path, arguments.source)
    try:
        record.update(run_probe(path, arguments, deadline))
    except (subprocess.SubprocessError, ValueError, TimeoutError) as error:
        record.update(status="error", error=type(error).__name__)
    return record


def inventory(arguments, files):
    """Build a fingerprint report that never asserts Android compatibility."""
    deadline = time.monotonic() + arguments.max_parser_seconds
    return {"schema_version": 1, "android_compatible": False,
            "tool": {"name": "UnityPy", "version": version("UnityPy")},
            "fallback_unity_version": arguments.unity_version,
            "files": [inspect_file(path, arguments, deadline) for path in files]}


def main():
    """Print JSON; exit 0 for inspection, 1 for incomplete parsing, 2 for bad inputs."""
    parser, arguments = parse_arguments()
    if arguments.probe:
        print(json.dumps(probe(arguments)))
        return 0
    try:
        files = discover_files(arguments)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    report = inventory(arguments, files)
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(any(item["status"] != "inspected" for item in report["files"]))


if __name__ == "__main__":
    sys.exit(main())
