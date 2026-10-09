"""Beatmap data structures and types for SpaceApe Beatstar charts."""

from __future__ import annotations

from enum import IntEnum
from typing import Any
from pydantic import BaseModel, Field


class InteractionType(IntEnum):
    """Note interaction type matching SpaceApe InteractionType enum."""

    NONE = 0
    TAP = 1
    DRAG = 2
    TAP_HOLD_DEPRECATED = 3
    BENDY_HOLD_DEPRECATED = 4
    SWITCH_HOLD = 5


class FlickDirection(IntEnum):
    """Direction for swipe/flick notes matching SpaceApe FlickDirection enum."""

    NONE = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
    LEFT_UP = 5
    RIGHT_UP = 6
    RIGHT_DOWN = 7
    LEFT_DOWN = 8


class InteractionPoint(BaseModel):
    """A spatial and temporal point on a track lane."""

    beat_offset: float = Field(default=0.0, description="Musical beat timing offset")
    lane: int = Field(default=1, description="Track lane index (1, 2, or 3)")


class TapInteractionData(BaseModel):
    """Data for an instantaneous tap or swipe note."""

    point: InteractionPoint = Field(default_factory=InteractionPoint)
    flick: FlickDirection = Field(default=FlickDirection.NONE)


class DragInteractionData(BaseModel):
    """Data for a sustained hold / drag note across one or more points."""

    points: list[InteractionPoint] = Field(default_factory=list)
    flick: FlickDirection = Field(default=FlickDirection.NONE)


class InteractionData(BaseModel):
    """Represents a playable note or interaction element in the chart."""

    interaction_type: InteractionType = Field(default=InteractionType.TAP)
    track: int = Field(default=1, description="Physical visual lane (1, 2, or 3)")
    tap_data: TapInteractionData | None = None
    drag_data: DragInteractionData | None = None
    raw_extra: dict[int, Any] = Field(default_factory=dict, description="Preserved extra tags for wire roundtrip")


class BeatmapStar(BaseModel):
    """Threshold required to earn a specific star level."""

    star_index: int = 1
    points_required: int = 0


class BeatmapInteractionsTemplate(BaseModel):
    """Top-level Beatstar chart containing all gameplay notes and metadata."""

    id: int = Field(default=0, description="Unique variant identifier")
    id_label: str = Field(default="", description="Human-readable label, e.g. '710-1'")
    interactions: list[InteractionData] = Field(default_factory=list)
    stars: list[BeatmapStar] = Field(default_factory=list)
    raw_trailing_tags: dict[int, bytes] = Field(
        default_factory=dict, description="Additional tags preserved for byte-for-byte fidelity"
    )
