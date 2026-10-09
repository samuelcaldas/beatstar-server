"""Async SQLite database manager."""

from __future__ import annotations

from pathlib import Path
import aiosqlite


class DatabaseManager:
    """Manages database connection and schema lifecycle."""

    def __init__(self, db_path: str = "data/beatstar.db") -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        """Creates tables if not already present."""
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    cinta TEXT PRIMARY KEY,
                    clide TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    stars INTEGER NOT NULL,
                    coins INTEGER NOT NULL,
                    gems INTEGER NOT NULL,
                    selected_song TEXT NOT NULL,
                    unlocked_songs TEXT NOT NULL,
                    customisation TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """)
            await db.commit()

    def connect(self):
        """Returns an async context manager for SQLite connection."""
        return aiosqlite.connect(self.db_path)
