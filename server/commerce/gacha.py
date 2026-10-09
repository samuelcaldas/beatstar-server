"""Gacha and Lootbox resolution engine for Beatstar Song Cases."""

from __future__ import annotations

from server.commerce.models import LootboxReward
from server.models.player import PlayerProfile


class GachaLootboxEngine:
    """Simulates song case and themed box openings with reward generation."""

    AVAILABLE_SONGS = {
        "Rock": ["song_rock_01", "song_rock_02"],
        "Pop": ["song_pop_01", "song_pop_02"],
        "Electronic": ["song_electronic_01", "song_electronic_02"],
    }

    def resolve_box(
        self, profile: PlayerProfile, box_id: str, genre: str = "Pop"
    ) -> list[LootboxReward]:
        """Resolves prizes for a song case, unlocking songs or granting cards/coins."""
        rewards: list[LootboxReward] = []
        candidates = self.AVAILABLE_SONGS.get(genre, self.AVAILABLE_SONGS["Pop"])
        new_song = next((s for s in candidates if s not in profile.unlocked_songs), None)

        if new_song:
            profile.unlocked_songs.append(new_song)
            rewards.append(LootboxReward(reward_type="song", reward_id=new_song))
            return rewards

        # Se já possui todas as músicas do gênero, concede cartas e moedas
        profile.coins += 150
        rewards.append(LootboxReward(reward_type="coins", reward_id="coins", amount=150))
        rewards.append(LootboxReward(reward_type="cards", reward_id=f"{genre.lower()}_cards", amount=10))
        return rewards
