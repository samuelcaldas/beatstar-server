"""Game chart import behavior on isolated migrated databases."""

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from server.admin.database import create_admin_engine, create_admin_session_maker
from server.music.chart_document import ChartNote, ChartPoint, document_from_raw, encode_notes, raw_bytes
from server.music.example_songs import build_examples
from server.music.models import AuditEvent, ChartRevision, Song
from server.music.raksha import InteractionType, decode_beatmap_interactions
from server.music.song_errors import GameIdentifierInUse
from server.music.song_schemas import SongCreate
from server.music.song_service import SongLibraryService
from server.music.song_repository import SongRepository
from server.music.unity_catalog import UnityCatalogImporter
from server.storage.migrations.runner import upgrade_to_head


@pytest.fixture
async def song_database(tmp_path: Path):
    """Creates the music schema in a disposable SQLite database."""
    database_path = tmp_path / "songs.db"
    upgrade_to_head(str(database_path))
    engine = create_admin_engine(str(database_path))
    try:
        yield create_admin_session_maker(engine)
    finally:
        await engine.dispose()


def _raw_chart(beat: float = 4.0) -> bytes:
    """Builds a deterministic Raksha chart for beatmap 660."""
    return encode_notes(660, "710-1", [ChartNote(beat_offset=beat, lane=1)])


def _payload() -> SongCreate:
    """Returns candidate metadata without asserting a verified game-song linkage."""
    return SongCreate(title="Unlinked beatmap 660", artist="Não identificado", difficulty="normal", beatmap_id=660)


async def test_same_chart_import_is_idempotent(song_database):
    """Reruns do not duplicate songs, revisions, or audit events for identical bytes."""
    async with song_database() as session:
        service = SongLibraryService(session)
        first = await service.import_song(_payload(), "unity-import", _raw_chart(), actor_id=None)
        second = await service.import_song(_payload(), "unity-import", _raw_chart(), actor_id=None)
        chart_count = await session.scalar(select(func.count()).select_from(ChartRevision))
        song_count = await session.scalar(select(func.count()).select_from(Song))
        audit_count = await session.scalar(select(func.count()).select_from(AuditEvent))

    assert first.id == second.id
    assert song_count == 1
    assert chart_count == 1
    assert audit_count == 2


async def test_changed_chart_content_appends_an_immutable_revision(song_database):
    """A changed hash is retained as a new revision instead of rewriting prior bytes."""
    async with song_database() as session:
        service = SongLibraryService(session)
        song = await service.import_song(_payload(), "unity-import", _raw_chart(4.0), actor_id=None)
        await service.import_song(_payload(), "unity-import", _raw_chart(5.0), actor_id=None)
        charts = list((await session.scalars(select(ChartRevision).where(ChartRevision.song_id == song.id)
                                           .order_by(ChartRevision.revision_number))).all())

    assert [chart.revision_number for chart in charts] == [1, 2]
    assert raw_bytes(json.loads(charts[0].document)) == _raw_chart(4.0)
    assert raw_bytes(json.loads(charts[1].document)) == _raw_chart(5.0)
    assert charts[0].sha256 != charts[1].sha256


async def test_song_and_chart_insert_roll_back_as_one_transaction(song_database, monkeypatch):
    """A failed chart flush leaves no draft song committed without its chart."""
    def fail_chart_flush(_repository: SongRepository, _chart: ChartRevision) -> None:
        raise IntegrityError("chart flush", {}, RuntimeError("simulated constraint failure"))

    monkeypatch.setattr(SongRepository, "add_chart", fail_chart_flush)
    async with song_database() as session:
        with pytest.raises(GameIdentifierInUse):
            await SongLibraryService(session).import_song(
                _payload(), "unity-import", _raw_chart(), actor_id=None
            )
        count = await session.scalar(select(func.count()).select_from(Song))

    assert count == 0


async def test_importer_does_not_claim_unverified_game_song_link(song_database, tmp_path: Path):
    """A chart label like 710-1 is retained as chart data, not promoted to a verified song ID."""
    chart_directory = tmp_path / "charts"
    chart_directory.mkdir()
    (chart_directory / "660.chart.bytes").write_bytes(_raw_chart())
    async with song_database() as session:
        report = await UnityCatalogImporter(session).import_charts(chart_directory)
        song = await session.scalar(select(Song).where(Song.beatmap_id == 660))
        document = document_from_raw(_raw_chart())

    assert len(report.imported_song_ids) == 1
    assert document["id_label"] == "710-1"
    assert song.game_song_id is None
    assert song.title == "Unlinked beatmap 660 (710-1)"


def test_example_set_exercises_taps_drags_and_every_lane():
    """Each public example format includes tap and drag interactions on all three lanes."""
    for example in build_examples():
        raw = encode_notes(example.beatmap_id, f"{example.metadata.variant_label}-1", list(example.notes))
        decoded = decode_beatmap_interactions(raw)
        types = {interaction.interaction_type for interaction in decoded.interactions}
        lanes = set()
        for interaction in decoded.interactions:
            if interaction.tap_data is not None:
                lanes.add(interaction.tap_data.point.lane)
            if interaction.drag_data is not None:
                lanes.update(point.lane for point in interaction.drag_data.points)
        assert InteractionType.TAP in types
        assert InteractionType.DRAG in types
        assert lanes == {1, 2, 3}
