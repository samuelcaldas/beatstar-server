"""Domain failures for the song library; the router maps each to one HTTP response."""


class SongError(Exception):
    """Base class for song library failures."""


class SongNotFound(SongError):
    """Raised when no song has the requested identifier."""


class RevisionConflict(SongError):
    """Raised when the caller's expected revision is no longer current."""

    def __init__(self, current_revision: int) -> None:
        """Stores the revision the caller must reload before retrying."""
        super().__init__(f"Song changed; current revision is {current_revision}")
        self.current_revision = current_revision


class InvalidSongState(SongError):
    """Raised when the requested transition is not allowed from the song's current status."""


class SongInUse(SongError):
    """Raised when a hard delete would orphan assets, charts, jobs or releases."""
