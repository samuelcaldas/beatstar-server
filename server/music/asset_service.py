"""Asset upload orchestration: song checks, quota accounting, deduplication per song and audit."""

import uuid
from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.assets.ingest import AssetIngestor, AssetLimits, MediaProbe, WaveformGenerator
from server.music.models import Asset, AuditEvent
from server.music.song_errors import InvalidSongState
from server.music.song_service import SongLibraryService


class AssetNotFound(Exception):
    """Raised when no asset has the requested identifier, or its stored object is missing."""


class AssetService:
    """Runs one upload end to end; the caller supplies the request body as an async iterator."""

    def __init__(
        self,
        session: AsyncSession,
        ingestor: AssetIngestor,
        probe: MediaProbe,
        waveform: WaveformGenerator | None,
        limits: AssetLimits,
    ) -> None:
        """Binds the service to one session and its collaborators."""
        self._session = session
        self._ingestor = ingestor
        self._probe = probe
        self._waveform = waveform
        self._limits = limits

    async def upload(
        self,
        song_id: str,
        kind: str,
        chunks: AsyncIterator[bytes],
        actor_id: uuid.UUID,
    ) -> tuple[Asset, bool]:
        """Attaches verified media to a song.

        Returns:
            The asset row and True when it was created, or the existing row and False when the
            same bytes were already attached to this song.

        Raises:
            SongNotFound: when the song does not exist.
            InvalidSongState: when the song is archived.
            UnsupportedFormat, AssetTooLarge, QuotaExceeded, ProbeRejected, ConflictingObject:
                refusals from the ingestor; nothing is stored.
        """
        song = await SongLibraryService(self._session).get(song_id)
        if song.status == "archived":
            raise InvalidSongState("Archived songs do not accept new media; restore the song first")
        remaining = self._limits.quota_bytes - await self._stored_bytes()
        ingested = await self._ingestor.ingest(kind, chunks, remaining, self._probe, self._waveform)
        existing = await self._find_in_song(song.id, ingested.storage_key)
        if existing is not None:
            return existing, False
        asset = Asset(
            song_id=song.id,
            kind=kind,
            storage_key=ingested.storage_key,
            sha256=ingested.sha256,
            byte_size=ingested.byte_size,
            content_type=ingested.content_type,
            duration_milliseconds=ingested.duration_milliseconds,
            width=ingested.width,
            height=ingested.height,
        )
        try:
            self._session.add(asset)
            self._session.add(AuditEvent(actor_id=actor_id, action="asset.upload", target_type="song",
                                         target_id=song.id, detail=kind))
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._find_in_song(song.id, ingested.storage_key)
            if existing is None:
                raise
            return existing, False
        return asset, True

    async def find(self, asset_id: str) -> Asset:
        """Returns the asset row.

        Raises:
            AssetNotFound: when no asset has the identifier.
        """
        asset = await self._session.get(Asset, asset_id)
        if asset is None:
            raise AssetNotFound(asset_id)
        return asset

    async def list_for_song(self, song_id: str) -> list[Asset]:
        """Returns the song's assets, oldest first.

        Raises:
            SongNotFound: when no song has the identifier.
        """
        await SongLibraryService(self._session).get(song_id)
        statement = select(Asset).where(Asset.song_id == song_id).order_by(Asset.created_at, Asset.id)
        return list((await self._session.execute(statement)).scalars().all())

    async def _find_in_song(self, song_id: str, storage_key: str) -> Asset | None:
        """Returns the asset already attached to this song with this storage key, if any."""
        statement = select(Asset).where(Asset.song_id == song_id, Asset.storage_key == storage_key)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def _stored_bytes(self) -> int:
        """Returns the bytes occupied by distinct stored objects, counting each object once."""
        distinct = select(Asset.storage_key, Asset.byte_size).distinct().subquery()
        total = await self._session.scalar(select(func.coalesce(func.sum(distinct.c.byte_size), 0)))
        return int(total or 0)
