"""Serves the exported administration UI under /admin with a client-side routing fallback.

The fallback answers unknown paths with the application shell so deep links work, but only for
paths that look like app routes. Paths with a file extension are never answered with HTML, and
the resolved file must stay inside the export directory, so encoded traversal cannot escape it.
Routes under /api are not part of this router and keep their JSON 404 responses.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException

INDEX_FILE = "index.html"


def build_admin_ui_router(export_directory: Path) -> APIRouter:
    """Builds the /admin routes for a static export directory.

    Args:
        export_directory: Output of the UI build (for example frontend/out). It may not exist yet;
            requests then return 404 instead of failing at startup.

    Returns:
        A router with the admin index and the catch-all static and fallback route.
    """
    router = APIRouter(include_in_schema=False)
    root = export_directory.resolve()

    @router.get("/admin")
    @router.get("/admin/")
    async def admin_index() -> FileResponse:
        """Serves the application shell."""
        return _index(root)

    @router.get("/admin/{requested:path}")
    async def admin_asset_or_route(requested: str) -> FileResponse:
        """Serves an exported file, or the shell for an app route; never a missing asset."""
        candidate = (root / requested).resolve()
        if _inside(candidate, root) and candidate.is_file():
            return FileResponse(candidate)
        if Path(requested).suffix:
            raise HTTPException(status_code=404, detail="Not Found")
        return _index(root)

    return router


def _inside(path: Path, root: Path) -> bool:
    """Returns True when path is root itself or lies beneath it."""
    return path == root or root in path.parents


def _index(root: Path) -> FileResponse:
    """Returns the application shell with revalidation so new builds are picked up.

    Raises:
        HTTPException: 404 when the UI has not been built.
    """
    index = root / INDEX_FILE
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
