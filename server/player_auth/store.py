"""Server-side player ticket store: opaque tickets, digests at rest, and expiry."""

from __future__ import annotations

import hashlib
import secrets
import time
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from server.player_auth.models import PlayerTicket

TICKET_PREFIX = "auth-"
MILLISECONDS_PER_SECOND = 1000


class PlayerTicketStore:
    """Issues opaque login tickets and resolves them back to a player while they are unexpired."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        lifetime_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Binds the database, the ticket lifetime and the clock used for expiry.

        Raises:
            ValueError: when the lifetime is not positive.
        """
        if lifetime_seconds <= 0:
            raise ValueError("ticket lifetime must be positive")
        self._session_maker = session_maker
        self._lifetime_seconds = lifetime_seconds
        self._clock = clock

    async def issue(self, cinta: str) -> str:
        """Creates a ticket for a player and returns the only copy of its raw value.

        Raises:
            ValueError: when cinta is empty.
        """
        if not cinta:
            raise ValueError("a ticket must be issued for a non-empty cinta")
        raw_ticket = TICKET_PREFIX + secrets.token_urlsafe(32)
        expires_at = self._milliseconds(self._clock() + self._lifetime_seconds)
        async with self._session_maker() as session, session.begin():
            session.add(PlayerTicket(digest=_digest(raw_ticket), cinta=cinta, expires_at=expires_at))
        return raw_ticket

    async def resolve(self, ticket: str | None) -> str | None:
        """Returns the cinta the ticket was issued for, or None when unknown or expired."""
        if not ticket:
            return None
        async with self._session_maker() as session:
            row = await session.get(PlayerTicket, _digest(ticket))
        if row is None or row.expires_at <= self._milliseconds(self._clock()):
            return None
        return row.cinta

    def _milliseconds(self, seconds: float) -> int:
        """Converts a clock reading to the integer millisecond timestamps the legacy tables use."""
        return int(seconds * MILLISECONDS_PER_SECOND)


def _digest(raw_ticket: str) -> str:
    """Returns the SHA-256 hex digest that is stored in place of the ticket."""
    return hashlib.sha256(raw_ticket.encode("utf-8")).hexdigest()
