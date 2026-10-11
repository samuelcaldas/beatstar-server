#!/usr/bin/env python3
"""Imports extracted client charts, reference artwork and example constructions into the song library.

Safe to rerun: charts are matched by beatmap id, examples by beatmap id, and artwork is attached only
when the song has none. Migrations are applied first, as the server does at startup.

Usage (from the repository root):
    .venv/bin/python scripts/import_unity_catalog.py --database-path data/beatstar.db \
        --extracted-dir data/extracted --asset-root data
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from server.admin.database import create_admin_engine, create_admin_session_maker  # noqa: E402
from server.assets.client_adapters import SOURCE_ONLY, ClientAdapterFactory  # noqa: E402
from server.assets.formats import default_registry  # noqa: E402
from server.assets.ingest import AssetIngestor, AssetLimits  # noqa: E402
from server.assets.probes import default_media_probe  # noqa: E402
from server.assets.storage import AssetStorage  # noqa: E402
from server.music.asset_service import AssetService  # noqa: E402
from server.music.chart_document import encode_notes  # noqa: E402
from server.music.example_songs import ExampleSong, artwork_png, build_examples  # noqa: E402
from server.music.models import Asset, Song  # noqa: E402
from server.music.song_service import SongLibraryService  # noqa: E402
from server.music.unity_catalog import UnityCatalogImporter, single_chunk  # noqa: E402
from server.storage.migrations.runner import upgrade_to_head  # noqa: E402

def parse_arguments() -> argparse.Namespace:
    """Reads the paths; every input is required so that nothing is assumed silently."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-path", type=Path, required=True)
    parser.add_argument("--extracted-dir", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    return parser.parse_args()


class ArtworkAttacher:
    """Uploads artwork through the real asset pipeline; each song receives at most one artwork."""

    def __init__(self, session: AsyncSession, asset_root: Path) -> None:
        """Builds the ingestion collaborators the server uses at runtime."""
        limits = AssetLimits()
        storage = AssetStorage(asset_root / "uploads")
        ingestor = AssetIngestor(storage, default_registry(), ClientAdapterFactory.default().create(SOURCE_ONLY), limits)
        self._session = session
        self._service = AssetService(session, ingestor, default_media_probe(), None, limits)

    async def attach_if_missing(self, song: Song, png: bytes) -> bool:
        """Uploads the PNG unless the song already has artwork; returns True when it was attached."""
        existing = await self._session.scalar(
            select(Asset.id).where(Asset.song_id == song.id, Asset.kind == "artwork").limit(1)
        )
        if existing is not None:
            return False
        await self._service.upload(song.id, "artwork", single_chunk(png), actor_id=None)
        return True


async def import_examples(session: AsyncSession, attacher: ArtworkAttacher) -> list[str]:
    """Creates each example song whose beatmap is absent, and gives it its artwork."""
    library = SongLibraryService(session)
    created: list[str] = []
    for example in build_examples():
        song = await _song_for_beatmap(session, example.beatmap_id)
        if song is None:
            song = await _create_example(library, example)
            created.append(song.id)
        await attacher.attach_if_missing(song, artwork_png(example))
    return created


async def _create_example(library: SongLibraryService, example: ExampleSong) -> Song:
    """Creates one example song from its encoded chart."""
    label = f"{example.metadata.variant_label}-1"
    raw = encode_notes(example.beatmap_id, label, list(example.notes))
    return await library.import_song(example.metadata, "example", raw, actor_id=None)


async def _song_for_beatmap(session: AsyncSession, beatmap_id: int) -> Song | None:
    """Returns the song bound to the beatmap, if any."""
    return await session.scalar(select(Song).where(Song.beatmap_id == beatmap_id))


async def run(arguments: argparse.Namespace) -> dict[str, object]:
    """Applies migrations, imports unlinked charts and creates synthetic examples."""
    database_path = str(arguments.database_path)
    await asyncio.to_thread(upgrade_to_head, database_path)
    engine = create_admin_engine(database_path)
    session_maker = create_admin_session_maker(engine)
    try:
        async with session_maker() as session:
            charts = await UnityCatalogImporter(session).import_charts(arguments.extracted_dir)
        async with session_maker() as session:
            attacher = ArtworkAttacher(session, arguments.asset_root)
            examples = await import_examples(session, attacher)
    finally:
        await engine.dispose()
    return {
        "imported_songs": len(charts.imported_song_ids),
        "skipped_existing_beatmaps": len(charts.skipped_beatmap_ids),
        "examples_created": len(examples),
    }


def main() -> None:
    """Runs the import and prints the counts."""
    arguments = parse_arguments()
    print(asyncio.run(run(arguments)))


if __name__ == "__main__":
    main()
