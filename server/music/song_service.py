"""Song library operations: revision checks, state transitions, deletion guards and audit records."""

import uuid
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.music.chart_document import ChartNote, document_from_notes, document_from_raw, serialize
from server.music.models import ChartRevision, Song
from server.music.song_errors import (
    ChartNumberConflict,
    GameIdentifierInUse,
    InvalidSongState,
    RevisionConflict,
    SongInUse,
    SongNotFound,
)
from server.music.song_repository import SongRepository
from server.music.song_schemas import SongCreate, SongQuery, SongUpdate


class SongLibraryService:
    """Owns every song write; each public method commits exactly one short transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Binds the service to one session."""
        self._session = session
        self._songs = SongRepository(session)

    async def create(self, payload: SongCreate, actor_id: uuid.UUID) -> Song:
        """Creates a draft at revision 1 and records the action."""
        song = Song(
            title=payload.title,
            artist=payload.artist,
            difficulty=payload.difficulty,
            game_song_id=payload.game_song_id,
            beatmap_id=payload.beatmap_id,
            bpm=payload.bpm,
            time_signature=payload.time_signature,
            variant_label=payload.variant_label,
            source="manual",
            status="draft",
            revision=1,
        )
        await self._add_song(song, "song.create", actor_id)
        return song

    async def charts(self, song_id: str) -> list[ChartRevision]:
        """Returns the song's chart revisions, oldest first.

        Raises:
            SongNotFound: when no song has the identifier.
        """
        await self.get(song_id)
        return await self._songs.list_charts(song_id)

    async def add_chart(self, song_id: str, notes: list[ChartNote], actor_id: uuid.UUID) -> ChartRevision:
        """Encodes authored notes as the song's next chart revision.

        Raises:
            SongNotFound: when no song has the identifier.
            InvalidSongState: when the song is archived or has no beatmap identifier to bind the chart to.
            ValueError: when the notes cannot be encoded (see chart_document.encode_notes).
        """
        song = await self.get(song_id)
        if song.status == "archived":
            raise InvalidSongState("Archived songs do not accept new charts; restore the song first")
        if song.beatmap_id is None:
            raise InvalidSongState("Assign a beatmap id before adding charts; the game binds notes to it")
        game_song_id = song.game_song_id or 0

        def build(number: int) -> dict:
            return document_from_notes(song.beatmap_id, f"{game_song_id}-{number}", notes)

        return await self._store_chart(song, build, actor_id, "chart.create")

    async def import_chart(self, song: Song, raw: bytes, actor_id: uuid.UUID) -> ChartRevision:
        """Stores existing Raksha bytes (for example extracted from the client) as the next revision.

        Raises:
            ValueError: when the bytes are not a decodable chart.
            ChartNumberConflict: when a concurrent writer took the revision number first.
        """
        return await self._store_chart(song, lambda _number: document_from_raw(raw), actor_id, "chart.import")

    async def import_song(self, payload: SongCreate, source: str, raw: bytes, actor_id: uuid.UUID | None) -> Song:
        """Imports a draft and its chart atomically, reusing identical beatmap content.

        Raises:
            ValueError: when the bytes are not a decodable chart.
            GameIdentifierInUse: when an identifier is assigned to different content.
        """
        document = document_from_raw(raw)
        existing = await self._songs.find_by_beatmap(document["beatmap_id"])
        if existing is not None:
            return await self._reuse_or_append_chart(existing, raw, document, actor_id)
        song = self._imported_song(payload, source)
        try:
            await self._songs.add(song)
            await self._songs.add_audit(actor_id, "song.import", song.id)
            chart = self._build_chart(song.id, 1, document)
            await self._songs.add_chart(chart)
            await self._songs.add_audit(actor_id, "chart.import", song.id, changed=["revision:1"])
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            existing = await self._songs.find_by_beatmap(document["beatmap_id"])
            if existing is not None and await self._has_chart_hash(existing.id, document["raw_sha256"]):
                return existing
            raise GameIdentifierInUse("Game song id or beatmap id is already assigned to different content") from error
        return song

    async def _reuse_or_append_chart(
        self, song: Song, raw: bytes, document: dict, actor_id: uuid.UUID | None
    ) -> Song:
        """Leaves identical chart bytes unchanged or appends a new immutable revision."""
        if await self._has_chart_hash(song.id, document["raw_sha256"]):
            return song
        await self._store_chart(song, lambda _number: document_from_raw(raw), actor_id, "chart.import")
        return song

    async def _has_chart_hash(self, song_id: str, digest: str) -> bool:
        """Checks whether this song already contains the imported chart content."""
        return any(chart.sha256 == digest for chart in await self._songs.list_charts(song_id))

    def _imported_song(self, payload: SongCreate, source: str) -> Song:
        """Builds the draft row for a new imported chart."""
        return Song(
            title=payload.title, artist=payload.artist, difficulty=payload.difficulty,
            game_song_id=payload.game_song_id, beatmap_id=payload.beatmap_id, bpm=payload.bpm,
            time_signature=payload.time_signature, variant_label=payload.variant_label,
            source=source, status="draft", revision=1,
        )

    def _build_chart(self, song_id: str, number: int, document: dict) -> ChartRevision:
        """Builds an immutable chart revision from a validated canonical document."""
        return ChartRevision(
            song_id=song_id, revision_number=number, schema_version=document["schema_version"],
            document=serialize(document), sha256=document["raw_sha256"],
        )

    async def _store_chart(
        self, song: Song, build: Callable[[int], dict], actor_id: uuid.UUID | None, action: str
    ) -> ChartRevision:
        """Writes one immutable revision with the next number and records the action.

        Args:
            build: Receives the revision number and returns the document; it may raise ValueError,
                in which case nothing is written.
        """
        number = await self._songs.next_chart_number(song.id)
        document = build(number)
        chart = ChartRevision(
            song_id=song.id,
            revision_number=number,
            schema_version=document["schema_version"],
            document=serialize(document),
            sha256=document["raw_sha256"],
        )
        await self._songs.add_chart(chart)
        await self._songs.add_audit(actor_id, action, song.id, changed=[f"revision:{number}"])
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise ChartNumberConflict("Chart revision number was taken concurrently; retry") from error
        return chart

    async def _add_song(self, song: Song, action: str, actor_id: uuid.UUID | None) -> None:
        """Stages and commits a new song with its audit record.

        Raises:
            GameIdentifierInUse: when the game song or beatmap identifier is already assigned.
        """
        try:
            await self._songs.add(song)
            await self._songs.add_audit(actor_id, action, song.id)
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise GameIdentifierInUse("Game song id or beatmap id is already assigned to another song") from error

    async def page(self, query: SongQuery) -> tuple[list[Song], int]:
        """Returns one page of songs and the total for the same filters."""
        return await self._songs.list_page(query)

    async def get(self, song_id: str) -> Song:
        """Returns the song.

        Raises:
            SongNotFound: when no song has the identifier.
        """
        song = await self._songs.find(song_id)
        if song is None:
            raise SongNotFound(song_id)
        return song

    async def update(self, song_id: str, payload: SongUpdate, actor_id: uuid.UUID) -> Song:
        """Changes editable metadata when the expected revision is current and the song is not archived.

        Raises:
            RevisionConflict: when the expected revision is stale.
            InvalidSongState: when the song is archived.
        """
        song = await self.get(song_id)
        self._require_revision(song, payload.expected_revision)
        if song.status == "archived":
            raise InvalidSongState("Archived songs are read-only; restore the song before editing it")
        changes = payload.model_dump(exclude_none=True, exclude={"expected_revision"})
        return await self._apply(song, payload.expected_revision, changes, "song.update", actor_id)

    async def archive(self, song_id: str, expected_revision: int, actor_id: uuid.UUID) -> Song:
        """Moves a draft or published song to archived; archived songs stay in the library.

        Raises:
            RevisionConflict: when the expected revision is stale.
            InvalidSongState: when the song is already archived.
        """
        song = await self.get(song_id)
        self._require_revision(song, expected_revision)
        if song.status == "archived":
            raise InvalidSongState("Song is already archived")
        return await self._apply(song, expected_revision, {"status": "archived"}, "song.archive", actor_id)

    async def restore(self, song_id: str, expected_revision: int, actor_id: uuid.UUID) -> Song:
        """Returns an archived song to draft so that it can be edited again.

        Raises:
            RevisionConflict: when the expected revision is stale.
            InvalidSongState: when the song is not archived.
        """
        song = await self.get(song_id)
        self._require_revision(song, expected_revision)
        if song.status != "archived":
            raise InvalidSongState("Only archived songs can be restored")
        return await self._apply(song, expected_revision, {"status": "draft"}, "song.restore", actor_id)

    async def delete(self, song_id: str, expected_revision: int, actor_id: uuid.UUID) -> None:
        """Hard-deletes an unreferenced draft; everything else must be archived instead.

        Raises:
            RevisionConflict: when the expected revision is stale.
            SongInUse: when the song is not a draft, or assets, charts, jobs or releases reference it.
        """
        song = await self.get(song_id)
        self._require_revision(song, expected_revision)
        if song.status != "draft":
            raise SongInUse("Only draft songs can be deleted; archive the song instead")
        if await self._songs.reference_count(song.id) > 0:
            raise SongInUse("Song is referenced by assets, charts, build jobs or releases")
        await self._songs.add_audit(actor_id, "song.delete", song.id)
        await self._songs.delete(song)
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise SongInUse("Song became referenced before it could be deleted") from error

    def _require_revision(self, song: Song, expected_revision: int) -> None:
        """Rejects requests built from a revision other than the current one.

        Raises:
            RevisionConflict: carrying the current revision.
        """
        if song.revision != expected_revision:
            raise RevisionConflict(song.revision)

    async def _apply(self, song: Song, expected_revision: int, changes: dict, action: str, actor_id: uuid.UUID) -> Song:
        """Applies a conditional update, refreshes the song, and records the action.

        Raises:
            RevisionConflict: when a concurrent writer advanced the revision first.
        """
        if not await self._songs.update_if_current(song.id, expected_revision, changes):
            await self._session.refresh(song)
            raise RevisionConflict(song.revision)
        await self._session.refresh(song)
        await self._songs.add_audit(actor_id, action, song.id, changed=list(changes))
        await self._session.commit()
        return song
