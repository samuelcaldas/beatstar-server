"""Friend Brags and competitive challenge management."""

from __future__ import annotations

import time
import uuid
from server.gameplay.models import FriendBragRecord
from server.storage.database import DatabaseManager


class BragManager:
    """Manages asynchronous player challenges and rival notifications."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    async def create_brag(
        self, sender_cinta: str, target_cinta: str, song_id: str, score_to_beat: int
    ) -> FriendBragRecord:
        """Issues a new competitive brag challenge to a friend."""
        brag_id = f"brag-{uuid.uuid4().hex[:12]}"
        now_ms = int(time.time() * 1000)

        async with self.db_manager.connect() as conn:
            await conn.execute("""
                INSERT INTO player_brags (brag_id, sender_cinta, target_cinta, song_id, score_to_beat, beaten, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (brag_id, sender_cinta, target_cinta, song_id, score_to_beat, now_ms))
            await conn.commit()

        return FriendBragRecord(
            brag_id=brag_id, sender_cinta=sender_cinta, sender_name="",
            target_cinta=target_cinta, song_id=song_id, score_to_beat=score_to_beat,
            beaten=False, created_at=now_ms,
        )

    async def get_pending_brags(self, player_cinta: str) -> list[FriendBragRecord]:
        """Retrieves active, undefeated brag challenges sent to this player."""
        query = """
            SELECT b.brag_id, b.sender_cinta, p.player_name, b.target_cinta, b.song_id,
                   b.score_to_beat, b.beaten, b.created_at
            FROM player_brags b
            JOIN players p ON b.sender_cinta = p.cinta
            WHERE b.target_cinta = ? AND b.beaten = 0
            ORDER BY b.created_at DESC
        """
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(query, (player_cinta,))
            rows = await cursor.fetchall()

        return [
            FriendBragRecord(
                brag_id=r[0], sender_cinta=r[1], sender_name=r[2], target_cinta=r[3],
                song_id=r[4], score_to_beat=r[5], beaten=bool(r[6]), created_at=r[7],
            )
            for r in rows
        ]

    async def resolve_brags(self, player_cinta: str, song_id: str, new_score: int) -> int:
        """Marks pending challenges as beaten if player exceeded the challenge score."""
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute("""
                UPDATE player_brags SET beaten = 1
                WHERE target_cinta = ? AND song_id = ? AND score_to_beat <= ? AND beaten = 0
            """, (player_cinta, song_id, new_score))
            await conn.commit()
            return cursor.rowcount
