"""Store catalog definitions and product repository."""

from __future__ import annotations

from typing import Optional
from server.commerce.models import CurrencyType, ProductItem, ProductType


class StoreCatalog:
    """Provides product catalog lookup and management."""

    def __init__(self) -> None:
        self._products: dict[str, ProductItem] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        items = [
            ProductItem(
                product_id="gem_pack_100",
                name="100 Gems Pouch",
                product_type=ProductType.GEMS,
                currency=CurrencyType.REAL_MONEY,
                cost=99,
                grants={"gems": 100},
            ),
            ProductItem(
                product_id="coins_500",
                name="500 Beat Coins",
                product_type=ProductType.COINS,
                currency=CurrencyType.GEMS,
                cost=25,
                grants={"coins": 500},
            ),
            ProductItem(
                product_id="box_rock",
                name="Rock Song Case",
                product_type=ProductType.THEMED_BOX,
                currency=CurrencyType.GEMS,
                cost=149,
                grants={"genre": "Rock", "cards": 10},
            ),
            ProductItem(
                product_id="box_pop",
                name="Pop Song Case",
                product_type=ProductType.THEMED_BOX,
                currency=CurrencyType.GEMS,
                cost=149,
                grants={"genre": "Pop", "cards": 10},
            ),
            ProductItem(
                product_id="campaign_box_speedup",
                name="Instant Case Unlock",
                product_type=ProductType.CAMPAIGN_BOX,
                currency=CurrencyType.GEMS,
                cost=20,
                grants={"unlock_now": True},
            ),
            ProductItem(
                product_id="tour_pass_premium",
                name="Tour Pass Premium Season",
                product_type=ProductType.TOUR_PASS_PREMIUM,
                currency=CurrencyType.GEMS,
                cost=249,
                grants={"premium_unlocked": True},
            ),
            ProductItem(
                product_id="tour_pass_tier_skip",
                name="Tour Pass Level Skip",
                product_type=ProductType.TOUR_PASS_TIER,
                currency=CurrencyType.GEMS,
                cost=30,
                grants={"levels": 1},
            ),
            ProductItem(
                product_id="skin_synthwave_lane",
                name="Synthwave Track Skin",
                product_type=ProductType.TRACK_SKIN,
                currency=CurrencyType.GEMS,
                cost=100,
                grants={"skin_id": "skin_synthwave_lane", "genre": "Electronic"},
            ),
            ProductItem(
                product_id="skin_neon_grid",
                name="Neon Grid Track Skin",
                product_type=ProductType.TRACK_SKIN,
                currency=CurrencyType.GEMS,
                cost=150,
                grants={"skin_id": "skin_neon_grid", "genre": "Pop"},
            ),
        ]
        for it in items:
            self._products[it.product_id] = it

    def get(self, product_id: str) -> Optional[ProductItem]:
        """Looks up a product by unique product ID."""
        return self._products.get(product_id)

    def list_all(self, ptype: Optional[ProductType] = None) -> list[ProductItem]:
        """Lists products, optionally filtered by product type."""
        if not ptype:
            return list(self._products.values())
        return [p for p in self._products.values() if p.product_type == ptype]

    def register(self, item: ProductItem) -> None:
        """Registers a new or updated product into catalog."""
        self._products[item.product_id] = item
