"""Tour Pass and Season progression manager."""

from __future__ import annotations

from typing import Any
from server.models.player import PlayerProfile


class TourPassManager:
    """Manages season pass levels, boosters, and premium tier unlocking."""

    MAX_LEVEL = 30

    def get_season_info(self, profile: PlayerProfile) -> dict[str, Any]:
        """Retrieves player's active tour pass season status."""
        return {
            "season_id": "season_01",
            "current_level": profile.customisation.get("tour_pass_level", 1),
            "is_premium": profile.customisation.get("tour_pass_premium", False),
            "max_level": self.MAX_LEVEL,
        }

    def buy_levels(self, profile: PlayerProfile, num_levels: int) -> int:
        """Advances tour pass levels up to the max season cap."""
        current = profile.customisation.get("tour_pass_level", 1)
        new_level = min(current + max(num_levels, 1), self.MAX_LEVEL)
        profile.customisation["tour_pass_level"] = new_level
        return new_level

    def unlock_premium(self, profile: PlayerProfile) -> None:
        """Unlocks premium reward track for the current season."""
        profile.customisation["tour_pass_premium"] = True
