"""Imports the client's extracted charts and the reference artwork into the song library.

Each chart file is one playable beatmap. Its id_label ("<game song id>-<variant>") gives the game
song id; the beatmap id is the chart's own id. Only the reference song (710/660) carries metadata
recovered from the client; every other import is labelled as unidentified rather than guessed.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.music.chart_document import document_from_raw
from server.music.models import ChartRevision, Song
from server.music.song_schemas import SongCreate
from server.music.song_service import SongLibraryService

SOURCE_IMPORT = "unity-import"
UNIDENTIFIED_ARTIST = "Não identificado"
MAXIMUM_CHART_FILES = 512


@dataclass(frozen=True)
class CatalogImportReport:
    """Counts of what one import run created and what it left alone."""

    imported_song_ids: tuple[str, ...]
    skipped_beatmap_ids: tuple[int, ...]


class UnityCatalogImporter:
    """Creates one draft song per unseen beatmap; running it again changes nothing."""

    def __init__(self, session: AsyncSession) -> None:
        """Binds the importer to one session."""
        self._session = session
        self._library = SongLibraryService(session)

    async def import_charts(self, extracted_directory: Path) -> CatalogImportReport:
        """Imports every chart file in the directory that is not yet in the library.

        Raises:
            ValueError: when the directory holds more chart files than the import accepts, or a chart is invalid.
        """
        paths = sorted(extracted_directory.glob("*.chart.bytes"))
        if len(paths) > MAXIMUM_CHART_FILES:
            raise ValueError("Extracted directory holds more chart files than the import accepts")
        imported: list[str] = []
        skipped: list[int] = []
        for path in paths:
            raw = path.read_bytes()
            document = document_from_raw(raw)
            beatmap_id = document["beatmap_id"]
            existing = await self._session.scalar(select(Song).where(Song.beatmap_id == beatmap_id))
            if existing is not None and await self._has_chart_hash(existing.id, document["raw_sha256"]):
                skipped.append(beatmap_id)
                continue
            payload = _payload_for(beatmap_id, document["id_label"])
            song = await self._library.import_song(payload, SOURCE_IMPORT, raw, actor_id=None)
            imported.append(song.id)
        return CatalogImportReport(tuple(imported), tuple(skipped))

    async def _has_chart_hash(self, song_id: str, digest: str) -> bool:
        """Returns whether this song already stores these exact immutable bytes."""
        statement = select(ChartRevision.id).where(ChartRevision.song_id == song_id, ChartRevision.sha256 == digest)
        return await self._session.scalar(statement) is not None


def _payload_for(beatmap_id: int, id_label: str) -> SongCreate:
    """Labels an unlinked chart without claiming that its label identifies a starter song."""
    return SongCreate(
        title=f"Unlinked beatmap {beatmap_id} ({id_label})",
        artist=UNIDENTIFIED_ARTIST,
        difficulty="normal",
        beatmap_id=beatmap_id,
    )


async def single_chunk(payload: bytes) -> AsyncIterator[bytes]:
    """Yields the whole payload as one chunk, matching the streamed upload interface."""
    yield payload
