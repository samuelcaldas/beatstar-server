"""CORS policy: only explicitly configured origins receive browser access, with credentials."""

from httpx import ASGITransport, AsyncClient

from server.app_factory import create_app

ALLOWED_ORIGIN = "https://admin.example.com"
FOREIGN_ORIGIN = "https://evil.example.com"
PREFLIGHT_PATH = "/api/commerce/catalog"


async def _preflight(app, origin: str, requested_headers: str = "Content-Type"):
    """Sends a CORS preflight for a cross-origin GET request and returns the response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.options(
            PREFLIGHT_PATH,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": requested_headers,
            },
        )


async def test_configured_origin_receives_credentialed_access(tmp_path):
    """Breaks if configured origins are not allowed to send cookies cross-origin."""
    app = create_app(database_path=str(tmp_path / "cors.db"), cors_origins=[ALLOWED_ORIGIN])

    response = await _preflight(app, ALLOWED_ORIGIN)

    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_foreign_origin_receives_no_cors_grant(tmp_path):
    """Breaks if any origin is reflected or wildcarded instead of matched exactly."""
    app = create_app(database_path=str(tmp_path / "cors.db"), cors_origins=[ALLOWED_ORIGIN])

    response = await _preflight(app, FOREIGN_ORIGIN)

    assert "access-control-allow-origin" not in response.headers


async def test_csrf_header_is_allowed_for_configured_origin(tmp_path):
    """Breaks if the admin CSRF header cannot be sent from the allowed origin."""
    app = create_app(database_path=str(tmp_path / "cors.db"), cors_origins=[ALLOWED_ORIGIN])

    response = await _preflight(app, ALLOWED_ORIGIN, requested_headers="X-CSRF-Token")

    assert "x-csrf-token" in response.headers["access-control-allow-headers"].lower()


async def test_empty_configuration_grants_no_browser_access(tmp_path):
    """Breaks if the default configuration reintroduces wildcard CORS."""
    app = create_app(database_path=str(tmp_path / "cors.db"), cors_origins=[])

    response = await _preflight(app, ALLOWED_ORIGIN)

    assert "access-control-allow-origin" not in response.headers
