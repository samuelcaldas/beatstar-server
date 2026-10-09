# Music asset contract — verified specification v2

**Status: VERIFIED / APK-Recovered Contract & Reference Package (Milestone 0 Unblocked)**

This records Milestone 0 evidence and verification completed on 2026-10-09 for client
`36.1.4.9545` (`versionCode=1937149545`). 

Because official game servers are decommissioned, all serialization schemas, content linkage,
and reference song packages were reverse-engineered and recovered directly from local APK assets
and native binaries (`data.unity3d`, `dump.cs`, `libil2cpp.so`, and `assets/AssetBundles/`).

---

## 1. Verified complete reference song package

A known-good, complete, 100% linked reference song package was identified, extracted, and verified
from the APK assets:

- **Song Title:** *Sweet Home Alabama (Tutorial)*
- **Artist:** *Lynyrd Skynyrd*
- **Song ID:** `710` (Template: `LynyrdSk-00687_SweetHomeA-TUT`)
- **Beatmap Variant ID:** `660` (Label: `"710-1"`, Difficulty: `Tutorial`, Variant Label: `LynyrdSk-00687_SweetHomeA-TUT-Tutorial`)
- **Chart Asset:** `Assets/beatmapInteractions/660.bytes`
  - **AssetBundle:** `39cf5b304affe47c7ad8e5fe2add65ac_7739e0a86bf03b786f6448c524919b6f1994021439.bundle`
  - **Size:** 1,846 bytes (97 interaction notes)
- **Audio SoundBank:** `Assets/Audio/Banks/tst00687.bytes`
  - **AssetBundle:** `ed13530a47a434ee482b52406ad57a86_fc96c0d74c64fee844121cf004c3b1373814866549.bundle`
  - **Format:** Wwise SoundBank (header `BKHD` v145, `DIDX`, `DATA` chunk containing raw WEM audio, 693,566 bytes)
- **Cover Artwork:** `Assets/Textures/AlbumArtwork/lynyrd skynyrd_sweethomealabama.png`
  - **AssetBundle:** `0db2525d863d34c7ead654cc0a24002f_c4015cee4caa69eedc70c36e574b09482119362438.bundle`
- **Metadata Linkage:** Mapped deterministically through `SongConfig.bin` and `AssetsConfig.bin`.

---

## 2. Serialization format (Raksha Protobuf Wire Contract)

SpaceApe's Raksha database engine uses standard low-level Protobuf wire framing (`ProtoInput` / `ProtoOutput`).

### 2.1 Top-level `BeatmapInteractionsTemplate`
| Tag | Wire Type | Field Name | Description |
|---|---|---|---|
| 1 | 0 (Varint) | `id` | Unique beatmap variant ID (e.g. 660) |
| 2 | 2 (Length-Delimited) | `idLabel` | Human-readable identifier (e.g. `"710-1"`) |
| 5 | 2 (Length-Delimited) | `InteractionData[]` | Packed length-prefixed array of note interaction items |
| 6 | 2 (Length-Delimited) | `Stars[]` | Score thresholds for star progression |
| 7 | 2 (Length-Delimited) | `MaxHitTimeOffsetMultipliers[]` | Timing window multipliers |
| 8 | 2 (Length-Delimited) | `NumBeatsInHeightModifiers[]` | Scroll speed / scroll height modifiers |
| 9 | 2 (Length-Delimited) | `VisualImpacts[]` | Gameplay visual impact markers |

### 2.2 `InteractionData` Item
| Tag | Wire Type | Field Name | Description |
|---|---|---|---|
| 1 | 0 (Varint) | `InteractionType` | 1 = Tap, 2 = Drag, 3 = TapHold, 5 = SwitchHold |
| 3 | 2 (Length-Delimited) | `TapInteractionData` | Present when `InteractionType == 1` |
| 4 | 2 (Length-Delimited) | `DragInteractionData` | Present when `InteractionType == 2` |
| 6 | 0 (Varint) | `Track` | Physical lane (1, 2, or 3). *Omitted if default value 1* |

