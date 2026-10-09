# Music administration, chart authoring, and Android playback

## Context

The user wants a web UI for server-side music management, creation, uploads, and related operations. They explicitly require a visual chart editor, interactive browser playtesting, and actual playback of authored songs in the Beatstar Android client. Only existing repository artifacts are available; there is no supplied, known-good complete song package.

The current FastAPI server exposes mock song catalogs and dummy UnityFS bundles. There is no frontend, music persistence, upload pipeline, or proven chart exporter. Existing autoplay scripts simulate protocol traffic and are not evidence of real Android gameplay. This is a new subsystem, not a UI wrapper around finished song APIs.

## Recommended approach

Build a React/TypeScript/Vite administration application at `/admin/`, backed by the existing FastAPI application at `/api/admin/`. Keep browser/API traffic same-origin behind the existing reverse proxy. Use SQLAlchemy's async ORM with SQLite and Alembic for the new administration/music domain, an established authentication framework for administrators, immutable filesystem assets, and versioned chart/release records.

First establish a real Android-compatible vertical slice using repository artifacts. Then build the authoring workflow around that verified contract. Deliver the work in the milestones below; browser-only functionality is useful progress but does not satisfy the complete request.

### Explicit boundaries

- Initial users are trusted server administrators; no public registration, social features, or collaborative realtime editing.
- Include library search/filtering, song creation/editing/duplication, uploads, waveform preview, chart authoring, playtesting, package export, publish/unpublish, release history, rollback, and archive.
- Musical composition, AI chart generation, licensing acquisition, multiplayer, and general player-account administration are outside this feature.
- Support client `36.1.4.9545` first, subject to verifying the installed client against the artifacts. No promise of cross-version export compatibility.
- Do not introduce a new production deployment or configure NPM programmatically. Development and verification use `docker-dev`.

## Existing code to reuse and preserve

- `server/app.py`: FastAPI application/lifespan, `/health`, gateway endpoints, `get_config()`, and `get_bundle()`. Split new routers out rather than continuing to expand the entry point.
- `server/gateway/dispatcher.py`: `GatewayDispatcher.dispatch_payload()` and its `songservice`/`beatmapservice` routing. Inject a shared catalog service into the relevant handlers.
- `server/handlers/songs_handler.py`: retain its public handler interface while replacing `DEFAULT_SONGS` with published data.
- `server/handlers/cms_handler.py`: adapt `CMSHandler.handle()` to versioned catalog resources; preserve unrelated configuration entries.
- `server/storage/database.py` and `player_repository.py`: preserve existing player data and behavior. New tables use the ORM; a wholesale rewrite of player persistence is unnecessary.
- `server/config.py`: extend existing Pydantic settings for admin authentication, asset storage, upload quotas, worker settings, and public URLs.
- `server/tests/test_app.py`, `test_ads_config.py`, and handler tests: reuse pytest/asyncio and HTTPX ASGITransport patterns; make their application/database fixtures isolated.
- `scripts/decompile.py`, `scripts/analyze_protocol.py`, `client_patch/frida_hook_network.js`, and the protocol/reference docs: reuse inspection and connection mechanisms where verified. Do not mistake generated protocol models for an implemented chart format.

### Representative new files

- `frontend/package.json`, `frontend/src/features/library/`, `frontend/src/features/chart_editor/`, and `frontend/src/features/playtest/`: UI, audio clock, editor commands, and browser interaction tests.
- `server/admin/router.py`, `server/admin/auth.py`, and `server/admin/provision.py`: protected management surface and administrator provisioning.
- `server/music/catalog_service.py`, `server/music/chart_schema.py`, and `server/music/release_service.py`: shared domain operations used by admin and game handlers.
- `server/assets/storage.py`, `server/assets/validation.py`, and `server/assets/exporters/`: safe asset lifecycle and client-version-specific format adapters.
- `server/jobs/worker.py`, ORM model/repository modules, and Alembic revisions: durable build execution and persistence.
- `server/tests/test_admin_auth.py`, `test_music_catalog.py`, `test_asset_uploads.py`, and `test_music_releases.py`: representative new backend suites.

## Milestone 0 — Prove the Android content contract

1. Inventory `tmp/apktool_base/assets/AssetBundles/`, other extracted APK artifacts, available metadata, and the installed emulator/client without altering source artifacts. Determine whether they contain a complete song's chart, audio, artwork, manifest, and dependency chain.
2. Inspect available assets with UnityPy and existing extraction tooling. Use isolated processes for untrusted data; keep inspection scripts outside extracted directories. Establish actual Unity serialization, audio/Wwise requirements, chart fields/note semantics, identifiers, hashes, compression, and catalog/config lookup paths.
3. Establish a known-good song loading and playing through this server in the real Android client. Capture requests and any minimum missing bootstrap/catalog/protocol support. Implement only prerequisites necessary for the song workflow, preserving existing ads behavior. Do not infer compatibility from a `UnityFS` prefix or a successful synthetic gateway request.
4. Prove the chosen packaging route by changing a recognizable note sequence and audio excerpt, rebuilding the required artifacts, serving correct manifests/hashes, and observing the changed content playing in Android. Prefer tooling that correctly serializes the verified assets; use Unity/Wwise tools only when required and available with the necessary licensing. UnityPy inspection support alone does not establish export support.
5. Record a versioned compatibility contract and fixture manifests, toolchain versions, supported note types, timing rules, and evidence in `docs/sot/music_asset_contract.md`. Keep proprietary binaries and captured secrets out of Git.

