"""Real media verifiers: ffprobe for audio, Pillow for artwork, behind the MediaProbe protocol.

External tools run as argument lists (never through a shell), in their own process group, with
CPU and address-space limits and a wall-clock budget. On timeout the whole group is killed, so
an orphaned child cannot keep the request open. A missing tool is reported as unavailable; it is
never treated as a successful verification.
"""

import json
import os
import resource
import signal
import subprocess
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from server.assets.formats import AUDIO, AssetFormat
from server.assets.ingest import (
    MediaProbe,
    ProbeReport,
    ProbeRejected,
    ProbeTimeout,
    VerificationUnavailable,
)

FFPROBE_TIMEOUT_SECONDS = 10.0
TOOL_CPU_SECONDS = 10
TOOL_ADDRESS_BYTES = 512 * 1024 * 1024


def _limit_tool_resources() -> None:
    """Applies CPU and address-space limits in the child before the tool starts."""
    resource.setrlimit(resource.RLIMIT_CPU, (TOOL_CPU_SECONDS, TOOL_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (TOOL_ADDRESS_BYTES, TOOL_ADDRESS_BYTES))


class FfprobeAudioProbe:
    """Reads duration and stream presence with ffprobe; never follows network protocols."""

    def __init__(self, binary: str = "ffprobe", timeout_seconds: float = FFPROBE_TIMEOUT_SECONDS) -> None:
        """Stores the executable and the wall-clock budget."""
        self._binary = binary
        self._timeout = timeout_seconds

    def inspect(self, path: Path, asset_format: AssetFormat) -> ProbeReport:
        """Returns the measured duration of a readable audio file.

        Raises:
            VerificationUnavailable: when the executable cannot be started.
            ProbeTimeout: when the budget expires; the process group is killed.
            ProbeRejected: when the file is unreadable or has no audio stream.
        """
        command = [
            self._binary, "-v", "error", "-protocol_whitelist", "file",
            "-print_format", "json", "-show_format", "-show_streams", str(path),
        ]
        stdout = self._run(command)
        return _audio_report(stdout)

    def _run(self, command: list[str]) -> bytes:
        """Runs the command in its own session and returns stdout when it exits successfully."""
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                start_new_session=True,
                preexec_fn=_limit_tool_resources,
            )
        except FileNotFoundError as error:
            raise VerificationUnavailable("ffprobe is not installed") from error
        try:
            stdout, _ = process.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ProbeTimeout("ffprobe exceeded its time budget") from error
        if process.returncode != 0:
            raise ProbeRejected("Audio could not be read")
        return stdout


def _audio_report(stdout: bytes) -> ProbeReport:
    """Extracts the duration from ffprobe's JSON output.

    Raises:
        ProbeRejected: when the output is not JSON or contains no audio stream.
    """
    try:
        document = json.loads(stdout)
    except ValueError as error:
        raise ProbeRejected("Audio verifier produced no readable result") from error
    streams = document.get("streams", [])
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise ProbeRejected("File contains no audio stream")
    duration = document.get("format", {}).get("duration")
    try:
        seconds = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        seconds = None
    return ProbeReport(duration_seconds=seconds, width=None, height=None)


class PillowArtworkProbe:
    """Verifies image structure and reads dimensions with Pillow, without a full pixel decode."""

    def inspect(self, path: Path, asset_format: AssetFormat) -> ProbeReport:
        """Returns the width and height of a structurally valid image.

        Raises:
            ProbeRejected: when the image cannot be identified or its structure is damaged.
        """
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as error:
            raise ProbeRejected("Artwork could not be decoded") from error
        return ProbeReport(duration_seconds=None, width=width, height=height)


class RoutingProbe:
    """Strategy selector: sends each file to the verifier for its kind."""

    def __init__(self, audio: MediaProbe, artwork: MediaProbe) -> None:
        """Stores one verifier per kind."""
        self._audio = audio
        self._artwork = artwork

    def inspect(self, path: Path, asset_format: AssetFormat) -> ProbeReport:
        """Delegates to the verifier registered for the format's kind."""
        verifier = self._audio if asset_format.kind == AUDIO else self._artwork
        return verifier.inspect(path, asset_format)


def default_media_probe() -> MediaProbe:
    """Returns the production verifier set: ffprobe for audio and Pillow for artwork."""
    return RoutingProbe(FfprobeAudioProbe(), PillowArtworkProbe())
