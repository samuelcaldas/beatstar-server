#!/usr/bin/env python3
"""Tool to patch Ad Unit IDs and metadata in Beatstar global-metadata.dat.

Allows replacing default ad units (AppLovin MAX / Google Mobile Ads) with custom IDs.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


class MetadataAdPatcher:
    """Replaces Ad Unit string literals in Unity global-metadata.dat."""

    ORIGINAL_REWARDED = b"6adcd39d323d305a"
    ORIGINAL_INTERSTITIAL = b"075af25fa8b87ff7"
    ORIGINAL_SOCKET_GATEWAY = b"socket-gateway.prod.flamingo.newbirds.net"

    def __init__(self, metadata_path: Path) -> None:
        self.metadata_path = metadata_path.resolve()

    def _read_metadata(self) -> bytearray:
        """Reads metadata file into a mutable bytearray."""
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.metadata_path}")
        with open(self.metadata_path, "rb") as f:
            return bytearray(f.read())

    def _update_string_literal_length(
        self, data: bytearray, target_idx: int, new_length: int
    ) -> None:
        """Updates string length field in Il2CppStringLiteral table."""
        str_data_offset = int.from_bytes(data[16:20], "little")
        rel_offset = target_idx - str_data_offset
        table_offset = int.from_bytes(data[8:12], "little")
        table_size = int.from_bytes(data[12:16], "little")
        for i in range(table_size // 8):
            entry_off = table_offset + i * 8
            data_idx = int.from_bytes(data[entry_off + 4 : entry_off + 8], "little")
            if data_idx == rel_offset:
                data[entry_off : entry_off + 4] = new_length.to_bytes(4, "little")
                return

    def _replace_socket_gateway_host(self, data: bytearray, new_host: str) -> int:
        """Replaces gateway host string literal and updates its length in header."""
        idx = data.find(self.ORIGINAL_SOCKET_GATEWAY)
        if idx == -1:
            return 0
        new_bytes = new_host.encode("utf-8")
        pad_len = len(self.ORIGINAL_SOCKET_GATEWAY)
        if len(new_bytes) > pad_len:
            return 0
        self._update_string_literal_length(data, idx, len(new_bytes))
        data[idx : idx + pad_len] = new_bytes.ljust(pad_len, b"\x00")
        return 1

    def _replace_string_literal(
        self, data: bytearray, old_bytes: bytes, new_bytes: bytes
    ) -> int:
        """Finds and replaces string literal in data section."""
        idx = data.find(old_bytes)
        if idx == -1:
            return 0
        pad_len = len(old_bytes)
        if len(new_bytes) <= pad_len:
            replacement = new_bytes.ljust(pad_len, b"\x00")
            data[idx : idx + pad_len] = replacement
            return 1
        return 0

    def patch(
        self,
        rewarded_id: str | None = None,
        interstitial_id: str | None = None,
        socket_gateway_host: str | None = None,
        output_path: Path | None = None,
    ) -> bool:
        """Applies ad unit and host replacements and writes updated metadata."""
        data = self._read_metadata()
        count = 0

        if rewarded_id:
            count += self._replace_string_literal(
                data, self.ORIGINAL_REWARDED, rewarded_id.encode("utf-8")
            )

        if interstitial_id:
            count += self._replace_string_literal(
                data, self.ORIGINAL_INTERSTITIAL, interstitial_id.encode("utf-8")
            )

        if socket_gateway_host:
            count += self._replace_socket_gateway_host(data, socket_gateway_host)

        target = (output_path or self.metadata_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        return count > 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch Beatstar Ad Unit IDs in Metadata")
    parser.add_argument("--metadata", type=Path, required=True, help="Path to global-metadata.dat")
    parser.add_argument("--output", type=Path, default=None, help="Output metadata path")
    parser.add_argument("--rewarded-id", type=str, default=None, help="Custom rewarded ad unit ID")
    parser.add_argument("--interstitial-id", type=str, default=None, help="Custom interstitial ad unit ID")
    args = parser.parse_args()

    patcher = MetadataAdPatcher(args.metadata)
    success = patcher.patch(
        rewarded_id=args.rewarded_id,
        interstitial_id=args.interstitial_id,
        output_path=args.output,
    )
    status = "sucesso" if success else "nenhum ID modificado"
    print(f"[*] Patching concluído com {status}.")


if __name__ == "__main__":
    main()
