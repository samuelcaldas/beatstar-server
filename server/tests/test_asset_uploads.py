"""Asset upload pipeline over HTTP: streaming limits, sniffing, probing, quotas, immutability, previews."""

import os
import time
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app
from server.assets.ingest import AssetLimits, ProbeRejected, ProbeReport, ProbeTimeout
from server.assets.storage import AssetStorage, ConflictingObject, object_path
from server.music.models import Asset
from sqlalchemy import select

SECRET = "test-admin-secret-with-at-least-32-characters"
ORIGIN = "http://test"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
SONGS = "/api/admin/songs"

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 200
OGG = b"OggS\x00\x02" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
TEXT = b"<script>alert(1)</script>" + b"x" * 200


class ScriptedProbe:
    """Boundary double for the external media tools; returns a fixed report or raises a fixed error."""

    def __init__(self, report: ProbeReport | None = None, error: Exception | None = None) -> None:
        """Stores the outcome every inspection will produce."""
        self._report = report or ProbeReport(duration_seconds=12.5, width=None, height=None)
        self._error = error

    def inspect(self, path: Path, asset_format) -> ProbeReport:
        """Returns the scripted report or raises the scripted error."""
        if self._error is not None:
            raise self._error
        return self._report


class ScriptedWaveform:
    """Boundary double for the FFmpeg decoder; the synthetic test files carry no real samples."""

    def generate(self, path: Path, asset_format) -> list[int]:
        """Returns fixed peaks so that only storage and routing behaviour is under test."""
        return [0, 128, 255]


@pytest.fixture
async def uploads(tmp_path, monkeypatch):
    """Builds an authenticated client with a private upload root and a scripted probe."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(
        secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,), login_max_attempts=50
    )
    limits = AssetLimits(
        max_audio_bytes=4096, max_artwork_bytes=4096, quota_bytes=10_000,
        max_audio_seconds=600, max_artwork_pixels=4096 * 4096,
    )
    app = create_app(
        database_path=str(tmp_path / "uploads.db"),
        admin_settings=settings,
        asset_limits=limits,
        asset_root=tmp_path / "uploads",
        media_probe=ScriptedProbe(),
        waveform=ScriptedWaveform(),
    )
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
            yield app, client, app.state, tmp_path / "uploads"


def _write_headers(client) -> dict[str, str]:
    """Returns the CSRF header matching the browser's CSRF cookie."""
    return {CSRF_HEADER: client.cookies.get(CSRF_COOKIE)}


async def _song(client, title="Upload target") -> str:
    """Creates a draft song and returns its identifier."""
    response = await client.post(SONGS, json={"title": title, "artist": "Artist", "difficulty": "normal"},
                                 headers=_write_headers(client))
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _put(client, song_id: str, kind: str, body: bytes | AsyncIterator[bytes], **headers):
    """Sends a raw upload body to the song's asset endpoint."""
    return await client.put(
        f"{SONGS}/{song_id}/assets/{kind}",
        content=body,
        headers={**_write_headers(client), **headers},
    )


def _tree_files(root: Path) -> list[Path]:
    """Lists every regular file under root; empty when the directory does not exist."""
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file()]


async def test_text_disguised_as_audio_is_rejected_without_residue(uploads):
    """Breaks if non-media bytes reach storage or leave a database row or staged file behind."""
    app, client, _, root = uploads
    song_id = await _song(client)

    response = await _put(client, song_id, "audio", TEXT)

    assert response.status_code == 415
    assert _tree_files(root) == []
    async with app.state.admin_session_maker() as session:
        assert (await session.execute(select(Asset))).scalars().all() == []


async def test_image_renamed_as_audio_is_rejected(uploads):
    """Breaks if an image body passes the audio slot because the client claims audio."""
    _, client, _, _ = uploads
    song_id = await _song(client)

    response = await _put(client, song_id, "audio", PNG, **{"Content-Type": "audio/ogg"})

    assert response.status_code == 415


async def test_streamed_body_without_content_length_stops_at_the_limit(uploads):
    """Breaks if an oversized chunked upload is buffered in full before the limit is applied."""
    _, client, _, root = uploads
    song_id = await _song(client)
    produced = []

    async def endless() -> AsyncIterator[bytes]:
        yield WAV[:64]
        for _ in range(1000):
            chunk = b"\x00" * 512
            produced.append(len(chunk))
            yield chunk

    response = await _put(client, song_id, "audio", endless())

    assert response.status_code == 413
    assert sum(produced) < 4096 + 4096
    assert _tree_files(root) == []


def _audio(size: int, tag: bytes) -> bytes:
    """Returns a WAV-signed body of exactly size bytes whose content differs by tag."""
    return WAV + tag * (size - len(WAV))


async def test_quota_is_enforced_before_the_third_object_is_committed(uploads):
    """Breaks if storage accepts an upload that pushes total stored bytes past the quota.

    Quota is 10000 bytes and each file is 3900 bytes, so the third file must be refused
    even though it is under the per-file limit.
    """
    _, client, _, root = uploads
    songs = [await _song(client, f"Quota {index}") for index in range(3)]

    first = await _put(client, songs[0], "audio", _audio(3900, b"a"))
    second = await _put(client, songs[1], "audio", _audio(3900, b"b"))
    third = await _put(client, songs[2], "audio", _audio(3900, b"c"))

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 413
    assert len(_tree_files(root / "objects")) == 2


