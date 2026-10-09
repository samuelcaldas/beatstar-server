"""Idempotent administrator provisioning; the only way to create administrator accounts.

Usage (secrets are read from the environment, never from arguments):
    ADMIN_AUTH_SECRET=... ADMIN_PASSWORD=... python -I -m server.admin.provision \
        --database-path data/beatstar.db --email admin@example.test
Omit ADMIN_PASSWORD to be prompted without echo.
"""

import argparse
import asyncio
import getpass
import os
import sys
from collections.abc import Mapping, Sequence

from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.schemas import BaseUserCreate
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from server.admin.auth import AdministratorManager
from server.admin.database import create_admin_engine, create_admin_session_maker
from server.admin.models import AdministratorUser
from server.admin.settings import MINIMUM_SECRET_LENGTH
from server.storage.migrations.runner import upgrade_to_head

CREATED = "created"
EXISTS = "exists"


async def provision_administrator(
    session_maker: async_sessionmaker[AsyncSession],
    secret: str,
    email: str,
    password: str,
) -> str:
    """Creates the administrator if absent; leaves an existing account unchanged.

    Args:
        session_maker: Factory for sessions on the administration database.
        secret: Token secret bound to the manager; must match the running application.
        email: Administrator login name.
        password: Plaintext password, hashed by the manager and never stored.

    Returns:
        "created" when a new account was written, "exists" otherwise.
    """
    async with session_maker() as session:
        user_database = SQLAlchemyUserDatabase(session, AdministratorUser)
        if await user_database.get_by_email(email) is not None:
            return EXISTS
        manager = AdministratorManager(user_database, secret)
        await manager.create(
            BaseUserCreate(email=email, password=password, is_superuser=True, is_verified=True)
        )
    return CREATED


def _parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    """Parses CLI arguments; both database path and email are required."""
    parser = argparse.ArgumentParser(description="Provision a Beatstar administrator.")
    parser.add_argument("--database-path", required=True)
    parser.add_argument("--email", required=True)
    return parser.parse_args(argv)


def _read_password(environment: Mapping[str, str]) -> str:
    """Returns ADMIN_PASSWORD from the environment or prompts without echo."""
    password = environment.get("ADMIN_PASSWORD")
    if password:
        return password
    return getpass.getpass("Senha do administrador: ")


def main(argv: Sequence[str], environment: Mapping[str, str]) -> int:
    """Runs migrations and provisions one administrator.

    Args:
        argv: Command-line arguments without the program name.
        environment: Environment mapping; must contain ADMIN_AUTH_SECRET.

    Returns:
        0 on success, 2 when the secret is missing or too short.
    """
    arguments = _parse_arguments(argv)
    secret = environment.get("ADMIN_AUTH_SECRET", "")
    if len(secret) < MINIMUM_SECRET_LENGTH:
        print(
            f"ADMIN_AUTH_SECRET must be set to at least {MINIMUM_SECRET_LENGTH} characters.",
            file=sys.stderr,
        )
        return 2
    password = _read_password(environment)
    upgrade_to_head(arguments.database_path)
    outcome = asyncio.run(_provision(arguments.database_path, secret, arguments.email, password))
    print(f"Administrator {arguments.email}: {outcome}")
    return 0


async def _provision(database_path: str, secret: str, email: str, password: str) -> str:
    """Opens the engine, provisions, and always disposes the engine."""
    engine = create_admin_engine(database_path)
    try:
        return await provision_administrator(create_admin_session_maker(engine), secret, email, password)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], dict(os.environ)))
