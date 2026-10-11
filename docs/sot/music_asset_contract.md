# Music asset contract — evidence record

**Overall status: BLOCKED for native export and Android playback.** Milestone 0 is not complete.
Asset presence, offline decoding, and delivery mechanics are evidenced below. Linkage and
native semantics are not. Android acceptance (discovery, download, audible changed audio,
observed note sequence, result screen, persisted audit/profile) has not been performed.

Client under investigation: Beatstar `36.1.4.9545` (`versionCode=1937149545`), Unity `2022.3.50f1`.

## 1. Evidence status by claim

| Claim | Status | Evidence |
|---|---|---|
| Candidate assets are present in the APK tree | **Observed** | `tmp/apktool_base/assets` (ignored, main checkout): 166 files, 109 MB; `bin/Data/data.unity3d`; 112 `AssetBundles/*.bundle` |
| Offline extraction produces the expected inventory | **Observed** | Sandboxed run on the real tree (see §4): configs 5, bundles 112, charts 60, audio banks 4 |
| Extracted reference chart and configs match prior copies | **Observed** | SHA-256 of `660.chart.bytes` and the five `*.bin` configs equals `data/` copies |
| Chart decoding is self-consistent | **Partially evidenced** | 60/60 charts decode and re-encode byte-equal from the model (§3). Not all fields are understood. |
| Unknown fields are preserved | **Evidenced as opaque bytes** | Preserved raw, not interpreted (§3) |
| Song ↔ beatmap ↔ audio ↔ artwork linkage | **Hardcoded, not derived** | `server/music/reference_fixture.py` constants. `SongConfig.bin`/`AssetsConfig.bin` are not yet parsed to derive it. |
| Wwise bank format | **Candidate only** | `BKHD` header observed on four banks; no decoder, no export, no playback verification |
| Native export toolchain | **Not available** | No validated exporter for Unity AssetBundles or Wwise banks |
| Android discovery, playback, result, audit/profile persistence | **BLOCKED** | Not performed |
| HTTP delivery of baked configs and bundles | **Verified in tests** | Synthetic and real-mount tests (§5). Delivery mechanics only. |

## 2. Reference candidate (unlinked)

Candidate identifiers from the APK inventory. They are **not** a verified complete package:

- Title/artist: *Sweet Home Alabama (Tutorial)*, *Lynyrd Skynyrd*
- Song ID `710`, beatmap ID `660`
- Chart label decoded from `660.chart.bytes`: `"710-1"`
- Variant (template) label: `LynyrdSk-00687_SweetHomeA-TUT-Tutorial`
- Chart asset: `Assets/beatmapInteractions/660.bytes` (decoded chart: 97 interactions)
- Audio asset: `Assets/Audio/Banks/tst00687.bytes` (`BKHD` bank, 693,566 bytes extracted payload)
- Artwork: `Assets/Textures/AlbumArtwork/lynyrd skynyrd_sweethomealabama.png`

Bundle file sizes and extracted payload sizes are different measures. Chart bundle 1,237 bytes contains a
1,846-byte chart payload. Audio bundle 695,824 bytes contains a 693,566-byte bank payload. Artwork bundle is 64,912 bytes.

Required before any "complete song" claim: derive the song-to-beatmap-to-audio-to-artwork links from the binary
configs, and show the Unity object names are used by the client as those links.

## 3. Raksha chart schema (self-consistent, partially understood)

Field numbers below are inferred from IL2CPP member names and the decoder in `server/music/raksha/`.
They are **not** confirmed by a native reader. Member declarations in `dump.cs` have no method bodies, so offsets and
order are not wire-tag proof.

Top level (`BeatmapInteractionsTemplate`): `1` id varint; `2` id_label string; `5` packed interaction items.
Also present but **not decoded** into the schema: `6`, `7`, `8`, `9` length-delimited (4 per chart, all 60 charts).
Item level (`InteractionData`): `1` type; `3` tap data; `4` drag data; `6` track. Field `13` varint is present on
1,108 items across the 60 charts and is **not** decoded.

Coverage measurement (committed as `test_decode_all_extracted_apk_charts` and the chart 660 detached test; the
unknown-tag histogram came from a one-off sandboxed script that is not committed):

