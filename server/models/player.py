"""Domain models representing player entity and identity."""

from __future__ import annotations

import re
import uuid
from typing import Any
from pydantic import BaseModel, Field


class CintaIdentifier:
    """Value object wrapping player unique UUID."""

    UUID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    def __init__(self, raw_value: str | None = None) -> None:
        self._value = self._validate_and_assign(raw_value)

    def _validate_and_assign(self, raw: str | None) -> str:
        if not raw:
            return str(uuid.uuid4())
        if not self.UUID_PATTERN.match(raw):
            raise ValueError(f"Formato de Cinta inválido: {raw}")
        return raw.lower()

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value


class PlayerProfile(BaseModel):
    """Aggregate root for player profile state."""

    cinta: str = Field(default_factory=lambda: str(uuid.uuid4()))
    clide: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    player_name: str = Field(default="BeatstarPlayer")
    level: int = Field(default=1)
    stars: int = Field(default=0)
    coins: int = Field(default=1000)
    gems: int = Field(default=100)
    selected_song: str = Field(default="starter_song_01")
    unlocked_songs: list[str] = Field(
        default_factory=lambda: ["starter_song_01", "starter_song_02"]
    )
    customisation: dict[str, Any] = Field(default_factory=dict)
