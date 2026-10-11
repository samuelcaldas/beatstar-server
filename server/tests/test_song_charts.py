"""Chart authoring, game identity and client-chart import on disposable databases."""

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER
from server.admin.database import create_admin_engine, create_admin_session_maker
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app
from server.music.chart_document import ChartNote, document_from_notes, document_from_raw, encode_notes, raw_bytes
from server.music.models import ChartRevision, Song
from server.music.raksha import decode_beatmap_interactions
from server.music.song_errors import GameIdentifierInUse
from server.music.unity_catalog import UnityCatalogImporter
from server.storage.migrations.runner import upgrade_to_head

SECRET = "test-admin-secret-with-at-least-32-characters"
ORIGIN = "http://test"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
SONGS = "/api/admin/songs"
EXTRACTED = Path("data/extracted")


@pytest.fixture
async def library(tmp_path, monkeypatch):
    """Runs the real startup path, provisions an administrator and logs in."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,), login_max_attempts=50)
    app = create_app(database_path=str(tmp_path / "library.db"), admin_settings=settings)
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
            yield app, client


def _write(client) -> dict[str, str]:
    """Returns the CSRF header that matches the browser's CSRF cookie."""
    return {CSRF_HEADER: client.cookies.get(CSRF_COOKIE)}


def _notes(count: int) -> list[dict]:
    """Returns count JSON notes, one per beat across the three lanes."""
    return [{"beat_offset": float(beat), "lane": beat % 3 + 1} for beat in range(count)]


def test_notes_round_trip_through_raksha_bytes():
    """Breaks if authored notes are not what the game reads back from the chart."""
    notes = [ChartNote(8.0, 1), ChartNote(16.0, 3), ChartNote(16.5, 2)]

    decoded = decode_beatmap_interactions(encode_notes(660, "710-1", notes))

    assert decoded.id == 660
    assert decoded.id_label == "710-1"
    assert [(i.tap_data.point.beat_offset, i.track, i.tap_data.point.lane) for i in decoded.interactions] == [
        (8.0, 1, 1),
        (16.0, 3, 3),
        (16.5, 2, 2),
    ]


def test_notes_outside_the_game_rules_are_refused():
    """Breaks if the encoder accepts lanes or beats the client cannot place."""
    with pytest.raises(ValueError):
        ChartNote(beat_offset=1.0, lane=4)
    with pytest.raises(ValueError):
        ChartNote(beat_offset=float("nan"), lane=1)
    with pytest.raises(ValueError):
        encode_notes(1, "1-1", [ChartNote(2.0, 1), ChartNote(2.0, 1)])


def test_document_summary_counts_notes_per_lane():
    """Breaks if the summary shown in the administration UI disagrees with the chart bytes."""
    document = document_from_notes(900, "9-1", [ChartNote(1.0, 1), ChartNote(2.0, 1), ChartNote(3.0, 2)])

    assert document["note_count"] == 3
    assert document["lanes"] == {"1": 2, "2": 1, "3": 0}
    assert document["first_beat"] == 1.0 and document["last_beat"] == 3.0
    assert "raw_base64" in document and len(raw_bytes(document)) > 0


async def test_chart_create_and_list_for_a_song_with_a_beatmap(library):
    """Breaks if authored notes are not stored as immutable numbered revisions."""
    _, client = library
    created = await client.post(
        SONGS,
        json={"title": "Exemplo", "artist": "Teste", "difficulty": "easy", "beatmap_id": 901, "bpm": 120, "time_signature": 4},
        headers=_write(client),
    )
    song_id = created.json()["id"]

    first = await client.post(f"{SONGS}/{song_id}/charts", json={"notes": _notes(6)}, headers=_write(client))
    second = await client.post(f"{SONGS}/{song_id}/charts", json={"notes": _notes(3)}, headers=_write(client))
    listed = await client.get(f"{SONGS}/{song_id}/charts")

    assert first.status_code == 201 and first.json()["revision_number"] == 1
    assert first.json()["note_count"] == 6 and first.json()["beatmap_id"] == 901
    assert second.json()["revision_number"] == 2
    assert [chart["note_count"] for chart in listed.json()] == [6, 3]
    assert "raw_base64" not in listed.text


