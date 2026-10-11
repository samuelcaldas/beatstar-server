"""Commerce administration: grant and flag changes need a superuser session and CSRF; reads stay public."""

import pytest
from httpx import ASGITransport, AsyncClient

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository

SECRET = "test-admin-secret-with-at-least-32-characters"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
CINTA = "commerce-admin-cinta"
GRANT_PATH = "/api/commerce/grant"
FLAGS_PATH = "/api/commerce/flags"
GAME_CONFIG_PATH = "/assets/configs/gameconfig"


@pytest.fixture
async def admin_app(tmp_path):
    """Starts the application with administration enabled and one provisioned superuser."""
    settings = AdminAuthSettings(secret=SECRET, cookie_secure=False)
    app = create_app(
        database_path=str(tmp_path / "commerce.db"),
        admin_settings=settings,
        asset_root=tmp_path / "u",
    )
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        await PlayerRepository(app.state.database).save(
            PlayerProfile(cinta=CINTA, clide="c", coins=10, gems=0)
        )
        yield app


@pytest.fixture
async def signed_in_client(admin_app):
    """Yields a client holding the administrator session and CSRF cookies from a real login."""
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as client:
        await client.post("/api/admin/auth/login", data={"username": EMAIL, "password": PASSWORD})
        yield client


def _csrf_headers(client):
    """Echoes the CSRF cookie in the header, as the browser client does."""
    return {CSRF_HEADER: client.cookies.get(CSRF_COOKIE)}


async def test_grant_without_session_is_rejected(admin_app):
    """Breaks if /api/commerce/grant credits funds to anyone who can reach the server."""
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as client:
        response = await client.post(GRANT_PATH, json={"cinta": CINTA, "currency": "coins", "amount": 5})

    assert response.status_code == 401


async def test_flag_change_without_session_is_rejected(admin_app):
    """Breaks if /api/commerce/flags can be changed without an administrator."""
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as client:
        response = await client.post(FLAGS_PATH, json={"flag_name": "iap_enabled", "enabled": True})

    assert response.status_code == 401


async def test_grant_with_session_but_without_csrf_is_rejected(signed_in_client):
    """Breaks if a cookie-authenticated write can be forged from another site."""
    response = await signed_in_client.post(GRANT_PATH, json={"cinta": CINTA, "currency": "coins", "amount": 5})

    assert response.status_code == 403


async def test_administrator_grant_credits_the_player(signed_in_client):
    """Breaks if an authorized grant does not reach the player's stored profile."""
    response = await signed_in_client.post(
        GRANT_PATH,
        json={"cinta": CINTA, "currency": "coins", "amount": 5},
        headers=_csrf_headers(signed_in_client),
    )

    assert response.status_code == 200
    assert response.json()["coins"] == 15


async def test_administrator_flag_change_reaches_the_game_config(admin_app, signed_in_client):
    """Breaks if the flag route changes a different CommerceService than the one GameConfig reads."""
    update = await signed_in_client.post(
        FLAGS_PATH,
        json={"flag_name": "iap_enabled", "enabled": True},
        headers=_csrf_headers(signed_in_client),
    )
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as public:
        config = await public.get(GAME_CONFIG_PATH)

    assert update.status_code == 200
    assert config.json()["data"]["feature_flags"]["NotEnoughGemsShowIAPPopup"] is True


async def test_grant_route_is_absent_when_administration_is_not_configured(tmp_path):
    """Breaks if an unconfigured server exposes an unprotected grant route."""
    app = create_app(database_path=str(tmp_path / "plain.db"), asset_root=tmp_path / "u")
    async with app.router.lifespan_context(app):
        await PlayerRepository(app.state.database).save(PlayerProfile(cinta=CINTA, clide="c", coins=10, gems=0))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(GRANT_PATH, json={"cinta": CINTA, "currency": "coins", "amount": 5})

    assert response.status_code == 404


async def test_flag_and_catalog_reads_stay_public(tmp_path):
    """Breaks if the game's read-only commerce endpoints start requiring a session."""
    app = create_app(database_path=str(tmp_path / "plain.db"), asset_root=tmp_path / "u")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        flags = await client.get(FLAGS_PATH)
        catalog = await client.get("/api/commerce/catalog")

    assert flags.status_code == 200
    assert catalog.status_code == 200
