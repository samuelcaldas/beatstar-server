"""FastAPI router for Commerce SDK administration and querying."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.commerce.models import CurrencyType
from server.commerce.service import CommerceService
from server.storage.player_repository import PlayerRepository


class FlagUpdatePayload(BaseModel):
    flag_name: str
    enabled: bool


class GrantPayload(BaseModel):
    cinta: str
    currency: CurrencyType
    amount: int


class PurchasePayload(BaseModel):
    cinta: str
    product_id: str


def build_commerce_router(
    commerce_service: CommerceService, player_repository: PlayerRepository
) -> APIRouter:
    """Builds commerce routes bound to one service and one player repository."""
    router = APIRouter()

    @router.get("/flags")
    async def get_flags() -> dict[str, bool]:
        """Retrieves current commerce and monetization feature flags."""
        return commerce_service.flags.get_flags()

    @router.post("/flags")
    async def update_flag(payload: FlagUpdatePayload) -> dict[str, Any]:
        """Updates a commerce feature flag dynamically at runtime."""
        try:
            commerce_service.flags.set_flag(payload.flag_name, payload.enabled)
            return {"success": True, "flags": commerce_service.flags.get_flags()}
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/catalog")
    async def get_catalog() -> list[dict[str, Any]]:
        """Lists all store and economy catalog items."""
        return [p.model_dump() for p in commerce_service.catalog.list_all()]

    @router.get("/wallet/{cinta}")
    async def get_wallet(cinta: str) -> dict[str, Any]:
        """Retrieves player wallet balance and unlocked items."""
        profile = await player_repository.get_by_cinta(cinta)
        if not profile:
            raise HTTPException(status_code=404, detail="Jogador não encontrado")
        return {
            "cinta": profile.cinta,
            "coins": profile.coins,
            "gems": profile.gems,
            "customisation": profile.customisation,
            "unlocked_songs": profile.unlocked_songs,
        }

    @router.post("/grant")
    async def grant_funds(payload: GrantPayload) -> dict[str, Any]:
        """Grants coins or gems directly to player profile."""
        profile = await player_repository.get_by_cinta(payload.cinta)
        if not profile:
            raise HTTPException(status_code=404, detail="Jogador não encontrado")
        commerce_service.wallet.credit(profile, payload.currency, payload.amount)
        await player_repository.save(profile)
        return {"success": True, "coins": profile.coins, "gems": profile.gems}

    @router.post("/purchase")
    async def execute_purchase(payload: PurchasePayload) -> dict[str, Any]:
        """Executes catalog item purchase on behalf of player."""
        profile = await player_repository.get_by_cinta(payload.cinta)
        if not profile:
            raise HTTPException(status_code=404, detail="Jogador não encontrado")
        try:
            res = commerce_service.purchase(profile, payload.product_id)
            await player_repository.save(profile)
            return res.model_dump()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
