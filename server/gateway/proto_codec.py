"""Protobuf wire codec for SpaceApe binary socket traffic."""

from __future__ import annotations

import time
from typing import Any
from server.models.headers import ClientHeader, ServerHeader


class ProtoWire:
    """Low-level Protocol Buffers wire format serializer and deserializer."""

    @staticmethod
    def encode_varint(value: int) -> bytes:
        buf = bytearray()
        val = value
        while val >= 0x80:
            buf.append((val & 0x7F) | 0x80)
            val >>= 7
        buf.append(val & 0x7F)
        return bytes(buf)

    @staticmethod
    def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
        result, shift, idx = 0, 0, offset
        while idx < len(data):
            b = data[idx]
            idx += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result, idx
            shift += 7
        return result, idx

    @classmethod
    def encode_field(cls, tag: int, wire: int, payload: bytes) -> bytes:
        header = cls.encode_varint((tag << 3) | wire)
        return header + payload

    @classmethod
    def encode_int(cls, tag: int, val: int) -> bytes:
        return cls.encode_field(tag, 0, cls.encode_varint(val))

    @classmethod
    def encode_str(cls, tag: int, val: str) -> bytes:
        raw = val.encode("utf-8")
        return cls.encode_field(tag, 2, cls.encode_varint(len(raw)) + raw)

    @classmethod
    def encode_msg(cls, tag: int, raw: bytes) -> bytes:
        return cls.encode_field(tag, 2, cls.encode_varint(len(raw)) + raw)

    @classmethod
    def decode_fields_list(cls, data: bytes) -> list[tuple[int, int, Any]]:
        """Decodes raw protobuf buffer into list of (tag, wire, value)."""
        entries: list[tuple[int, int, Any]] = []
        idx = 0
        while idx < len(data):
            key, idx = cls.decode_varint(data, idx)
            tag, wire = key >> 3, key & 7
            if wire == 0:
                val, idx = cls.decode_varint(data, idx)
                entries.append((tag, wire, val))
                continue
            if wire == 2:
                length, idx = cls.decode_varint(data, idx)
                entries.append((tag, wire, data[idx : idx + length]))
                idx += length
                continue
            break
        return entries

    @classmethod
    def decode_dict(cls, data: bytes) -> dict[int, Any]:
        """Decodes raw protobuf buffer into dictionary of tags."""
        fields: dict[int, Any] = {}
        for tag, _, val in cls.decode_fields_list(data):
            fields[tag] = val
        return fields