async def test_identical_upload_to_the_same_song_reuses_the_row_and_file(uploads):
    """Breaks if re-uploading the same bytes duplicates the row or the stored object."""
    _, client, _, root = uploads
    song_id = await _song(client)

    created = await _put(client, song_id, "audio", WAV)
    repeated = await _put(client, song_id, "audio", WAV)

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["id"] == created.json()["id"]
    assert len(_tree_files(root / "objects")) == 1


async def test_same_content_under_two_songs_shares_one_object(uploads):
    """Breaks if content deduplication stops being shared across songs or rows are merged."""
    app, client, _, root = uploads
    first = await _song(client, "A")
    second = await _song(client, "B")

    await _put(client, first, "audio", WAV)
    await _put(client, second, "audio", WAV)

    assert len(_tree_files(root / "objects")) == 1
    async with app.state.admin_session_maker() as session:
        rows = (await session.execute(select(Asset))).scalars().all()
    assert len(rows) == 2


async def test_client_content_type_and_name_are_ignored(uploads):
    """Breaks if the declared media type decides the stored type or extension."""
    _, client, _, _ = uploads
    song_id = await _song(client)

    response = await _put(client, song_id, "audio", WAV, **{"Content-Type": "image/png"})

    body = response.json()
    assert body["content_type"] == "audio/wav"
    assert body["storage_key"].endswith(".wav")


async def test_probe_rejection_leaves_no_row_and_no_file(uploads):
    """Breaks if a file that fails verification (too long, unreadable) is kept."""
    app, client, _, root = uploads
    app.state.media_probe = ScriptedProbe(error=ProbeRejected("Audio exceeds the maximum duration"))
    song_id = await _song(client)

    response = await _put(client, song_id, "audio", WAV)

    assert response.status_code == 422
    assert _tree_files(root) == []
    async with app.state.admin_session_maker() as session:
        assert (await session.execute(select(Asset))).scalars().all() == []


async def test_probe_timeout_is_refused_like_any_unverifiable_file(uploads):
    """Breaks if a verification that times out is treated as success."""
    app, client, _, root = uploads
    app.state.media_probe = ScriptedProbe(error=ProbeTimeout("ffprobe exceeded its time budget"))
    song_id = await _song(client)

    response = await _put(client, song_id, "audio", WAV)

    assert response.status_code == 422
    assert _tree_files(root) == []


async def test_existing_object_with_different_bytes_is_never_overwritten(uploads):
    """Breaks if a committed object can be replaced by a later upload."""
    _, client, _, root = uploads
    song_id = await _song(client)
    target = object_path(root / "objects", _digest(WAV), ".wav")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"different bytes at the same address")

    response = await _put(client, song_id, "audio", WAV)

    assert response.status_code == 409
    assert target.read_bytes() == b"different bytes at the same address"


async def test_archived_song_refuses_uploads(uploads):
    """Breaks if an archived song can receive new media."""
    _, client, _, _ = uploads
    song_id = await _song(client)
    await client.post(f"{SONGS}/{song_id}/archive", json={"expected_revision": 1},
                      headers=_write_headers(client))

    response = await _put(client, song_id, "audio", WAV)

    assert response.status_code == 409


async def test_upload_to_unknown_song_is_not_found(uploads):
    """Breaks if an upload can be attached to a nonexistent song."""
    _, client, _, _ = uploads

    response = await _put(client, "00000000-0000-4000-8000-00000000dead", "audio", WAV)

    assert response.status_code == 404


async def test_upload_requires_csrf(uploads):
    """Breaks if raw uploads bypass the double-submit check used for other writes."""
    _, client, _, _ = uploads
    song_id = await _song(client)

    response = await client.put(f"{SONGS}/{song_id}/assets/audio", content=WAV)

    assert response.status_code == 403


async def test_preview_serves_stored_bytes_with_range_and_media_type(uploads):
    """Breaks if previews return the wrong bytes, ignore Range, or use the wrong media type."""
    _, client, _, _ = uploads
    song_id = await _song(client)
    asset_id = (await _put(client, song_id, "audio", WAV)).json()["id"]

    response = await client.get(f"/api/admin/assets/{asset_id}/content", headers={"Range": "bytes=0-3"})

    assert response.status_code == 206
    assert response.content == b"RIFF"
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["cache-control"] == "no-store"


async def test_preview_of_unknown_asset_is_not_found(uploads):
    """Breaks if a preview request for a missing asset returns anything other than 404."""
    _, client, _, _ = uploads

    response = await client.get("/api/admin/assets/00000000-0000-4000-8000-00000000dead/content")

    assert response.status_code == 404


def test_symlinked_upload_root_is_refused(tmp_path):
    """Breaks if uploads are written through a symlink into an unintended directory."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError):
        AssetStorage(link)


def test_stale_staging_files_are_swept_but_fresh_ones_are_kept(tmp_path):
    """Breaks if abandoned uploads accumulate forever, or in-flight uploads are deleted."""
    storage = AssetStorage(tmp_path / "uploads")
    stale = storage.new_staging_path()
    fresh = storage.new_staging_path()
    stale.write_bytes(b"old")
    fresh.write_bytes(b"new")
    old_time = time.time() - 7200
    os.utime(stale, (old_time, old_time))

    storage.sweep_stale_staging(max_age_seconds=3600)

    assert not stale.exists()
    assert fresh.exists()


def test_object_path_refuses_anything_but_a_sha256_digest(tmp_path):
    """Breaks if a client-controlled value can influence the on-disk path."""
    with pytest.raises(ValueError):
        object_path(tmp_path, "../../etc/passwd", ".wav")


def _digest(data: bytes) -> str:
    """Returns the SHA-256 hex digest the storage layer uses as the object address."""
    import hashlib
    return hashlib.sha256(data).hexdigest()
