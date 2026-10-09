#!/usr/bin/env python3
"""Offline asset and configuration extractor for Beatstar APK assets."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import struct
from pathlib import Path
import UnityPy


def parse_text_asset_payload(raw_data: bytes) -> tuple[str, bytes]:
    """Unpacks Unity TextAsset name and payload from raw serialized bytes."""
    bio = io.BytesIO(raw_data)
    name_len = struct.unpack("<I", bio.read(4))[0]
    name_str = bio.read(name_len).decode("utf-8", errors="replace")
    pad = (4 - (name_len % 4)) % 4
    bio.read(pad)
    data_len = struct.unpack("<I", bio.read(4))[0]
    payload = bio.read(data_len)
    return name_str, payload


def extract_assets(assets_dir: Path, output_dir: Path) -> dict[str, int]:
    """Extracts baked configurations and bundles to persistent data directory."""
    UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.50f1"

    configs_dir = output_dir / "configs"
    bundles_dir = output_dir / "bundles"
    extracted_dir = output_dir / "extracted"
    catalog_dir = output_dir / "catalog"

    for d in (configs_dir, bundles_dir, extracted_dir, catalog_dir):
        d.mkdir(parents=True, exist_ok=True)

    stats = {"configs": 0, "bundles": 0, "charts": 0, "audio_banks": 0}

    # 1. Extract baked configurations from data.unity3d
    data_unity3d = assets_dir / "bin" / "Data" / "data.unity3d"
    if data_unity3d.exists():
        print(f"[*] Extracting baked configs from {data_unity3d}...")
        env = UnityPy.load(str(data_unity3d))
        target_configs = {"SongConfig", "AssetsConfig", "AudioConfig", "GameConfig", "BeatmapsConfig"}
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                try:
                    name = obj.peek_name()
                    if name in target_configs:
                        raw = obj.get_raw_data()
                        _, payload = parse_text_asset_payload(raw)
                        target_file = configs_dir / f"{name}.bin"
                        target_file.write_bytes(payload)
                        stats["configs"] += 1
                        print(f"    [+] Saved config {name} ({len(payload)} bytes)")
                except Exception as exc:
                    print(f"    [-] Erro extraindo config: {exc}")

    # 2. Inventory and copy AssetBundles
    bundles_source = assets_dir / "AssetBundles"
    if bundles_source.exists():
        bundle_files = list(bundles_source.glob("*.bundle"))
        print(f"[*] Processing {len(bundle_files)} AssetBundles from {bundles_source}...")
        for b_path in bundle_files:
            dest_bundle = bundles_dir / b_path.name
            if not dest_bundle.exists() or dest_bundle.stat().st_size != b_path.stat().st_size:
                shutil.copy2(b_path, dest_bundle)
            stats["bundles"] += 1

            # Inspect bundle content for charts and audio banks
            try:
                b_env = UnityPy.load(str(b_path))
                for obj in b_env.objects:
                    if obj.type.name == "TextAsset":
                        raw = obj.get_raw_data()
                        name_str, payload = parse_text_asset_payload(raw)
                        if payload.startswith(b"BKHD"):
                            out_file = extracted_dir / f"{name_str}.wem.bytes"
                            out_file.write_bytes(payload)
                            stats["audio_banks"] += 1
                        elif len(payload) > 4 and payload[0] == 0x08:
                            out_file = extracted_dir / f"{name_str}.chart.bytes"
                            out_file.write_bytes(payload)
                            stats["charts"] += 1
            except Exception:
                pass

    # 3. Create metadata catalog JSON
    catalog_path = catalog_dir / "asset_catalog.json"
    catalog_data = {
        "client_version": "36.1.4.9545",
        "unity_version": "2022.3.50f1",
        "total_bundles": stats["bundles"],
        "total_charts": stats["charts"],
        "total_audio_banks": stats["audio_banks"],
        "reference_song": {
            "title": "Sweet Home Alabama (Tutorial)",
            "artist": "Lynyrd Skynyrd",
            "song_id": 710,
            "beatmap_id": 660,
            "beatmap_bundle": "39cf5b304affe47c7ad8e5fe2add65ac_7739e0a86bf03b786f6448c524919b6f1994021439.bundle",
            "audio_bundle": "ed13530a47a434ee482b52406ad57a86_fc96c0d74c64fee844121cf004c3b1373814866549.bundle",
            "cover_bundle": "0db2525d863d34c7ead654cc0a24002f_c4015cee4caa69eedc70c36e574b09482119362438.bundle",
        },
    }
    catalog_path.write_text(json.dumps(catalog_data, indent=2))
    print(f"[✓] Extração concluída com sucesso! Catálogo gravado em {catalog_path}")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Beatstar Offline Asset Extractor")
    parser.add_argument(
        "--assets-dir",
        default="tmp/apktool_base/assets",
        type=Path,
        help="Caminho dos assets descompactados do APK",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        type=Path,
        help="Diretório de saída para dados persistentes do servidor",
    )
    args = parser.parse_args()

    extract_assets(args.assets_dir, args.output_dir)


if __name__ == "__main__":
    main()
