"""CORS for the development domain: anchored pattern for timoteo.mg.gov.br dev subdomains, over HTTPS only."""

from httpx import ASGITransport, AsyncClient

from server.app_factory import create_app

PREFLIGHT_PATH = "/api/commerce/catalog"
DEV_ORIGIN = "https://beatstar.dev.timoteo.mg.gov.br"
NESTED_DEV_ORIGIN = "https://admin.game.dev.timoteo.mg.gov.br"


async def _preflight_allowed_origin(tmp_path, origin: str) -> str | None:
    """Returns the Access-Control-Allow-Origin value for a preflight, or None when no grant is made."""
    app = create_app(database_path=str(tmp_path / "cors-dev.db"), cors_origins=[], asset_root=tmp_path / "u")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            PREFLIGHT_PATH,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
    return response.headers.get("access-control-allow-origin")


async def test_dev_subdomain_receives_credentialed_access(tmp_path):
    """Breaks if the development frontend cannot call the API with its session cookie."""
    assert await _preflight_allowed_origin(tmp_path, DEV_ORIGIN) == DEV_ORIGIN


async def test_nested_dev_subdomain_receives_access(tmp_path):
    """Breaks if multi-level development hosts are rejected."""
    assert await _preflight_allowed_origin(tmp_path, NESTED_DEV_ORIGIN) == NESTED_DEV_ORIGIN


async def test_plain_http_dev_origin_is_refused(tmp_path):
    """Breaks if the pattern accepts an unencrypted origin."""
    assert await _preflight_allowed_origin(tmp_path, "http://beatstar.dev.timoteo.mg.gov.br") is None


async def test_domain_appended_after_dev_domain_is_refused(tmp_path):
    """Breaks if an attacker-controlled domain that merely starts with the dev domain is accepted."""
    origin = "https://dev.timoteo.mg.gov.br.attacker.example"

    assert await _preflight_allowed_origin(tmp_path, origin) is None


async def test_label_that_only_ends_with_dev_is_refused(tmp_path):
    """Breaks if a host such as evildev.timoteo.mg.gov.br passes as a development subdomain."""
    origin = "https://evildev.timoteo.mg.gov.br"

    assert await _preflight_allowed_origin(tmp_path, origin) is None


async def test_production_host_is_not_granted_by_the_dev_pattern(tmp_path):
    """Breaks if the development pattern also grants the base production domain."""
    assert await _preflight_allowed_origin(tmp_path, "https://beatstar.timoteo.mg.gov.br") is None


async def test_regex_can_be_disabled_by_configuration(tmp_path):
    """Breaks if the dev pattern cannot be turned off, leaving no way to remove the grant."""
    app = create_app(
        database_path=str(tmp_path / "cors-off.db"),
        cors_origins=[],
        cors_origin_regex="",
        asset_root=tmp_path / "u",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            PREFLIGHT_PATH,
            headers={"Origin": DEV_ORIGIN, "Access-Control-Request-Method": "GET"},
        )

    assert response.headers.get("access-control-allow-origin") is None
