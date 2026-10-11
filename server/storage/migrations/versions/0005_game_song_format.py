"""Add the game's song identity (song id, beatmap id, tempo, variant) and the origin of each song.

Revision ID: 0005_game_song_format
Revises: 0004_asset_media_metadata

Columns are nullable so that songs created by hand before this revision keep working. Uniqueness
is enforced by partial-free unique indexes: SQLite allows many NULLs, so only assigned game ids
collide. source defaults to "manual" for existing rows.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_game_song_format"
down_revision = "0004_asset_media_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adds game identity columns and unique indexes for the assigned identifiers."""
    op.add_column("songs", sa.Column("game_song_id", sa.Integer(), nullable=True))
    op.add_column("songs", sa.Column("beatmap_id", sa.Integer(), nullable=True))
    op.add_column("songs", sa.Column("bpm", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("time_signature", sa.Integer(), nullable=True))
    op.add_column("songs", sa.Column("variant_label", sa.String(length=64), nullable=True))
    op.add_column(
        "songs",
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
    )
    op.create_index("uq_songs_game_song_id", "songs", ["game_song_id"], unique=True)
    op.create_index("uq_songs_beatmap_id", "songs", ["beatmap_id"], unique=True)


def downgrade() -> None:
    """Removes the game identity columns and their indexes."""
    op.drop_index("uq_songs_beatmap_id", table_name="songs")
    op.drop_index("uq_songs_game_song_id", table_name="songs")
    for column in ("source", "variant_label", "time_signature", "bpm", "beatmap_id", "game_song_id"):
        op.drop_column("songs", column)
