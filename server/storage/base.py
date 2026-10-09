"""Declarative base shared by administration and music domain tables."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata registry so Alembic compares every new table at once."""