async def test_chart_requires_a_beatmap_identifier(library):
    """Breaks if a chart is stored without the beatmap id the game uses to bind it."""
    _, client = library
    song = (await client.post(SONGS, json={"title": "Sem mapa", "artist": "A", "difficulty": "normal"},
                              headers=_write(client))).json()

    response = await client.post(f"{SONGS}/{song['id']}/charts", json={"notes": _notes(2)}, headers=_write(client))

    assert response.status_code == 409
    assert "beatmap" in response.json()["detail"].lower()


async def test_chart_notes_are_validated_before_storage(library):
    """Breaks if an out-of-range lane reaches the database."""
    _, client = library
    song = (await client.post(SONGS, json={"title": "Faixa", "artist": "A", "difficulty": "normal", "beatmap_id": 902},
                              headers=_write(client))).json()

    response = await client.post(f"{SONGS}/{song['id']}/charts",
                                 json={"notes": [{"beat_offset": 1.0, "lane": 4}]}, headers=_write(client))

    assert response.status_code == 422


async def test_duplicate_game_identifiers_are_refused(library):
    """Breaks if two songs can claim the same game song or beatmap id."""
    _, client = library
    body = {"title": "Um", "artist": "A", "difficulty": "normal", "game_song_id": 77, "beatmap_id": 770}
    first = await client.post(SONGS, json=body, headers=_write(client))
    second = await client.post(SONGS, json={**body, "title": "Dois"}, headers=_write(client))

    assert first.status_code == 201
    assert second.status_code == 409


async def test_game_fields_are_returned_and_editable(library):
    """Breaks if tempo or variant metadata is dropped on read or update."""
    _, client = library
    song = (await client.post(SONGS, json={"title": "Tempo", "artist": "A", "difficulty": "hard"},
                              headers=_write(client))).json()

    updated = await client.patch(f"{SONGS}/{song['id']}",
                                 json={"bpm": 98.5, "time_signature": 4, "variant_label": "TEST_01",
                                       "expected_revision": 1},
                                 headers=_write(client))

    assert updated.status_code == 200
    assert updated.json()["bpm"] == 98.5
    assert updated.json()["variant_label"] == "TEST_01"
    assert updated.json()["source"] == "manual"


async def test_import_is_idempotent_and_keeps_client_bytes(tmp_path):
    """Breaks if rerunning the import duplicates songs or alters the chart bytes."""
    if not (EXTRACTED / "660.chart.bytes").is_file():
        pytest.skip("data/extracted is not present")
    chart_directory = tmp_path / "charts"
    chart_directory.mkdir()
    source = (EXTRACTED / "660.chart.bytes").read_bytes()
    (chart_directory / "660.chart.bytes").write_bytes(source)
    engine = create_admin_engine(str(tmp_path / "import.db"))
    upgrade_to_head(str(tmp_path / "import.db"))
    session_maker = create_admin_session_maker(engine)
    try:
        async with session_maker() as session:
            first = await UnityCatalogImporter(session).import_charts(chart_directory)
        async with session_maker() as session:
            second = await UnityCatalogImporter(session).import_charts(chart_directory)
            song = await session.scalar(select(Song).where(Song.beatmap_id == 660))
            chart = await session.scalar(select(ChartRevision).where(ChartRevision.song_id == song.id))
            count = await session.scalar(select(func.count()).select_from(Song))
    finally:
        await engine.dispose()

    assert len(first.imported_song_ids) == 1 and second.imported_song_ids == ()
    assert count == 1
    assert song.game_song_id is None and song.bpm is None and song.source == "unity-import"
    assert song.title.startswith("Unlinked beatmap 660")
    assert raw_bytes(json.loads(chart.document)) == source
    assert document_from_raw(source)["beatmap_id"] == 660
