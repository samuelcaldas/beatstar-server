"""Persistence queries for songs: filtered pages, conditional revision updates and reference counts."""

import json
import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.music.models import Asset, AuditEvent, BuildJob, ChartRevision, Release, Song, now_milliseconds
from server.music.song_schemas import SongQuery

LIKE_ESCAPE = "\\"


def like_pattern(text: str) -> str:
    """Returns a case-insensitive contains-pattern with % and _ matched literally."""
    escaped = text.lower().replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", LIKE_ESCAPE + "%")
    escaped = escaped.replace("_", LIKE_ESCAPE + "_")
    return f"%{escaped}%"


class SongRepository:
    """Runs song queries inside the caller's session; the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Binds the repository to one session."""
        self._session = session

    async def find(self, song_id: str) -> Song | None:
        """Returns the song with the identifier, or None."""
        return await self._session.get(Song, song_id)

    async def add(self, song: Song) -> None:
        """Stages a new song and flushes so that generated defaults and identifiers exist."""
        self._session.add(song)
        await self._session.flush()

    async def list_page(self, query: SongQuery) -> tuple[list[Song], int]:
        """Returns one deterministic page of songs and the total matching count."""
        conditions = self._conditions(query)
        total = await self._session.scalar(select(func.count()).select_from(Song).where(*conditions))
        statement = (
            select(Song)
            .where(*conditions)
            .order_by(Song.title, Song.id)
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        songs = (await self._session.execute(statement)).scalars().all()
        return list(songs), int(total or 0)

    async def list_charts(self, song_id: str) -> list[ChartRevision]:
        """Returns every chart revision of the song, oldest first."""
        statement = (
            select(ChartRevision)
            .where(ChartRevision.song_id == song_id)
            .order_by(ChartRevision.revision_number)
        )
        return list((await self._session.execute(statement)).scalars().all())

    async def find_by_beatmap(self, beatmap_id: int) -> Song | None:
        """Returns the song already assigned to a beatmap identifier, if any."""
        statement = select(Song).where(Song.beatmap_id == beatmap_id)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def next_chart_number(self, song_id: str) -> int:
        """Returns the number the song's next chart revision will carry."""
        current = await self._session.scalar(
            select(func.max(ChartRevision.revision_number)).where(ChartRevision.song_id == song_id)
        )
        return int(current or 0) + 1

    async def add_chart(self, chart: ChartRevision) -> None:
        """Stages a chart revision; the caller commits and handles number collisions."""
        self._session.add(chart)
        await self._session.flush()

    async def update_if_current(self, song_id: str, expected_revision: int, changes: dict) -> bool:
        """Applies changes only while the stored revision still equals expected_revision.

        Returns:
            True when exactly one row was updated; False when another writer advanced the revision.
        """
        statement = (
            update(Song)
            .where(Song.id == song_id, Song.revision == expected_revision)
            .values(**changes, revision=Song.revision + 1, updated_at=now_milliseconds())
        )
        result = await self._session.execute(statement)
        return result.rowcount == 1

    async def reference_count(self, song_id: str) -> int:
        """Counts rows in every table that depends on the song."""
        total = 0
        for model in (Asset, ChartRevision, BuildJob, Release):
            count = await self._session.scalar(
                select(func.count()).select_from(model).where(model.song_id == song_id)
            )
            total += int(count or 0)
        return total

    async def delete(self, song: Song) -> None:
        """Stages deletion of a song; the caller commits."""
        await self._session.delete(song)
        await self._session.flush()

    async def add_audit(
        self, actor_id: uuid.UUID | None, action: str, song_id: str, changed: list[str] | None = None
    ) -> None:
        """Records an administrator action; detail holds field names only, never values."""
        detail = json.dumps(sorted(changed)) if changed is not None else None
        self._session.add(
            AuditEvent(actor_id=actor_id, action=action, target_type="song", target_id=song_id, detail=detail)
        )
        await self._session.flush()

    def _conditions(self, query: SongQuery) -> list:
        """Builds WHERE clauses for the filters that were provided."""
        conditions = []
        if query.status is not None:
            conditions.append(Song.status == query.status)
        if query.difficulty is not None:
            conditions.append(Song.difficulty == query.difficulty)
        if query.search:
            pattern = like_pattern(query.search)
            conditions.append(
                or_(
                    func.lower(Song.title).like(pattern, escape=LIKE_ESCAPE),
                    func.lower(Song.artist).like(pattern, escape=LIKE_ESCAPE),
                )
            )
        return conditions
