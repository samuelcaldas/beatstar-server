# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project scope and requirements

Beatstar reverse-engineering toolkit and Python private-server emulator.
Use established libraries for authentication, and an ORM with SQLite.
These remain requirements: current storage uses direct aiosqlite SQL,
and current authentication is a stub rather than a framework integration.

Read docs/README.md for the documentation index. Before changing protocol
behavior, consult docs/sot/protocol_specification.md; distinguish the
documented game protocol from the emulator's implemented subset.

## Development commands

Run commands from the repository root. The Docker runtime uses Python 3.12.
Python dependencies, including pytest, are in requirements.txt.

Local tooling environment:
```bash
./scripts/setup_env.sh
source .venv/bin/activate
```
The setup script also attempts a global ilspycmd installation when .NET
is available.

Use the docker-dev context for builds and tests:
```bash
docker --context docker-dev build -t beatstar-dev .

# Entire suite in a disposable container, without development DB mounts
docker --context docker-dev run --rm beatstar-dev \
  python -m pytest server/tests/ -v

# Single test
docker --context docker-dev run --rm beatstar-dev \
  python -m pytest server/tests/test_gateway.py::test_wire_codec_encode_and_decode_roundtrip -v

# Python syntax check; not a substitute for tests or a linter
docker --context docker-dev run --rm beatstar-dev \
  python -m compileall -q server scripts

# Validate Compose configuration
docker --context docker-dev compose config --quiet
```

No repository linter or formatter is configured. pytest configuration in
pyproject.toml sets the repository import path, server/tests discovery,
and automatic asyncio mode. Rebuild the image after source changes when
using the mount-free test commands above.

Run the Compose service:
```bash
docker --context docker-dev compose up -d --build
```
Compose binds ./server and ./data into the container. With a remote Docker
context, these paths refer to the daemon host, not this checkout; ensure
the source and data directories are provisioned there before using Compose.
The image starts server.app:app through Uvicorn on port 8080; /health is
the health endpoint. The existing command does not enable auto-reload.

server/config.py loads .env using Pydantic Settings. Compose supplies
explicit environment overrides. Keep advertised gateway/asset URLs aligned
with the Nginx reverse proxy; NPM configuration is applied manually.

## Architecture

- server/app.py owns FastAPI startup, database initialization, and HTTP
  endpoints. Both /gateway and /socket-gateway feed GatewayDispatcher;
  there is no standalone TCP listener.
- /gateway accepts JSON header/body envelopes. /socket-gateway accepts
  length-prefixed binary frames over HTTP. WireCodec handles framing;
  the dispatcher currently decodes the header and body as JSON, not
  Protobuf. Gzip encoding exists, but decoding does not decompress.
- GatewayDispatcher routes service names to handlers for login, CMS,
  profiles, sync, and songs. Handlers use Pydantic models and
  PlayerRepository; DatabaseManager creates the SQLite schema.
- Login establishes Cinta/Clide player identity and returns a random
  authentication ticket. Incoming tickets are not currently validated.
  JWT configuration does not imply implemented JWT authentication.
- CMS, songs, and asset responses are mocks. Sync handles the song-ended
  audit by updating player rewards; it does not verify gameplay or scores.
- API tests initialize the application's configured database. Run them in
  a disposable container without the development data mount. Handler
  tests use temporary databases; wire tests primarily exercise helpers.

## Reverse-engineering pipeline

scripts/decompile.py extracts APKM contents and Unity IL2CPP inputs, runs
Il2CppDumper, and optionally decompiles C# assemblies and Java. Read
docs/sot/decompilation_guide.md before using it; external tools require
Java/.NET tooling beyond the Python server image.

scripts/analyze_protocol.py consumes dump.cs and regenerates:
- docs/sot/protocol_commands.json
- server/models/protocol/generated_commands.py
- server/models/protocol/__init__.py

Change the generator for durable generation fixes; regeneration overwrites
those outputs. Generated models are not proof that a command is supported
by runtime handlers.

For client connection changes, read docs/sot/client_patching_guide.md.
scripts/patch_apk.py and client_patch/ provide APK-patching and Frida paths.

scripts/simulate_autoplay.py drives synthetic protocol traffic.
scripts/validate_emulator_song.py additionally uses ADB and the Android
shell runner; these are not proof of real song completion. The shell runner
defaults to 10.0.2.2:8080, and the Python wrapper does not forward its --url
or --cinta arguments to that runner. Screenshots belong in .playwright-mcp/.
