import pytest
from server.gameplay import (
    GameplayService,
    LeaderboardEngine,
    MedalType,
    MultiplayerManager,
    ProgressionEngine,
)
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository


@pytest.fixture
async def test_env(tmp_path):
    db_file = str(tmp_path / "test_gameplay.db")
    db = DatabaseManager(db_file)
    await db.initialize()
    repo = PlayerRepository(db)

    p1 = PlayerProfile(cinta="player-cinta-01", clide="clide001", player_name="PlayerOne", stars=10, level=1)
    p2 = PlayerProfile(cinta="player-cinta-02", clide="clide002", player_name="PlayerTwo", stars=30, level=1)
    await repo.save(p1)
    await repo.save(p2)

    service = GameplayService(db)
    return db, repo, service, p1, p2



def test_progression_engine_venues():
    engine = ProgressionEngine()
    venue = engine.calculate_current_venue(stars=0)
    assert venue.level == 1
    assert venue.name == "The Garage"

    venue_high = engine.calculate_current_venue(stars=55)
    assert venue_high.level == 5
    assert venue_high.name == "The Arena"


def test_progression_engine_level_up():
    engine = ProgressionEngine()
    profile = PlayerProfile(stars=10, level=1)
    res = engine.check_level_up(profile)
    assert res["level_up"] is True
    assert profile.level == 2
    assert "song_rock_01" in profile.unlocked_songs


def test_leaderboard_score_evaluation():
    engine = LeaderboardEngine(DatabaseManager())
    stars, medal = engine.evaluate_score(50000)
    assert stars == 5
    assert medal == MedalType.DIAMOND_PERFECT

    stars, medal = engine.evaluate_score(48500)
    assert stars == 5
    assert medal == MedalType.GOLD


async def test_gameplay_service_submit_score_and_ranking(test_env):
    db, repo, service, p1, p2 = test_env

    # 1. Player 1 joga e marca 45.000 pts
    res1 = await service.submit_score(p1, "starter_song_01", 45000)
    assert res1["score"] == 45000
    assert p1.stars >= 14

    # 2. Player 2 joga e marca 50.000 pts (Diamond Perfect)
    res2 = await service.submit_score(p2, "starter_song_01", 50000)
    assert res2["medal"] == MedalType.DIAMOND_PERFECT.value

    # 3. Consulta ranking da música
    board = await service.get_leaderboard("starter_song_01", friends_only=False, player_cinta=None)
    assert len(board) == 2
    assert board[0].cinta == p2.cinta
    assert board[0].score == 50000
    assert board[1].cinta == p1.cinta


async def test_multiplayer_friendship_and_brags(test_env):
    db, repo, service, p1, p2 = test_env

    # Estabelece amizade
    added = await service.multiplayer.add_friend(p1.cinta, p2.clide)
    assert added is True

    friends = await service.multiplayer.list_friends(p1.cinta)
    assert len(friends) == 1
    assert friends[0]["cinta"] == p2.cinta

    # Player 1 joga com 30.000 pts
    await service.submit_score(p1, "song_rock_01", 30000)

    # Player 2 supera com 48.000 pts -> Gera Brag para Player 1
    await service.submit_score(p2, "song_rock_01", 48000)

    brags = await service.brags.get_pending_brags(p1.cinta)
    assert len(brags) == 1
    assert brags[0].sender_cinta == p2.cinta
    assert brags[0].score_to_beat == 48000
