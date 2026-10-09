"""Administrator authentication: database-backed cookie sessions, CSRF, Origin and login throttling.

Public registration is not mounted. Administrators are created only by the provisioning CLI.
"""

import secrets
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from server.admin.models import AdministratorSession, AdministratorUser
from server.admin.settings import AdminAuthSettings
from server.admin.throttle import LoginAttemptLimiter
from server.music.asset_router import build_asset_router
from server.music.song_router import build_song_library_router

SESSION_COOKIE = "beatstar_admin"
CSRF_COOKIE = "beatstar_admin_csrf"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AdministratorManager(UUIDIDMixin, BaseUserManager[AdministratorUser, uuid.UUID]):
    """Owns administrator password hashing and token secrets for one application."""

    def __init__(self, user_database: SQLAlchemyUserDatabase, secret: str) -> None:
        """Binds the user database and the secret used for reset and verification tokens."""
        super().__init__(user_database)
        self.reset_password_token_secret = secret
        self.verification_token_secret = secret


def client_address(request: Request) -> str:
    """Returns the direct peer address; behind a proxy this is the proxy's address."""
    return request.client.host if request.client else "unknown"


def enforce_origin(request: Request, settings: AdminAuthSettings) -> None:
    """Rejects unsafe requests whose Origin is present but not explicitly allowed.

    Raises:
        HTTPException: status 403 for a foreign Origin.
    """
    origin = request.headers.get("origin")
    if request.method not in UNSAFE_METHODS or origin is None:
        return
    if origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origem não permitida")


def require_csrf(request: Request) -> None:
    """Checks the double-submit token: the header must equal the CSRF cookie.

    Raises:
        HTTPException: status 403 when either value is missing or they differ.
    """
    cookie_value = request.cookies.get(CSRF_COOKIE)
    header_value = request.headers.get(CSRF_HEADER)
    if not cookie_value or not header_value or not secrets.compare_digest(cookie_value, header_value):
        raise HTTPException(status_code=403, detail="Token CSRF inválido")


def build_admin_router(
    settings: AdminAuthSettings, session_maker: async_sessionmaker[AsyncSession]
) -> APIRouter:
    """Builds the administrator authentication router bound to one settings object and database.

    Args:
        settings: Validated administrator authentication configuration.
        session_maker: Factory for sessions on the administration database.

    Returns:
        A router mounting login, logout and the current-administrator endpoint under /api/admin.
    """
    limiter = LoginAttemptLimiter(settings.login_max_attempts, settings.login_window_seconds)

    async def get_session() -> AsyncIterator[AsyncSession]:
        """Yields one session per request; shared by user and session lookups in that request."""
        async with session_maker() as session:
            yield session

    async def get_user_manager(
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> AsyncIterator[AdministratorManager]:
        """Yields a manager bound to the request's session."""
        yield AdministratorManager(SQLAlchemyUserDatabase(session, AdministratorUser), settings.secret)

    def get_strategy(
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> DatabaseStrategy:
        """Returns the revocable database-backed session strategy."""
        return DatabaseStrategy(
            SQLAlchemyAccessTokenDatabase(session, AdministratorSession),
            lifetime_seconds=settings.session_lifetime_seconds,
        )

    transport = CookieTransport(
        cookie_name=SESSION_COOKIE,
        cookie_max_age=settings.session_lifetime_seconds,
        cookie_secure=settings.cookie_secure,
        cookie_httponly=True,
        cookie_samesite="strict",
    )
    backend = AuthenticationBackend(name="admin-cookie", transport=transport, get_strategy=get_strategy)
    users = FastAPIUsers[AdministratorUser, uuid.UUID](get_user_manager, [backend])

    def check_origin(request: Request) -> None:
        """Router-wide Origin guard; annotated so FastAPI injects the Request, not a query value."""
        enforce_origin(request, settings)

    router = APIRouter(
        prefix="/api/admin",
        tags=["admin"],
        dependencies=[Depends(check_origin)],
    )

    @router.post("/auth/login", status_code=204)
    async def login(
        request: Request,
        credentials: Annotated[OAuth2PasswordRequestForm, Depends()],
        user_manager: Annotated[AdministratorManager, Depends(get_user_manager)],
        strategy: Annotated[DatabaseStrategy, Depends(get_strategy)],
    ) -> Response:
        """Authenticates an administrator and sets the session and CSRF cookies.

        Raises:
            HTTPException: 429 when throttled, 401 for invalid credentials.
        """
        client = client_address(request)
        limiter.ensure_allowed(client)
        user = await user_manager.authenticate(credentials)
        if user is None or not user.is_superuser:
            limiter.record_failure(client)
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        limiter.reset(client)
        response = await backend.login(strategy, user)
        response.set_cookie(
            CSRF_COOKIE,
            secrets.token_urlsafe(32),
            max_age=settings.session_lifetime_seconds,
            path="/",
            secure=settings.cookie_secure,
            httponly=False,
            samesite="strict",
        )
        return response

    @router.post("/auth/logout", status_code=204, dependencies=[Depends(require_csrf)])
    async def logout(
        user_and_token: Annotated[tuple, Depends(users.authenticator.current_user_token(superuser=True))],
        strategy: Annotated[DatabaseStrategy, Depends(get_strategy)],
    ) -> Response:
        """Revokes the server-side session token and clears both cookies."""
        user, token = user_and_token
        response = await backend.logout(strategy, user, token)
        response.delete_cookie(CSRF_COOKIE, path="/")
        return response

    @router.get("/me")
    async def read_current_administrator(
        user: Annotated[AdministratorUser, Depends(users.current_user(active=True, superuser=True))],
    ) -> dict[str, str]:
        """Returns the authenticated administrator's identity without credential material."""
        return {"id": str(user.id), "email": user.email}

    router.include_router(
        build_song_library_router(
            get_session,
            users.current_user(active=True, superuser=True),
            require_csrf,
        )
    )
    router.include_router(
        build_asset_router(
            get_session,
            users.current_user(active=True, superuser=True),
            require_csrf,
        )
    )
    return router
