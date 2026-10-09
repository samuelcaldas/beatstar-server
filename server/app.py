"""FastAPI Application for Beatstar Private Server."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
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
async def get_config(config_name: str) -> dict[str, Any]:
    """Delivers CMS game configuration files."""
    return {
        "name": config_name,
        "version": 1,
        "data": {},
        "timestamp": int(datetime.now(TIMEZONE).timestamp() * 1000),
    }


@app.get("/assets/bundles/{bundle_name}")
async def get_bundle(bundle_name: str) -> Response:
    """Mock endpoint serving AssetBundles."""
    dummy_bundle = b"UnityFS\x00\x00\x00\x00\x085.x.x\x002022.3.50f1\x00"
    return Response(content=dummy_bundle, media_type="application/octet-stream")
