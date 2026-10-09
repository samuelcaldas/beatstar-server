"""Module-level application used by uvicorn (server.app:app) and existing tests."""

from __future__ import annotations

from server.app_factory import create_app

app = create_app()
db_manager = app.state.database
dispatcher = app.state.dispatcher
