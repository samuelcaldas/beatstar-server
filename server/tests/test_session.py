"""Unit tests for user service and session management."""

import pytest
from server.admin.database import create_admin_engine, create_admin_session_maker
from server.handlers.session_handler import SessionHandler
from server.player_auth.store import PlayerTicketStore
from server.models.headers import ClientHeader
from server.storage.database import DatabaseManager
from server.storage.migrations.runner import upgrade_to_head
from server.storage.player_repository import PlayerRepository


@pytest.mark.asyncio
async def test_session_handler_new_player(tmp_path):
    db_file = str(tmp_path / "test.db")
    db_manager = DatabaseManager(db_file)
    await db_manager.initialize()
    upgrade_to_head(db_file)
    engine = create_admin_engine(db_file)
    store = PlayerTicketStore(create_admin_session_maker(engine), lifetime_seconds=3600)
    repo = PlayerRepository(db_manager)

    handler = SessionHandler(repo, store)
    client_hdr = ClientHeader(service="userservice", rpcthing="rpc-1")
    body = {"all_in_one_login": {"cinta": "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905"}}

    resp = await handler.handle(client_hdr, body)
    assert resp["status"] == 200
    auth_data = resp["resp_login_of_some_type"]
    assert auth_data["cinta"] == "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905"
    assert auth_data["authenticationTicket"].startswith("auth-")

    # Verifica persistência
    saved_profile = await repo.get_by_cinta("676d4d53-f0cb-41c6-8c27-4bb3c3c3c905")
    assert saved_profile is not None
    assert saved_profile.player_name == "BeatstarPlayer"
