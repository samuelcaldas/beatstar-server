"""Reference song identifiers and asset paths recovered from client 36.1.4.9545 artifacts.

The values are constants copied from the APK inventory. They are not proof of
native playback: linkage between song, beatmap, bundles and audio is hardcoded here
and has not been derived from SongConfig.bin or AssetsConfig.bin.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceSongPackage:
    """Identifiers and internal asset paths for the candidate reference song."""

    title: str = "Sweet Home Alabama (Tutorial)"
    artist: str = "Lynyrd Skynyrd"
    song_id: int = 710
    beatmap_id: int = 660
    # Label stored inside the decoded chart (what the Raksha decoder returns).
    chart_id_label: str = "710-1"
    # Variant label used as the template name in the candidate asset metadata.
    variant_label: str = "LynyrdSk-00687_SweetHomeA-TUT-Tutorial"
    difficulty: str = "Tutorial"
    bpm: float = 98.0
    time_signature: int = 4

    # Asset bundle filenames from assets/AssetBundles/
    beatmap_bundle_filename: str = "39cf5b304affe47c7ad8e5fe2add65ac_7739e0a86bf03b786f6448c524919b6f1994021439.bundle"
    audio_bundle_filename: str = "ed13530a47a434ee482b52406ad57a86_fc96c0d74c64fee844121cf004c3b1373814866549.bundle"
    cover_bundle_filename: str = "0db2525d863d34c7ead654cc0a24002f_c4015cee4caa69eedc70c36e574b09482119362438.bundle"

    # Internal asset paths inside bundles
    beatmap_asset_path: str = "Assets/beatmapInteractions/660.bytes"
    audio_asset_path: str = "Assets/Audio/Banks/tst00687.bytes"
    cover_asset_path: str = "Assets/Textures/AlbumArtwork/lynyrd skynyrd_sweethomealabama.png"


REFERENCE_SONG = ReferenceSongPackage()
