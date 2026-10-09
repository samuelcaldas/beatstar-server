"""Create music catalog, asset, chart revision, build job, release and audit tables.

Revision ID: 0002_music_catalog
Revises: 0001_admin_auth

Creation order follows the foreign-key graph: songs first, then the tables that reference
songs, then releases (which reference chart revisions and build jobs), then audit events
(which reference the administrator table created by 0001).
"""

import sqlalchemy as sa
from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID

revision = "0002_music_catalog"
down_revision = "0001_admin_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the music-domain tables in dependency order."""
    op.create_table(
        "songs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("artist", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_songs_status"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("song_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('audio', 'artwork')", name="ck_assets_kind"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_assets_storage_key"),
    )
    op.create_index(op.f("ix_assets_song_id"), "assets", ["song_id"], unique=False)

    op.create_table(
        "chart_revisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("song_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("document", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("song_id", "revision_number", name="uq_chart_revisions_song_number"),
    )
    op.create_index(op.f("ix_chart_revisions_song_id"), "chart_revisions", ["song_id"], unique=False)

    op.create_table(
        "build_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("song_id", sa.String(length=36), nullable=False),
        sa.Column("chart_revision_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("lease_expires_at", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_build_jobs_status"
        ),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chart_revision_id"], ["chart_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_build_jobs_idempotency_key"),
    )
    op.create_index(op.f("ix_build_jobs_song_id"), "build_jobs", ["song_id"], unique=False)

    op.create_table(
        "releases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("song_id", sa.String(length=36), nullable=False),
        sa.Column("chart_revision_id", sa.String(length=36), nullable=False),
        sa.Column("build_job_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("client_target", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('published', 'unpublished')", name="ck_releases_status"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chart_revision_id"], ["chart_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["build_job_id"], ["build_jobs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("song_id", "version", name="uq_releases_song_version"),
    )
    op.create_index(op.f("ix_releases_song_id"), "releases", ["song_id"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", GUID(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_target_id"), "audit_events", ["target_id"], unique=False)


def downgrade() -> None:
    """Drops music tables in reverse dependency order: children before their parents."""
    op.drop_index(op.f("ix_audit_events_target_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_releases_song_id"), table_name="releases")
    op.drop_table("releases")
    op.drop_index(op.f("ix_build_jobs_song_id"), table_name="build_jobs")
    op.drop_table("build_jobs")
    op.drop_index(op.f("ix_chart_revisions_song_id"), table_name="chart_revisions")
    op.drop_table("chart_revisions")
    op.drop_index(op.f("ix_assets_song_id"), table_name="assets")
    op.drop_table("assets")
    op.drop_table("songs")
