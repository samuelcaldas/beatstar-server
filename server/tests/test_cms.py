"""Unit tests for CMS catalog handler."""

import pytest
from server.handlers.cms_handler import CMSHandler
from server.models.headers import ClientHeader


@pytest.mark.asyncio
async def test_cms_handler_returns_catalogs():
    handler = CMSHandler()
    client_hdr = ClientHeader(service="cmsservice", rpcthing="rpc-cms-1")
    body = {"id": 1}

    resp = await handler.handle(client_hdr, body)
    assert resp["status"] == 200
    resources = resp["blah"]["blah"]["blah"]
    assert len(resources) >= 5

    names = [r["name"] for r in resources]
    assert "GameConfig" in names
    assert "AudioConfig" in names
    assert "AssetsPatchConfig" in names
