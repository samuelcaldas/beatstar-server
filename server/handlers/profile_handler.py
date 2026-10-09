"""Player profile and identity management handler."""

from __future__ import annotations

import time
from typing import Any
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader
from server.storage.player_repository import PlayerRepository


class ProfileHandler(BaseServiceHandler):
    """Processes profile queries and updates."""

    def __init__(self, repository: PlayerRepository) -> None:
        self.repository = repository

    async def handle(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatches profile commands."""
        cinta = body.get("cinta") or header.clide or "default-player"
        profile = await self.repository.get_by_cinta(cinta)

        # Atualização de nome se presente
        new_name = body.get("player_name")
        if profile and new_name:
            profile.player_name = str(new_name)
            await self.repository.save(profile)

        profile_data = profile.model_dump() if profile else {}
        return {
            "status": 200,
            "timestamp": int(time.time() * 1000),
            "profile": profile_data,
        }
