"""Application factory isolation: routers must write only to the database the app was built with."""

from httpx import ASGITransport, AsyncClient

from server.app_factory import create_app
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository


async def test_commerce_grant_writes_only_to_injected_database(tmp_path, monkeypatch):
    """Breaks if a router keeps a module-level default DatabaseManager (data/beatstar.db)."""
    monkeypatch.chdir(tmp_path)
    database_file = tmp_path / "isolated.db"
    database = DatabaseManager(str(database_file))
    await database.initialize()
    await PlayerRepository(database).save(
        PlayerProfile(cinta="factory-cinta", clide="factory", coins=10, gems=0)
    )

    app = create_app(database_path=str(database_file))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/commerce/grant",
            json={"cinta": "factory-cinta", "currency": "coins", "amount": 5},
        )

    assert response.status_code == 200
    stored = await PlayerRepository(database).get_by_cinta("factory-cinta")
    assert stored.coins == 15
    assert not (tmp_path / "data" / "beatstar.db").exists()
