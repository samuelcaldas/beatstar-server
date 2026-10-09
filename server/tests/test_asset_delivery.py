"""Tests for AssetBundle streaming, Range requests, and CMS catalog delivery."""

from __future__ import annotations

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from server.app import app
from server.music.reference_fixture import REFERENCE_SONG


@pytest.mark.asyncio
async def test_bundle_endpoint_serves_real_bundle():
    """Validates delivery of real AssetBundles with content length and accept-ranges."""
    bundle_name = REFERENCE_SONG.beatmap_bundle_filename
    bundle_file = Path("data/bundles") / bundle_name
    if not bundle_file.exists():
        pytest.skip("Reference bundle not found in data/bundles")

    expected_size = bundle_file.stat().st_size

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/assets/bundles/{bundle_name}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["accept-ranges"] == "bytes"
        assert int(response.headers["content-length"]) == expected_size
        assert len(response.content) == expected_size
        assert response.content[:7] == b"UnityFS"


@pytest.mark.asyncio
async def test_bundle_endpoint_supports_http_range_requests():
    """Validates partial content delivery for AssetBundle streaming."""
    bundle_name = REFERENCE_SONG.beatmap_bundle_filename
    bundle_file = Path("data/bundles") / bundle_name
    if not bundle_file.exists():
        pytest.skip("Reference bundle not found in data/bundles")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"Range": "bytes=0-49"}
        response = await client.get(f"/assets/bundles/{bundle_name}", headers=headers)

        assert response.status_code == 206
        assert len(response.content) == 50
        assert "Content-Range" in response.headers
        assert response.headers["Content-Range"].startswith("bytes 0-49/")
        assert response.content[:7] == b"UnityFS"


@pytest.mark.asyncio
async def test_bundle_endpoint_nonexistent_returns_404():
    """Verifies that missing bundles return 404 rather than placeholder stubs."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/assets/bundles/nonexistent_fake_bundle.bundle")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_binary_config_delivery():
    """Validates binary delivery of baked configurations (SongConfig, AssetsConfig)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/assets/configs/SongConfig.bin")
        if Path("data/configs/SongConfig.bin").exists():
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/octet-stream"
            assert len(response.content) == 845233


@pytest.mark.asyncio
async def test_cms_handler_includes_music_catalogs():
    """Validates cmsservice returns URLs for SongConfig, BeatmapsConfig and AssetsConfig."""
    from server.handlers.cms_handler import CMSHandler
    from server.models.headers import ClientHeader

    handler = CMSHandler()
    header = ClientHeader(session_id="test", player_id="test", timestamp=123)
    result = await handler.handle(header, {})

    resources = result["blah"]["blah"]["blah"]
    resource_names = {r["name"] for r in resources}

    assert "GameConfig" in resource_names
    assert "SongConfig" in resource_names
    assert "BeatmapsConfig" in resource_names
    assert "AssetsConfig" in resource_names
    assert "AdsConfig" in resource_names
