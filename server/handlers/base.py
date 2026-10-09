"""Abstract base class for service command handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from server.models.headers import ClientHeader


class BaseServiceHandler(ABC):
    """Contract for handling specific SpaceApe services."""

    @abstractmethod
    async def handle(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Processes request and returns response body dictionary."""
        raise NotImplementedError