- Rebuilt each chart by `model_validate(model_dump())`, which drops retained source bytes, then re-encoded.
- Result: **60/60 charts re-encode byte-equal** with source retention defeated.
- Unknown-field totals: top-level 240 (fields 6–9), items 1,108 (field 13).

Interpretation: known fields reproduce exactly. Unknown fields are kept as opaque bytes. Byte equality therefore
shows the decoder/encoder round-trips the bytes it knows about. It does not show that the stars, multiplier,
beat-height, visual-impact, or item-13 semantics are understood.

Edits: unknown fields are appended after the known fields of their message. Whether the native reader accepts that
ordering is **unproven**. The existing test that compares `encode(decode(x))` to `x` returns retained source bytes
when the model is unchanged, so it is not a coverage proof. The detached test in `server/tests/test_raksha_codec.py`
is the coverage check.

Editing `stars` raises `ValueError`. Star semantics are unverified.

## 4. Offline extraction

Reproduced command (read-only input mount, new output directory, `python -I`, no network):

```bash
docker run --rm --network none --memory 1536m --cpus 2 --pids-limit 128 \
  -v <APK_ASSETS_DIR>:/in:ro -v <EMPTY_HOST_DIR>:/out \
  beatstar-music-audit python -I scripts/extract_baked_assets.py \
  --assets-dir /in --output-dir /out/result
```

Output: `{"configs": 5, "bundles": 112, "charts": 60, "audio_banks": 4}`. The catalog records
`android_compatible: false`.

The extractor rejects unsafe TextAsset names, requires a new output directory, stages privately, and publishes only
on success. Source budgets are 4,096 entries (counted during traversal), 256 MiB per file, and 512 MiB total. The
real tree is far below these budgets. Outputs are named `.bnk.bytes` for sound banks, not `.wem.bytes`.

## 5. Tests and their limits

- Default suite, no data mounts: **73 passed, 7 skipped**. All seven skips are real-fixture tests that need
  `data/extracted`, `data/configs` or `data/bundles` (listed with `-rs`). The binary-config delivery test skips
  instead of passing vacuously when its file is absent.
- Real-mount suite (`test_raksha_codec.py`, `test_asset_delivery.py`, read-only mounts of the new extractor output,
  `python -I`, no network): **10 passed, 0 skipped**. The all-60 charts test asserts detached byte equality.
- Earlier "49 tests passing" was an overstatement. The 44-pass/5-skip baseline is the honest starting count.

Delivery:

- `/assets/configs/{Name}.bin` serves real baked configs as `application/octet-stream` with `Cache-Control: no-cache`.
  Missing binary configs return 404 instead of generic JSON.
- `/assets/bundles/{name}` uses Starlette `FileResponse`, supporting `Range` (`bytes=-5`, `bytes=3-`).
- Malformed descending ranges (`bytes=8-3`) return 400 under Starlette. Unsatisfiable starts (`bytes=100-`) return 416.
- CMS advertises only configs that exist on disk, with real SHA-256 digests. `GameConfig` remains JSON feature flags.
- Advertised digests are fingerprints. They are not proof of the client's hash algorithm.

## 6. Requirements to close the gate

1. Derive the song/beatmap/audio/artwork linkage from `SongConfig.bin`, `BeatmapsConfig.bin`, and `AssetsConfig.bin`.
2. Identify the native reader for the chart and bank formats and confirm field semantics, including field order tolerance.
3. Obtain or build an export path that writes client-accepted bundles and banks. UnityPy inspection alone is insufficient.
4. Demonstrate Android discovery, download, audible changed audio, observed changed note sequence, result screen, and audit/profile persistence on the supported client.

Until those are shown, native export is unavailable and no publication path may claim Android compatibility.
Internal, browser-only, and admin work may proceed against an explicitly internal chart schema.

### Internal chart-library status (2026-10-10)

Extracted Raksha charts can be retained as immutable revisions with SHA-256 fingerprints, and synthetic
admin examples encode tap and drag interactions across all three lanes. The chart label `710-1` and
beatmap `660` remain a candidate association only; import stores chart identities without inferring a
verified game-song link. No Unity bundle is exported, no Wwise bank is decoded, and no candidate bundle artwork or
audio is attached by this internal workflow; example covers are synthetic. These admin records are drafts and do not establish client
compatibility or close the native export gate above.
