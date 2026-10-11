"""Unit tests for TcpSocketGatewayServer binary framing and RPC processing."""

from __future__ import annotations

import asyncio
import json
import logging
import pytest
from server.gateway.wire_codec import WireCodec
from server.gateway.dispatcher import GatewayDispatcher
from server.gateway.tcp_listener import TcpSocketGatewayServer
from server.storage.database import DatabaseManager


@pytest.mark.asyncio
async def test_tcp_socket_gateway_handles_wire_frame(tmp_path):
    """Validates raw binary TCP socket client connection and roundtrip frame processing."""
    db_file = str(tmp_path / "test.db")
    db = DatabaseManager(db_file)
    await db.initialize()
    dispatcher = GatewayDispatcher(db)

    test_port = 19090
    server = TcpSocketGatewayServer(dispatcher=dispatcher, host="127.0.0.1", port=test_port)
    await server.start()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", test_port)

        hdr_dict = {
            "service": "userservice",
            "version": "36.1.4.9545",
            "rpcthing": "rpc-tcp-test",
            "authenticationTicket": "",
            "clide": "",
        }
        body_dict = {
            "id": 1,
            "type": 7,
            "all_in_one_login": {"cinta": "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905"},
        }

        req_frame = WireCodec.encode_frame(
            json.dumps(hdr_dict).encode("utf-8"),
            json.dumps(body_dict).encode("utf-8"),
        )
        writer.write(req_frame)
        await writer.drain()

        resp_len_bytes = await reader.readexactly(4)
        payload_len = int.from_bytes(resp_len_bytes, "big")
        resp_payload_bytes = await reader.readexactly(payload_len)
        full_resp_frame = resp_len_bytes + resp_payload_bytes

        res_hdr_bytes, res_body_bytes = WireCodec.decode_frame(full_resp_frame)
        res_hdr = json.loads(res_hdr_bytes.decode("utf-8"))
        res_body = json.loads(res_body_bytes.decode("utf-8"))

        assert res_hdr["status"] == 200
        assert res_body["status"] == 200
        assert "authenticationTicket" in res_body["resp_login_of_some_type"]

        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_tcp_socket_gateway_handles_protobuf_wire_frame(tmp_path):
    """Validates real-device protobuf wire frame reception and response generation."""
    db_file = str(tmp_path / "test_proto.db")
    db = DatabaseManager(db_file)
    await db.initialize()
    dispatcher = GatewayDispatcher(db)

    test_port = 19091
    server = TcpSocketGatewayServer(dispatcher=dispatcher, host="127.0.0.1", port=test_port)
    await server.start()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
        hdr_bytes = bytes.fromhex(
            "0a0b33362e312e342e39353435120b75736572736572766963651a0c7270632d332d32323932373330013802"
        )
        body_bytes = bytes.fromhex(
            "080110073a0b33362e312e342e393534355899f7e5939234820700"
        )
        req_frame = WireCodec.encode_frame(hdr_bytes, body_bytes)
        writer.write(req_frame)
        await writer.drain()

        resp_len_bytes = await reader.readexactly(4)
        payload_len = int.from_bytes(resp_len_bytes, "big")
        resp_payload_bytes = await reader.readexactly(payload_len)
        full_resp_frame = resp_len_bytes + resp_payload_bytes

        res_hdr_bytes, res_body_bytes = WireCodec.decode_frame(full_resp_frame)
        from server.gateway.proto_codec import ProtoWire
        res_hdr_dict = ProtoWire.decode_dict(res_hdr_bytes)
        res_body_dict = ProtoWire.decode_dict(res_body_bytes)

        assert res_hdr_dict[1] == b"36.1.4.9545"
        assert res_hdr_dict[5] == 1  # GW_OK
        assert res_hdr_dict[10] == b"userservice"
        assert res_body_dict[1] == 1  # req_id
        assert res_body_dict[2] == 7  # AllInOneLogin
        assert 112 in res_body_dict  # respAllInOneLogin

        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_tcp_socket_gateway_logs_rpc_summary_without_payloads(
    tmp_path, capsys, caplog
):
    """Validates CMS BatchRequest processing and BatchResponse generation."""
    db_file = str(tmp_path / "test_batch.db")
    db = DatabaseManager(db_file)
    await db.initialize()
    dispatcher = GatewayDispatcher(db)
    caplog.set_level(logging.INFO, logger="beatstar.dispatcher")

    test_port = 19092
    server = TcpSocketGatewayServer(dispatcher=dispatcher, host="127.0.0.1", port=test_port)
    await server.start()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
        hdr_bytes = bytes.fromhex(
            "0a0b33362e312e342e39353435120a636d73736572766963651a0c7270632d322d333032353232"
        )
        from server.gateway.proto_codec import ProtoWire
        sensitive_marker = "sensitive-test-token"
        req_item = b"".join([
            ProtoWire.encode_int(1, 1),
            ProtoWire.encode_int(3, 1),
            ProtoWire.encode_str(4, sensitive_marker),
        ])
        body_bytes = b"".join([
            ProtoWire.encode_int(1, 2),
            ProtoWire.encode_msg(5, req_item),
        ])
        req_frame = WireCodec.encode_frame(hdr_bytes, body_bytes)
        writer.write(req_frame)
        await writer.drain()

        resp_len_bytes = await reader.readexactly(4)
        payload_len = int.from_bytes(resp_len_bytes, "big")
        resp_payload_bytes = await reader.readexactly(payload_len)
        full_resp_frame = resp_len_bytes + resp_payload_bytes

        _, res_body_bytes = WireCodec.decode_frame(full_resp_frame)
        res_body_dict = ProtoWire.decode_dict(res_body_bytes)

        assert res_body_dict[1] == 2  # batch_id
        assert 5 in res_body_dict  # responses

        resp_item_dict = ProtoWire.decode_dict(res_body_dict[5])
        assert resp_item_dict[1] == 1  # req_id matches 1
        assert resp_item_dict[3] == 1  # rpc_type matches 1

        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()

    captured = capsys.readouterr()
    assert sensitive_marker.encode().hex() not in captured.out
    assert "service=cmsservice" in caplog.text
    assert "request_types=(1,)" in caplog.text
    assert sensitive_marker not in caplog.text


