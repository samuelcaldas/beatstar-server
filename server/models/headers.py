"""Protocol header domain models."""

from __future__ import annotations

import time
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ClientHeader(BaseModel):
    """Parsed SpaceApe.Network client request header."""

    model_config = ConfigDict(populate_by_name=True)

    version: str = Field(default="36.1.4.9545")
    service: str = Field(default="userservice")
    rpcthing: str = Field(default="")
    authentication_ticket: Optional[str] = Field(
        default=None, alias="authenticationTicket"
    )
    clide: Optional[str] = Field(default=None)
    supports_compression: bool = Field(default=True, alias="supportsCompression")
    ignore_maintenance: bool = Field(default=False, alias="ignoreMaintenance")


class ServerHeader(BaseModel):
    """SpaceApe.Network server response header."""

    model_config = ConfigDict(populate_by_name=True)

    status: int = Field(default=200)
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    rpcthing: str = Field(default="")
    service: str = Field(default="")
    tokenid: Optional[str] = Field(default=None)
    gzipped: int = Field(default=0)
    redirect_host: Optional[str] = Field(default=None, alias="redirectHost")
    redirect_port: Optional[int] = Field(default=None, alias="redirectPort")