**Gate:** Android-compatible export and complete-song playback must be demonstrated before declaring the asset pipeline feasible or freezing client-specific editor behavior. If the repository lacks a complete reference song, necessary type information, bootstrap support, or an available export toolchain, report the precise blocker and request the missing prerequisite. Independent admin/browser work may proceed against an explicitly internal chart schema, but Android-dependent tasks remain blocked and the full feature is not complete.

## Milestone 1 — Persistence and administrator access

- Add focused packages such as `server/admin/`, `server/music/`, `server/assets/`, and `server/storage/migrations/`; keep business services independent of route handlers and client serializers.
- Introduce an application factory with injected settings/services while retaining `server.app:app`. Establish one startup migration path and clean engine disposal. Baseline the existing `players` table without changing its columns or losing rows; coordinate legacy initialization with migrations and test upgrades from an existing database.
- Model administrators/sessions, songs, assets, chart revisions, build jobs, releases, and audit events. A song references source audio/artwork and charts; a release snapshots exact song metadata, chart revision, assets, and client target. Store bounded, schema-versioned chart documents with stable note IDs and optimistic revision numbers.
- Keep imported assets, generated previews, and release artifacts separate under a configured persistent storage root. Use generated identifiers/content digests as storage keys rather than user filenames.
- Use FastAPI Users with its SQLAlchemy adapter and database-backed, revocable cookie sessions. Disable public signup; provide idempotent admin provisioning via CLI with credentials from environment/mounted secret inputs. Do not reuse game authentication tickets or default JWT secrets.
- Protect every administration API, draft preview, and job endpoint. Require CSRF protection for cookie-authenticated writes, HTTP-only cookies, HTTPS-secure cookies outside explicit development, expiration/logout revocation, origin checks, and bounded login attempts. Replace wildcard credentialed CORS with explicit configuration.
- Enable SQLite foreign keys, bounded busy timeouts, and short write transactions; serialize conversion/publication writes where needed. Keep credentials and sensitive headers out of logs.

## Milestone 2 — Song library and upload pipeline

- Add typed CRUD/list APIs with pagination, search, difficulty/status filters, validation errors, optimistic concurrency, and archive semantics. Hard deletion is restricted to unreferenced drafts/assets; retained releases must not acquire broken references.
- Build the React library, song detail, upload, and release views. Use React Router and TanStack Query for navigation/server state and a maintained accessible component library. Keep long-running upload/build statuses visible, including actionable failures and retry controls.
- Accept audio/artwork plus validated chart/package inputs supported by the compatibility contract. Validate streaming byte limits even without Content-Length, file signatures, duration/dimensions, chart size, permitted types, and total storage quotas. Reject traversal, executable content, and unsupported formats. Avoid arbitrary archive extraction; if the verified package format requires archives, enforce per-entry paths, count, decompressed size, and symlink restrictions.
- Stage uploads privately, verify them in bounded worker processes, then finalize immutable assets. Use FFmpeg/ffprobe for browser-compatible previews and waveform peaks, not as an assumed Wwise/Unity exporter. Apply parser resource/time limits and cleanup on failure.
- Serve authenticated draft previews with audio range/seek support and appropriate MIME types. Published game assets use immutable URLs and validated cache headers; never expose the raw storage directory.

## Milestone 3 — Visual chart editor and browser playtest

- Create a desktop-first editor: library/song navigation, waveform with tempo/grid controls, synchronized note lanes, note/property inspector, validation panel, and transport controls. Library management remains usable on smaller screens.
- Use wavesurfer.js for waveform display and a focused canvas renderer for the timeline/playfield. Use the Web Audio playback clock as the timing source; requestAnimationFrame renders state but does not determine note timing.
- Define a versioned internal chart schema using integer musical ticks, a tempo map, an explicit audio offset, stable note IDs, and deterministic tick/time conversion. Match precision and supported semantics to the Android contract; preserve raw source data when importing unsupported fields rather than silently discarding them.
- Include note placement/move/resize/delete, multi-select/copy/paste, snap/grid, zoom/scroll, BPM/offset editing, supported stage/difficulty settings, undo/redo, and shortcuts. Expose tap/hold/swipe or compound notes only when their conversion semantics are verified; clearly separate browser-only capabilities from Android-compatible charts.
- Add debounced autosave with revision checks and explicit save/error state. On stale revisions return a conflict and offer reload or duplicate, rather than overwriting another session. Warn before leaving with unsaved changes.
- Provide interactive keyboard/touch playtesting, pause/resume, seeking, section loops, calibration offset, hit/miss feedback, and browser preview results. Label preview scoring as such unless native scoring parity is proven. Validate timing bounds, lane indices, hold endpoints, ordering, and unsupported combinations before export.

