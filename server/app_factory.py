"""Application factory: builds a FastAPI app with an injected database and its routers.

Each app owns its DatabaseManager, GatewayDispatcher and router services, so tests and
future admin/worker entry points can build isolated applications without touching
the default data/ directory.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.api_routes import core_router
from server.commerce.router import build_commerce_router
from server.commerce.service import CommerceService
from server.config import settings
from server.gameplay.router import build_gameplay_router
from server.gameplay.service import GameplayService
from server.gateway.dispatcher import GatewayDispatcher
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository

# Configuração de timezone America/Sao_Paulo
os.environ["TZ"] = settings.timezone


def default_database_path() -> str:
    """Returns the SQLite file path configured by DATABASE_URL.

    Raises:
        ValueError: when DATABASE_URL is not a sqlite+aiosqlite URL.
    """
    prefix = "sqlite+aiosqlite:///"
    if not settings.database_url.startswith(prefix):
        raise ValueError("DATABASE_URL must use the sqlite+aiosqlite:/// scheme")
    return settings.database_url[len(prefix):]


def create_app(database_path: str | None = None) -> FastAPI:
    """Builds an application whose routes and lifespan use one injected database.

    Args:
        database_path: SQLite file to use. Defaults to the path from DATABASE_URL.

    Returns:
        A configured FastAPI application with state.database and state.dispatcher set.
    """
    database = DatabaseManager(database_path or default_database_path())
    dispatcher = GatewayDispatcher(database)
    repository = PlayerRepository(database)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initializes the injected database schema at startup."""
        await database.initialize()
        yield

    app = FastAPI(
        title="Beatstar Private Server",
        description="Emulador de servidor para Beatstar (Space Ape Games - Flamingo)",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.dispatcher = dispatcher
    app.include_router(core_router)
    app.include_router(
        build_commerce_router(CommerceService(), repository),
        prefix="/api/commerce",
        tags=["commerce"],
    )
    app.include_router(
        build_gameplay_router(GameplayService(database), repository),
        prefix="/api/gameplay",
        tags=["gameplay"],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app
