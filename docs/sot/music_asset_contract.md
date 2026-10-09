# Music asset contract — investigation v1

**Status: BLOCKED / not a verified export contract.**

This records Milestone 0 evidence collected on 2026-10-09 for client
`36.1.4.9545` (`versionCode=1937149545`). It does **not** establish that an
admin-authored song can be exported or played. No Android note semantics,
timing rules, scoring parity, or supported export note types are declared.
Do not use this document to enable publication or mark the music feature done.

## Verified evidence

- ADB identified the installed client as the target version, with an
  `arm64-v8a` application on an Android 16 `x86_64` emulator.
- The available decoded APK has 112 files in `assets/AssetBundles/` and a
  separate `assets/bin/Data/data.unity3d` core archive. Inspection did not
  alter those source files or copy proprietary payloads into Git.
- The core archive header declares Unity `2022.3.50f1`. Inspected standalone
  bundle headers have stripped `0.0.0` engine versions. UnityPy 1.25.4 needs
  an explicit `FALLBACK_UNITY_VERSION=2022.3.50f1` for these bundles; the
  initial run without it failed with `UnityVersionFallbackError`.
- All 112 bundle files were parsed using that fallback. Container names
  identify **60 beatmap-interaction assets** and **4 audio-bank assets**,
  as well as album artwork and shared UI assets. Asset presence is not
  proof of a complete, linked, playable song package.
- One chart candidate is `assets/beatmapinteractions/2708.bytes`: a
  6,883-byte binary TextAsset, SHA-256
  `4d1147ca04dec12333a3eb3ce9cf8ccd1e3fd7c7d421067417c9f26513185a50`.
  It is not an established JSON/internal-chart representation. Field
  numbers, interaction semantics, lane mapping, and tick units are unverified.
- Audio containers include `tst01696.bytes`, `dbg99002.bytes`,
  `tst00687.bytes`, and `tst00942.bytes`. The inspected `TST01696` payload
  starts with the Wwise `BKHD` signature; its length is 643,480 bytes and
  its SHA-256 is
  `c2f3b1c66555deff05294e75df6df127afd3d9f1b0630a2b5c96923c0a94e2bc`.
  Bank membership does not establish a song's duration, event mapping,
  codec requirements, or an available Wwise authoring toolchain.
- `data.unity3d` contains binary TextAssets named `SongConfig`,
  `BeatmapsConfig`, `AssetsConfig`, `AssetsPatchConfig`, and `AudioConfig`.
  It also contains `Init` and `persistent` TextAssets with Wwise `BKHD`
  signatures. `BeatmapsConfig` is only 22 bytes and includes a
  `blankBeatmaps` version marker. None of these selected configs decoded
  as JSON. A byte prefix is not a verified Raksha/Protobuf schema.
- The core archive exposed object types, but **55,999 object type-tree
  reads raised ValueError** during the initial inventory. This is partial
  inspection, not complete recovery of serialized MonoBehaviour fields.
- The sole core Unity `AudioClip` identified by that inventory is named
  `Cymbal`; this does not classify the audio inside Wwise banks.

The metadata-only [fixture inventory](fixtures/music_asset_inventory_v1.json)
records source paths, lengths, SHA-256 fingerprints, object counts, text-asset
fingerprints, and parser status. Its `android_compatible` flag is deliberately
false. SHA-256 here identifies inspection inputs; it is **not** a claim about
the hash algorithm or identifier scheme expected by the native client.

## Native bootstrap and playback status

The emulator's external app storage contained five files: three IL2CPP
runtime/metadata files, a Unity marker, and a LogstashSender file. No song
cache or OBB payload was found in those external directories. Internal
private app storage was not acquired; absence of an external cache does not
prove absence of every cached asset.

The baseline screenshot showed **“Could not connect to server”** behind an
Android fullscreen-help overlay. It is retained locally at
`.playwright-mcp/music-contract/android-baseline.png`, excluded from Git.
This only establishes the observed baseline state; it does not diagnose
which endpoint or protocol step failed. No successful native bootstrap,
audio playback, authored-note playback, or result screen was captured.
No credentials or captured network traffic are committed.

The emulator implementation is not a substitute for that evidence:

- `server/gateway/dispatcher.py` decodes JSON header/body payloads within
  its HTTP wire framing. Native serialization compatibility is unproven.
- `server/handlers/songs_handler.py` still returns mock songs.
- `server/handlers/cms_handler.py` still emits placeholder resource hashes.
- `server/app.py` still serves dummy `UnityFS`-prefixed bytes for bundles,
  and empty data for most configuration resources. Ads behavior is unchanged.
- Synthetic autoplay and successful audit requests are not playback tests.

## Type information already available

