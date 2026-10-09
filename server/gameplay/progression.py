"""Progression and Star Milestones Journey engine."""

from __future__ import annotations

from typing import Any
from server.gameplay.models import VenueDefinition
from server.models.player import PlayerProfile


class ProgressionEngine:
    """Calculates Journey venues, level progression, and star milestone rewards."""

    VENUES = [
        VenueDefinition(level=1, name="The Garage", stars_required=0, unlocked_songs=["starter_song_01", "starter_song_02"]),
        VenueDefinition(level=2, name="The Pub", stars_required=5, unlocked_songs=["song_rock_01"]),
        VenueDefinition(level=3, name="The Club", stars_required=15, unlocked_songs=["song_pop_01"]),
        VenueDefinition(level=4, name="The Warehouse", stars_required=30, unlocked_songs=["song_electronic_01"]),
        VenueDefinition(level=5, name="The Arena", stars_required=50, unlocked_songs=["song_rock_02"]),
        VenueDefinition(level=6, name="The Amphitheatre", stars_required=75, unlocked_songs=["song_pop_02"]),
        VenueDefinition(level=7, name="The Festival", stars_required=110, unlocked_songs=["song_electronic_02"]),
        VenueDefinition(level=8, name="The Stadium", stars_required=150, unlocked_songs=["song_extreme_01"]),
        VenueDefinition(level=9, name="The Metropolis", stars_required=200, unlocked_songs=["song_extreme_02"]),
        VenueDefinition(level=10, name="The Hall of Fame", stars_required=260, unlocked_songs=["song_master_01"]),
    ]

    def get_venue(self, level: int) -> VenueDefinition:
        """Retrieves venue definition by numerical level."""
        idx = max(1, min(level, len(self.VENUES))) - 1
        return self.VENUES[idx]

    def calculate_current_venue(self, stars: int) -> VenueDefinition:
        """Determines active venue based on total stars accumulated."""
        highest = self.VENUES[0]
        for venue in self.VENUES:
            if stars >= venue.stars_required:
                highest = venue
        return highest

    def check_level_up(self, profile: PlayerProfile) -> dict[str, Any]:
        """Evaluates if player qualified for a higher venue and applies rewards."""
        target_venue = self.calculate_current_venue(profile.stars)
        if target_venue.level <= profile.level:
            return {"level_up": False, "level": profile.level}

        profile.level = target_venue.level
        profile.coins += target_venue.bonus_coins
        profile.gems += target_venue.bonus_gems
        for song in target_venue.unlocked_songs:
            if song not in profile.unlocked_songs:
                profile.unlocked_songs.append(song)

        return {
            "level_up": True,
            "level": profile.level,
            "venue_name": target_venue.name,
            "unlocked_songs": target_venue.unlocked_songs,
        }
