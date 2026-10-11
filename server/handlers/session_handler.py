"""User service and authentication handler."""

from __future__ import annotations

import time
from typing import Any
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader
from server.models.player import CintaIdentifier, PlayerProfile
from server.player_auth.store import PlayerTicketStore
from server.storage.player_repository import PlayerRepository


class SessionHandler(BaseServiceHandler):
    """Processes userservice requests (AllInOneLogin, Cinta resolution)."""

    def __init__(self, repository: PlayerRepository, ticket_store: PlayerTicketStore) -> None:
        self.repository = repository
        self.ticket_store = ticket_store

    async def handle(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolves authentication and yields session credentials."""
        login_data = body.get("all_in_one_login", {})
        raw_cinta = login_data.get("cinta")
        cinta_id = CintaIdentifier(raw_cinta)

        profile = await self.repository.get_by_cinta(cinta_id.value)
        if not profile:
            profile = PlayerProfile(cinta=cinta_id.value)
            await self.repository.save(profile)

        auth_ticket = await self.ticket_store.issue(profile.cinta)
        return {
            "status": 200,
            "id": body.get("id", 1),
            "timestamp": int(time.time() * 1000),
            "resp_login_of_some_type": {
                "authenticationTicket": auth_ticket,
                "clide": profile.clide,
                "cinta": profile.cinta,
            },
            "player_profile": profile.model_dump(),
        }
