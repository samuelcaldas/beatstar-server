"""Domain models for CMS configuration and catalog metadata."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class CMSResourceItem(BaseModel):
    """Metadata item for versioned CMS resources."""

    name: str
    url: str
    hash: str = Field(default="mock_hash_000000000000000000000000")
    version: int = Field(default=1)
    locale: Optional[str] = Field(default=None)


class CMSCatalogResponse(BaseModel):
    """Envelope response for CMS service queries."""

    resources: dict[str, CMSResourceItem] = Field(default_factory=dict)