### 2.3 Note Components (`InteractionPoint`, `TapInteractionData`, `DragInteractionData`)
- **`InteractionPoint`:**
  - Tag 1 (Fixed32 Float): `BeatOffset` (musical timing offset in beats)
  - Tag 3 (Varint): `Lane` (1, 2, or 3)
- **`TapInteractionData`:**
  - Tag 1 (Length-Delimited): `InteractionPoint`
  - Tag 2 (Varint, Optional): `FlickDirection` (0=None, 1=Up, 2=Down, 3=Left, 4=Right, 5=LeftUp, 6=RightUp, 7=RightDown, 8=LeftDown)
- **`DragInteractionData`:**
  - Tag 1 (Length-Delimited, Repeated): `InteractionPoint[]` (hold start, bend points, release point)
  - Tag 2 (Varint, Optional): `FlickDirection` (release flick swipe)

### 2.4 Codec Verification
- Pure Python codec implemented in `server/music/raksha/`:
  - `codec.py`: `ProtoReader`, `ProtoWriter`
  - `beatmap_schema.py`: Pydantic data models
  - `serializer.py`: `decode_beatmap_interactions`, `encode_beatmap_interactions`
- Verified:
  - Exact 100% bit-for-bit roundtrip on reference chart `660.chart.bytes`.
  - Clean error-free deserialization of all 60 APK beatmaps (17,130 tap notes, 930 drag notes).
  - Note modification (timings, lanes, insertions) re-encodes and deserializes deterministically.

---

## 3. Server asset delivery & CMS integration

1. **AssetBundle Endpoint (`/assets/bundles/{bundle_name}`):**
   - Serves real Unity AssetBundles from `data/bundles/`.
   - Supports HTTP `Range` requests (`status 206`, `Accept-Ranges: bytes`, `Content-Range`) for streaming.
   - Missing bundles return `404 Not Found` rather than placeholder bytes.
2. **Configuration Endpoint (`/assets/configs/{config_name}`):**
   - Delivers binary configurations (`SongConfig.bin`, `AssetsConfig.bin`, `AudioConfig.bin`) as `application/octet-stream`.
   - Delivers JSON configurations (`AdsConfig`, `GameConfig`) preserving feature flags.
3. **CMS Handler (`cmsservice`):**
   - Returns discovery catalog URLs for `SongConfig`, `BeatmapsConfig`, `AssetsConfig`, `GameConfig`, `AdsConfig`.

---

## 4. Offline extraction pipeline

The script `scripts/extract_baked_assets.py` automates extraction without external server dependency:
```bash
python scripts/extract_baked_assets.py --assets-dir tmp/apktool_base/assets --output-dir data
```
- Extracts `SongConfig`, `AssetsConfig`, `AudioConfig`, `GameConfig` from `data.unity3d`.
- Populates `data/bundles/` with 112 AssetBundles.
- Extracts all 60 chart `.bytes` and 4 Wwise `.wem.bytes` audio banks to `data/extracted/`.
- Generates `data/catalog/asset_catalog.json`.

---

## 5. Milestone 0 Gate Status

| Requirement | Status | Evidence |
|---|---|---|
| Complete reference song | **PASSED** | *Lynyrd Skynyrd* (Song 710, Beatmap 660, Audio TST00687, Cover 0db2525d...) |
| Wire serialization contract | **PASSED** | Raksha Protobuf codec with bit-for-bit roundtrip on `660.bytes` |
| Native asset manifests | **PASSED** | `AssetsConfig.bin` & `SongConfig.bin` extracted and cataloged |
| Real AssetBundle delivery | **PASSED** | `/assets/bundles/` with HTTP Range and streaming support |
| Test suite coverage | **PASSED** | `server/tests/test_raksha_codec.py`, `server/tests/test_asset_delivery.py` (49 tests passing) |

**Milestone 0 is complete and unblocked.** Implementation of Milestone 1 (Persistence and Administrator Access) and Milestone 2 (Song Library and Upload Pipeline) may proceed.
