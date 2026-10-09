"""Sync and audit events handler."""

from __future__ import annotations

import time
from typing import Any
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader
from server.storage.player_repository import PlayerRepository


class SyncHandler(BaseServiceHandler):
    """Processes SyncReq, auditing gameplay actions and rhythm game sessions."""

    def __init__(self, repository: PlayerRepository) -> None:
        self.repository = repository

    async def handle(self, header: ClientHeader, body: dict[str, Any]) -> dict[str, Any]:
        """Acks client synchronization requests and records audit events."""
        audits = body.get("audits", [])
        cinta = body.get("cinta") or header.clide or "default-player"
        profile = await self.repository.get_by_cinta(cinta)

        # Processa auditorias de pontuação se presentes
        for audit in audits:
            if audit.get("event") == "RhythmGameEnded_SharplaAudit":
                score = audit.get("score", 0)
                if profile:
                    profile.stars += 1
                    profile.coins += min(score // 1000, 100)
                    await self.repository.save(profile)

        return {
            "status": 200,
            "timestamp": int(time.time() * 1000),
            "audits_processed": len(audits),
            "sync_success": True,
        }
