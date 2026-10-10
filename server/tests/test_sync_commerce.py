import pytest
from httpx import AsyncClient, ASGITransport
from server.app import app, db_manager
from server.commerce import CommerceService
from server.handlers.sync_handler import SyncHandler
from server.models.headers import ClientHeader
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository


@pytest.fixture
async def setup_test_player():
    await db_manager.initialize()
    repo = PlayerRepository(db_manager)
    profile = PlayerProfile(
        cinta="player-test-commerce-uuid",
        clide="c0mm3rc3",
        coins=1000,
        gems=500,
    )
    await repo.save(profile)
    return profile


async def test_sync_handler_processes_commerce_audits(setup_test_player):
    repo = PlayerRepository(db_manager)
    service = CommerceService()
    handler = SyncHandler(repo, service)

    header = ClientHeader(
        service="syncservice",
        command="SyncReq",
        clide="c0mm3rc3",
    )
    body = {
        "cinta": setup_test_player.cinta,
        "audits": [
            {"event": "BuyShopItem_SharplaAudit", "product_id": "coins_500"},
            {"event": "Season_BuyLevel_SharplaAudit", "numLevels": 1},
            {"event": "SetGlobalTrackSkin_SharplaAudit", "trackSkin_id": "skin_synthwave_lane"},
        ],
    }

    resp = await handler.handle(header, body)
    assert resp["sync_success"] is True

    updated = await repo.get_by_cinta(setup_test_player.cinta)
    assert updated is not None
    # 500 gems - 25 (coins_500) - 30 (1 level skip) = 445 gems
    assert updated.gems == 445
    # 1000 coins + 500 = 1500 coins
    assert updated.coins == 1500
    assert updated.customisation.get("tour_pass_level") == 2
    assert updated.customisation.get("active_track_skin") == "skin_synthwave_lane"


async def test_commerce_api_endpoints(setup_test_player):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Flags endpoint
        resp_flags = await client.get("/api/commerce/flags")
        assert resp_flags.status_code == 200
        flags = resp_flags.json()
        assert "shop_enabled" in flags

        # 2. POST is not mounted without administration; GET stays public (see test_commerce_administration)
        resp_update = await client.post(
            "/api/commerce/flags",
            json={"flag_name": "iap_enabled", "enabled": True},
        )
        assert resp_update.status_code == 405

        # 3. Catalog endpoint
        resp_catalog = await client.get("/api/commerce/catalog")
        assert resp_catalog.status_code == 200
        items = resp_catalog.json()
        assert len(items) > 0
        assert any(it["product_id"] == "box_rock" for it in items)

        # 4. Wallet endpoint
        resp_wallet = await client.get(
            f"/api/commerce/wallet/{setup_test_player.cinta}"
        )
        assert resp_wallet.status_code == 200
        wallet_data = resp_wallet.json()
        assert wallet_data["cinta"] == setup_test_player.cinta

        # 5. Grant endpoint is not mounted without administration
        resp_grant = await client.post(
            "/api/commerce/grant",
            json={
                "cinta": setup_test_player.cinta,
                "currency": "gems",
                "amount": 100,
            },
        )
        assert resp_grant.status_code == 404