The original checkout (not the clean worktree) contains
`tmp/il2cpp_test/out/dump.cs`. Targeted inspection located declarations for
`SongConfig` (line 336479), `BeatmapInteractionsTemplate` (line 368091),
`BeatmapVariant` (line 378816), `InteractionData` (line 391253),
`SongTemplate` (line 409587), and `UnityAssetBundle` (line 651734).
These reveal audio/artwork asset IDs, interaction references, BPM/timing
members, and bundle dependency/hash/size/CRC fields.

They are valuable reverse-engineering inputs, **not missing files**. However,
the dump's `ReadKey(int, ProtoInput)` and `Write(ProtoOutput)` declarations
have no method bodies (for example lines 368116–368123). Member order or
IL2CPP memory offsets cannot be substituted for verified wire field tags.
The available declarations do not yet establish lossless decoding/re-encoding
of the binary configs/charts. These source artifacts remain outside Git.

## Precise blockers and required prerequisites

1. **Content linkage and serialization:** no verified field-level decoder
   or exporter currently links the embedded song/config records to their
   chart, Wwise events/media, artwork, and dependencies. Generated gateway
   command models do not describe this content format. Supply usable
   version-matching type/serialization definitions, or a known-good complete
   package with that mapping and manifests, to establish the contract.
2. **Export toolchain:** UnityPy inspection success is not evidence of a
   round-trip writer for these assets. No available, licensed Unity/Wwise
   authoring/export route has been demonstrated. Tool installation alone
   will not establish format or playback correctness.
3. **Bootstrap support:** a sanitized native request/response trace or a
   reproducible connected reference session is still needed to establish
   the minimum gateway/catalog responses. Do not publish raw authentication
   tickets, account identifiers, or commercial content in fixtures.
4. **Acceptance:** neither a reference song nor a deliberately modified
   chart/audio excerpt has reached native playback and the results screen
   through this server. This remains the gate even after all unit tests pass.

These are **unverified contracts**, not a claim that the repository contains
no charts or no audio. Further reverse engineering may recover some missing
information from the existing artifacts. Until then, Android-dependent
editor behavior, release building, and publication remain blocked.
Independent admin/browser work can use a clearly internal schema, but is
not implemented by this investigation checkpoint and would not satisfy
native acceptance.

## Reproduce the bounded inventory

Run from the repository root. The input must be an immutable extracted asset
directory on the **docker-dev daemon host**. Do not extract it into the code
directory, execute scripts from it, or mount secrets or live player data.
Set `ASSET_SOURCE` to its absolute daemon-host path; no production deployment
or NPM change is involved.

```bash
docker --context docker-dev build -t beatstar-music-dev .
mkdir -p .playwright-mcp/music-contract
ASSET_SOURCE=/absolute/daemon/host/path/to/apk/assets

docker --context docker-dev run --rm \
  --user 65534:65534 --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 1536m --cpus 1 --pids-limit 64 \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --mount "type=bind,src=$ASSET_SOURCE,dst=/artifacts,readonly" \
  beatstar-music-dev python -I /app/scripts/inspect_music_assets.py \
  /artifacts --unity-version 2022.3.50f1 \
  > .playwright-mcp/music-contract/inventory.json
```

The CLI launches a fresh `python -I` process for each bundle/core file,
with a 1 GiB address-space limit, 25 CPU seconds and a 30-second wall timeout.
Defaults permit at most 4,096 visited directory entries, 512 candidate files,
256 MiB per file, and 512 MiB of total candidate input. A shared 600-second
parser deadline caps cumulative worker time; remaining files are fingerprinted
but report `TimeoutError` rather than starting more parsers after that deadline.
UnityPy is pinned to the investigated version, 1.25.4, in requirements.txt.
It rejects symlinks and nonregular candidate files. The surrounding container
is required for network/filesystem isolation; Python's `-I` alone is not a
security sandbox. Do not run binary inspection unsandboxed on the host.

Exit codes: `0` means all candidate files were inspected (including an empty
inventory), `1` means at least one partial/error result, and `2` means invalid
inputs. **None means compatible or playable.** Missing type trees are
explicitly recorded; worker failures contain a failure category rather than
raw payloads or traceback text. Preserve the JSON report on exit `1`.

For this input, core type-tree failures make a partial report expected.
The system-level dependency installation in the Docker image allows `-I`
and an unprivileged container user without depending on root's user site.

## Verification commands

No live database or asset directory is mounted into the test containers.

```bash
# Entire backend suite, including existing ads tests and CLI boundaries.
docker --context docker-dev run --rm --network none beatstar-music-dev \
  python -m pytest server/tests/ -q

# A single new CLI test.
docker --context docker-dev run --rm --network none beatstar-music-dev \
  python -m pytest server/tests/test_music_inspection.py::test_invalid_bundle_is_fingerprinted_but_not_verified -q

docker --context docker-dev run --rm --network none beatstar-music-dev \
  python -m compileall -q server scripts
docker --context docker-dev compose config --quiet
git diff --check
```

There is no frontend build, browser playtest, release worker, publish path,
backup/restore acceptance, or Android acceptance result at this checkpoint.
