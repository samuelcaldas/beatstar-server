"""Create the server-side player ticket table.

Revision ID: 0005_player_tickets
Revises: 0004_asset_media_metadata

Tickets are stored as SHA-256 digests with an expiry in milliseconds, so a database read
does not reveal usable tickets and expired rows can be rejected without a clock skew.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_player_tickets"
down_revision = "0004_asset_media_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the player_tickets table and its cinta index."""
    op.create_table(
        "player_tickets",
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("cinta", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("digest"),
    )
    op.create_index("ix_player_tickets_cinta", "player_tickets", ["cinta"])


def downgrade() -> None:
    """Drops the player_tickets table and its index."""
    op.drop_index("ix_player_tickets_cinta", table_name="player_tickets")
    op.drop_table("player_tickets")
