"""Sync and audit events handler integrated with Commerce SDK."""

from __future__ import annotations

import time
from typing import Any
from server.commerce import CommerceService
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository


class SyncHandler(BaseServiceHandler):
    """Processes SyncReq, auditing gameplay actions and rhythm game sessions."""

    def __init__(
        self,
        repository: PlayerRepository,
        commerce_service: CommerceService | None = None,
    ) -> None:
        self.repository = repository
        self.commerce_service = commerce_service or CommerceService()

    def _process_rhythm_game_ended(self, profile: PlayerProfile, audit: dict[str, Any]) -> None:
        score = audit.get("score", 0)
        profile.stars += 1
        profile.coins += min(score // 1000, 100)

    def _process_commerce_audit(self, profile: PlayerProfile, event: str, audit: dict[str, Any]) -> None:
        if event in ("BuyShopItem_SharplaAudit", "MakeGameCurrencyPurchase_SharplaAudit"):
            pid = audit.get("product_id") or audit.get("ToBuy_id") or "coins_500"
            self.commerce_service.purchase(profile, str(pid))
            return
        if event == "BuyShopThemedBox_SharplaAudit":
            box_id = audit.get("themeBox_id") or "box_rock"
            self.commerce_service.purchase(profile, str(box_id))
            return
        if event in ("StartIAPPurchase_SharplaAudit", "CompleteIAPPurchase_SharplaAudit"):
            pid = audit.get("product_id") or "gem_pack_100"
            self.commerce_service.purchase(profile, str(pid))
            return
        if event in ("OpenCampaignGachaBox_SharplaAudit", "PayToForceOpenCampaignGachaBox_SharplaAudit"):
            self.commerce_service.purchase(profile, "campaign_box_speedup")
            return
        if event == "Season_BuyLevel_SharplaAudit":
            self.commerce_service.buy_season_level(profile, audit.get("numLevels", 1))
            return
        if event == "SetGlobalTrackSkin_SharplaAudit":
            skin_id = audit.get("trackSkin_id") or "skin_synthwave_lane"
            self.commerce_service.equip_track_skin(profile, str(skin_id))

    def _handle_single_audit(self, profile: PlayerProfile, audit: dict[str, Any]) -> None:
        event = audit.get("event", "")
        if event == "RhythmGameEnded_SharplaAudit":
            self._process_rhythm_game_ended(profile, audit)
            return
        try:
            self._process_commerce_audit(profile, event, audit)
        except Exception:
            pass

    async def handle(self, header: ClientHeader, body: dict[str, Any]) -> dict[str, Any]:
        """Acks client synchronization requests and records audit events."""
        audits = body.get("audits", [])
        cinta = body.get("cinta") or header.clide or "default-player"
        profile = await self.repository.get_by_cinta(cinta)

        if profile:
            for audit in audits:
                self._handle_single_audit(profile, audit)
            await self.repository.save(profile)

        return {
            "status": 200,
            "timestamp": int(time.time() * 1000),
            "audits_processed": len(audits),
            "sync_success": True,
        }
