"""Unit tests for synchronization and audit events."""

import pytest
from server.handlers.sync_handler import SyncHandler
from server.models.headers import ClientHeader
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository


@pytest.mark.asyncio
async def test_sync_handler_records_rhythm_game_ended(tmp_path):
    db_file = str(tmp_path / "sync_test.db")
    db_manager = DatabaseManager(db_file)
    await db_manager.initialize()
    repo = PlayerRepository(db_manager)

    profile = PlayerProfile(
        cinta="676d4d53-f0cb-41c6-8c27-4bb3c3c3c905", stars=10, coins=50
    )
    await repo.save(profile)

    handler = SyncHandler(repo)
    client_hdr = ClientHeader(
        service="syncservice",
        rpcthing="rpc-sync-1",
        clide="676d4d53-f0cb-41c6-8c27-4bb3c3c3c905",
    )
    body = {
        "audits": [
            {
                "event": "RhythmGameEnded_SharplaAudit",
                "score": 49500,
            }
        ]
    }

    resp = await handler.handle(client_hdr, body)
    assert resp["status"] == 200
    assert resp["sync_success"] is True

    updated_profile = await repo.get_by_cinta("676d4d53-f0cb-41c6-8c27-4bb3c3c3c905")
    assert updated_profile.stars == 15
    assert updated_profile.coins >= 99

