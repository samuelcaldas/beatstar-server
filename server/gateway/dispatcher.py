"""Gateway dispatcher routing client requests to service handlers."""

from __future__ import annotations

import json
from typing import Any
from server.gateway.header_parser import HeaderParser
from server.gateway.response_builder import ResponseBuilder
from server.gateway.wire_codec import WireCodec
from server.handlers.cms_handler import CMSHandler
from server.handlers.profile_handler import ProfileHandler
from server.handlers.session_handler import SessionHandler
from server.handlers.songs_handler import SongsHandler
from server.handlers.sync_handler import SyncHandler
from server.models.headers import ClientHeader, ServerHeader
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository


class GatewayDispatcher:
    """Dispatches requests to appropriate service handlers."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.repository = PlayerRepository(db_manager)
        self.session_handler = SessionHandler(self.repository)
        self.cms_handler = CMSHandler()
        self.profile_handler = ProfileHandler(self.repository)
        self.sync_handler = SyncHandler(self.repository)
        self.songs_handler = SongsHandler()

    async def dispatch_payload(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> tuple[ServerHeader, dict[str, Any]]:
        """Routes request based on service name."""
        service = header.service.lower()

        if service == "userservice":
            res_body = await self.session_handler.handle(header, body)
            token = res_body.get("resp_login_of_some_type", {}).get(
                "authenticationTicket"
            )
            res_hdr = ResponseBuilder.build_success_header(header, token_id=token)
            return res_hdr, res_body

        if service == "cmsservice":
            res_body = await self.cms_handler.handle(header, body)
            res_hdr = ResponseBuilder.build_success_header(header)
            return res_hdr, res_body

        if service in ("profileservice", "flamingoprofile"):
            res_body = await self.profile_handler.handle(header, body)
            res_hdr = ResponseBuilder.build_success_header(header)
            return res_hdr, res_body

        if service in ("syncservice", "sharplaservice", "flamingo"):
            res_body = await self.sync_handler.handle(header, body)
            res_hdr = ResponseBuilder.build_success_header(header)
            return res_hdr, res_body

        if service in ("songservice", "beatmapservice"):
            res_body = await self.songs_handler.handle(header, body)
            res_hdr = ResponseBuilder.build_success_header(header)
            return res_hdr, res_body

        # Fallback genérico para serviços desconhecidos
        res_hdr = ResponseBuilder.build_success_header(header)
        return res_hdr, {"status": 200, "message": f"Service {service} acknowledged"}

    async def dispatch_wire_frame(self, raw_frame: bytes) -> bytes:
        """Decodes binary wire frame, processes service, and encodes response frame."""
        header_bytes, body_bytes = WireCodec.decode_frame(raw_frame)
        header_dict = json.loads(header_bytes.decode("utf-8", errors="ignore"))
        body_dict = (
            json.loads(body_bytes.decode("utf-8", errors="ignore"))
            if body_bytes
            else {}
        )

        client_hdr = HeaderParser.parse_dict(header_dict)
        res_hdr, res_body = await self.dispatch_payload(client_hdr, body_dict)

        res_hdr_bytes = json.dumps(res_hdr.model_dump(by_alias=True)).encode("utf-8")
        res_body_bytes = json.dumps(res_body).encode("utf-8")

        return WireCodec.encode_frame(res_hdr_bytes, res_body_bytes)
