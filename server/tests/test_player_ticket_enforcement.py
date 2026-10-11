"""Player ticket enforcement: observe-only while the flag is off, rejection on player routes when it is on."""

import logging
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from server.app_factory import create_app
from server.models.player import PlayerProfile
from server.storage.player_repository import PlayerRepository

CINTA = "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905"
OTHER_CINTA = "11111111-2222-4333-8444-555555555555"
TICKET_HEADER = "authenticationTicket"
WALLET_PATH = f"/api/commerce/wallet/{CINTA}"
PURCHASE_PATH = "/api/commerce/purchase"
PROGRESSION_PATH = f"/api/gameplay/progression/{CINTA}"
LEADERBOARD_PATH = "/api/gameplay/leaderboards/global"
GATEWAY_PATH = "/gateway"


@asynccontextmanager
async def _started_app(tmp_path, enforcement: bool):
    """Starts an application with the given enforcement setting and two saved players."""
    app = create_app(
        database_path=str(tmp_path / "players.db"),
        asset_root=tmp_path / "u",
        player_ticket_enforcement=enforcement,
    )
    async with app.router.lifespan_context(app):
        repository = PlayerRepository(app.state.database)
        await repository.save(PlayerProfile(cinta=CINTA, clide="c1", coins=100, gems=10))
        await repository.save(PlayerProfile(cinta=OTHER_CINTA, clide="c2", coins=100, gems=10))
        yield app


@pytest.fixture
async def enforced_app(tmp_path):
    """Application with the player ticket flag enabled."""
    async with _started_app(tmp_path, enforcement=True) as app:
        yield app


@pytest.fixture
async def observing_app(tmp_path):
    """Application with the player ticket flag disabled, which is the shipped default."""
    async with _started_app(tmp_path, enforcement=False) as app:
        yield app


async def test_flag_is_off_by_default():
    """Breaks if enforcement starts enabled and rejects clients before real traffic confirms the ticket."""
    from server.config import ServerSettings

    assert ServerSettings().feature_flag_player_ticket_enforcement_enabled is False


async def test_wallet_without_ticket_is_served_while_flag_is_off(observing_app):
    """Breaks if observing tickets also rejects requests before enforcement is enabled."""
    async with AsyncClient(transport=ASGITransport(app=observing_app), base_url="http://test") as client:
        response = await client.get(WALLET_PATH)

    assert response.status_code == 200


async def test_gateway_request_without_ticket_is_logged_not_rejected(observing_app, caplog):
    """Breaks if gateway requests without a valid ticket are refused, or are not recorded for analysis."""
    caplog.set_level(logging.WARNING, logger="server.player_auth")
    payload = {"header": {"service": "profileservice", "rpcthing": "r1"}, "body": {"cinta": CINTA}}

    async with AsyncClient(transport=ASGITransport(app=observing_app), base_url="http://test") as client:
        response = await client.post(GATEWAY_PATH, json=payload)

    assert response.status_code == 200
    assert "outcome=missing" in caplog.text


async def test_wallet_without_ticket_is_rejected_when_enforced(enforced_app):
    """Breaks if an anonymous request can read a player's wallet once enforcement is on."""
    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.get(WALLET_PATH)

    assert response.status_code == 401


async def test_wallet_with_unknown_ticket_is_rejected_when_enforced(enforced_app):
    """Breaks if a made-up ticket value is accepted."""
    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.get(WALLET_PATH, headers={TICKET_HEADER: "auth-forged"})

    assert response.status_code == 401


async def test_wallet_with_another_players_ticket_is_forbidden(enforced_app):
    """Breaks if a valid ticket for one player can read a different player's wallet."""
    other_ticket = await enforced_app.state.player_ticket_store.issue(OTHER_CINTA)

    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.get(WALLET_PATH, headers={TICKET_HEADER: other_ticket})

    assert response.status_code == 403


async def test_wallet_with_own_ticket_is_served_when_enforced(enforced_app):
    """Breaks if the player's own valid ticket is refused on their own route."""
    own_ticket = await enforced_app.state.player_ticket_store.issue(CINTA)

    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.get(WALLET_PATH, headers={TICKET_HEADER: own_ticket})

    assert response.status_code == 200


async def test_purchase_for_another_player_is_forbidden_when_enforced(enforced_app):
    """Breaks if a purchase body can name a player other than the ticket's owner."""
    own_ticket = await enforced_app.state.player_ticket_store.issue(CINTA)

    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.post(
            PURCHASE_PATH,
            json={"cinta": OTHER_CINTA, "product_id": "coins_500"},
            headers={TICKET_HEADER: own_ticket},
        )

    assert response.status_code == 403


async def test_gameplay_progression_without_ticket_is_rejected_when_enforced(enforced_app):
    """Breaks if gameplay progression can be read anonymously once enforcement is on."""
    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.get(PROGRESSION_PATH)

    assert response.status_code == 401


async def test_leaderboards_stay_public_when_enforced(enforced_app):
    """Breaks if public leaderboards start requiring a ticket."""
    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        response = await client.get(LEADERBOARD_PATH)

    assert response.status_code == 200


async def test_ticket_value_never_reaches_the_log(enforced_app, caplog):
    """Breaks if a rejected ticket is written to the logs, where it would be a usable credential."""
    caplog.set_level(logging.WARNING, logger="server.player_auth")
    secret_like_ticket = "auth-do-not-log-this-value"

    async with AsyncClient(transport=ASGITransport(app=enforced_app), base_url="http://test") as client:
        await client.get(WALLET_PATH, headers={TICKET_HEADER: secret_like_ticket})

    assert "outcome=unknown" in caplog.text
    assert secret_like_ticket not in caplog.text
