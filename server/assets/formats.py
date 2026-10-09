"""Format detection by magic bytes (Strategy pattern).

Each supported format is one FormatRule. The registry asks every rule registered for the
requested kind, so an audio upload can never be accepted by an image rule and vice versa.
Client-specific handling is not decided here; see client_adapters.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

AUDIO = "audio"
ARTWORK = "artwork"
HEADER_BYTES = 64


@dataclass(frozen=True)
class AssetFormat:
    """A recognised media format; extension and content type come from the format, not the client."""

    kind: str
    name: str
    extension: str
    content_type: str


class FormatRule(ABC):
    """Decides whether a file header belongs to one format."""

    def __init__(self, asset_format: AssetFormat) -> None:
        """Binds the rule to the format it recognises."""
        self.asset_format = asset_format

    @abstractmethod
    def matches(self, head: bytes) -> bool:
        """Returns True when the leading bytes match this format's signature."""


class PrefixRule(FormatRule):
    """Matches a fixed byte signature at the start of the file."""

    def __init__(self, asset_format: AssetFormat, signature: bytes) -> None:
        """Stores the signature to match."""
        super().__init__(asset_format)
        self._signature = signature

    def matches(self, head: bytes) -> bool:
        """Returns True when the header starts with the signature."""
        return head.startswith(self._signature)


class RiffWaveRule(FormatRule):
    """Matches a RIFF container whose form type is WAVE; other RIFF forms are rejected."""

    def matches(self, head: bytes) -> bool:
        """Returns True for RIFF....WAVE headers."""
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"


class Mp3Rule(FormatRule):
    """Matches an ID3 tag or an MPEG audio frame sync (eleven set bits)."""

    def matches(self, head: bytes) -> bool:
        """Returns True for ID3-tagged or frame-synchronised MP3 headers."""
        if head.startswith(b"ID3"):
            return True
        return len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0


class FormatRegistry:
    """Holds rules and answers which format, if any, a header belongs to for one kind."""

    def __init__(self, rules: list[FormatRule]) -> None:
        """Stores the rules in registration order; the first matching rule wins."""
        self._rules = list(rules)

    def detect(self, kind: str, head: bytes) -> AssetFormat | None:
        """Returns the format for head within kind, or None when no rule matches.

        Args:
            kind: AUDIO or ARTWORK; rules of other kinds are never consulted.
            head: The leading bytes of the upload, at most HEADER_BYTES long.
        """
        candidate = head[:HEADER_BYTES]
        for rule in self._rules:
            if rule.asset_format.kind == kind and rule.matches(candidate):
                return rule.asset_format
        return None


def default_registry() -> FormatRegistry:
    """Returns the registry for the formats accepted as source uploads."""
    wav = AssetFormat(AUDIO, "wav", ".wav", "audio/wav")
    ogg = AssetFormat(AUDIO, "ogg", ".ogg", "audio/ogg")
    mp3 = AssetFormat(AUDIO, "mp3", ".mp3", "audio/mpeg")
    png = AssetFormat(ARTWORK, "png", ".png", "image/png")
    jpeg = AssetFormat(ARTWORK, "jpeg", ".jpg", "image/jpeg")
    return FormatRegistry([
        RiffWaveRule(wav),
        PrefixRule(ogg, b"OggS"),
        Mp3Rule(mp3),
        PrefixRule(png, b"\x89PNG\r\n\x1a\n"),
        PrefixRule(jpeg, b"\xff\xd8\xff"),
    ])
