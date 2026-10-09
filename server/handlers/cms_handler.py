"""CMS service handler for delivering configuration and asset catalog."""

from __future__ import annotations

import time
from typing import Any
from server.config import settings
from server.handlers.base import BaseServiceHandler
from server.models.headers import ClientHeader
from server.assets.catalog import binary_resource, MUSIC_CONFIGS


class CMSHandler(BaseServiceHandler):
    """Processes cmsservice requests delivering asset and config URLs."""

    CATALOG_NAMES = [
        "GameConfig",
        "SongConfig",
        "BeatmapsConfig",
        "AssetsConfig",
        "LangConfig",
        "AssetsPatchConfig",
        "AudioConfig",
        "NewsFeed",
        "ScalingConfig",
        "NotificationConfig",
        "FontFallbackConfig",
        "LiveOpsBundleConfig",
        "LiveOpsDeeplinkRewardConfig",
        "MusicKitConfig",
        "AdsConfig",
    ]

    async def handle(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Returns catalog resource URLs pointing to the local server."""
        resources_list = []
        base_url = settings.assets_base_url.rstrip("/")

        for name in self.CATALOG_NAMES:
            resource = binary_resource(settings.asset_storage_root, base_url, name)
            if resource is not None and name != "GameConfig":
                resources_list.append(resource)
                continue
            if name in MUSIC_CONFIGS:
                continue
            resources_list.append(
                {
                    "name": name,
                    "url": f"{base_url}/configs/{name.lower()}.json",
                    "hash": f"hash_{name.lower()}_v1",
                    "version": 1,
                }
            )

        return {
            "status": 200,
            "id": body.get("id", 1),
            "timestamp": int(time.time() * 1000),
            "blah": {
                "blah": {
                    "blah": resources_list,
                }
            },
        }