class ProtoCodec:
    """High-level SpaceApe RPC protobuf header and payload codec."""

    @classmethod
    def decode_client_header(cls, raw: bytes) -> ClientHeader:
        """Parses ClientServerMessageHeader protobuf into ClientHeader model."""
        fields = ProtoWire.decode_dict(raw)
        ver = fields.get(1, b"").decode("utf-8", errors="ignore")
        svc = fields.get(2, b"").decode("utf-8", errors="ignore")
        rpc = fields.get(3, b"").decode("utf-8", errors="ignore")
        return ClientHeader(
            version=ver or "36.1.4.9545",
            service=svc or "userservice",
            rpcthing=rpc or "rpc-0",
            supports_compression=bool(fields.get(6, 0)),
        )

    @classmethod
    def encode_server_header(cls, client_header: ClientHeader) -> bytes:
        """Serializes ServerClientMessageHeader with GW_OK (1) status mirroring rpcthing."""
        now_ms = int(time.time() * 1000)
        parts = [
            ProtoWire.encode_str(1, client_header.version),
            ProtoWire.encode_int(2, now_ms),
            ProtoWire.encode_str(3, client_header.rpcthing),
            ProtoWire.encode_int(5, 1),
            ProtoWire.encode_str(10, client_header.service),
        ]
        return b"".join(parts)

    @classmethod
    def decode_batch_request(
        cls, body_bytes: bytes
    ) -> tuple[int, list[tuple[int, int, bytes]]]:
        """Parses BatchRequest returning batch_id and list of (req_id, rpc_type, req_body)."""
        entries = ProtoWire.decode_fields_list(body_bytes)
        batch_id = 1
        requests: list[tuple[int, int, bytes]] = []
        for tag, wire, val in entries:
            if tag == 1 and wire == 0:
                batch_id = int(val)
                continue
            if tag == 5 and wire == 2 and isinstance(val, (bytes, bytearray)):
                req_fields = ProtoWire.decode_dict(val)
                req_id = int(req_fields.get(1, 1))
                rpc_type = int(req_fields.get(3, 1))
                req_body = req_fields.get(4, b"")
                requests.append((req_id, rpc_type, req_body))
        if not requests:
            requests.append((1, 1, b""))
        return batch_id, requests

    @classmethod
    def encode_batch_response(
        cls, batch_id: int, responses: list[tuple[int, int, bytes]]
    ) -> bytes:
        """Serializes standard BatchResponse acknowledging client requests."""
        now_ms = int(time.time() * 1000)
        parts = [
            ProtoWire.encode_int(1, batch_id),
            ProtoWire.encode_int(2, now_ms),
        ]
        for req_id, rpc_type, body_data in responses:
            resp_payload = b"".join([
                ProtoWire.encode_int(1, req_id),
                ProtoWire.encode_int(3, rpc_type),
                ProtoWire.encode_msg(5, body_data),
            ])
            parts.append(ProtoWire.encode_msg(5, resp_payload))
        return b"".join(parts)

    @classmethod
    def encode_sharpla_response(cls, save_count: int = 1) -> bytes:
        """Serializes ExecuteSharplaBatchResp with status Ok (1)."""
        return b"".join([
            ProtoWire.encode_int(1, 1),
            ProtoWire.encode_str(2, ""),
            ProtoWire.encode_int(3, save_count),
        ])

    @classmethod
    def encode_sync_response(cls, player_name: str = "Player") -> bytes:
        """Serializes SyncResp containing MyProfileTO with IL2CPP Raksha tags."""
        camp_bytes = b"".join([
            ProtoWire.encode_str(1, "US"),
            ProtoWire.encode_str(2, "default"),
        ])
        loc_bytes = ProtoWire.encode_msg(1, camp_bytes)
        profile_parts = [
            ProtoWire.encode_str(4, player_name),
            ProtoWire.encode_msg(5, b""),
            ProtoWire.encode_msg(11, b""),
            ProtoWire.encode_msg(14, b""),
            ProtoWire.encode_msg(36, b""),
            ProtoWire.encode_msg(52, b""),
            ProtoWire.encode_int(55, 1),
            ProtoWire.encode_msg(58, b""),
            ProtoWire.encode_msg(59, b""),
            ProtoWire.encode_msg(60, b""),
            ProtoWire.encode_msg(61, b""),
            ProtoWire.encode_msg(64, b""),
            ProtoWire.encode_msg(69, b""),
            ProtoWire.encode_msg(70, b""),
            ProtoWire.encode_msg(75, b""),
            ProtoWire.encode_msg(77, b""),
            ProtoWire.encode_msg(79, b""),
            ProtoWire.encode_msg(80, b""),
            ProtoWire.encode_msg(82, loc_bytes),
            ProtoWire.encode_msg(89, b""),
            ProtoWire.encode_msg(90, b""),
            ProtoWire.encode_msg(91, b""),
            ProtoWire.encode_msg(92, b""),
            ProtoWire.encode_msg(96, b""),
            ProtoWire.encode_msg(97, b""),
        ]
        profile_bytes = b"".join(profile_parts)
        return b"".join([
            ProtoWire.encode_msg(7, profile_bytes),
            ProtoWire.encode_int(8, 0),
            ProtoWire.encode_int(9, 0),
        ])

    @classmethod
    def decode_user_request(cls, body_bytes: bytes) -> dict[str, Any]:
        """Parses userservice BaseReq for AllInOneLogin."""
        fields = ProtoWire.decode_dict(body_bytes)
        req_id = fields.get(1, 1)
        req_type = fields.get(2, 7)
        login_bytes = fields.get(112, b"")
        login_fields = ProtoWire.decode_dict(login_bytes) if login_bytes else {}
        cinta = login_fields.get(4, b"").decode("utf-8", errors="ignore")
        return {
            "id": req_id,
            "type": req_type,
            "all_in_one_login": {"cinta": cinta or None},
        }

    @classmethod
    def encode_user_response(
        cls, req_id: int, ticket: str, clide: str, cinta: str
    ) -> bytes:
        """Serializes userservice BaseResp containing RespAllInOneLogin."""
        expiry = int(time.time() * 1000) + 86400000 * 30
        login_payload = b"".join([
            ProtoWire.encode_str(1, ticket),
            ProtoWire.encode_str(2, clide),
            ProtoWire.encode_int(3, expiry),
            ProtoWire.encode_str(4, cinta),
        ])
        return b"".join([
            ProtoWire.encode_int(1, req_id),
            ProtoWire.encode_int(2, 7),
            ProtoWire.encode_int(3, 200),
            ProtoWire.encode_str(7, clide),
            ProtoWire.encode_msg(112, login_payload),
        ])
