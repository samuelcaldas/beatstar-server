"""Real media verification: ffprobe for audio and Pillow for artwork, on generated files."""

import stat
import time
import wave
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app
from server.assets.formats import ARTWORK, AUDIO, AssetFormat
from server.assets.ingest import ProbeRejected, ProbeTimeout, VerificationUnavailable
from server.assets.probes import FfprobeAudioProbe, PillowArtworkProbe

SECRET = "test-admin-secret-with-at-least-32-characters"
ORIGIN = "http://test"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
WAV_FORMAT = AssetFormat(AUDIO, "wav", ".wav", "audio/wav")
PNG_FORMAT = AssetFormat(ARTWORK, "png", ".png", "image/png")


def _write_wav(path: Path, seconds: float, sample_rate: int = 8000) -> Path:
    """Writes a mono 8-bit silent WAV of the requested length."""
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(1)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x80" * frames)
    return path


def _write_png(path: Path, width: int, height: int) -> Path:
    """Writes a solid-colour PNG of the requested dimensions."""
    Image.new("RGB", (width, height), (10, 20, 30)).save(path, format="PNG")
    return path


def test_ffprobe_reports_the_duration_of_a_real_wav(tmp_path):
    """Breaks if verification does not read real duration from the file."""
    wav = _write_wav(tmp_path / "one-second.wav", seconds=1.0)

    report = FfprobeAudioProbe().inspect(wav, WAV_FORMAT)

    assert report.duration_seconds == pytest.approx(1.0, abs=0.05)


def test_ffprobe_rejects_a_wav_header_followed_by_garbage(tmp_path):
    """Breaks if a file that only looks like a WAV at the first bytes is accepted."""
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\xde\xad\xbe\xef" * 64)

    with pytest.raises(ProbeRejected):
        FfprobeAudioProbe().inspect(broken, WAV_FORMAT)


def test_missing_ffprobe_is_reported_as_unavailable_not_as_success(tmp_path):
    """Breaks if an absent verifier is treated as a passing verification."""
    wav = _write_wav(tmp_path / "any.wav", seconds=0.5)

    with pytest.raises(VerificationUnavailable):
        FfprobeAudioProbe(binary="/nonexistent/ffprobe").inspect(wav, WAV_FORMAT)


def test_slow_verifier_is_stopped_at_its_time_budget(tmp_path):
    """Breaks if a hung verifier can hold an upload request open indefinitely."""
    slow = tmp_path / "slow-probe"
    slow.write_text("#!/bin/sh\nsleep 5\n")
    slow.chmod(slow.stat().st_mode | stat.S_IXUSR)
    wav = _write_wav(tmp_path / "wait.wav", seconds=0.2)
    started = time.monotonic()

    with pytest.raises(ProbeTimeout):
        FfprobeAudioProbe(binary=str(slow), timeout_seconds=0.5).inspect(wav, WAV_FORMAT)

    assert time.monotonic() - started < 3


def test_pillow_reports_the_dimensions_of_a_real_png(tmp_path):
    """Breaks if artwork dimensions are not read from the file itself."""
    png = _write_png(tmp_path / "cover.png", width=320, height=180)

    report = PillowArtworkProbe().inspect(png, PNG_FORMAT)

    assert (report.width, report.height) == (320, 180)


def test_pillow_rejects_a_truncated_image(tmp_path):
    """Breaks if a truncated PNG with a valid signature is accepted as artwork."""
    truncated = tmp_path / "cut.png"
    truncated.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 12)

    with pytest.raises(ProbeRejected):
        PillowArtworkProbe().inspect(truncated, PNG_FORMAT)


@pytest.fixture
async def default_pipeline(tmp_path, monkeypatch):
    """An administrator client using the real default verifiers, not a scripted one."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(
        secret=SECRET, cookie_secure=False, allowed_origins=(ORIGIN,), login_max_attempts=50
    )
    app = create_app(
        database_path=str(tmp_path / "real.db"),
        admin_settings=settings,
        asset_root=tmp_path / "uploads",
    )
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
            yield client


async def _new_song(client) -> str:
    """Creates a draft song for an upload."""
    response = await client.post(
        "/api/admin/songs",
        json={"title": "Real media", "artist": "Artist", "difficulty": "normal"},
        headers={CSRF_HEADER: client.cookies.get(CSRF_COOKIE)},
    )
    return response.json()["id"]


async def _upload(client, song_id: str, kind: str, path: Path):
    """Uploads a file's bytes through the raw PUT endpoint."""
    return await client.put(
        f"/api/admin/songs/{song_id}/assets/{kind}",
        content=path.read_bytes(),
        headers={CSRF_HEADER: client.cookies.get(CSRF_COOKIE)},
    )


async def test_real_wav_is_accepted_with_measured_duration(default_pipeline, tmp_path):
    """Breaks if the default pipeline cannot accept a genuine audio file end to end."""
    wav = _write_wav(tmp_path / "ok.wav", seconds=2.0)
    song_id = await _new_song(default_pipeline)

    response = await _upload(default_pipeline, song_id, "audio", wav)

    assert response.status_code == 201
    assert response.json()["duration_milliseconds"] == pytest.approx(2000, abs=60)


async def test_real_png_is_accepted_with_measured_dimensions(default_pipeline, tmp_path):
    """Breaks if artwork is accepted without its real dimensions being recorded."""
    png = _write_png(tmp_path / "cover.png", width=256, height=256)
    song_id = await _new_song(default_pipeline)

    response = await _upload(default_pipeline, song_id, "artwork", png)

    assert response.status_code == 201
    assert (response.json()["width"], response.json()["height"]) == (256, 256)


async def test_real_audio_longer_than_the_maximum_is_refused(default_pipeline, tmp_path):
    """Breaks if a genuine file that exceeds the duration bound is stored."""
    long_wav = _write_wav(tmp_path / "long.wav", seconds=601.0)
    song_id = await _new_song(default_pipeline)

    response = await _upload(default_pipeline, song_id, "audio", long_wav)

    assert response.status_code == 422
