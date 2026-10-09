"""Waveform peaks decoded with FFmpeg (Strategy: WaveformGenerator).

The file is decoded to 16-bit mono PCM at a low rate on stdout, then reduced to a fixed number
of bins; each bin keeps the largest absolute amplitude scaled to 0..255. The decoder runs
through the same sandboxed runner as the probes, so a hostile file cannot hold the request open.
"""

import math
from array import array
from pathlib import Path

from server.assets.formats import AssetFormat
from server.assets.ingest import ProbeRejected
from server.assets.probes import run_tool

DEFAULT_BINS = 256
DECODE_RATE_HZ = 8000
DECODE_TIMEOUT_SECONDS = 60.0
FULL_SCALE = 32768


class FfmpegWaveform:
    """Derives fixed-resolution peak data from the decoded samples of an audio file."""

    def __init__(
        self,
        binary: str = "ffmpeg",
        bins: int = DEFAULT_BINS,
        timeout_seconds: float = DECODE_TIMEOUT_SECONDS,
    ) -> None:
        """Stores the decoder executable, the number of output bins and the time budget."""
        self._binary = binary
        self._bins = bins
        self._timeout = timeout_seconds

    def generate(self, path: Path, asset_format: AssetFormat) -> list[int]:
        """Returns one peak per bin, each in 0..255.

        Raises:
            VerificationUnavailable: when the decoder is not installed.
            ProbeTimeout: when decoding exceeds the budget.
            ProbeRejected: when the file cannot be decoded or yields no samples.
        """
        command = [
            self._binary, "-v", "error", "-protocol_whitelist", "file", "-i", str(path),
            "-vn", "-ac", "1", "-ar", str(DECODE_RATE_HZ), "-f", "s16le", "pipe:1",
        ]
        raw = run_tool(command, self._timeout, "ffmpeg", "Audio could not be decoded")
        samples = _samples(raw)
        if not samples:
            raise ProbeRejected("Audio decoded to no samples")
        return _peaks(samples, self._bins)


def _samples(raw: bytes) -> array:
    """Interprets decoder output as signed 16-bit samples, dropping a dangling odd byte."""
    usable = raw[: len(raw) - (len(raw) % 2)]
    samples = array("h")
    samples.frombytes(usable)
    return samples


def _peaks(samples: array, bins: int) -> list[int]:
    """Reduces samples to bins, keeping each bin's largest absolute amplitude scaled to 0..255."""
    count = len(samples)
    peaks = []
    for index in range(bins):
        start = index * count // bins
        end = max((index + 1) * count // bins, start + 1)
        loudest = max((abs(value) for value in samples[start:end]), default=0)
        peaks.append(min(255, math.ceil(loudest * 255 / FULL_SCALE)))
    return peaks
