"""Immutable content-addressed storage for uploaded media.

Objects live at objects/<first two hex digits>/<sha256><extension>. The path is derived only
from a validated digest and a known extension, never from anything a client sent. A committed
object is never replaced: identical bytes reuse it, different bytes at the same address are a
conflict.
"""

import hashlib
import os
import re
import time
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = frozenset({".wav", ".ogg", ".mp3", ".png", ".jpg"})
PREVIEW_SUFFIX = ".peaks.json"
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
CHUNK_BYTES = 1024 * 1024


class ConflictingObject(Exception):
    """An object already exists at the address with different bytes; it is left untouched."""


def object_path(base: Path, digest: str, extension: str) -> Path:
    """Returns the content address for a digest and extension.

    Raises:
        ValueError: when the digest is not 64 lowercase hex characters or the extension is unknown.
    """
    if DIGEST_PATTERN.fullmatch(digest) is None:
        raise ValueError("Object address must be a lowercase SHA-256 hex digest")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension {extension!r} is not a storable media extension")
    return base / digest[:2] / f"{digest}{extension}"


def _file_digest(path: Path) -> str:
    """Returns the SHA-256 hex digest of a file, read in bounded chunks."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_BYTES), b""):
            hasher.update(block)
    return hasher.hexdigest()


class AssetStorage:
    """Owns the staging and object directories under one private root."""

    def __init__(self, root: Path) -> None:
        """Creates the directories; refuses a symlinked root or subdirectory.

        Raises:
            ValueError: when the root or one of its managed directories is a symlink.
        """
        if root.is_symlink():
            raise ValueError("Upload root must not be a symlink")
        self._root = root
        self._staging = root / "staging"
        self._objects = root / "objects"
        self._previews = root / "previews"
        for directory in (self._root, self._staging, self._objects, self._previews):
            directory.mkdir(parents=True, exist_ok=True)
            if directory.is_symlink():
                raise ValueError(f"{directory.name} must not be a symlink")

    @property
    def objects_directory(self) -> Path:
        """Directory holding committed, immutable objects."""
        return self._objects

    def preview_path(self, digest: str) -> Path:
        """Returns the address of the waveform preview derived from the object with this digest.

        Raises:
            ValueError: when the digest is not 64 lowercase hex characters.
        """
        if DIGEST_PATTERN.fullmatch(digest) is None:
            raise ValueError("Preview address must be a lowercase SHA-256 hex digest")
        return self._previews / digest[:2] / f"{digest}{PREVIEW_SUFFIX}"

    def commit_preview(self, staged: Path, digest: str) -> Path:
        """Places a derived preview at its address; identical content is reused, different content conflicts.

        Raises:
            ConflictingObject: when a different preview already occupies the address.
        """
        target = self.preview_path(digest)
        if target.exists():
            if _file_digest(target) != _file_digest(staged):
                raise ConflictingObject(target.name)
            staged.unlink(missing_ok=True)
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, target)
        return target

    def new_staging_path(self) -> Path:
        """Returns a fresh, unpredictable path inside the staging directory."""
        return self._staging / uuid.uuid4().hex

    def commit(self, staged: Path, digest: str, extension: str) -> Path:
        """Moves a verified staged file to its content address, or reuses an identical object.

        Raises:
            ConflictingObject: when a different file already occupies the address.
        """
        target = object_path(self._objects, digest, extension)
        if target.exists():
            if _file_digest(target) != digest:
                raise ConflictingObject(target.name)
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, target)
        return target

    def discard(self, path: Path) -> None:
        """Removes a staged file if it still exists."""
        path.unlink(missing_ok=True)

    def sweep_stale_staging(self, max_age_seconds: float) -> int:
        """Removes staged files older than max_age_seconds and returns how many were removed."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        for path in self._staging.iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        return removed
