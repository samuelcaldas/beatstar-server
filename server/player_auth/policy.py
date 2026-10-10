"""Player ticket policy: every request is classified; rejection happens only when enforcement is enabled.

Outcomes are logged without the ticket value, so a rejected ticket never becomes a log credential.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from server.player_auth.store import PlayerTicketStore

TICKET_HEADER = "authenticationTicket"
ACCEPTED = "accepted"
MISSING = "missing"
UNKNOWN = "unknown"
OTHER_PLAYER = "other_player"
UNAUTHORIZED_STATUS = 401
FORBIDDEN_STATUS = 403
LOGGER = logging.getLogger("server.player_auth")


class PlayerTicketPolicy:
    """Classifies player tickets and, when enforcement is enabled, rejects unauthorized player requests."""

    def __init__(self, store: PlayerTicketStore, enforcement_enabled: bool) -> None:
        """Binds the ticket store and whether unauthorized requests are rejected."""
        self._store = store
        self._enforcement_enabled = enforcement_enabled

    async def observe(self, ticket: str | None, route: str) -> str:
        """Records whether a gateway request carries a valid ticket. Never rejects a request."""
        outcome = ACCEPTED if await self._store.resolve(ticket) is not None else _unauthorized_reason(ticket)
        self._record(outcome, route)
        return outcome

    async def authorize(self, ticket: str | None, cinta: str, route: str) -> None:
        """Checks that the ticket belongs to the cinta the operation acts on.

        Raises:
            HTTPException: 401 for a missing or unknown ticket, 403 for another player's ticket;
                raised only when enforcement is enabled.
        """
        owner = await self._store.resolve(ticket)
        outcome = _owner_outcome(owner, cinta) if owner is not None else _unauthorized_reason(ticket)
        self._record(outcome, route)
        if outcome == ACCEPTED or not self._enforcement_enabled:
            return
        status = FORBIDDEN_STATUS if outcome == OTHER_PLAYER else UNAUTHORIZED_STATUS
        raise HTTPException(status_code=status, detail="Ticket de jogador inválido para esta operação")

    def _record(self, outcome: str, route: str) -> None:
        """Logs non-accepted outcomes with the route and enforcement state, never the ticket."""
        if outcome == ACCEPTED:
            return
        LOGGER.warning(
            "player ticket outcome=%s route=%s enforcement=%s",
            outcome,
            route,
            self._enforcement_enabled,
        )


def _unauthorized_reason(ticket: str | None) -> str:
    """Distinguishes a request without any ticket from one carrying a ticket the server does not know."""
    return MISSING if not ticket else UNKNOWN


def _owner_outcome(owner: str, cinta: str) -> str:
    """Accepts a ticket only for the player it was issued to."""
    return ACCEPTED if owner == cinta else OTHER_PLAYER
