"""Leaderboard engine calculating song high scores, ranks, and medals."""

from __future__ import annotations

import time
from server.gameplay.models import LeaderboardEntry, MedalType, SongScoreRecord
from server.storage.database import DatabaseManager


class LeaderboardEngine:
    """Manages player scores, rankings, and medal calculations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def evaluate_score(self, score: int) -> tuple[int, MedalType]:
        """Maps numerical score to stars and medal tier."""
        if score >= 50000:
            return 5, MedalType.DIAMOND_PERFECT
        if score >= 49500:
            return 5, MedalType.DIAMOND
        if score >= 49000:
            return 5, MedalType.PLATINUM
        if score >= 48000:
            return 5, MedalType.GOLD
        if score >= 35000:
            return 4, MedalType.NONE
        if score >= 20000:
            return 3, MedalType.NONE
        if score >= 10000:
            return 2, MedalType.NONE
        stars = 1 if score >= 2500 else 0
        return stars, MedalType.NONE

    async def record_score(
        self, cinta: str, clide: str, song_id: str, score: int, accuracy: float = 1.0
    ) -> SongScoreRecord:
        """Upserts player high score if current score exceeds existing record."""
        stars, medal = self.evaluate_score(score)
        now_ms = int(time.time() * 1000)

        async with self.db_manager.connect() as conn:
            await conn.execute("""
                INSERT INTO song_scores (cinta, clide, song_id, score, stars, medal, accuracy, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cinta, song_id) DO UPDATE SET
                    score = MAX(song_scores.score, excluded.score),
                    stars = MAX(song_scores.stars, excluded.stars),
                    medal = CASE WHEN excluded.score > song_scores.score THEN excluded.medal ELSE song_scores.medal END,
                    accuracy = CASE WHEN excluded.score > song_scores.score THEN excluded.accuracy ELSE song_scores.accuracy END,
                    updated_at = excluded.updated_at
            """, (cinta, clide, song_id, score, stars, medal.value, accuracy, now_ms))
            await conn.commit()

        return SongScoreRecord(
            cinta=cinta, clide=clide, song_id=song_id, score=score,
            stars=stars, medal=medal, accuracy=accuracy, updated_at=now_ms,
        )

    async def get_song_leaderboard(
        self, song_id: str, filter_cintas: list[str] | None = None, limit: int = 50
    ) -> list[LeaderboardEntry]:
        """Retrieves song leaderboard, optionally filtered by friend IDs."""
        query = """
            SELECT s.cinta, s.clide, p.player_name, s.score, p.stars, p.level, s.medal
            FROM song_scores s
            JOIN players p ON s.cinta = p.cinta
            WHERE s.song_id = ?
        """
        params: list[object] = [song_id]
        if filter_cintas:
            placeholders = ",".join("?" for _ in filter_cintas)
            query += f" AND s.cinta IN ({placeholders})"
            params.extend(filter_cintas)

        query += " ORDER BY s.score DESC LIMIT ?"
        params.append(limit)

        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

        entries: list[LeaderboardEntry] = []
        for idx, r in enumerate(rows, start=1):
            entries.append(LeaderboardEntry(
                rank=idx, cinta=r[0], clide=r[1], player_name=r[2],
                score=r[3], total_stars=r[4], venue_level=r[5], medal=MedalType(r[6]),
            ))
        return entries

    async def get_global_leaderboard(
        self, filter_cintas: list[str] | None = None, limit: int = 50
    ) -> list[LeaderboardEntry]:
        """Retrieves cumulative score leaderboard across all played songs."""
        query = """
            SELECT p.cinta, p.clide, p.player_name, COALESCE(SUM(s.score), 0) as total_score,
                   p.stars, p.level
            FROM players p
            LEFT JOIN song_scores s ON p.cinta = s.cinta
        """
        params: list[object] = []
        if filter_cintas:
            placeholders = ",".join("?" for _ in filter_cintas)
            query += f" WHERE p.cinta IN ({placeholders})"
            params.extend(filter_cintas)

        query += " GROUP BY p.cinta ORDER BY total_score DESC LIMIT ?"
        params.append(limit)

        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

        entries: list[LeaderboardEntry] = []
        for idx, r in enumerate(rows, start=1):
            entries.append(LeaderboardEntry(
                rank=idx, cinta=r[0], clide=r[1], player_name=r[2],
                score=r[3], total_stars=r[4], venue_level=r[5],
            ))
        return entries
