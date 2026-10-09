"""Request and response schemas for the song library API."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Difficulty = Literal["tutorial", "easy", "normal", "hard", "expert"]
SongStatus = Literal["draft", "published", "archived"]
TrimmedText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
MAXIMUM_PAGE_SIZE = 100


class SongCreate(BaseModel):
    """Fields required to create a draft song."""

    model_config = ConfigDict(extra="forbid")

    title: TrimmedText
    artist: TrimmedText
    difficulty: Difficulty


class SongUpdate(BaseModel):
    """Partial metadata change guarded by the revision the caller last read."""

    model_config = ConfigDict(extra="forbid")

    title: TrimmedText | None = None
    artist: TrimmedText | None = None
    difficulty: Difficulty | None = None
    expected_revision: int = Field(ge=1)

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "SongUpdate":
        """Rejects empty updates so that every accepted write changes something.

        Raises:
            ValueError: when no editable field is provided.
        """
        if self.title is None and self.artist is None and self.difficulty is None:
            raise ValueError("Provide at least one field to change")
        return self


class RevisionGuard(BaseModel):
    """Carries only the revision the caller expects for a state transition or deletion."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)


class SongOut(BaseModel):
    """Public representation of a song."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    artist: str
    difficulty: Difficulty
    status: SongStatus
    revision: int
    created_at: int
    updated_at: int


class SongPage(BaseModel):
    """One page of songs with the total count for the same filters."""

    items: list[SongOut]
    total: int
    page: int
    page_size: int


class SongQuery(BaseModel):
    """Validated list parameters; the service never sees unbounded input."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=MAXIMUM_PAGE_SIZE)
    search: str | None = Field(default=None, max_length=200)
    status: SongStatus | None = None
    difficulty: Difficulty | None = None
