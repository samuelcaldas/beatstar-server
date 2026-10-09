"""Commerce Feature Flags Manager."""

from __future__ import annotations

from typing import Any
from server.commerce.models import ProductType
from server.config import settings


class CommerceFeatureDisabledError(RuntimeError):
    """Raised when an operation is attempted on a disabled commerce feature."""


class CommerceFeatureFlagManager:
    """Controls activation and dynamic toggling of monetization features."""

    def __init__(self) -> None:
        self._iap = settings.feature_flag_iap_enabled
        self._shop = settings.feature_flag_shop_enabled
        self._lootboxes = settings.feature_flag_lootboxes_enabled
        self._premium_pass = settings.feature_flag_premium_pass_enabled
        self._cosmetics = settings.feature_flag_cosmetics_enabled

    def is_type_enabled(self, ptype: ProductType) -> bool:
        """Determines if a given product type is enabled by active feature flags."""
        if ptype == ProductType.GEMS:
            return self._iap
        if ptype in (ProductType.THEMED_BOX, ProductType.CAMPAIGN_BOX):
            return self._lootboxes
        if ptype in (ProductType.TOUR_PASS_TIER, ProductType.TOUR_PASS_PREMIUM):
            return self._premium_pass
        if ptype == ProductType.TRACK_SKIN:
            return self._cosmetics
        return self._shop

    def assert_enabled(self, ptype: ProductType) -> None:
        """Fail-fast guard verifying if the product type is allowed."""
        if self.is_type_enabled(ptype):
            return
        raise CommerceFeatureDisabledError(f"Feature flag para '{ptype.value}' está desabilitada.")

    def get_flags(self) -> dict[str, bool]:
        """Returns current feature flags dictionary."""
        return {
            "iap_enabled": self._iap,
            "shop_enabled": self._shop,
            "lootboxes_enabled": self._lootboxes,
            "premium_pass_enabled": self._premium_pass,
            "cosmetics_enabled": self._cosmetics,
        }

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        """Dynamically overrides a feature flag at runtime."""
        lookup = {
            "iap_enabled": "_iap",
            "shop_enabled": "_shop",
            "lootboxes_enabled": "_lootboxes",
            "premium_pass_enabled": "_premium_pass",
            "cosmetics_enabled": "_cosmetics",
        }
        attr = lookup.get(flag_name)
        if not attr:
            raise KeyError(f"Feature flag desconhecida: {flag_name}")
        setattr(self, attr, enabled)

    def to_game_config_flags(self) -> dict[str, Any]:
        """Translates commerce flags to Beatstar FeatureFlagsConfig schema."""
        return {
            "CanPurchaseMoreGemsFromContinue": self._iap,
            "CanPurchaseMoreGemsFromBundlesPopup": self._shop,
            "NotEnoughGemsShowIAPPopup": self._iap,
            "ThemedBoxesEnabled": self._lootboxes,
            "SeasonsEnabled": self._premium_pass,
            "TourPassBoostersEnabled": self._premium_pass,
            "TrackSkinsEnabled": self._cosmetics,
            "LiveOpsBundlesEnabled": self._shop,
            "LeaderboardEventsShop": self._shop,
            "LeaderboardEventGachaPurchaseFlowEnabled": self._lootboxes,
        }
