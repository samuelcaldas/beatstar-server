"""Format detection by magic bytes and client adapter selection; no file I/O."""

import pytest

from server.assets.client_adapters import ClientAdapterFactory, UnsupportedClientVersion
from server.assets.formats import default_registry

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 16
OGG = b"OggS\x00\x02" + b"\x00" * 20
MP3_TAGGED = b"ID3\x04\x00\x00" + b"\x00" * 20
MP3_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20


@pytest.mark.parametrize("head, kind, name", [
    (WAV, "audio", "wav"),
    (OGG, "audio", "ogg"),
    (MP3_TAGGED, "audio", "mp3"),
    (MP3_FRAME, "audio", "mp3"),
    (PNG, "artwork", "png"),
    (JPEG, "artwork", "jpeg"),
])
def test_known_signatures_are_detected_for_their_kind(head, kind, name):
    """Breaks if a real file of a supported format is rejected or mislabelled."""
    detected = default_registry().detect(kind, head)

    assert detected is not None
    assert detected.name == name
    assert detected.kind == kind


@pytest.mark.parametrize("head", [
    b"<script>alert(1)</script>",
    b"RIFF\x24\x00\x00\x00AVI LIST",
    b"PK\x03\x04" + b"\x00" * 20,
    b"",
])
def test_unknown_or_non_media_content_is_not_detected(head):
    """Breaks if text, archives or other RIFF containers are accepted as media."""
    assert default_registry().detect("audio", head) is None
    assert default_registry().detect("artwork", head) is None


def test_image_bytes_are_never_accepted_as_audio():
    """Breaks if a PNG renamed to an audio upload passes the audio signature check."""
    assert default_registry().detect("audio", PNG) is None


def test_audio_bytes_are_never_accepted_as_artwork():
    """Breaks if a WAV uploaded as artwork passes the image signature check."""
    assert default_registry().detect("artwork", WAV) is None


def test_source_adapter_is_selected_and_marked_not_client_compatible():
    """Breaks if source-only storage is reported as Android-compatible."""
    adapter = ClientAdapterFactory.default().create("source")

    assert adapter.client_compatible is False
    assert adapter.accepts(default_registry().detect("audio", WAV))


def test_unknown_client_version_is_refused_instead_of_guessed():
    """Breaks if an unregistered client version silently falls back to another format."""
    with pytest.raises(UnsupportedClientVersion):
        ClientAdapterFactory.default().create("36.1.4.9545")