def test_cms_response_uses_string_fields_for_all_tags():
    """Verifies CMSMetaInfo response encoding uses wire type 2 (string) for every field.

    The Raksha Protobuf runtime calls ReadString() for tag 4 (variant).
    Previously tag 4 was encoded as varint (wire type 0 = int), which caused
    'bad wire' and PROBLEM (-2) on the Android client.
    """
    from server.gateway.proto_codec import ProtoCodec, ProtoWire

    resource = {
        "name": "GameConfig",
        "version_str": "36.1.4.9545-baked",
        "hash": "a3f0955c0b89838553709abed1d3c96c",
        "variant": "",
        "url": "",
    }
    item_bytes = ProtoCodec.encode_cms_resource_item(resource)
    fields = ProtoWire.decode_fields_list(item_bytes)

    # All five fields must be wire type 2 (length-delimited / string)
    for tag, wire, val in fields:
        assert wire == 2, f"tag {tag} has wire type {wire}, expected 2 (string)"

    decoded = ProtoWire.decode_dict(item_bytes)
    assert decoded[1] == b"GameConfig"
    assert decoded[2] == b"36.1.4.9545-baked"
    assert decoded[3] == b"a3f0955c0b89838553709abed1d3c96c"
    assert decoded[4] == b""   # variant
    assert decoded[5] == b""   # url


def test_cms_response_includes_variant_from_client_request():
    """Verifies that client-supplied variant (e.g. 'en') round-trips through merge."""
    from server.gateway.proto_codec import ProtoCodec, ProtoWire

    client_items = {
        "LangConfig": {"version": "36.1.4.9545-baked", "hash": "abc123", "variant": "en"},
    }
    server_resources = [
        {"name": "LangConfig", "url": "", "hash": "abc123", "version": "36.1.4.9545-baked"},
    ]
    merged = ProtoCodec.merge_cms_resources(server_resources, client_items)
    assert len(merged) == 1
    assert merged[0]["variant"] == "en"
    assert merged[0]["version_str"] == "36.1.4.9545-baked"

    item_bytes = ProtoCodec.encode_cms_resource_item(merged[0])
    decoded = ProtoWire.decode_dict(item_bytes)
    assert decoded[4] == b"en"


