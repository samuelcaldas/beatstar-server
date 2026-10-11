"""Application factory isolation: routers must write only to the database the app was built with."""

from httpx import ASGITransport, AsyncClient

from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import admin_settings_from_environment, create_app
from server.config import ServerSettings
from server.models.player import PlayerProfile
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository

ADMIN_SECRET = "test-admin-secret-with-at-least-32-characters"
ADMIN_PASSWORD = "correct horse battery staple"


async def test_commerce_grant_writes_only_to_injected_database(tmp_path, monkeypatch):
    """Breaks if a router keeps a module-level default DatabaseManager (data/beatstar.db)."""
    monkeypatch.chdir(tmp_path)
    database_file = tmp_path / "isolated.db"
    database = DatabaseManager(str(database_file))
    await database.initialize()
    await PlayerRepository(database).save(
        PlayerProfile(cinta="factory-cinta", clide="factory", coins=10, gems=0)
    )

    settings = AdminAuthSettings(secret=ADMIN_SECRET, cookie_secure=False)
    app = create_app(database_path=str(database_file), admin_settings=settings, asset_root=tmp_path / "u")
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, ADMIN_SECRET, "factory@example.com", ADMIN_PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/admin/auth/login",
                data={"username": "factory@example.com", "password": ADMIN_PASSWORD},
            )
            response = await client.post(
                "/api/commerce/grant",
                json={"cinta": "factory-cinta", "currency": "coins", "amount": 5},
                headers={"X-CSRF-Token": client.cookies.get("beatstar_admin_csrf")},
            )

    assert response.status_code == 200
    stored = await PlayerRepository(database).get_by_cinta("factory-cinta")
    assert stored.coins == 15
    assert not (tmp_path / "data" / "beatstar.db").exists()


def test_blank_admin_secret_leaves_administration_unconfigured(monkeypatch):
    """Breaks if copying .env.example with an empty ADMIN_AUTH_SECRET stops the game server."""
    monkeypatch.setenv("ADMIN_AUTH_SECRET", "")

    assert admin_settings_from_environment(ServerSettings()) is None
