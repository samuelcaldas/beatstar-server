"""Domain models for gameplay, progression, leaderboards, and social interaction."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class MedalType(str, Enum):
    """Medal tiers awarded based on rhythm game scores."""

    NONE = "none"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    DIAMOND_PERFECT = "diamond_perfect"


class VenueDefinition(BaseModel):
    """Represents a milestone Journey venue/stage."""

    level: int
    name: str
    stars_required: int
    unlocked_songs: list[str] = Field(default_factory=list)
    bonus_coins: int = 100
    bonus_gems: int = 10


class SongScoreRecord(BaseModel):
    """High score entry achieved by a player on a specific beatmap."""

    cinta: str
    clide: str
    song_id: str
    score: int
    stars: int
    medal: MedalType = MedalType.NONE
    accuracy: float = 1.0
    updated_at: int = 0


class LeaderboardEntry(BaseModel):
    """Single row entry in global, song, or friend leaderboards."""

    rank: int
    cinta: str
    clide: str
    player_name: str
    score: int
    total_stars: int
    venue_level: int
    medal: MedalType = MedalType.NONE


class FriendBragRecord(BaseModel):
    """Competitive score challenge issued to a friend."""

    brag_id: str
    sender_cinta: str
    sender_name: str
    target_cinta: str
    song_id: str
    score_to_beat: int
    beaten: bool = False
    created_at: int = 0
