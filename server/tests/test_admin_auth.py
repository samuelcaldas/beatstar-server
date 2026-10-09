"""Administrator authentication on disposable databases: sessions, CSRF, Origin and throttling."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from server.admin.auth import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from server.admin.models import AdministratorSession, AdministratorUser
from server.admin.provision import main as provision_main
from server.admin.provision import provision_administrator
from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app

SECRET = "test-admin-secret-with-at-least-32-characters"
ORIGIN = "http://test"
FOREIGN_ORIGIN = "http://evil.example"
EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"
LOGIN_PATH = "/api/admin/auth/login"
LOGOUT_PATH = "/api/admin/auth/logout"
ME_PATH = "/api/admin/me"


@pytest.fixture
async def admin_client(tmp_path, monkeypatch):
    """Runs the real startup path (legacy init + migrations) and provisions one administrator."""
    monkeypatch.chdir(tmp_path)
    settings = AdminAuthSettings(
        secret=SECRET,
        cookie_secure=False,
        allowed_origins=(ORIGIN,),
        login_max_attempts=3,
        login_window_seconds=900,
    )
    app = create_app(database_path=str(tmp_path / "admin.db"), admin_settings=settings)
    async with app.router.lifespan_context(app):
        await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield app, client


async def _login(client, password=PASSWORD):
    return await client.post(LOGIN_PATH, data={"username": EMAIL, "password": password})


async def test_register_route_is_absent(admin_client):
    """Breaks if fastapi-users' public register router is mounted."""
    _, client = admin_client
    response = await client.post(
        "/api/admin/auth/register", json={"email": "new@example.com", "password": PASSWORD}
    )
    assert response.status_code == 404


async def test_login_sets_http_only_session_cookie_that_authorizes_me(admin_client):
    """Breaks if the session cookie is readable by scripts or does not authorize requests."""
    _, client = admin_client
    response = await _login(client)

    assert response.status_code == 204
    session_cookies = [v for v in response.headers.get_list("set-cookie") if v.startswith(SESSION_COOKIE)]
    assert session_cookies and "httponly" in session_cookies[0].lower()
    me = await client.get(ME_PATH)
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


async def test_logout_revokes_the_session_on_the_server(admin_client):
    """Breaks if logout only clears the browser cookie and the old token stays valid."""
    app, client = admin_client
    await _login(client)
    old_token = client.cookies.get(SESSION_COOKIE)
    csrf_token = client.cookies.get(CSRF_COOKIE)

    logout = await client.post(LOGOUT_PATH, headers={CSRF_HEADER: csrf_token})
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", cookies={SESSION_COOKIE: old_token}
    ) as replay_client:
        replay = await replay_client.get(ME_PATH)

    assert logout.status_code == 204
    assert replay.status_code == 401


async def test_expired_session_is_rejected(admin_client):
    """Breaks if sessions never expire after the configured lifetime."""
    app, client = admin_client
    await _login(client)
    async with app.state.admin_session_maker() as session:
        token_row = (await session.execute(select(AdministratorSession))).scalar_one()
        token_row.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        await session.commit()

    response = await client.get(ME_PATH)

    assert response.status_code == 401


async def test_cookie_write_without_csrf_header_is_forbidden(admin_client):
    """Breaks if cookie-authenticated writes skip the double-submit CSRF check."""
    _, client = admin_client
    await _login(client)

    response = await client.post(LOGOUT_PATH)

    assert response.status_code == 403
    assert (await client.get(ME_PATH)).status_code == 200


async def test_foreign_origin_write_is_forbidden_even_with_csrf_header(admin_client):
    """Breaks if the Origin allowlist is not enforced on unsafe requests."""
    _, client = admin_client
    await _login(client)
    csrf_token = client.cookies.get(CSRF_COOKIE)

    response = await client.post(
        LOGOUT_PATH, headers={CSRF_HEADER: csrf_token, "Origin": FOREIGN_ORIGIN}
    )

    assert response.status_code == 403
    assert (await client.get(ME_PATH)).status_code == 200


async def test_repeated_failed_logins_are_throttled(admin_client):
    """Breaks if unlimited password guesses are accepted after the configured maximum."""
    _, client = admin_client
    for _ in range(3):
        assert (await _login(client, password="wrong password")).status_code == 401

    throttled = await _login(client)

    assert throttled.status_code == 429
    assert throttled.headers["retry-after"]


async def test_provisioning_is_idempotent(admin_client):
    """Breaks if re-running provisioning duplicates the administrator row."""
    app, _ = admin_client

    outcome = await provision_administrator(app.state.admin_session_maker, SECRET, EMAIL, PASSWORD)

    assert outcome == "exists"
    async with app.state.admin_session_maker() as session:
        count = (await session.execute(select(func.count()).select_from(AdministratorUser))).scalar_one()
    assert count == 1


def test_provisioning_cli_never_echoes_the_password(tmp_path, capsys):
    """Breaks if the CLI prints the password it was given through the environment."""
    database_file = tmp_path / "cli.db"
    environment = {"ADMIN_AUTH_SECRET": SECRET, "ADMIN_PASSWORD": PASSWORD}

    exit_code = provision_main(
        ["--database-path", str(database_file), "--email", EMAIL], environment
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert PASSWORD not in captured.out + captured.err
    with sqlite3.connect(database_file) as connection:
        assert connection.execute('SELECT COUNT(*) FROM "user"').fetchone()[0] == 1
