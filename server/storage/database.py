"""Async SQLite database manager with schema lifecycle management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
import aiosqlite

BUSY_TIMEOUT_MILLISECONDS = 5000


class DatabaseManager:
    """Manages database connection and schema initialization."""

    def __init__(self, db_path: str = "data/beatstar.db") -> None:
        self.db_path = db_path

    async def _create_tables(self, db: aiosqlite.Connection) -> None:
        """Executes table creation DDL."""
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS song_scores (
                cinta TEXT NOT NULL,
                clide TEXT NOT NULL,
                song_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                medal TEXT NOT NULL,
                accuracy REAL NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (cinta, song_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_friends (
                player_cinta TEXT NOT NULL,
                friend_cinta TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (player_cinta, friend_cinta)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_brags (
                brag_id TEXT PRIMARY KEY,
                sender_cinta TEXT NOT NULL,
                target_cinta TEXT NOT NULL,
                song_id TEXT NOT NULL,
                score_to_beat INTEGER NOT NULL,
                beaten INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)

    async def initialize(self) -> None:
        """Creates tables if not already present."""
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with self.connect() as db:
            await self._create_tables(db)
            await db.commit()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Yields a connection with foreign keys enforced and a bounded busy timeout.

        The pragmas are per-connection in SQLite, so every caller must go through here.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MILLISECONDS}")
            yield db
