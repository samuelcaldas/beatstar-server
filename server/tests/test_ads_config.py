"""Tests for Ads configuration and feature flags."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from server.app import app
from server.config import settings


@pytest.mark.asyncio
async def test_ads_config_endpoint() -> None:
    """Verifies that /assets/configs/adsconfig.json serves the configured ad parameters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/assets/configs/adsconfig.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "AdsConfig"
        assert "data" in data
        ads_data = data["data"]
        assert ads_data["feature_flag_enabled"] == settings.feature_flag_google_ads_enabled
        assert ads_data["app_id"] == settings.google_ads_app_id
        assert ads_data["rewarded_unit_id"] == settings.google_ads_rewarded_unit_id
        assert ads_data["interstitial_unit_id"] == settings.google_ads_interstitial_unit_id
        assert ads_data["instant_reward_on_disabled"] is True


@pytest.mark.asyncio
async def test_game_config_includes_ads_feature_flag() -> None:
    """Verifies that /assets/configs/gameconfig.json includes VideoAdsEnabled flag."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/assets/configs/gameconfig.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "GameConfig"
        flags = data["data"]["feature_flags"]
        assert "VideoAdsEnabled" in flags
        assert flags["VideoAdsEnabled"] == settings.feature_flag_google_ads_enabled
