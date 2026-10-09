"""Read-only baked asset discovery; not an authored release catalog."""
import hashlib
from pathlib import Path
from fastapi import HTTPException
from starlette.responses import FileResponse

MUSIC_CONFIGS = frozenset({"SongConfig", "BeatmapsConfig", "AssetsConfig"})
BINARY_CONFIGS = MUSIC_CONFIGS | {"AudioConfig", "GameConfig", "AssetsPatchConfig"}


def confined_file(directory: Path, name: str) -> Path:
    """Resolve a single regular file beneath directory, rejecting links and traversal."""
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise HTTPException(404, "Asset not found")
    candidate = directory / name
    if directory.is_symlink() or candidate.is_symlink() or not candidate.is_file():
        raise HTTPException(404, "Asset not found")
    if candidate.resolve().parent != directory.resolve():
        raise HTTPException(404, "Asset not found")
    return candidate


def file_response(directory: Path, name: str) -> FileResponse:
    """Stream a file with framework-managed range validation and seeking."""
    path = confined_file(directory, name)
    return FileResponse(path, media_type="application/octet-stream",
                        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})


def binary_resource(root: Path, base_url: str, name: str) -> dict | None:
    """Describe an available baked config using a content fingerprint (not native hash proof)."""
    try:
        path = confined_file(root / "configs", f"{name}.bin")
    except HTTPException as error:
        if error.status_code != 404:
            raise
        return None
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"name": name, "url": f"{base_url}/configs/{name}.bin", "hash": digest,
            "version": 1, "size": path.stat().st_size, "hash_algorithm": "sha256"}