def test_cms_http_urls_are_echo_hashed_not_served():
    """HTTP asset URLs must never be served to the client.

    Unity 2022.x raises InvalidOperationException: Insecure connection not
    allowed for any HTTP UnityWebRequest regardless of Android network security
    config, producing PROBLEM (916966628).  The server must echo the client's
    own hash and return an empty URL so the client skips the download entirely.
    """
    from server.gateway.proto_codec import ProtoCodec

    client_items = {
        "SongConfig": {"version": "36.1.4.9545-baked", "hash": "deadbeef00", "variant": ""},
        "BeatmapsConfig": {"version": "36.1.4.9545-baked", "hash": "cafebabe11", "variant": ""},
    }
    server_resources = [
        # HTTP URLs — must be downgraded to hash-echo regardless of having a real binary
        {"name": "SongConfig", "url": "http://192.168.1.68:8080/assets/configs/SongConfig.bin",
         "hash": "serverside_hash_abc", "version": "36.1.4.9545-baked"},
        {"name": "BeatmapsConfig", "url": "http://192.168.1.68:8080/assets/configs/BeatmapsConfig.bin",
         "hash": "serverside_hash_def", "version": "36.1.4.9545-baked"},
    ]
    merged = ProtoCodec.merge_cms_resources(server_resources, client_items)

    for entry in merged:
        assert entry["url"] == "", (
            f"{entry['name']}: HTTP URL must be replaced with empty string, got {entry['url']!r}"
        )
        assert "_has_binary" not in entry, (
            f"{entry['name']}: must not be flagged as real binary when URL is HTTP"
        )

    # Hashes must be the client's own (echo strategy)
    song = next(e for e in merged if e["name"] == "SongConfig")
    assert song["hash"] == "deadbeef00", "SongConfig hash must echo client value"

    beats = next(e for e in merged if e["name"] == "BeatmapsConfig")
    assert beats["hash"] == "cafebabe11", "BeatmapsConfig hash must echo client value"


def test_cms_https_urls_are_served_with_server_hash():
    """HTTPS asset URLs are safe to serve; the client will download from them."""
    from server.gateway.proto_codec import ProtoCodec

    client_items = {
        "SongConfig": {"version": "36.1.4.9545-baked", "hash": "aabbccdd00112233", "variant": ""},
    }
    server_resources = [
        {"name": "SongConfig",
         "url": "https://assets.example.com/SongConfig.bin",
         # Real MD5-like hex — must NOT contain the substring "hash_" (that marks synthetics)
         "hash": "a3f0955c0b89838553709abed1d3c96c",
         "version": "36.1.4.9545-baked"},
    ]
    merged = ProtoCodec.merge_cms_resources(server_resources, client_items)
    assert len(merged) == 1
    entry = merged[0]
    assert entry["url"] == "https://assets.example.com/SongConfig.bin"
    assert entry["hash"] == "a3f0955c0b89838553709abed1d3c96c"
    assert entry.get("_has_binary") is True


def test_encode_sync_response_structure():
    """Validates SyncResp and MyProfileTO serialization wire tags."""
    from server.gateway.proto_codec import ProtoCodec, ProtoWire

    sync_bytes = ProtoCodec.encode_sync_response("BeatstarTester")
    sync_fields = ProtoWire.decode_dict(sync_bytes)

    assert 7 in sync_fields  # profile tag
    assert sync_fields[9] == 0  # playerHubStatus

    profile_bytes = sync_fields[7]
    profile_fields = ProtoWire.decode_dict(profile_bytes)
    assert profile_fields[4] == b"BeatstarTester"  # name tag
    assert profile_fields[55] == 1  # version tag
    assert 82 in profile_fields  # location tag

    loc_fields = ProtoWire.decode_dict(profile_fields[82])
    assert 1 in loc_fields  # activeLocalisedCampaignData tag
    camp_fields = ProtoWire.decode_dict(loc_fields[1])
    assert camp_fields[1] == b"US"

