"""Table of player tickets: each row holds a digest of the ticket, never the ticket itself."""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from server.storage.base import Base


class PlayerTicket(Base):
    """One issued login ticket, bound to a player and valid until expires_at (milliseconds)."""

    __tablename__ = "player_tickets"

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    cinta: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger)
