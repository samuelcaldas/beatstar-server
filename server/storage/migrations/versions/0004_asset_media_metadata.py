"""Add verified media metadata to assets and scope content uniqueness to each song.

Revision ID: 0004_asset_media_metadata
Revises: 0003_song_difficulty

assets is not referenced by any foreign key, so rebuilding it in batch mode is safe. The
unique rule moves from storage_key alone to (song_id, storage_key): the same bytes may be
attached to several songs, but only once per song. Downgrade fails loudly if rows already
share a storage_key across songs, rather than silently dropping one of them.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_asset_media_metadata"
down_revision = "0003_song_difficulty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adds nullable duration and dimensions, and replaces the global storage key uniqueness."""
    with op.batch_alter_table("assets") as batch:
        batch.add_column(sa.Column("duration_milliseconds", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("width", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("height", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_assets_storage_key", type_="unique")
        batch.create_unique_constraint("uq_assets_song_storage_key", ["song_id", "storage_key"])


def downgrade() -> None:
    """Restores global storage key uniqueness and removes the media metadata columns."""
    with op.batch_alter_table("assets") as batch:
        batch.drop_constraint("uq_assets_song_storage_key", type_="unique")
        batch.create_unique_constraint("uq_assets_storage_key", ["storage_key"])
        batch.drop_column("height")
        batch.drop_column("width")
        batch.drop_column("duration_milliseconds")
