"""Song library operations: revision checks, state transitions, deletion guards and audit records."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.music.models import Song
from server.music.song_errors import InvalidSongState, RevisionConflict, SongInUse, SongNotFound
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
        song = Song(title=payload.title, artist=payload.artist, difficulty=payload.difficulty, status="draft", revision=1)
        await self._songs.add(song)
        await self._songs.add_audit(actor_id, "song.create", song.id)
        await self._session.commit()
        return song

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
