"""HTTP routes for the administration song library; mounted under /api/admin by the admin router."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.admin.models import AdministratorUser
from server.music.song_errors import InvalidSongState, RevisionConflict, SongInUse, SongNotFound
from server.music.song_schemas import (
    MAXIMUM_PAGE_SIZE,
    Difficulty,
    RevisionGuard,
    SongCreate,
    SongOut,
    SongPage,
    SongQuery,
    SongStatus,
    SongUpdate,
)
from server.music.song_service import SongLibraryService


def build_song_library_router(
    get_session: Callable[..., AsyncIterator[AsyncSession]],
    current_administrator: Callable[..., object],
    csrf_guard: Callable[..., None],
) -> APIRouter:
    """Builds the song routes with the administrator session and authentication injected.

    Args:
        get_session: Dependency yielding one database session per request.
        current_administrator: Dependency returning the authenticated superuser.
        csrf_guard: Dependency enforcing the CSRF token on every write.

    Returns:
        A router mounted at /songs.
    """
    router = APIRouter(prefix="/songs", tags=["songs"])

    async def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> SongLibraryService:
        """Returns a service bound to the request's session."""
        return SongLibraryService(session)

    ServiceDependency = Annotated[SongLibraryService, Depends(get_service)]
    AdministratorDependency = Annotated[AdministratorUser, Depends(current_administrator)]

    @router.get("", response_model=SongPage)
    async def list_songs(
        service: ServiceDependency,
        _administrator: AdministratorDependency,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=MAXIMUM_PAGE_SIZE),
        q: str | None = Query(None, max_length=200),
        status_filter: SongStatus | None = Query(None, alias="status"),
        difficulty: Difficulty | None = Query(None),
    ) -> SongPage:
        """Lists songs with pagination, title/artist search and status and difficulty filters."""
        query = SongQuery(page=page, page_size=page_size, search=q, status=status_filter, difficulty=difficulty)
        songs, total = await service.page(query)
        return SongPage(
            items=[SongOut.model_validate(song) for song in songs],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    @router.get("/{song_id}", response_model=SongOut)
    async def read_song(song_id: str, service: ServiceDependency, _administrator: AdministratorDependency) -> SongOut:
        """Returns one song with its current revision."""
        return SongOut.model_validate(await service.get(song_id))

    @router.post("", response_model=SongOut, status_code=status.HTTP_201_CREATED,
                 dependencies=[Depends(csrf_guard)])
    async def create_song(payload: SongCreate, service: ServiceDependency, administrator: AdministratorDependency) -> SongOut:
        """Creates a draft song at revision 1."""
        return SongOut.model_validate(await service.create(payload, administrator.id))

    @router.patch("/{song_id}", response_model=SongOut, dependencies=[Depends(csrf_guard)])
    async def update_song(song_id: str, payload: SongUpdate, service: ServiceDependency, administrator: AdministratorDependency) -> SongOut:
        """Changes metadata when expected_revision is current; returns 409 with current_revision otherwise."""
        return SongOut.model_validate(await service.update(song_id, payload, administrator.id))

    @router.post("/{song_id}/archive", response_model=SongOut, dependencies=[Depends(csrf_guard)])
    async def archive_song(song_id: str, guard: RevisionGuard, service: ServiceDependency, administrator: AdministratorDependency) -> SongOut:
        """Archives a song, making it read-only and hiding it from future game discovery."""
        return SongOut.model_validate(await service.archive(song_id, guard.expected_revision, administrator.id))

    @router.post("/{song_id}/restore", response_model=SongOut, dependencies=[Depends(csrf_guard)])
    async def restore_song(song_id: str, guard: RevisionGuard, service: ServiceDependency, administrator: AdministratorDependency) -> SongOut:
        """Returns an archived song to draft."""
        return SongOut.model_validate(await service.restore(song_id, guard.expected_revision, administrator.id))

    @router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(csrf_guard)])
    async def delete_song(song_id: str, guard: RevisionGuard, service: ServiceDependency, administrator: AdministratorDependency) -> Response:
        """Hard-deletes an unreferenced draft; referenced or published songs must be archived."""
        await service.delete(song_id, guard.expected_revision, administrator.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


def register_song_error_handlers(app: FastAPI) -> None:
    """Maps song domain failures to HTTP responses; conflicts carry the current revision at top level."""

    @app.exception_handler(SongNotFound)
    async def handle_not_found(request: Request, error: SongNotFound) -> JSONResponse:
        """Returns 404 without echoing the identifier."""
        return JSONResponse(status_code=404, content={"detail": "Música não encontrada"})

    @app.exception_handler(RevisionConflict)
    async def handle_conflict(request: Request, error: RevisionConflict) -> JSONResponse:
        """Returns 409 with the revision the caller must reload."""
        return JSONResponse(
            status_code=409,
            content={"detail": str(error), "current_revision": error.current_revision},
        )

    @app.exception_handler(InvalidSongState)
    async def handle_invalid_state(request: Request, error: InvalidSongState) -> JSONResponse:
        """Returns 409 for transitions the current status does not allow."""
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(SongInUse)
    async def handle_in_use(request: Request, error: SongInUse) -> JSONResponse:
        """Returns 409 when a hard delete would orphan retained data."""
        return JSONResponse(status_code=409, content={"detail": str(error)})
