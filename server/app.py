"""FastAPI Application for Beatstar Private Server."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
import zoneinfo
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from server.config import settings
from server.gateway.dispatcher import GatewayDispatcher
from server.gateway.header_parser import HeaderParser
from server.models.headers import ClientHeader
from server.storage.database import DatabaseManager

# Configuração de timezone America/Sao_Paulo
os.environ["TZ"] = settings.timezone
from server.commerce.router import commerce_router
from server.gameplay.router import gameplay_router

TIMEZONE = zoneinfo.ZoneInfo(settings.timezone)

db_manager = DatabaseManager(settings.database_url.replace("sqlite+aiosqlite:///", ""))
dispatcher = GatewayDispatcher(db_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema at startup."""
    await db_manager.initialize()
    yield


app = FastAPI(
    title="Beatstar Private Server",
    description="Emulador de servidor para Beatstar (Space Ape Games - Flamingo)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(commerce_router, prefix="/api/commerce", tags=["commerce"])
app.include_router(gameplay_router, prefix="/api/gameplay", tags=["gameplay"])

app.add_middleware(

    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health")
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


@app.post("/gateway")
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
    server_header, res_body = await dispatcher.dispatch_payload(
        client_header, body_data
    )

    return {
        "header": server_header.model_dump(by_alias=True),
        "body": res_body,
    }


@app.post("/socket-gateway")
async def socket_gateway(request: Request) -> Response:
    """Raw binary wire frame endpoint matching SocketGateway wire format."""
    raw_body = await request.body()
    if len(raw_body) < 8:
        raise HTTPException(status_code=400, detail="Frame binário inválido.")

    try:
        res_wire = await dispatcher.dispatch_wire_frame(raw_body)
        return Response(content=res_wire, media_type="application/octet-stream")
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar frame: {exc}"
        ) from exc


@app.get("/assets/configs/{config_name}")
async def get_config(config_name: str) -> Any:
    """Delivers CMS game configuration files including Feature Flags and Ads."""
    config_key = config_name.lower()
    now_ms = int(datetime.now(TIMEZONE).timestamp() * 1000)

    # Check for binary config payload
    if config_name.endswith(".bin"):
        base_name = config_name[:-4]
        for candidate_name in (config_name, f"{base_name.capitalize()}.bin", f"{base_name}.bin"):
            p = Path("data/configs") / candidate_name
            if p.exists() and p.is_file():
                return Response(content=p.read_bytes(), media_type="application/octet-stream")

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
        flags.update(dispatcher.commerce_service.flags.to_game_config_flags())
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


@app.get("/assets/bundles/{bundle_name}")
async def get_bundle(bundle_name: str, request: Request) -> Response:
    """Delivers real Unity AssetBundles with HTTP Range support."""
    # Prevent directory traversal
    safe_name = os.path.basename(bundle_name)
    bundle_path = Path("data/bundles") / safe_name

    if not bundle_path.exists() or not bundle_path.is_file():
        raise HTTPException(status_code=404, detail=f"AssetBundle '{safe_name}' não encontrado.")

    total_size = bundle_path.stat().st_size
    range_header = request.headers.get("Range")

    if range_header and range_header.startswith("bytes="):
        # Range: bytes=start-end
        parts = range_header[6:].split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else total_size - 1
        end = min(end, total_size - 1)
        length = end - start + 1

        with open(bundle_path, "rb") as f:
            f.seek(start)
            data = f.read(length)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{total_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        return Response(
            content=data,
            status_code=206,
            headers=headers,
            media_type="application/octet-stream",
        )

    data = bundle_path.read_bytes()
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(total_size),
    }
    return Response(
        content=data,
        status_code=200,
        headers=headers,
        media_type="application/octet-stream",
    )
