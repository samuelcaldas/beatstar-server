"""Commerce domain models and data transfer objects."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ProductType(str, Enum):
    """Categorizes store and in-game economy products."""

    GEMS = "gems"
    COINS = "coins"
    THEMED_BOX = "themed_box"
    CAMPAIGN_BOX = "campaign_box"
    TOUR_PASS_TIER = "tour_pass_tier"
    TOUR_PASS_PREMIUM = "tour_pass_premium"
    TRACK_SKIN = "track_skin"
    BUNDLE = "bundle"


class CurrencyType(str, Enum):
    """Types of currencies accepted by the game economy."""

    COINS = "coins"
    GEMS = "gems"
    REAL_MONEY = "real_money"
    FREE = "free"


class ProductItem(BaseModel):
    """Catalog item available for purchase."""

    product_id: str
    name: str
    product_type: ProductType
    currency: CurrencyType = CurrencyType.GEMS
    cost: int = 0
    grants: dict[str, Any] = Field(default_factory=dict)


class PurchaseResult(BaseModel):
    """Outcome of a commerce transaction."""

    success: bool
    product_id: str
    message: str
    coins_remaining: int
    gems_remaining: int
    items_granted: dict[str, Any] = Field(default_factory=dict)


class LootboxReward(BaseModel):
    """Prize outcome granted from opening a gacha box or song case."""

    reward_type: str
    reward_id: str
    amount: int = 1
