"""Wire framing codec for SpaceApe socket gateway."""

from __future__ import annotations

import gzip
import io


class WireCodecError(Exception):
    """Raised when wire frame decoding or encoding fails."""


class WireCodec:
    """Encodes and decodes 4-byte prefixed packets with optional gzip body compression."""

    @staticmethod
    def decode_frame(raw_data: bytes) -> tuple[bytes, bytes]:
        """Decodes wire buffer into (header_bytes, body_bytes)."""
        if len(raw_data) < 8:
            raise WireCodecError(
                "Frame muito curto para conter cabeçalho de comprimento."
            )

        pkt_len = int.from_bytes(raw_data[:4], "big")
        if len(raw_data) < pkt_len + 4:
            raise WireCodecError(
                f"Pacote incompleto: esperado {pkt_len + 4}, recebido {len(raw_data)}"
            )

        header_len = int.from_bytes(raw_data[4:8], "big")
        header_end = 8 + header_len
        if len(raw_data) < header_end:
            raise WireCodecError("Comprimento de cabeçalho excede tamanho do pacote.")

        header_bytes = raw_data[8:header_end]
        body_bytes = raw_data[header_end : 4 + pkt_len]
        return header_bytes, body_bytes

    @staticmethod
    def encode_frame(
        header_bytes: bytes, body_bytes: bytes, compress_body: bool = False
    ) -> bytes:
        """Encodes (header_bytes, body_bytes) into prefixed wire frame."""
        final_body = body_bytes
        if compress_body and len(body_bytes) > 0:
            final_body = gzip.compress(body_bytes)

        header_len = len(header_bytes)
        body_len = len(final_body)
        pkt_len = 4 + header_len + body_len

        prefix = pkt_len.to_bytes(4, "big")
        hdr_prefix = header_len.to_bytes(4, "big")
        return prefix + hdr_prefix + header_bytes + final_body
