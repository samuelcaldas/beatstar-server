import pytest
from httpx import AsyncClient, ASGITransport
from server.app import app, db_manager
from server.models.headers import ClientHeader
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository
from server.handlers.sync_handler import SyncHandler


@pytest.fixture
async def setup_multiplayer_environment():
    await db_manager.initialize()
    repo = PlayerRepository(db_manager)

    p1 = PlayerProfile(cinta="cinta-multi-alpha", clide="alpha001", player_name="AlphaGamer", stars=5, level=1)
    p2 = PlayerProfile(cinta="cinta-multi-beta", clide="beta002", player_name="BetaBeater", stars=20, level=2)
    await repo.save(p1)
    await repo.save(p2)
    return p1, p2, repo


async def test_protocol_sync_records_gameplay_and_leaderboard(setup_multiplayer_environment):
    p1, p2, repo = setup_multiplayer_environment
    handler = SyncHandler(repo)

    # 1. Envia auditoria de partida concluída para Player 1
    header = ClientHeader(service="syncservice", command="SyncReq", clide=p1.clide)
    body = {
        "cinta": p1.cinta,
        "audits": [
            {"event": "RhythmGameEnded_SharplaAudit", "song_id": "song_test_proto_01", "score": 49600, "accuracy": 0.99}
        ],
    }
    sync_res = await handler.handle(header, body)
    assert sync_res["sync_success"] is True

    # 2. Requisita Leaderboard via protocolo SpaceApe
    lb_hdr = ClientHeader(service="syncservice", command="LeaderboardWithViews_Req", clide=p1.clide)
    lb_body = {"cinta": p1.cinta, "leaderboardName": "song_test_proto_01", "friendsOnly": False}
    lb_res = await handler.handle(lb_hdr, lb_body)
    assert lb_res["status"] == 200
    assert len(lb_res["results"]) >= 1
    assert lb_res["results"][0]["player"]["clide"] == p1.clide
    assert lb_res["results"][0]["score"] == 49600


async def test_protocol_social_add_friend_and_views(setup_multiplayer_environment):
    p1, p2, repo = setup_multiplayer_environment
    handler = SyncHandler(repo)

    # 1. Adiciona amigo via AddFriend_Req
    add_hdr = ClientHeader(service="sharplaservice", command="AddFriend_Req", clide=p1.clide)
    add_body = {"cinta": p1.cinta, "clide": p2.clide}
    add_res = await handler.handle(add_hdr, add_body)
    assert add_res["success"] is True

    # 2. Consulta lista de amigos via FriendViews_Req
    views_hdr = ClientHeader(service="sharplaservice", command="FriendViews_Req", clide=p1.clide)
    views_body = {"cinta": p1.cinta}
    views_res = await handler.handle(views_hdr, views_body)
    assert views_res["status"] == 200
    assert len(views_res["friendViews"]) == 1
    assert views_res["friendViews"][0]["clide"] == p2.clide


async def test_gameplay_api_routes(setup_multiplayer_environment):
    p1, p2, _ = setup_multiplayer_environment
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Progression endpoint
        prog_res = await client.get(f"/api/gameplay/progression/{p1.cinta}")
        assert prog_res.status_code == 200
        prog_data = prog_res.json()
        assert prog_data["cinta"] == p1.cinta

        # 2. Global Leaderboard endpoint
        lb_res = await client.get("/api/gameplay/leaderboards/global")
        assert lb_res.status_code == 200
        assert isinstance(lb_res.json(), list)

        # 3. Friends endpoint
        friends_res = await client.get(f"/api/gameplay/friends/{p1.cinta}")
        assert friends_res.status_code == 200
