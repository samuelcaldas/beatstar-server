"""Application factory: builds a FastAPI app with an injected database and its routers.

Each app owns its DatabaseManager, GatewayDispatcher, administration engine and router
services, so tests and future entry points can build isolated applications without
touching the default data/ directory.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.admin.auth import build_administration_access
from server.admin.database import create_admin_engine, create_admin_session_maker
from server.admin.settings import AdminAuthSettings
from server.admin.ui import build_admin_ui_router
from server.api_routes import core_router
from server.commerce.router import build_commerce_administration_router, build_commerce_router
from server.commerce.service import CommerceService
from server.config import ServerSettings, settings
from server.gameplay.router import build_gameplay_router
from server.gameplay.service import GameplayService
from server.handlers.onboarding_handler import router as onboarding_router
from server.player_auth.policy import PlayerTicketPolicy
from server.player_auth.store import PlayerTicketStore
from server.gateway.dispatcher import GatewayDispatcher
from server.assets.client_adapters import SOURCE_ONLY, ClientAdapterFactory
from server.assets.ingest import AssetLimits, MediaProbe, WaveformGenerator
from server.assets.probes import default_media_probe
from server.assets.waveform import FfmpegWaveform
from server.assets.storage import AssetStorage
from server.music.asset_router import register_asset_error_handlers
from server.music.song_router import register_song_error_handlers
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


def default_admin_ui_directory() -> Path:
    """Returns the export directory produced by the frontend build (frontend/out at the repository root)."""
    return Path(__file__).resolve().parent.parent / "frontend" / "out"


def admin_settings_from_environment(server_settings: ServerSettings) -> AdminAuthSettings | None:
    """Builds administrator settings from configuration, or None when no secret is configured.

    A blank value counts as unset, so a copied .env.example does not stop the game server.
    Returns None so the game server starts without administration routes.
    """
    secret = server_settings.admin_auth_secret
    if secret is None or not secret.get_secret_value():
        return None
    return AdminAuthSettings(
        secret=secret.get_secret_value(),
        session_lifetime_seconds=server_settings.admin_session_lifetime_seconds,
        cookie_secure=server_settings.admin_cookie_secure,
        allowed_origins=tuple(server_settings.cors_origins),
        login_max_attempts=server_settings.admin_login_max_attempts,
        login_window_seconds=server_settings.admin_login_window_seconds,
    )


def create_app(
    database_path: str | None = None,
    admin_settings: AdminAuthSettings | None = None,
    cors_origins: list[str] | None = None,
    asset_limits: AssetLimits | None = None,
    asset_root: Path | None = None,
    media_probe: MediaProbe | None = None,
    waveform: WaveformGenerator | None = None,
    admin_ui_directory: Path | None = None,
    player_ticket_enforcement: bool | None = None,
) -> FastAPI:
    """Builds an application whose routes and lifespan use one injected database.

    Args:
        database_path: SQLite file to use. Defaults to the path from DATABASE_URL.
        admin_settings: Administrator authentication configuration. Defaults to the
            environment; when neither is set, administration routes are not mounted.
        cors_origins: Exact browser origins allowed to call the API with credentials.
            Defaults to CORS_ORIGINS; an empty list grants no browser access.

    Returns:
        A configured FastAPI application with state.database, state.dispatcher and,
        when administration is enabled, state.admin_session_maker set.
    """
    resolved_path = database_path or default_database_path()
    resolved_admin = admin_settings or admin_settings_from_environment(settings)
    admin_engine = create_admin_engine(resolved_path)
    admin_session_maker = create_admin_session_maker(admin_engine)
    database = DatabaseManager(resolved_path)
    commerce_service = CommerceService()
    ticket_store = PlayerTicketStore(admin_session_maker, settings.session_expiration_hours * 3600)
    enforce_tickets = (
        settings.feature_flag_player_ticket_enforcement_enabled
        if player_ticket_enforcement is None
        else player_ticket_enforcement
    )
    ticket_policy = PlayerTicketPolicy(ticket_store, enforce_tickets)
    dispatcher = GatewayDispatcher(database, ticket_store, ticket_policy, commerce_service)
    repository = PlayerRepository(database)

    swept_storage: AssetStorage | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initializes legacy tables, applies migrations, sweeps abandoned uploads, and disposes the admin engine on exit."""
        await database.initialize()
        await asyncio.to_thread(upgrade_to_head, resolved_path)
        if swept_storage is not None:
            await asyncio.to_thread(
                swept_storage.sweep_stale_staging, app.state.asset_limits.staging_max_age_seconds
            )
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
    app.state.player_ticket_store = ticket_store
    register_song_error_handlers(app)
    register_asset_error_handlers(app)
    if resolved_admin is not None:
        app.state.asset_limits = asset_limits or AssetLimits()
        app.state.asset_storage = AssetStorage(asset_root or settings.asset_storage_root / "uploads")
        app.state.media_probe = media_probe or default_media_probe()
        app.state.waveform_generator = waveform or FfmpegWaveform()
        app.state.client_adapter = ClientAdapterFactory.default().create(SOURCE_ONLY)
        swept_storage = app.state.asset_storage
    app.include_router(core_router)
    app.include_router(onboarding_router)
    app.include_router(
        build_commerce_router(commerce_service, repository, ticket_policy),
        prefix="/api/commerce",
        tags=["commerce"],
    )
    app.include_router(
        build_gameplay_router(GameplayService(database), repository, ticket_policy),
        prefix="/api/gameplay",
        tags=["gameplay"],
    )
    if resolved_admin is not None:
        access = build_administration_access(resolved_admin, admin_session_maker)
        app.include_router(access.router)
        app.include_router(
            build_commerce_administration_router(commerce_service, repository, access),
            prefix="/api/commerce",
            tags=["commerce"],
        )
        app.include_router(build_admin_ui_router(admin_ui_directory or default_admin_ui_directory()))
    resolved_cors = settings.cors_origins if cors_origins is None else cors_origins
    if resolved_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_cors,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )
    return app
