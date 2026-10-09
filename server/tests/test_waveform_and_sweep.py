"""Waveform peaks generated from real audio, served as immutable previews, and startup staging sweep."""

import os
import time
import wave
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app
from server.assets.formats import AUDIO, AssetFormat
from server.assets.ingest import AssetLimits, ProbeRejected, VerificationUnavailable
from server.assets.probes import FfprobeAudioProbe
from server.assets.storage import AssetStorage, ConflictingObject
from server.assets.waveform import FfmpegWaveform

SECRET = "test-admin-secret-with-at-least-32-characters"
ORIGIN = "http://test"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
WAV_FORMAT = AssetFormat(AUDIO, "wav", ".wav", "audio/wav")


def _write_half_silent_wav(path: Path) -> Path:
    """Writes two seconds: silence, then a full-scale square wave. Peaks must reflect this shape."""
    sample_rate = 8000
    silence = b"\x00\x00" * sample_rate
    loud = (b"\xff\x7f" * (sample_rate // 2) + b"\x00\x80" * (sample_rate // 2)) * 1
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(silence + loud)
    return path


def test_peaks_follow_the_real_shape_of_the_audio(tmp_path):
    """Breaks if waveform peaks are not derived from the decoded samples."""
    wav = _write_half_silent_wav(tmp_path / "shape.wav")

    peaks = FfmpegWaveform(bins=8).generate(wav, WAV_FORMAT)

    assert len(peaks) == 8
    assert max(peaks[:4]) < 10
    assert min(peaks[4:]) > 200


def test_missing_ffmpeg_is_unavailable_not_an_empty_waveform(tmp_path):
    """Breaks if an absent decoder produces a silent-looking waveform instead of a refusal."""
    wav = _write_half_silent_wav(tmp_path / "any.wav")

    with pytest.raises(VerificationUnavailable):
        FfmpegWaveform(binary="/nonexistent/ffmpeg").generate(wav, WAV_FORMAT)


def test_undecodable_audio_yields_no_waveform(tmp_path):
    """Breaks if a file whose decode fails gets a fabricated waveform."""
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\xde\xad" * 64)

    with pytest.raises(ProbeRejected):
        FfmpegWaveform().generate(broken, WAV_FORMAT)


def test_storage_refuses_to_replace_an_existing_preview(tmp_path):
    """Breaks if a committed preview can be silently replaced by different peaks."""
    storage = AssetStorage(tmp_path / "uploads")
    digest = "a" * 64
    first = storage.new_staging_path()
    first.write_bytes(b'{"peaks": [1]}')
    storage.commit_preview(first, digest)

    second = storage.new_staging_path()
    second.write_bytes(b'{"peaks": [2]}')
    with pytest.raises(ConflictingObject):
        storage.commit_preview(second, digest)

    assert storage.preview_path(digest).read_bytes() == b'{"peaks": [1]}'


class ScriptedWaveform:
    """Boundary double for the decoder; returns fixed peaks or raises a fixed error."""

    def __init__(self, error: Exception | None = None) -> None:
        """Stores the outcome every generation will produce."""
        self._error = error

    def generate(self, path: Path, asset_format: AssetFormat) -> list[int]:
        """Raises the scripted error, or returns a fixed peak list."""
        if self._error is not None:
            raise self._error
        return [1, 2, 3]


@pytest.fixture
async def audio_app(tmp_path, monkeypatch):
    """Administrator client with the real ffprobe verifier and the real waveform decoder."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(
        secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,), login_max_attempts=50
    )
    app = create_app(
        database_path=str(tmp_path / "waveform.db"),
        admin_settings=settings,
        asset_root=tmp_path / "uploads",
    )
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
            yield app, client


async def _song_and_upload(client, wav: Path):
    """Creates a song and uploads the WAV; returns the upload response."""
    song = await client.post(
        "/api/admin/songs",
        json={"title": "Waveform", "artist": "Artist", "difficulty": "normal"},
        headers={CSRF_HEADER: client.cookies.get(CSRF_COOKIE)},
    )
    return await client.put(
        f"/api/admin/songs/{song.json()['id']}/assets/audio",
        content=wav.read_bytes(),
        headers={CSRF_HEADER: client.cookies.get(CSRF_COOKIE)},
    )


async def test_uploaded_audio_exposes_its_waveform_as_an_immutable_preview(audio_app, tmp_path):
    """Breaks if an accepted upload has no retrievable waveform, or the preview is not served."""
    _, client = audio_app
    wav = _write_half_silent_wav(tmp_path / "upload.wav")

    uploaded = await _song_and_upload(client, wav)
    asset_id = uploaded.json()["id"]
    waveform = await client.get(f"/api/admin/assets/{asset_id}/waveform")

    assert uploaded.status_code == 201
    assert waveform.status_code == 200
    assert waveform.headers["cache-control"] == "no-store"
    body = waveform.json()
    assert body["bins"] == len(body["peaks"]) == 256
    assert max(body["peaks"][:64]) < 10
    assert min(body["peaks"][128:]) > 200


async def test_waveform_failure_refuses_the_upload_and_leaves_nothing(tmp_path, monkeypatch):
    """Breaks if an accepted audio file is stored without the preview it promises."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(
        secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,), login_max_attempts=50
    )
    app = create_app(
        database_path=str(tmp_path / "refused.db"),
        admin_settings=settings,
        asset_root=tmp_path / "uploads",
        media_probe=_AcceptingProbe(),
        waveform=ScriptedWaveform(error=ProbeRejected("decoder failed")),
    )
    wav = _write_half_silent_wav(tmp_path / "refused.wav")
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
            uploaded = await _song_and_upload(client, wav)

    assert uploaded.status_code == 422
    assert [p for p in (tmp_path / "uploads").rglob("*") if p.is_file()] == []


