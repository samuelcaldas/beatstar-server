"""Application factory: builds a FastAPI app with an injected database and its routers.

Each app owns its DatabaseManager, GatewayDispatcher, administration engine and router
services, so tests and future entry points can build isolated applications without
touching the default data/ directory.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.admin.auth import build_admin_router
from server.admin.database import create_admin_engine, create_admin_session_maker
from server.admin.settings import AdminAuthSettings
from server.api_routes import core_router
from server.commerce.router import build_commerce_router
from server.commerce.service import CommerceService
from server.config import ServerSettings, settings
from server.gameplay.router import build_gameplay_router
from server.gameplay.service import GameplayService
from server.gateway.dispatcher import GatewayDispatcher
from server.storage.database import DatabaseManager
from server.storage.migrations.runner import upgrade_to_head
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


def admin_settings_from_environment(server_settings: ServerSettings) -> AdminAuthSettings | None:
    """Builds administrator settings from configuration, or None when no secret is configured.

    Returns None so the game server starts without administration routes.
    """
    if server_settings.admin_auth_secret is None:
        return None
    return AdminAuthSettings(
        secret=server_settings.admin_auth_secret.get_secret_value(),
        session_lifetime_seconds=server_settings.admin_session_lifetime_seconds,
        cookie_secure=server_settings.admin_cookie_secure,
        allowed_origins=tuple(server_settings.cors_origins),
        login_max_attempts=server_settings.admin_login_max_attempts,
        login_window_seconds=server_settings.admin_login_window_seconds,
    )


def create_app(
    database_path: str | None = None,
    admin_settings: AdminAuthSettings | None = None,
) -> FastAPI:
    """Builds an application whose routes and lifespan use one injected database.

    Args:
        database_path: SQLite file to use. Defaults to the path from DATABASE_URL.
        admin_settings: Administrator authentication configuration. Defaults to the
            environment; when neither is set, administration routes are not mounted.

    Returns:
        A configured FastAPI application with state.database, state.dispatcher and,
        when administration is enabled, state.admin_session_maker set.
    """
    resolved_path = database_path or default_database_path()
    resolved_admin = admin_settings or admin_settings_from_environment(settings)
    database = DatabaseManager(resolved_path)
    dispatcher = GatewayDispatcher(database)
    repository = PlayerRepository(database)
    admin_engine = create_admin_engine(resolved_path)
    admin_session_maker = create_admin_session_maker(admin_engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initializes legacy tables, applies migrations, and disposes the admin engine on exit."""
        await database.initialize()
        await asyncio.to_thread(upgrade_to_head, resolved_path)
        yield
        await admin_engine.dispose()

    app = FastAPI(
        title="Beatstar Private Server",
        description="Emulador de servidor para Beatstar (Space Ape Games - Flamingo)",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.dispatcher = dispatcher
    app.state.admin_session_maker = admin_session_maker
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
    if resolved_admin is not None:
        app.include_router(build_admin_router(resolved_admin, admin_session_maker))
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )
    return app
