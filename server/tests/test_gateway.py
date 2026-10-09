"""Unit tests for wire codec, header parser, and response builder."""

import pytest
from server.gateway.header_parser import HeaderParser
from server.gateway.response_builder import ResponseBuilder
from server.gateway.wire_codec import WireCodec, WireCodecError
from server.models.headers import ClientHeader


def test_wire_codec_encode_and_decode_roundtrip():
    header_data = b'{"service":"userservice"}'
    body_data = b'{"type":7}'

    frame = WireCodec.encode_frame(header_data, body_data)
    assert len(frame) >= 8

    decoded_header, decoded_body = WireCodec.decode_frame(frame)
    assert decoded_header == header_data
    assert decoded_body == body_data


def test_wire_codec_too_short_raises_error():
    with pytest.raises(WireCodecError):
        WireCodec.decode_frame(b"short")


def test_header_parser_valid():
    raw = {"service": "cmsservice", "version": "36.1.4.9545", "rpcthing": "rpc-123"}
    hdr = HeaderParser.parse_dict(raw)
    assert hdr.service == "cmsservice"
    assert hdr.rpcthing == "rpc-123"


def test_response_builder():
    client_hdr = ClientHeader(service="userservice", rpcthing="rpc-456")
    resp_hdr = ResponseBuilder.build_success_header(client_hdr, token_id="token-abc")
    assert resp_hdr.status == 200
    assert resp_hdr.rpcthing == "rpc-456"
    assert resp_hdr.tokenid == "token-abc"