async def test_artwork_has_no_waveform_and_unknown_assets_are_not_found(audio_app, tmp_path):
    """Breaks if a non-audio asset is offered a waveform it cannot have, or a missing asset is not 404."""
    from PIL import Image

    _, client = audio_app
    png = tmp_path / "cover.png"
    Image.new("RGB", (32, 32), (1, 2, 3)).save(png, format="PNG")
    song = await client.post(
        "/api/admin/songs",
        json={"title": "Cover", "artist": "Artist", "difficulty": "normal"},
        headers={CSRF_HEADER: client.cookies.get(CSRF_COOKIE)},
    )
    artwork = await client.put(
        f"/api/admin/songs/{song.json()['id']}/assets/artwork",
        content=png.read_bytes(),
        headers={CSRF_HEADER: client.cookies.get(CSRF_COOKIE)},
    )
    artwork_id = artwork.json()["id"]

    response = await client.get(f"/api/admin/assets/{artwork_id}/waveform")
    unknown = await client.get("/api/admin/assets/00000000-0000-4000-8000-00000000dead/waveform")

    assert artwork.status_code == 201
    assert response.status_code == 404
    assert unknown.status_code == 404


async def test_startup_removes_stale_staging_files_and_keeps_fresh_ones(tmp_path, monkeypatch):
    """Breaks if abandoned uploads survive restarts, or in-flight uploads are removed at startup."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "uploads"
    storage = AssetStorage(root)
    stale = storage.new_staging_path()
    fresh = storage.new_staging_path()
    stale.write_bytes(b"abandoned")
    fresh.write_bytes(b"in flight")
    old = time.time() - 10 * 3600
    os.utime(stale, (old, old))
    settings = AdminAuthSettings(secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,))
    app = create_app(
        database_path=str(tmp_path / "sweep.db"),
        admin_settings=settings,
        asset_root=root,
        asset_limits=AssetLimits(staging_max_age_seconds=3600),
    )

    async with app.router.lifespan_context(app):
        assert not stale.exists()
        assert fresh.exists()


class _AcceptingProbe:
    """Boundary double for the verifier: accepts any audio with a fixed duration."""

    def inspect(self, path: Path, asset_format: AssetFormat):
        """Returns a plausible report so that only the waveform stage can refuse."""
        from server.assets.ingest import ProbeReport
        return ProbeReport(duration_seconds=2.0, width=None, height=None)
