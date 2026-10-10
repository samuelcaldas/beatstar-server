"""Gateway dispatcher routing client requests to service handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("beatstar.dispatcher")
from server.gateway.header_parser import HeaderParser
from server.gateway.proto_codec import ProtoCodec, ProtoWire
from server.gateway.response_builder import ResponseBuilder
from server.gateway.wire_codec import WireCodec
from server.handlers.cms_handler import CMSHandler
from server.handlers.profile_handler import ProfileHandler
from server.handlers.session_handler import SessionHandler
from server.handlers.songs_handler import SongsHandler
from server.handlers.sync_handler import SyncHandler
from server.models.headers import ClientHeader, ServerHeader
from server.player_auth.policy import PlayerTicketPolicy
from server.player_auth.store import PlayerTicketStore
from server.storage.database import DatabaseManager
from server.storage.player_repository import PlayerRepository


from server.commerce import CommerceService
from server.gameplay import GameplayService


class GatewayDispatcher:
    """Dispatches requests to appropriate service handlers."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        ticket_store: PlayerTicketStore,
        ticket_policy: PlayerTicketPolicy,
        commerce_service: CommerceService | None = None,
    ) -> None:
        self.repository = PlayerRepository(db_manager)
        self.ticket_policy = ticket_policy
        self.commerce_service = commerce_service or CommerceService()
        self.gameplay_service = GameplayService(db_manager)
        self.session_handler = SessionHandler(self.repository, ticket_store)
        self.cms_handler = CMSHandler()
        self.profile_handler = ProfileHandler(self.repository)
        self.sync_handler = SyncHandler(self.repository, self.commerce_service, self.gameplay_service)
        self.songs_handler = SongsHandler()



    async def dispatch_payload(
        self, header: ClientHeader, body: dict[str, Any]
    ) -> tuple[ServerHeader, dict[str, Any]]:
        """Routes request based on service name."""
        service = header.service.lower()
        if service != "userservice":
            await self.ticket_policy.observe(header.authentication_ticket, service)

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

    async def _dispatch_json_frame(
        self, header_bytes: bytes, body_bytes: bytes
    ) -> bytes:
        """Processes JSON-encoded wire frame."""
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

    async def _dispatch_proto_userservice(
        self, client_hdr: ClientHeader, body_bytes: bytes
    ) -> bytes:
        """Processes userservice Protobuf frame."""
        req_dict = ProtoCodec.decode_user_request(body_bytes)
        res_body = await self.session_handler.handle(client_hdr, req_dict)
        login_info = res_body.get("resp_login_of_some_type", {})
        ticket = login_info.get("authenticationTicket", "ticket")
        clide = login_info.get("clide", "clide")
        cinta = login_info.get("cinta", "cinta")
        res_hdr = ProtoCodec.encode_server_header(client_hdr)
        res_payload = ProtoCodec.encode_user_response(
            req_dict.get("id", 1), ticket, clide, cinta
        )
        return WireCodec.encode_frame(res_hdr, res_payload)

    def _resolve_response_body(self, service: str, rpc_type: int) -> bytes:
        """Resolves payload body based on service and RPC type."""
        if service == "gameservice" and rpc_type == 5:
            return ProtoCodec.encode_sync_response()
        if service in ("syncservice", "sharplaservice", "flamingo"):
            return ProtoCodec.encode_sharpla_response()
        return b""

    def _build_batch_responses(
        self, service: str, requests: list[tuple[int, int, bytes]]
    ) -> list[tuple[int, int, bytes]]:
        """Constructs response items for each request in a batch."""
        responses: list[tuple[int, int, bytes]] = []
        for req_id, rpc_type, _ in requests:
            resp_body = self._resolve_response_body(service, rpc_type)
            responses.append((req_id, rpc_type, resp_body))
        return responses

    async def _dispatch_proto_frame(
        self, header_bytes: bytes, body_bytes: bytes
    ) -> bytes:
        """Processes Protocol Buffers-encoded wire frame."""
        client_hdr = ProtoCodec.decode_client_header(header_bytes)
        service = client_hdr.service.lower()
        if service == "userservice":
            return await self._dispatch_proto_userservice(client_hdr, body_bytes)
        batch_id, requests = ProtoCodec.decode_batch_request(body_bytes)
        print(f"[PROTO_DEBUG] service={service}, batch_id={batch_id}, req_count={len(requests)}", flush=True)
        for r_id, r_type, r_body in requests:
            print(f"[PROTO_DEBUG] -> req_id={r_id}, rpc_type={r_type}, body_len={len(r_body)}, hex={r_body[:32].hex()}", flush=True)
        responses = self._build_batch_responses(service, requests)
        res_hdr = ProtoCodec.encode_server_header(client_hdr)
        res_payload = ProtoCodec.encode_batch_response(batch_id, responses)
        return WireCodec.encode_frame(res_hdr, res_payload)

    async def dispatch_wire_frame(self, raw_frame: bytes) -> bytes:
        """Decodes binary wire frame into JSON or Protobuf payload."""
        header_bytes, body_bytes = WireCodec.decode_frame(raw_frame)
        if not header_bytes.startswith(b"{"):
            return await self._dispatch_proto_frame(header_bytes, body_bytes)
        return await self._dispatch_json_frame(header_bytes, body_bytes)
