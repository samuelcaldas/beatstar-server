"""Onboarding, terms, preferences and starter catalog handlers."""

from __future__ import annotations

import time
from typing import Any
from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/v1", tags=["onboarding"])

STARTER_SONGS = [
    {
        "id": 710,
        "string_id": "starter_song_01",
        "title": "Welcome to the Rhythm",
        "artist": "Space Ape Beats",
        "difficulty": "Normal",
        "beatmap_id": 660,
    },
    {
        "id": 711,
        "string_id": "starter_song_02",
        "title": "Neon Beat",
        "artist": "Flamingo Studio",
        "difficulty": "Hard",
        "beatmap_id": 661,
    },
    {
        "id": 712,
        "string_id": "starter_song_03",
        "title": "Pulse Wave",
        "artist": "Synthwave Crew",
        "difficulty": "Normal",
        "beatmap_id": 662,
    },
    {
        "id": 713,
        "string_id": "starter_song_04",
        "title": "Supernova",
        "artist": "Cosmic Sound",
        "difficulty": "Expert",
        "beatmap_id": 663,
    },
]

@router.get("/songs/starters")
def get_starter_songs() -> dict[str, Any]:
    """Returns the four confirmed starter songs for onboarding/tutorial."""
    return {
        "status": 200,
        "timestamp": int(time.time() * 1000),
        "songs": STARTER_SONGS,
    }

@router.post("/onboarding/terms")
def accept_terms(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Records terms of use acceptance."""
    return {
        "status": 200,
        "accepted": True,
        "timestamp": int(time.time() * 1000),
        "received": payload,
    }

@router.post("/onboarding/preferences")
def save_preferences(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Records initial user preferences."""
    return {
        "status": 200,
        "saved": True,
        "timestamp": int(time.time() * 1000),
        "received": payload,
    }
