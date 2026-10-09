"""Player profile persistence repository."""

from __future__ import annotations

import json
import time
from typing import Optional
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager


class PlayerRepository:
    """Provides storage access for player entities."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    async def get_by_cinta(self, cinta: str) -> Optional[PlayerProfile]:
        """Loads a player profile by unique Cinta UUID or session clide."""
        async with self.db_manager.connect() as conn:
            cursor = await conn.execute(
                "SELECT cinta, clide, player_name, level, stars, coins, gems, "
                "selected_song, unlocked_songs, customisation FROM players WHERE cinta = ? OR clide = ?",
                (cinta, cinta),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            return PlayerProfile(
                cinta=row[0],
                clide=row[1],
                player_name=row[2],
                level=row[3],
                stars=row[4],
                coins=row[5],
                gems=row[6],
                selected_song=row[7],
                unlocked_songs=json.loads(row[8]),
                customisation=json.loads(row[9]),
            )

    async def save(self, profile: PlayerProfile) -> None:
        """Upserts a player profile into the database."""
        now = int(time.time() * 1000)
        unlocked = json.dumps(profile.unlocked_songs)
        custom = json.dumps(profile.customisation)

        async with self.db_manager.connect() as conn:
            await conn.execute(
                """
                INSERT INTO players (
                    cinta, clide, player_name, level, stars, coins, gems,
                    selected_song, unlocked_songs, customisation, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cinta) DO UPDATE SET
                    player_name = excluded.player_name,
                    level = excluded.level,
                    stars = excluded.stars,
                    coins = excluded.coins,
                    gems = excluded.gems,
                    selected_song = excluded.selected_song,
                    unlocked_songs = excluded.unlocked_songs,
                    customisation = excluded.customisation,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.cinta,
                    profile.clide,
                    profile.player_name,
                    profile.level,
                    profile.stars,
                    profile.coins,
                    profile.gems,
                    profile.selected_song,
                    unlocked,
                    custom,
                    now,
                ),
            )
            await conn.commit()
