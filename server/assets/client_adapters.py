"""Client-specific asset handling behind a Strategy interface, selected by a Factory.

Uploads are stored as source files. A ClientAssetAdapter states what a particular game
client accepts. The source-only adapter accepts every recognised format but reports
client_compatible=False, so nothing can mistake stored source files for playable content.
A future adapter for a verified client version is registered in ClientAdapterFactory.default();
the upload pipeline itself does not change.
"""

from collections.abc import Callable
from typing import Protocol

from server.assets.formats import AssetFormat

SOURCE_ONLY = "source"


class UnsupportedClientVersion(Exception):
    """Raised when no adapter is registered for the requested client version."""


class ClientAssetAdapter(Protocol):
    """Strategy describing one client's asset requirements."""

    client_version: str
    client_compatible: bool

    def accepts(self, asset_format: AssetFormat | None) -> bool:
        """Returns True when this adapter can store an upload of the given format."""


class SourceOnlyAdapter:
    """Accepts recognised source formats and makes no claim about any game client."""

    client_version = SOURCE_ONLY
    client_compatible = False

    def accepts(self, asset_format: AssetFormat | None) -> bool:
        """Returns True for any format the detector recognised."""
        return asset_format is not None


class ClientAdapterFactory:
    """Creates adapters by client version; unknown versions raise instead of falling back."""

    def __init__(self, builders: dict[str, Callable[[], ClientAssetAdapter]]) -> None:
        """Stores one builder per supported client version."""
        self._builders = dict(builders)

    def create(self, client_version: str) -> ClientAssetAdapter:
        """Returns a new adapter for the version.

        Raises:
            UnsupportedClientVersion: when the version has no registered builder.
        """
        builder = self._builders.get(client_version)
        if builder is None:
            raise UnsupportedClientVersion(f"No asset adapter registered for client {client_version}")
        return builder()

    @classmethod
    def default(cls) -> "ClientAdapterFactory":
        """Returns the factory with only the source-only adapter registered."""
        return cls({SOURCE_ONLY: SourceOnlyAdapter})
