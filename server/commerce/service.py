"""Central Commerce Service coordinating transactions, economy, and feature flags."""

from __future__ import annotations

from typing import Any
from server.commerce.catalog import StoreCatalog
from server.commerce.flags import CommerceFeatureFlagManager
from server.commerce.gacha import GachaLootboxEngine
from server.commerce.models import CurrencyType, ProductItem, ProductType, PurchaseResult
from server.commerce.tour_pass import TourPassManager
from server.commerce.wallet import WalletManager
from server.models.player import PlayerProfile


class CommerceService:
    """Orchestrates in-game store purchases, gacha boxes, and economy progression."""

    def __init__(
        self,
        flags: CommerceFeatureFlagManager | None = None,
        catalog: StoreCatalog | None = None,
        wallet: WalletManager | None = None,
        gacha: GachaLootboxEngine | None = None,
        tour_pass: TourPassManager | None = None,
    ) -> None:
        self.flags = flags or CommerceFeatureFlagManager()
        self.catalog = catalog or StoreCatalog()
        self.wallet = wallet or WalletManager()
        self.gacha = gacha or GachaLootboxEngine()
        self.tour_pass = tour_pass or TourPassManager()

    def _apply_grants(self, profile: PlayerProfile, product: ProductItem) -> dict[str, Any]:
        """Applies granted rewards based on product type."""
        grants = product.grants
        ptype = product.product_type
        if ptype == ProductType.GEMS:
            self.wallet.credit(profile, CurrencyType.GEMS, grants["gems"])
            return grants
        if ptype == ProductType.COINS:
            self.wallet.credit(profile, CurrencyType.COINS, grants["coins"])
            return grants
        if ptype == ProductType.THEMED_BOX:
            rewards = self.gacha.resolve_box(profile, product.product_id, grants.get("genre", "Pop"))
            return {"rewards": [r.model_dump() for r in rewards]}
        if ptype == ProductType.TOUR_PASS_PREMIUM:
            self.tour_pass.unlock_premium(profile)
            return {"premium_unlocked": True}
        if ptype == ProductType.TOUR_PASS_TIER:
            new_lvl = self.tour_pass.buy_levels(profile, grants.get("levels", 1))
            return {"new_level": new_lvl}
        if ptype == ProductType.TRACK_SKIN:
            self.wallet.grant_item(profile, "track_skins", grants["skin_id"])
            return {"skin_unlocked": grants["skin_id"]}
        return grants

    def purchase(self, profile: PlayerProfile, product_id: str) -> PurchaseResult:
        """Executes full purchase flow with feature flag check and currency debit."""
        product = self.catalog.get(product_id)
        if not product:
            raise KeyError(f"Produto não encontrado no catálogo: {product_id}")

        self.flags.assert_enabled(product.product_type)
        self.wallet.deduct(profile, product.currency, product.cost)
        granted = self._apply_grants(profile, product)

        return PurchaseResult(
            success=True,
            product_id=product_id,
            message="Compra realizada com sucesso.",
            coins_remaining=profile.coins,
            gems_remaining=profile.gems,
            items_granted=granted,
        )

    def buy_season_level(self, profile: PlayerProfile, num_levels: int) -> PurchaseResult:
        """Purchases and advances Tour Pass levels using gems."""
        self.flags.assert_enabled(ProductType.TOUR_PASS_TIER)
        cost_gems = max(num_levels, 1) * 30
        self.wallet.deduct(profile, CurrencyType.GEMS, cost_gems)
        new_level = self.tour_pass.buy_levels(profile, num_levels)

        return PurchaseResult(
            success=True,
            product_id="tour_pass_tier_skip",
            message=f"Avançado {num_levels} níveis no Tour Pass.",
            coins_remaining=profile.coins,
            gems_remaining=profile.gems,
            items_granted={"tour_pass_level": new_level},
        )

    def equip_track_skin(self, profile: PlayerProfile, skin_id: str) -> None:
        """Equips an active track skin if cosmetics are enabled."""
        self.flags.assert_enabled(ProductType.TRACK_SKIN)
        profile.customisation["active_track_skin"] = skin_id
