"""Add song difficulty with a default so existing rows are preserved.

Revision ID: 0003_song_difficulty
Revises: 0002_music_catalog

The column is added in place: songs is referenced by foreign keys, so the table is not
recreated. Allowed values are enforced by the request schema, not by a database CHECK,
because SQLite cannot add a named CHECK constraint to an existing table without a rebuild.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_song_difficulty"
down_revision = "0002_music_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adds the difficulty column, defaulting existing songs to normal."""
    op.add_column(
        "songs",
        sa.Column("difficulty", sa.String(length=16), nullable=False, server_default="normal"),
    )


def downgrade() -> None:
    """Removes the difficulty column."""
    op.drop_column("songs", "difficulty")
