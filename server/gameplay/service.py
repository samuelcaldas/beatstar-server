"""Unified Gameplay Service coordinating progression, leaderboards, and social events."""

from __future__ import annotations

from typing import Any
from server.gameplay.brags import BragManager
from server.gameplay.leaderboards import LeaderboardEngine
from server.gameplay.models import LeaderboardEntry
from server.gameplay.multiplayer import MultiplayerManager
from server.gameplay.progression import ProgressionEngine
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager


class GameplayService:
    """Orchestrates player journey progression, leaderboards, and friend competition."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager
        self.progression = ProgressionEngine()
        self.leaderboards = LeaderboardEngine(db_manager)
        self.multiplayer = MultiplayerManager(db_manager)
        self.brags = BragManager(db_manager)

    async def _emit_friend_brags(
        self, sender_cinta: str, song_id: str, score: int
    ) -> int:
        """Issues challenge brags to friends with lower scores on this song."""
        friend_cintas = await self.multiplayer.list_friend_cintas(sender_cinta)
        if not friend_cintas:
            return 0
        board = await self.leaderboards.get_song_leaderboard(song_id, filter_cintas=friend_cintas)
        created = 0
        for entry in board:
            if entry.score < score:
                await self.brags.create_brag(sender_cinta, entry.cinta, song_id, score)
                created += 1
        return created

    async def submit_score(
        self, profile: PlayerProfile, song_id: str, score: int, accuracy: float = 1.0
    ) -> dict[str, Any]:
        """Processes song completion: records high score, evaluates level up and brags."""
        record = await self.leaderboards.record_score(
            profile.cinta, profile.clide, song_id, score, accuracy
        )
        beaten_brags = await self.brags.resolve_brags(profile.cinta, song_id, score)
        profile.stars += record.stars
        profile.coins += min(score // 1000, 100)
        level_up_info = self.progression.check_level_up(profile)
        created_brags = await self._emit_friend_brags(profile.cinta, song_id, score)

        return {
            "score": score,
            "stars": record.stars,
            "medal": record.medal.value,
            "level_up": level_up_info["level_up"],
            "current_level": profile.level,
            "beaten_brags": beaten_brags,
            "created_brags": created_brags,
        }

    async def get_leaderboard(
        self, song_id: str | None, friends_only: bool, player_cinta: str | None, limit: int = 50
    ) -> list[LeaderboardEntry]:
        """Fetches leaderboard filtered globally or restricted to confirmed friends."""
        filter_cintas: list[str] | None = None
        if friends_only and player_cinta:
            friends = await self.multiplayer.list_friend_cintas(player_cinta)
            filter_cintas = friends + [player_cinta]

        if song_id:
            return await self.leaderboards.get_song_leaderboard(song_id, filter_cintas, limit)
        return await self.leaderboards.get_global_leaderboard(filter_cintas, limit)
