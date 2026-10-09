"""Builder for server response headers."""

from __future__ import annotations

import time
from server.models.headers import ClientHeader, ServerHeader


class ResponseBuilder:
    """Builds corresponding ServerHeader for given ClientHeader."""

    @staticmethod
    def build_success_header(
        client_header: ClientHeader, token_id: str | None = None
    ) -> ServerHeader:
        """Constructs successful 200 server response header."""
        return ServerHeader(
            status=200,
            timestamp=int(time.time() * 1000),
            rpcthing=client_header.rpcthing,
            service=client_header.service,
            tokenid=token_id or client_header.authentication_ticket,
        )

    @staticmethod
    def build_error_header(
        client_header: ClientHeader, status: int = 500
    ) -> ServerHeader:
        """Constructs error server response header."""
        return ServerHeader(
            status=status,
            timestamp=int(time.time() * 1000),
            rpcthing=client_header.rpcthing,
            service=client_header.service,
        )
