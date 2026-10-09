"""Core HTTP routes: health, gateways, baked configs and asset bundles.

Handlers read their dependencies from request.app.state so that each application
built by create_app() keeps its own database and dispatcher.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import zoneinfo
from fastapi import APIRouter, HTTPException, Request, Response
from server.assets.catalog import BINARY_CONFIGS, file_response
from server.config import settings
from server.gateway.header_parser import HeaderParser

TIMEZONE = zoneinfo.ZoneInfo(settings.timezone)

core_router = APIRouter()


@core_router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for Docker and monitoring."""
    now = datetime.now(TIMEZONE).isoformat()
    return {
        "status": "healthy",
        "service": "beatstar-private-server",
        "environment": settings.environment,
        "timezone": settings.timezone,
        "server_time": now,
    }


@core_router.post("/gateway")
async def http_gateway(request: Request) -> dict[str, Any]:
    """JSON-based Gateway endpoint for HTTP-based RPC calls."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Corpo da requisição deve ser JSON válido."
        ) from exc

    header_data = payload.get("header", {})
    body_data = payload.get("body", {})

    client_header = HeaderParser.parse_dict(header_data)
    server_header, res_body = await request.app.state.dispatcher.dispatch_payload(
        client_header, body_data
    )

    return {
        "header": server_header.model_dump(by_alias=True),
        "body": res_body,
    }


@core_router.post("/socket-gateway")
async def socket_gateway(request: Request) -> Response:
    """Raw binary wire frame endpoint matching SocketGateway wire format."""
    raw_body = await request.body()
    if len(raw_body) < 8:
        raise HTTPException(status_code=400, detail="Frame binário inválido.")

    try:
        res_wire = await request.app.state.dispatcher.dispatch_wire_frame(raw_body)
        return Response(content=res_wire, media_type="application/octet-stream")
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar frame: {exc}"
        ) from exc


@core_router.get("/assets/configs/{config_name}")
async def get_config(config_name: str, request: Request) -> Any:
    """Delivers CMS game configuration files including Feature Flags and Ads."""
    config_key = config_name.lower()
    now_ms = int(datetime.now(TIMEZONE).timestamp() * 1000)

    if config_key.endswith(".bin"):
        canonical = next((name for name in BINARY_CONFIGS if name.lower() == config_key[:-4]), None)
        if canonical is None:
            raise HTTPException(404, "Config not found")
        return file_response(settings.asset_storage_root / "configs", f"{canonical}.bin")

    if "adsconfig" in config_key:
        return {
            "name": "AdsConfig",
            "version": 1,
            "timestamp": now_ms,
            "data": {
                "feature_flag_enabled": settings.feature_flag_google_ads_enabled,
                "app_id": settings.google_ads_app_id,
                "rewarded_unit_id": settings.google_ads_rewarded_unit_id,
                "interstitial_unit_id": settings.google_ads_interstitial_unit_id,
                "instant_reward_on_disabled": True,
            },
        }

    if "gameconfig" in config_key:
        flags = {
            "VideoAdsEnabled": settings.feature_flag_google_ads_enabled,
            "BonusCardAdsInEventsTabEnabled": settings.feature_flag_google_ads_enabled,
            "UseAdBonusCardSkipCooldown": True,
        }
        flags.update(request.app.state.dispatcher.commerce_service.flags.to_game_config_flags())
        return {
            "name": "GameConfig",
            "version": 1,
            "timestamp": now_ms,
            "data": {
                "feature_flags": flags,
                "ads_config": {
                    "app_id": settings.google_ads_app_id,
                    "rewarded_unit_id": settings.google_ads_rewarded_unit_id,
                    "interstitial_unit_id": settings.google_ads_interstitial_unit_id,
                },
            },
        }

    return {
        "name": config_name,
        "version": 1,
        "data": {},
        "timestamp": now_ms,
    }


@core_router.get("/assets/bundles/{bundle_name}")
async def get_bundle(bundle_name: str) -> Response:
    """Delivers real Unity AssetBundles with HTTP Range support."""
    return file_response(settings.asset_storage_root / "bundles", bundle_name)
