"""Base classes for RPC commands and audit events in Flamingo/Sharpla."""

from __future__ import annotations

import time
from typing import Any, Optional
from pydantic import BaseModel, Field


class BaseRpcRequest(BaseModel):
    """Base structure for SpaceApe client commands."""

    command_id: Optional[int] = None
    command_name: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    payload: dict[str, Any] = Field(default_factory=dict)


class BaseRpcResponse(BaseModel):
    """Base structure for SpaceApe server command responses."""

    status: int = 200
    command_name: str
    error_code: Optional[int] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BaseAuditEvent(BaseModel):
    """Base structure for fire-and-forget audit events."""

    event_name: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    data: dict[str, Any] = Field(default_factory=dict)


class BatchRequestEnvelope(BaseModel):
    """Container for batch client requests."""

    commands: list[BaseRpcRequest] = Field(default_factory=list)
    audits: list[BaseAuditEvent] = Field(default_factory=list)


class BatchResponseEnvelope(BaseModel):
    """Container for batch server responses."""

    responses: list[BaseRpcResponse] = Field(default_factory=list)
    server_time: int = Field(default_factory=lambda: int(time.time() * 1000))
