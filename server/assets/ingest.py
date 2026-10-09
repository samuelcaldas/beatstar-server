"""Streaming ingestion: bounded copy, sniffing, verification and commit of one upload.

Order of checks: byte limits while streaming, format sniffing, client adapter acceptance,
external verification, then the immutable commit. Anything that fails leaves no staged file.
"""

import asyncio
import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from server.assets.client_adapters import ClientAssetAdapter
from server.assets.formats import ARTWORK, AUDIO, HEADER_BYTES, AssetFormat, FormatRegistry
from server.assets.storage import AssetStorage


class UnsupportedFormat(Exception):
    """The bytes are not a recognised format for the requested kind, or the client refuses it."""


class AssetTooLarge(Exception):
    """The upload exceeded the per-file limit for its kind."""


class QuotaExceeded(Exception):
    """The upload would exceed the total storage quota."""


class ProbeRejected(Exception):
    """External verification found the file unreadable or outside the configured bounds."""


class ProbeTimeout(Exception):
    """External verification did not finish within its time budget; the file is refused."""


class VerificationUnavailable(ProbeRejected):
    """No verification tool is configured; uploads are refused rather than accepted unverified."""


@dataclass(frozen=True)
class AssetLimits:
    """Per-kind byte limits, media bounds and the total storage quota."""

    max_audio_bytes: int = 50 * 1024 * 1024
    max_artwork_bytes: int = 10 * 1024 * 1024
    quota_bytes: int = 5 * 1024 * 1024 * 1024
    max_audio_seconds: int = 600
    max_artwork_pixels: int = 4096 * 4096

    def bytes_for(self, kind: str) -> int:
        """Returns the per-file byte limit for the kind."""
        return self.max_audio_bytes if kind == AUDIO else self.max_artwork_bytes


@dataclass(frozen=True)
class ProbeReport:
    """Facts a verifier reports about a readable file; None means the fact does not apply."""

    duration_seconds: float | None
    width: int | None
    height: int | None


class MediaProbe(Protocol):
    """Strategy for verifying one staged file with an external tool."""

    def inspect(self, path: Path, asset_format: AssetFormat) -> ProbeReport:
        """Returns the report or raises ProbeRejected or ProbeTimeout."""


class UnavailableProbe:
    """Fail-closed default: refuses every file until a real verifier is configured."""

    def inspect(self, path: Path, asset_format: AssetFormat) -> ProbeReport:
        """Always refuses; nothing is accepted unverified."""
        raise VerificationUnavailable("No media verifier is configured")


@dataclass(frozen=True)
class IngestedObject:
    """A committed, verified object and the metadata the asset row needs."""

    sha256: str
    byte_size: int
    storage_key: str
    content_type: str
    duration_milliseconds: int | None
    width: int | None
    height: int | None


class AssetIngestor:
    """Runs one upload from request body to committed object."""

    def __init__(
        self,
        storage: AssetStorage,
        registry: FormatRegistry,
        adapter: ClientAssetAdapter,
        limits: AssetLimits,
    ) -> None:
        """Stores the collaborators; each one is replaceable behind its protocol."""
        self._storage = storage
        self._registry = registry
        self._adapter = adapter
        self._limits = limits

    async def ingest(
        self,
        kind: str,
        chunks: AsyncIterator[bytes],
        remaining_quota: int,
        probe: MediaProbe,
    ) -> IngestedObject:
        """Streams, verifies and commits one upload; staged bytes are always removed on failure.

        Args:
            kind: AUDIO or ARTWORK.
            chunks: The request body as an async byte iterator.
            remaining_quota: Bytes still available under the total quota.
            probe: Verifier used after sniffing and before commit.

        Raises:
            UnsupportedFormat, AssetTooLarge, QuotaExceeded, ProbeRejected, ProbeTimeout,
            ConflictingObject: each refusal leaves nothing behind.
        """
        staged = self._storage.new_staging_path()
        try:
            digest, size, asset_format = await self._stream(kind, chunks, staged, remaining_quota)
            report = await asyncio.to_thread(probe.inspect, staged, asset_format)
            self._verify_bounds(kind, report)
            self._storage.commit(staged, digest, asset_format.extension)
        finally:
            self._storage.discard(staged)
        return IngestedObject(
            sha256=digest,
            byte_size=size,
            storage_key=f"{digest}{asset_format.extension}",
            content_type=asset_format.content_type,
            duration_milliseconds=_milliseconds(report.duration_seconds),
            width=report.width,
            height=report.height,
        )

    async def _stream(
        self, kind: str, chunks: AsyncIterator[bytes], staged: Path, remaining_quota: int
    ) -> tuple[str, int, AssetFormat]:
        """Copies the body to staging, enforcing the limit and sniffing the first bytes.

        Returns:
            The SHA-256 hex digest, the byte count, and the detected format.
        """
        kind_limit = self._limits.bytes_for(kind)
        limit = min(kind_limit, remaining_quota)
        hasher = hashlib.sha256()
        size = 0
        head = bytearray()
        asset_format: AssetFormat | None = None
        with staged.open("wb") as handle:
            async for chunk in chunks:
                size += len(chunk)
                if size > limit:
                    raise AssetTooLarge(kind) if kind_limit <= remaining_quota else QuotaExceeded()
                if asset_format is None:
                    head += chunk[: HEADER_BYTES - len(head)]
                    if len(head) >= HEADER_BYTES:
                        asset_format = self._recognise(kind, bytes(head))
                hasher.update(chunk)
                handle.write(chunk)
        if asset_format is None:
            asset_format = self._recognise(kind, bytes(head))
        return hasher.hexdigest(), size, asset_format

    def _recognise(self, kind: str, head: bytes) -> AssetFormat:
        """Returns the accepted format, or raises UnsupportedFormat."""
        asset_format = self._registry.detect(kind, head)
        if asset_format is None or not self._adapter.accepts(asset_format):
            raise UnsupportedFormat(kind)
        return asset_format

    def _verify_bounds(self, kind: str, report: ProbeReport) -> None:
        """Applies the media bounds to the verifier's report.

        Raises:
            ProbeRejected: when a required fact is missing or outside the limits.
        """
        if kind == AUDIO:
            if report.duration_seconds is None or report.duration_seconds <= 0:
                raise ProbeRejected("Audio has no readable duration")
            if report.duration_seconds > self._limits.max_audio_seconds:
                raise ProbeRejected("Audio exceeds the maximum duration")
        if kind == ARTWORK:
            if not report.width or not report.height:
                raise ProbeRejected("Artwork has no readable dimensions")
            if report.width * report.height > self._limits.max_artwork_pixels:
                raise ProbeRejected("Artwork exceeds the maximum pixel count")


def _milliseconds(seconds: float | None) -> int | None:
    """Converts a duration to whole milliseconds, keeping None when there is no duration."""
    return None if seconds is None else int(round(seconds * 1000))
