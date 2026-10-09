"""Wallet and player inventory manager with strict balance validation."""

from __future__ import annotations

from server.commerce.models import CurrencyType
from server.models.player import PlayerProfile


class InsufficientFundsError(ValueError):
    """Raised when a player attempts a purchase without sufficient currency."""


class WalletManager:
    """Manages player currency debits, credits, and inventory ownership."""

    def has_sufficient_funds(
        self, profile: PlayerProfile, currency: CurrencyType, cost: int
    ) -> bool:
        """Checks if profile possesses sufficient currency for an operation."""
        if currency == CurrencyType.FREE or currency == CurrencyType.REAL_MONEY:
            return True
        if currency == CurrencyType.COINS:
            return profile.coins >= cost
        return profile.gems >= cost

    def deduct(
        self, profile: PlayerProfile, currency: CurrencyType, cost: int
    ) -> None:
        """Deducts currency amount with fail-fast validation."""
        if not self.has_sufficient_funds(profile, currency, cost):
            raise InsufficientFundsError(
                f"Saldo insuficiente de {currency.value}: necessário {cost}."
            )
        if currency == CurrencyType.COINS:
            profile.coins -= cost
            return
        if currency == CurrencyType.GEMS:
            profile.gems -= cost

    def credit(
        self, profile: PlayerProfile, currency: CurrencyType, amount: int
    ) -> None:
        """Credits currency to profile balance."""
        if currency == CurrencyType.COINS:
            profile.coins += amount
            return
        if currency == CurrencyType.GEMS:
            profile.gems += amount

    def grant_item(
        self, profile: PlayerProfile, category: str, item_id: str
    ) -> None:
        """Grants an item into player profile customisation inventory."""
        items: list[str] = profile.customisation.setdefault(category, [])
        if item_id not in items:
            items.append(item_id)

    def has_item(
        self, profile: PlayerProfile, category: str, item_id: str
    ) -> bool:
        """Checks if player owns a specific inventory item."""
        items: list[str] = profile.customisation.get(category, [])
        return item_id in items
