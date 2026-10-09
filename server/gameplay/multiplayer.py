"""Multiplayer and social friendship management."""

from __future__ import annotations

import time
from typing import Any
from server.storage.database import DatabaseManager


class MultiplayerManager:
    """Manages player search, social friendships, and concurrent profile discovery."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    async def _resolve_cinta(self, identifier: str) -> str | None:
        """Resolves cinta from either clide or direct cinta UUID."""
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(
                "SELECT cinta FROM players WHERE cinta = ? OR clide = ?",
                (identifier, identifier),
            )
            row = await cursor.fetchone()
            return str(row[0]) if row else None

    async def add_friend(self, player_cinta: str, friend_identifier: str) -> bool:
        """Establishes bidirectional friendship between two players."""
        target_cinta = await self._resolve_cinta(friend_identifier)
        if not target_cinta or target_cinta == player_cinta:
            return False

        now_ms = int(time.time() * 1000)
        async with self.db_manager.connect() as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO player_friends (player_cinta, friend_cinta, created_at) VALUES (?, ?, ?)",
                (player_cinta, target_cinta, now_ms),
            )
            await conn.execute(
                "INSERT OR IGNORE INTO player_friends (player_cinta, friend_cinta, created_at) VALUES (?, ?, ?)",
                (target_cinta, player_cinta, now_ms),
            )
            await conn.commit()
        return True

    async def remove_friend(self, player_cinta: str, friend_identifier: str) -> bool:
        """Removes friendship connection."""
        target_cinta = await self._resolve_cinta(friend_identifier)
        if not target_cinta:
            return False

        async with self.db_manager.connect() as conn:
            await conn.execute(
                "DELETE FROM player_friends WHERE (player_cinta = ? AND friend_cinta = ?) OR (player_cinta = ? AND friend_cinta = ?)",
                (player_cinta, target_cinta, target_cinta, player_cinta),
            )
            await conn.commit()
        return True

    async def list_friend_cintas(self, player_cinta: str) -> list[str]:
        """Lists cinta UUIDs of all confirmed friends."""
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(
                "SELECT friend_cinta FROM player_friends WHERE player_cinta = ?",
                (player_cinta,),
            )
            rows = await cursor.fetchall()
            return [str(r[0]) for r in rows]

    async def list_friends(self, player_cinta: str) -> list[dict[str, Any]]:
        """Returns full profile data for all friends."""
        query = """
            SELECT p.cinta, p.clide, p.player_name, p.level, p.stars
            FROM player_friends f
            JOIN players p ON f.friend_cinta = p.cinta
            WHERE f.player_cinta = ?
        """
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(query, (player_cinta,))
            rows = await cursor.fetchall()
            return [
                {"cinta": r[0], "clide": r[1], "player_name": r[2], "level": r[3], "stars": r[4]}
                for r in rows
            ]

    async def search_players(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Searches players by display name or clide."""
        pattern = f"%{query}%"
        sql = "SELECT cinta, clide, player_name, level, stars FROM players WHERE player_name LIKE ? OR clide LIKE ? LIMIT ?"
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(sql, (pattern, pattern, limit))
            rows = await cursor.fetchall()
            return [
                {"cinta": r[0], "clide": r[1], "player_name": r[2], "level": r[3], "stars": r[4]}
                for r in rows
            ]
