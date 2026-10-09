"""Sync and audit events handler integrated with Commerce and Gameplay SDKs."""

from __future__ import annotations

import time
from typing import Any
from server.commerce import CommerceService
from server.gameplay import GameplayService
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository


class SyncHandler(BaseServiceHandler):
    """Processes Sharpla protocol requests, gameplay audits, and social features."""

    def __init__(
        self,
        repository: PlayerRepository,
        commerce_service: CommerceService | None = None,
        gameplay_service: GameplayService | None = None,
    ) -> None:
        self.repository = repository
        self.commerce_service = commerce_service or CommerceService()
        self.gameplay_service = gameplay_service or GameplayService(repository.db_manager)

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
        if event == "Season_BuyLevel_SharplaAudit":
            self.commerce_service.buy_season_level(profile, audit.get("numLevels", 1))
            return
        if event == "SetGlobalTrackSkin_SharplaAudit":
            skin_id = audit.get("trackSkin_id") or "skin_synthwave_lane"
            self.commerce_service.equip_track_skin(profile, str(skin_id))

    async def _handle_single_audit(self, profile: PlayerProfile, audit: dict[str, Any]) -> None:
        event = audit.get("event", "")
        if event == "RhythmGameEnded_SharplaAudit":
            score = audit.get("score", 0)
            song = audit.get("song_id") or profile.selected_song or "starter_song_01"
            acc = float(audit.get("accuracy", 1.0))
            await self.gameplay_service.submit_score(profile, song, score, acc)
            return
        if event == "ClaimStarMilestone_SharplaAudit":
            self.gameplay_service.progression.check_level_up(profile)
            return
        try:
            self._process_commerce_audit(profile, event, audit)
        except Exception:
            pass

    async def _handle_leaderboard(self, body: dict[str, Any], profile: PlayerProfile | None) -> dict[str, Any]:
        lb_name = body.get("leaderboardName") or "global"
        friends_only = bool(body.get("friendsOnly", False))
        song_id = None if lb_name in ("global", "country") else lb_name
        cinta = profile.cinta if profile else None
        entries = await self.gameplay_service.get_leaderboard(song_id, friends_only, cinta)
        results = [
            {"player": {"clide": e.clide, "name": e.player_name, "totalStars": e.total_stars, "venue_id": e.venue_level},
             "score": e.score, "rank": e.rank}
            for e in entries
        ]
        return {"status": 200, "results": results, "isError": False}

    async def _handle_social(self, cmd: str, body: dict[str, Any], profile: PlayerProfile | None) -> dict[str, Any]:
        if cmd == "AddFriend_Req" and profile:
            target = body.get("clide") or body.get("friend_clide") or ""
            ok = await self.gameplay_service.multiplayer.add_friend(profile.cinta, target)
            return {"status": 200, "result": 0 if ok else 1, "success": ok}
        if cmd == "FriendViews_Req" and profile:
            friends = await self.gameplay_service.multiplayer.list_friends(profile.cinta)
            return {"status": 200, "friendViews": friends}
        return {"status": 200, "acknowledged": True}

    async def handle(self, header: ClientHeader, body: dict[str, Any]) -> dict[str, Any]:
        cmd = getattr(header, "command", None) or body.get("command") or ""
        cinta = body.get("cinta") or header.clide or "default-player"
        profile = await self.repository.get_by_cinta(cinta)


        if cmd in ("LeaderboardWithViews_Req", "Leaderboard_Req"):
            return await self._handle_leaderboard(body, profile)
        if cmd in ("AddFriend_Req", "FriendViews_Req"):
            return await self._handle_social(cmd, body, profile)

        audits = body.get("audits", [])
        if profile:
            for audit in audits:
                await self._handle_single_audit(profile, audit)
            await self.repository.save(profile)

        return {"status": 200, "timestamp": int(time.time() * 1000), "audits_processed": len(audits), "sync_success": True}
