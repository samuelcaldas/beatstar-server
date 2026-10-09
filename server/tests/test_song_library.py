"""Song library API on disposable databases: validation, pagination, search, concurrency, archive and delete."""

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER
from server.admin.models import AdministratorUser
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app
from server.music.models import Asset, AuditEvent, Song
from server.storage.migrations.runner import downgrade_to, upgrade_to_head

SECRET = "test-admin-secret-with-at-least-32-characters"
ORIGIN = "http://test"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
SONGS = "/api/admin/songs"


@pytest.fixture
async def library(tmp_path, monkeypatch):
    """Runs the real startup path, provisions an administrator, and logs in."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(
        secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,), login_max_attempts=20
    )
    app = create_app(database_path=str(tmp_path / "library.db"), admin_settings=settings)
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
            yield app, client


def _write_headers(client) -> dict[str, str]:
    """Returns the CSRF header matching the browser's CSRF cookie."""
    return {CSRF_HEADER: client.cookies.get(CSRF_COOKIE)}


async def _create(client, title="Song", artist="Artist", difficulty="normal") -> dict:
    """Creates one song through the API and returns its JSON representation."""
    response = await client.post(
        SONGS,
        json={"title": title, "artist": artist, "difficulty": difficulty},
        headers=_write_headers(client),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_returns_draft_at_revision_one(library):
    """Breaks if new songs skip the draft state or the first revision number."""
    _, client = library

    song = await _create(client, title="  Sweet Home  ", artist="Lynyrd Skynyrd")

    assert song["status"] == "draft"
    assert song["revision"] == 1
    assert song["title"] == "Sweet Home"


@pytest.mark.parametrize("payload", [
    {"title": "   ", "artist": "A", "difficulty": "normal"},
    {"title": "T", "artist": "", "difficulty": "normal"},
    {"title": "T", "artist": "A", "difficulty": "impossible"},
    {"title": "x" * 201, "artist": "A", "difficulty": "normal"},
])
async def test_invalid_song_payloads_are_rejected(library, payload):
    """Breaks if whitespace-only, oversized or unknown-difficulty input reaches storage."""
    _, client = library

    response = await client.post(SONGS, json=payload, headers=_write_headers(client))

    assert response.status_code == 422


async def test_empty_library_lists_no_items(library):
    """Breaks if an empty catalog returns a missing or non-empty page."""
    _, client = library

    response = await client.get(SONGS)

    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


async def test_pagination_is_deterministic_and_reports_total(library):
    """Breaks if pages overlap, skip songs, or report a wrong total."""
    _, client = library
    for title in ["E", "B", "D", "A", "C"]:
        await _create(client, title=title)

    first = (await client.get(SONGS, params={"page_size": 2, "page": 1})).json()
    second = (await client.get(SONGS, params={"page_size": 2, "page": 2})).json()
    third = (await client.get(SONGS, params={"page_size": 2, "page": 3})).json()

    assert [s["title"] for s in first["items"]] == ["A", "B"]
    assert [s["title"] for s in second["items"]] == ["C", "D"]
    assert [s["title"] for s in third["items"]] == ["E"]
    assert first["total"] == 5


async def test_page_size_above_maximum_is_rejected(library):
    """Breaks if a client can request an unbounded page."""
    _, client = library

    response = await client.get(SONGS, params={"page_size": 101})

    assert response.status_code == 422


async def test_search_matches_title_or_artist_case_insensitively(library):
    """Breaks if search is case-sensitive or ignores the artist column."""
    _, client = library
    await _create(client, title="Sweet Home Alabama", artist="Lynyrd Skynyrd")
    await _create(client, title="Other", artist="Beatles")

    by_title = (await client.get(SONGS, params={"q": "sweet home"})).json()
    by_artist = (await client.get(SONGS, params={"q": "LYNYRD"})).json()

    assert [s["title"] for s in by_title["items"]] == ["Sweet Home Alabama"]
    assert [s["title"] for s in by_artist["items"]] == ["Sweet Home Alabama"]


async def test_search_treats_wildcards_literally(library):
    """Breaks if a percent sign or underscore in the query matches every song."""
    _, client = library
    await _create(client, title="Plain title", artist="Artist")

    response = (await client.get(SONGS, params={"q": "%"})).json()

    assert response["total"] == 0


async def test_status_and_difficulty_filters_combine(library):
    """Breaks if filters are ignored or applied with OR semantics."""
    _, client = library
    keep = await _create(client, title="Keep", difficulty="hard")
    await _create(client, title="Other", difficulty="hard")
    await _create(client, title="Easy one", difficulty="easy")
    await client.post(f"{SONGS}/{keep['id']}/archive",
                      json={"expected_revision": 1}, headers=_write_headers(client))

    response = (await client.get(SONGS, params={"difficulty": "hard", "status": "archived"})).json()

    assert [s["title"] for s in response["items"]] == ["Keep"]


async def test_stale_revision_is_rejected_with_current_revision(library):
    """Breaks if an update from an old revision silently overwrites a newer edit."""
    _, client = library
    song = await _create(client, title="Original")
    headers = _write_headers(client)
    first = await client.patch(f"{SONGS}/{song['id']}",
                               json={"title": "First", "expected_revision": 1}, headers=headers)

    stale = await client.patch(f"{SONGS}/{song['id']}",
                               json={"title": "Second", "expected_revision": 1}, headers=headers)

    assert first.status_code == 200 and first.json()["revision"] == 2
    assert stale.status_code == 409
    assert stale.json()["current_revision"] == 2
    current = (await client.get(f"{SONGS}/{song['id']}")).json()
    assert current["title"] == "First"


async def test_archived_song_is_read_only_until_restored(library):
    """Breaks if archived songs can still be edited or restoring skips the draft state."""
    _, client = library
    song = await _create(client, title="Shelf")
    headers = _write_headers(client)
    await client.post(f"{SONGS}/{song['id']}/archive", json={"expected_revision": 1}, headers=headers)

    blocked = await client.patch(f"{SONGS}/{song['id']}",
                                 json={"title": "Edit", "expected_revision": 2}, headers=headers)
    restored = await client.post(f"{SONGS}/{song['id']}/restore",
                                 json={"expected_revision": 2}, headers=headers)

    assert blocked.status_code == 409
    assert restored.status_code == 200
    assert restored.json()["status"] == "draft"
    assert restored.json()["revision"] == 3


async def test_hard_delete_removes_an_unreferenced_draft(library):
    """Breaks if an unreferenced draft cannot be removed."""
    _, client = library
    song = await _create(client, title="Throwaway")

    response = await client.request(
        "DELETE", f"{SONGS}/{song['id']}", json={"expected_revision": 1}, headers=_write_headers(client)
    )

    assert response.status_code == 204
    assert (await client.get(f"{SONGS}/{song['id']}")).status_code == 404


async def test_hard_delete_is_refused_when_an_asset_references_the_song(library):
    """Breaks if deleting a draft silently removes an asset that retained data depends on."""
    app, client = library
    song = await _create(client, title="Has audio")
    async with app.state.admin_session_maker() as session:
        session.add(Asset(song_id=song["id"], kind="audio", storage_key="key-1",
                          sha256="a" * 64, byte_size=10, content_type="audio/ogg"))
        await session.commit()

    response = await client.request(
        "DELETE", f"{SONGS}/{song['id']}", json={"expected_revision": 1}, headers=_write_headers(client)
    )

    assert response.status_code == 409


async def test_hard_delete_is_refused_for_published_songs(library):
    """Breaks if a published song can be erased instead of archived."""
    app, client = library
    song = await _create(client, title="Live")
    async with app.state.admin_session_maker() as session:
        row = await session.get(Song, song["id"])
        row.status = "published"
        await session.commit()

    response = await client.request(
        "DELETE", f"{SONGS}/{song['id']}", json={"expected_revision": 1}, headers=_write_headers(client)
    )

    assert response.status_code == 409


async def test_writes_require_csrf_and_authentication(library):
    """Breaks if song writes bypass the CSRF check or the administrator session."""
    app, client = library

    no_csrf = await client.post(SONGS, json={"title": "T", "artist": "A", "difficulty": "normal"})
    anonymous = await client.get(SONGS)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as stranger:
        unauthenticated = await stranger.get(SONGS)

    assert no_csrf.status_code == 403
    assert anonymous.status_code == 200
    assert unauthenticated.status_code == 401


async def test_every_write_records_an_audit_event_with_its_actor(library):
    """Breaks if song changes leave no trace of which administrator made them."""
    app, client = library
    song = await _create(client, title="Audited")
    await client.patch(f"{SONGS}/{song['id']}",
                       json={"title": "Audited again", "expected_revision": 1}, headers=_write_headers(client))

    async with app.state.admin_session_maker() as session:
        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.target_id == song["id"]).order_by(AuditEvent.created_at)
        )).scalars().all()
        actor = (await session.execute(select(AdministratorUser))).scalar_one()

    assert [event.action for event in events] == ["song.create", "song.update"]
    assert all(event.actor_id == actor.id for event in events)


async def test_existing_songs_gain_the_default_difficulty_on_upgrade(tmp_path):
    """Breaks if migration 0003 rewrites or drops existing song rows."""
    database_file = tmp_path / "upgrade.db"
    upgrade_to_head(str(database_file))
    downgrade_to(str(database_file), "0002_music_catalog")
    with sqlite3.connect(database_file) as connection:
        connection.execute(
            "INSERT INTO songs (id, title, artist, status, revision, created_at, updated_at) "
            "VALUES ('legacy-song', 'Old', 'Artist', 'draft', 1, 1, 1)"
        )

    upgrade_to_head(str(database_file))

    with sqlite3.connect(database_file) as connection:
        row = connection.execute("SELECT title, difficulty FROM songs WHERE id = 'legacy-song'").fetchone()
    assert row == ("Old", "normal")