## Milestone 4 — Build, publish, and serve playable releases

- Implement an explicit `validate -> build -> verify -> publish` workflow. Persist a bounded, single-worker job queue in SQLite with leases/heartbeats, retries, idempotency keys, failure reasons, and restart recovery. Conversion runs outside API request handlers and outside database transactions; avoid adding Redis solely for this queue.
- Use versioned client-export adapters implementing the verified contract. Build immutable audio/chart/artwork bundles and actual client-required hashes/dependency manifests; preserve a separate browser representation.
- Make publication atomic: finish and verify all files first, then switch a single active release/catalog snapshot in a short transaction. Never serve partially built releases. Protect the active pointer with revision checks and retain the previous release for rollback.
- Replace mock `SongsHandler` responses and dummy bundle delivery with the shared published catalog/asset services. Produce CMS configs/manifests from the same published snapshot, retaining ads/GameConfig fields and the envelope required by the client.
- Drafts never appear in game discovery. Unpublish removes future discovery but retains versioned assets long enough for in-flight clients and rollback; it is not a promise to erase previously downloaded copies. Missing assets return 404, not placeholder bundle bytes.
- Expose build progress, validation issues, target-client compatibility, release history, package download, rollback, and archive in the UI. Require confirmation for destructive or publication-state changes.

## Milestone 5 — Packaging and live documentation

- Extend `Dockerfile` with a frontend build stage and cacheable Python dependencies, serving the built UI through FastAPI with `/admin/`-scoped SPA fallback that cannot mask API/asset 404s. Add FFmpeg and the proven conversion toolchain only to the services/images that need them.
- Extend `docker-compose.yml` for API/worker, shared persistent database/assets, health checks, and `TZ=America/Sao_Paulo`. Ensure the worker has its own meaningful health signal. Use a development override or explicit file synchronization; remote Docker bind mounts must refer to files present on `docker-dev`.
- Add `.dockerignore` so `.env`, database/media contents, extraction trees, tools, caches, Git history, and test captures are not copied into build contexts/images. Include only deliberate frontend build outputs through multi-stage COPY instructions.
- Extend `.env.example` with non-secret defaults and document required secrets/limits. Add NPM instructions for TLS, trusted proxy headers, upload body limits/timeouts, and range delivery; the user applies them manually.
- Update `docs/README.md`, add an authoring/operator guide and the verified asset contract, and update `CLAUDE.md` with actual build/lint/test commands and implementation status. Preserve existing reverse-engineering docs and advertisements configuration.

## Verification and completion criteria

All builds/tests run on `docker-dev` against disposable databases/assets; never mount live player data into tests.

1. **Backend:** preserve the full existing pytest suite, including ads configuration. Add isolated app factories/fixtures and tests for migrations preserving player rows, session/CSRF/authorization boundaries, zero/one/many song catalogs, upload limits/spoofed files/traversal, chart validation, stale edits, idempotent jobs, crash recovery, and atomic publication/rollback.
2. **Frontend:** add type checking, linting, and Vitest tests for tick/time conversion, tempo/offset changes, note operations, undo/redo, revision conflicts, and deterministic preview judgments. Test no timing accumulation across long playback, seek, pause, and resume.
3. **Browser:** Playwright logs in, creates a song, uploads a short test audio/artwork fixture, authors and reloads a chart, interacts with playtest, builds/publishes it, and verifies catalog visibility, unpublish, and rollback. Include expired sessions, failed builds, and overlapping edits. Store screenshots/traces only under `.playwright-mcp/`.
4. **Game delivery:** fetch every emitted catalog/config/asset URL, verify lengths/hashes/versions and range responses where appropriate, and test that incomplete builds/drafts never reach discovery. Regress JSON/wire gateway and CMS envelope behavior.
5. **Android acceptance:** with the supported client connected to the development server, discover the newly authored song, download its real assets, hear its audio, observe the deliberately authored note sequence, play through to the native result screen, and verify the corresponding game audit/profile persistence. Repeat after a release update to detect stale caches. Capture screen recording/logs/network evidence without secrets. Neither synthetic autoplay scripts nor a submitted score satisfies this check.
6. **Operations:** validate Compose, image health, worker restart/retry, durable data after restart, and a backup/restore exercise using test data. Document commands for the full suite and selecting a single backend/frontend test.

**Done means:** a song created through the web UI can be edited, reloaded, browser-playtested, exported, published, and genuinely played in Android, with persistence, administrator protections, reproducible tests, and documented operations. Any missing Android/toolchain evidence remains an explicit blocker, not a completed feature.
