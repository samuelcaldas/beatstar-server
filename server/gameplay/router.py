"""FastAPI router for Gameplay, Progression, Multiplayer, and Leaderboards."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from server.config import settings
from server.gameplay.service import GameplayService
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository

gameplay_router = APIRouter()
db_manager = DatabaseManager(settings.database_url.replace("sqlite+aiosqlite:///", ""))
player_repository = PlayerRepository(db_manager)
gameplay_service = GameplayService(db_manager)


class ScoreSubmitPayload(BaseModel):
    cinta: str
    song_id: str
    score: int
    accuracy: float = 1.0


class FriendAddPayload(BaseModel):
    player_cinta: str
    friend_identifier: str


@gameplay_router.get("/progression/{cinta}")
async def get_progression(cinta: str) -> dict[str, Any]:
    """Retrieves player journey venue, stars, and unlock progression."""
    profile = await player_repository.get_by_cinta(cinta)
    if not profile:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    venue = gameplay_service.progression.calculate_current_venue(profile.stars)
    return {
        "cinta": profile.cinta,
        "level": profile.level,
        "stars": profile.stars,
        "current_venue": venue.model_dump(),
        "unlocked_songs": profile.unlocked_songs,
    }


@gameplay_router.get("/leaderboards/global")
async def get_global_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    cinta: str | None = None,
    friends_only: bool = False,
) -> list[dict[str, Any]]:
    """Retrieves global or friends-only cumulative score leaderboard."""
    entries = await gameplay_service.get_leaderboard(
        song_id=None, friends_only=friends_only, player_cinta=cinta, limit=limit
    )
    return [e.model_dump() for e in entries]


@gameplay_router.get("/leaderboards/song/{song_id}")
async def get_song_leaderboard(
    song_id: str,
    limit: int = Query(50, ge=1, le=100),
    cinta: str | None = None,
    friends_only: bool = False,
) -> list[dict[str, Any]]:
    """Retrieves high scores for a specific beatmap."""
    entries = await gameplay_service.get_leaderboard(
        song_id=song_id, friends_only=friends_only, player_cinta=cinta, limit=limit
    )
    return [e.model_dump() for e in entries]


@gameplay_router.post("/scores/submit")
async def submit_score(payload: ScoreSubmitPayload) -> dict[str, Any]:
    """Submits song performance and triggers progression / rival challenges."""
    profile = await player_repository.get_by_cinta(payload.cinta)
    if not profile:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    result = await gameplay_service.submit_score(
        profile, payload.song_id, payload.score, payload.accuracy
    )
    await player_repository.save(profile)
    return result


@gameplay_router.get("/friends/{cinta}")
async def list_friends(cinta: str) -> list[dict[str, Any]]:
    """Lists confirmed friends for a player."""
    return await gameplay_service.multiplayer.list_friends(cinta)


@gameplay_router.post("/friends/add")
async def add_friend(payload: FriendAddPayload) -> dict[str, Any]:
    """Adds a friend by cinta UUID or clide."""
    success = await gameplay_service.multiplayer.add_friend(
        payload.player_cinta, payload.friend_identifier
    )
    if not success:
        raise HTTPException(status_code=400, detail="Não foi possível adicionar amigo.")
    return {"success": True, "message": "Amizade estabelecida com sucesso."}


@gameplay_router.get("/brags/{cinta}")
async def list_brags(cinta: str) -> list[dict[str, Any]]:
    """Retrieves pending rival challenges sent to player."""
    brags = await gameplay_service.brags.get_pending_brags(cinta)
    return [b.model_dump() for b in brags]
