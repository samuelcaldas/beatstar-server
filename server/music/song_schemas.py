"""Request and response schemas for the song library API."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Difficulty = Literal["tutorial", "easy", "normal", "hard", "expert"]
SongStatus = Literal["draft", "published", "archived"]
SongSource = Literal["manual", "unity-import", "example"]
TrimmedText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
GameIdentifier = Annotated[int, Field(ge=1, le=2_147_483_647)]
Bpm = Annotated[float, Field(gt=20, le=300)]
BeatsPerBar = Annotated[int, Field(ge=1, le=16)]
VariantLabel = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
ChartBeat = Annotated[float, Field(ge=0, le=100_000)]
ChartLane = Annotated[int, Field(ge=1, le=3)]
MAXIMUM_PAGE_SIZE = 100
MAXIMUM_NOTES_PER_REQUEST = 5_000


class SongCreate(BaseModel):
    """Fields required to create a draft song; game identity is optional until the song is wired to the game."""

    model_config = ConfigDict(extra="forbid")

    title: TrimmedText
    artist: TrimmedText
    difficulty: Difficulty
    game_song_id: GameIdentifier | None = None
    beatmap_id: GameIdentifier | None = None
    bpm: Bpm | None = None
    time_signature: BeatsPerBar | None = None
    variant_label: VariantLabel | None = None


class SongUpdate(BaseModel):
    """Partial metadata change guarded by the revision the caller last read."""

    model_config = ConfigDict(extra="forbid")

    title: TrimmedText | None = None
    artist: TrimmedText | None = None
    difficulty: Difficulty | None = None
    bpm: Bpm | None = None
    time_signature: BeatsPerBar | None = None
    variant_label: VariantLabel | None = None
    expected_revision: int = Field(ge=1)

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "SongUpdate":
        """Rejects empty updates so that every accepted write changes something.

        Raises:
            ValueError: when no editable field is provided.
        """
        editable = (self.title, self.artist, self.difficulty, self.bpm, self.time_signature, self.variant_label)
        if all(value is None for value in editable):
            raise ValueError("Provide at least one field to change")
        return self


class RevisionGuard(BaseModel):
    """Carries only the revision the caller expects for a state transition or deletion."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)


class SongOut(BaseModel):
    """Public representation of a song, including the identity the game uses for it."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    artist: str
    difficulty: Difficulty
    game_song_id: int | None
    beatmap_id: int | None
    bpm: float | None
    time_signature: int | None
    variant_label: str | None
    source: SongSource
    status: SongStatus
    revision: int
    created_at: int
    updated_at: int


class ChartNoteIn(BaseModel):
    """One tap note authored in the administration UI."""

    model_config = ConfigDict(extra="forbid")

    beat_offset: ChartBeat
    lane: ChartLane


class ChartCreate(BaseModel):
    """Notes for a new chart revision; revisions are immutable and numbered by the server."""

    model_config = ConfigDict(extra="forbid")

    notes: list[ChartNoteIn] = Field(min_length=1, max_length=MAXIMUM_NOTES_PER_REQUEST)


class ChartOut(BaseModel):
    """Summary of one chart revision; the raw Raksha bytes are never returned as JSON."""

    id: str
    song_id: str
    revision_number: int
    schema_version: int
    beatmap_id: int
    id_label: str
    note_count: int
    unsupported_count: int
    lanes: dict[str, int]
    first_beat: float | None
    last_beat: float | None
    raw_sha256: str
    created_at: int


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
