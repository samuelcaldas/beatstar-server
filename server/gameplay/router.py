"""FastAPI router for Gameplay, Progression, Multiplayer, and Leaderboards."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from server.gameplay.service import GameplayService
from server.player_auth.policy import TICKET_HEADER, PlayerTicketPolicy
from server.storage.player_repository import PlayerRepository


class ScoreSubmitPayload(BaseModel):
    cinta: str
    song_id: str
    score: int
    accuracy: float = 1.0


class FriendAddPayload(BaseModel):
    player_cinta: str
    friend_identifier: str


def build_gameplay_router(
    gameplay_service: GameplayService,
    player_repository: PlayerRepository,
    ticket_policy: PlayerTicketPolicy,
) -> APIRouter:
    """Builds gameplay routes bound to one service, one player repository and one ticket policy.

    Leaderboards stay public; every route that acts on one player's data checks the ticket.
    """
    router = APIRouter()

    @router.get("/progression/{cinta}")
    async def get_progression(cinta: str, request: Request) -> dict[str, Any]:
        """Retrieves player journey venue, stars, and unlock progression."""
        await ticket_policy.authorize(request.headers.get(TICKET_HEADER), cinta, "gameplay.progression")
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

    @router.get("/leaderboards/global")
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

    @router.get("/leaderboards/song/{song_id}")
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

    @router.post("/scores/submit")
    async def submit_score(payload: ScoreSubmitPayload, request: Request) -> dict[str, Any]:
        """Submits song performance and triggers progression / rival challenges."""
        await ticket_policy.authorize(request.headers.get(TICKET_HEADER), payload.cinta, "gameplay.scores")
        profile = await player_repository.get_by_cinta(payload.cinta)
        if not profile:
            raise HTTPException(status_code=404, detail="Jogador não encontrado")
        result = await gameplay_service.submit_score(
            profile, payload.song_id, payload.score, payload.accuracy
        )
        await player_repository.save(profile)
        return result

    @router.get("/friends/{cinta}")
    async def list_friends(cinta: str, request: Request) -> list[dict[str, Any]]:
        """Lists confirmed friends for a player."""
        await ticket_policy.authorize(request.headers.get(TICKET_HEADER), cinta, "gameplay.friends")
        return await gameplay_service.multiplayer.list_friends(cinta)

    @router.post("/friends/add")
    async def add_friend(payload: FriendAddPayload, request: Request) -> dict[str, Any]:
        """Adds a friend by cinta UUID or clide."""
        await ticket_policy.authorize(request.headers.get(TICKET_HEADER), payload.player_cinta, "gameplay.friends")
        success = await gameplay_service.multiplayer.add_friend(
            payload.player_cinta, payload.friend_identifier
        )
        if not success:
            raise HTTPException(status_code=400, detail="Não foi possível adicionar amigo.")
        return {"success": True, "message": "Amizade estabelecida com sucesso."}

    @router.get("/brags/{cinta}")
    async def list_brags(cinta: str, request: Request) -> list[dict[str, Any]]:
        """Retrieves pending rival challenges sent to player."""
        await ticket_policy.authorize(request.headers.get(TICKET_HEADER), cinta, "gameplay.brags")
        brags = await gameplay_service.brags.get_pending_brags(cinta)
        return [b.model_dump() for b in brags]

    return router
