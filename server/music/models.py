"""ORM models for the administration music domain.

Foreign keys use RESTRICT so that releases and chart revisions can never be orphaned by a
delete; hard deletion is a domain decision made on unreferenced rows only. Timestamps are
integer milliseconds, matching the legacy tables. Audit actors use SET NULL so that removing
an administrator keeps the history of what happened.
"""

import time
import uuid

# fastapi_users.db must initialise before the SQLAlchemy extension it re-exports; imported in the
# other order, its optional exports are silently skipped and admin models fail to load.
import fastapi_users.db  # noqa: F401
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from server.storage.base import Base

RESTRICT = "RESTRICT"
SET_NULL = "SET NULL"


def new_identifier() -> str:
    """Returns a random identifier used for every music-domain primary key."""
    return str(uuid.uuid4())


def now_milliseconds() -> int:
    """Returns the current UTC time as integer milliseconds."""
    return int(time.time() * 1000)


class Song(Base):
    """Administrator-managed song; drafts are never visible to game discovery."""

    __tablename__ = "songs"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_songs_status"),
        Index("uq_songs_game_song_id", "game_song_id", unique=True),
        Index("uq_songs_beatmap_id", "beatmap_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_identifier)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    artist: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(16), nullable=False, default="normal", server_default="normal"
    )
    game_song_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    beatmap_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_signature: Mapped[int | None] = mapped_column(Integer, nullable=True)
    variant_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual", server_default="manual")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)


class Asset(Base):
    """Immutable uploaded file; the storage key is generated, never the user filename."""

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("kind IN ('audio', 'artwork')", name="ck_assets_kind"),
        UniqueConstraint("song_id", "storage_key", name="uq_assets_song_storage_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_identifier)
    song_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("songs.id", ondelete=RESTRICT), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_milliseconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)


class ChartRevision(Base):
    """Immutable, schema-versioned chart document; edits create new revision numbers."""

    __tablename__ = "chart_revisions"
    __table_args__ = (
        UniqueConstraint("song_id", "revision_number", name="uq_chart_revisions_song_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_identifier)
    song_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("songs.id", ondelete=RESTRICT), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)


class BuildJob(Base):
    """Durable build request; the idempotency key makes repeated submissions a no-op."""

    __tablename__ = "build_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_build_jobs_status"
        ),
        UniqueConstraint("idempotency_key", name="uq_build_jobs_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_identifier)
    song_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("songs.id", ondelete=RESTRICT), nullable=False, index=True
    )
    chart_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chart_revisions.id", ondelete=RESTRICT), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    lease_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)


class Release(Base):
    """Snapshot of one successful build; published releases are never deleted."""

    __tablename__ = "releases"
    __table_args__ = (
        CheckConstraint("status IN ('published', 'unpublished')", name="ck_releases_status"),
        UniqueConstraint("song_id", "version", name="uq_releases_song_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_identifier)
    song_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("songs.id", ondelete=RESTRICT), nullable=False, index=True
    )
    chart_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chart_revisions.id", ondelete=RESTRICT), nullable=False
    )
    build_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("build_jobs.id", ondelete=RESTRICT), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    client_target: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="published")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)


class AuditEvent(Base):
    """Append-only record of administrator actions."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_identifier)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("user.id", ondelete=SET_NULL), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=now_milliseconds)
