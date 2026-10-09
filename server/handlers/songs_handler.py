"""Song catalog and beatmap metadata handler."""

from __future__ import annotations

import time
from typing import Any
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader


class SongsHandler(BaseServiceHandler):
    """Provides song catalog, beatmap info and audio streaming URLs."""

    DEFAULT_SONGS = [
        {
            "id": "starter_song_01",
            "title": "Welcome to the Rhythm",
            "artist": "Space Ape Beats",
            "difficulty": "Normal",
            "bpm": 128,
            "bundle_url": "/assets/bundles/starter_song_01.bundle",
        },
        {
            "id": "starter_song_02",
            "title": "Neon Beat",
            "artist": "Flamingo Studio",
            "difficulty": "Hard",
            "bpm": 140,
            "bundle_url": "/assets/bundles/starter_song_02.bundle",
        },
    ]

    async def handle(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Returns catalog of playable songs."""
        return {
            "status": 200,
            "timestamp": int(time.time() * 1000),
            "songs": self.DEFAULT_SONGS,
        }
