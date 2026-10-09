"""HTTP routes for raw media upload and authenticated previews."""

import os
from collections.abc import AsyncIterator, Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from server.admin.models import AdministratorUser
from server.assets.formats import default_registry
from server.assets.ingest import (
    AssetIngestor,
    AssetLimits,
    AssetTooLarge,
    ProbeRejected,
    ProbeTimeout,
    QuotaExceeded,
    UnsupportedFormat,
)
from server.assets.storage import AssetStorage, ConflictingObject, object_path
from server.music.asset_service import AssetNotFound, AssetService


class AssetOut(BaseModel):
    """Public representation of a stored, verified asset."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    song_id: str
    kind: Literal["audio", "artwork"]
    storage_key: str
    sha256: str
    byte_size: int
    content_type: str
    duration_milliseconds: int | None
    width: int | None
    height: int | None
    created_at: int


def build_asset_router(
    get_session: Callable[..., AsyncIterator[AsyncSession]],
    current_administrator: Callable[..., object],
    csrf_guard: Callable[..., None],
) -> APIRouter:
    """Builds upload and preview routes; collaborators come from application state per request."""
    router = APIRouter(tags=["assets"])

    async def get_service(request: Request, session: Annotated[AsyncSession, Depends(get_session)]) -> AssetService:
        """Assembles the service from the application's configured storage, adapter and probe."""
        state = request.app.state
        limits: AssetLimits = state.asset_limits
        ingestor = AssetIngestor(state.asset_storage, default_registry(), state.client_adapter, limits)
        return AssetService(session, ingestor, state.media_probe, limits)

    ServiceDependency = Annotated[AssetService, Depends(get_service)]
    AdministratorDependency = Annotated[AdministratorUser, Depends(current_administrator)]

    @router.put("/songs/{song_id}/assets/{kind}", response_model=AssetOut, dependencies=[Depends(csrf_guard)])
    async def upload_asset(
        song_id: str,
        kind: Literal["audio", "artwork"],
        request: Request,
        response: Response,
        service: ServiceDependency,
        administrator: AdministratorDependency,
    ) -> AssetOut:
        """Streams a raw body into verified, immutable storage; 201 when created, 200 when already attached."""
        asset, created = await service.upload(song_id, kind, request.stream(), administrator.id)
        response.status_code = 201 if created else 200
        return AssetOut.model_validate(asset)

    @router.get("/assets/{asset_id}/content")
    async def read_asset_content(
        asset_id: str,
        request: Request,
        service: ServiceDependency,
        _administrator: AdministratorDependency,
    ) -> FileResponse:
        """Serves a stored object for review with Range support and no caching."""
        asset = await service.find(asset_id)
        extension = asset.storage_key[len(asset.sha256):]
        path = object_path(request.app.state.asset_storage.objects_directory, asset.sha256, extension)
        if not os.path.isfile(path):
            raise AssetNotFound(asset_id)
        return FileResponse(path, media_type=asset.content_type, headers={"Cache-Control": "no-store"})

    return router


def register_asset_error_handlers(app: FastAPI) -> None:
    """Maps ingestion refusals to HTTP responses; each refusal leaves nothing stored."""

    @app.exception_handler(UnsupportedFormat)
    async def handle_unsupported(request: Request, error: UnsupportedFormat) -> JSONResponse:
        """Returns 415 for bytes that are not an accepted format."""
        return JSONResponse(status_code=415, content={"detail": "Formato de arquivo não suportado"})

    @app.exception_handler(AssetTooLarge)
    async def handle_too_large(request: Request, error: AssetTooLarge) -> JSONResponse:
        """Returns 413 when the per-file limit is exceeded."""
        return JSONResponse(status_code=413, content={"detail": "Arquivo excede o limite por tipo"})

    @app.exception_handler(QuotaExceeded)
    async def handle_quota(request: Request, error: QuotaExceeded) -> JSONResponse:
        """Returns 413 when the total storage quota would be exceeded."""
        return JSONResponse(status_code=413, content={"detail": "Cota de armazenamento excedida"})

    @app.exception_handler(ProbeRejected)
    async def handle_rejected(request: Request, error: ProbeRejected) -> JSONResponse:
        """Returns 422 with the verifier's reason; the file is not kept."""
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(ProbeTimeout)
    async def handle_timeout(request: Request, error: ProbeTimeout) -> JSONResponse:
        """Returns 422 when verification exceeded its budget; the file is refused."""
        return JSONResponse(status_code=422, content={"detail": "Arquivo não pôde ser verificado a tempo"})

    @app.exception_handler(ConflictingObject)
    async def handle_conflict(request: Request, error: ConflictingObject) -> JSONResponse:
        """Returns 409 when stored bytes at the address differ; the stored object is untouched."""
        return JSONResponse(status_code=409, content={"detail": "Conflito de armazenamento de conteúdo"})

    @app.exception_handler(AssetNotFound)
    async def handle_asset_not_found(request: Request, error: AssetNotFound) -> JSONResponse:
        """Returns 404 for unknown assets or missing stored objects."""
        return JSONResponse(status_code=404, content={"detail": "Asset não encontrado"})
