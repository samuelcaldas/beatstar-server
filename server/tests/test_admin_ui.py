"""Serving the exported administration UI at /admin with an SPA fallback that cannot mask the API."""

from httpx import ASGITransport, AsyncClient

from server.admin.settings import AdminAuthSettings
from server.app_factory import create_app

SECRET = "test-admin-secret-with-at-least-32-characters"


def _build_output(root):
    """Writes a minimal static export: an index page and one hashed asset."""
    (root / "_next" / "static").mkdir(parents=True)
    (root / "index.html").write_text("<html><body>admin-shell</body></html>")
    (root / "_next" / "static" / "app.js").write_text("console.log('admin')")
    return root


def _app(tmp_path, ui_directory):
    """Builds an application with administration enabled and the given UI directory."""
    settings = AdminAuthSettings(secret=SECRET, cookie_secure=False)
    return create_app(
        database_path=str(tmp_path / "ui.db"),
        admin_settings=settings,
        asset_root=tmp_path / "uploads",
        admin_ui_directory=ui_directory,
    )


async def _get(app, path: str):
    """Requests a path from the application without starting its lifespan."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


async def test_admin_root_serves_the_exported_index(tmp_path):
    """Breaks if the administration UI is not reachable at /admin/."""
    app = _app(tmp_path, _build_output(tmp_path / "out"))

    response = await _get(app, "/admin/")

    assert response.status_code == 200
    assert "admin-shell" in response.text


async def test_client_side_routes_fall_back_to_the_index(tmp_path):
    """Breaks if a deep link such as /admin/songs/<id> returns 404 instead of the app shell."""
    app = _app(tmp_path, _build_output(tmp_path / "out"))

    response = await _get(app, "/admin/songs/00000000-0000-4000-8000-000000000001")

    assert response.status_code == 200
    assert "admin-shell" in response.text


async def test_exported_assets_are_served_with_their_own_content(tmp_path):
    """Breaks if hashed static assets are replaced by the index page."""
    app = _app(tmp_path, _build_output(tmp_path / "out"))

    response = await _get(app, "/admin/_next/static/app.js")

    assert response.status_code == 200
    assert "console.log('admin')" in response.text


async def test_encoded_traversal_cannot_read_files_outside_the_export(tmp_path):
    """Breaks if an encoded parent-directory segment escapes the export directory."""
    out = _build_output(tmp_path / "out")
    (tmp_path / "secret.txt").write_text("server-private")
    app = _app(tmp_path, out)

    response = await _get(app, "/admin/%2e%2e/secret.txt")

    assert "server-private" not in response.text


async def test_unknown_api_paths_stay_json_404_not_the_ui_shell(tmp_path):
    """Breaks if the SPA fallback masks missing API endpoints with HTML."""
    app = _app(tmp_path, _build_output(tmp_path / "out"))

    response = await _get(app, "/api/admin/does-not-exist")

    assert response.status_code == 404
    assert "text/html" not in response.headers.get("content-type", "")
    assert "admin-shell" not in response.text


async def test_missing_export_directory_is_not_found_rather_than_a_crash(tmp_path):
    """Breaks if an application started before the UI is built fails on /admin/."""
    app = _app(tmp_path, tmp_path / "not-built-yet")

    response = await _get(app, "/admin/")

    assert response.status_code == 404


async def test_missing_hashed_asset_is_404_not_the_shell(tmp_path):
    """Breaks if a stale client after a deploy receives HTML where JavaScript was expected."""
    app = _app(tmp_path, _build_output(tmp_path / "out"))

    response = await _get(app, "/admin/_next/static/gone-after-deploy.js")

    assert response.status_code == 404
    assert "admin-shell" not in response.text
