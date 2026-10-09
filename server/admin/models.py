"""ORM models for administrator accounts and database-backed sessions.

The fastapi-users SQLAlchemy access-token adapter hard-codes its foreign key to
``user.id``, so the administrator table keeps the adapter's ``user`` name.
"""

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by administration and music domain tables."""


class AdministratorUser(SQLAlchemyBaseUserTableUUID, Base):
    """Trusted server administrator; public registration is not offered."""

    __tablename__ = "user"


class AdministratorSession(SQLAlchemyBaseAccessTokenTableUUID, Base):
    """Revocable cookie session token bound to an administrator."""

    __tablename__ = "accesstoken"
