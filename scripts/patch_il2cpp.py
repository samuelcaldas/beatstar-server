#!/usr/bin/env python3
"""Binary patcher for Beatstar libil2cpp.so ARM64 library.

Patches default port and SSL configuration in AppConfig.GenerateDefaultEndPointConfig.
"""

from __future__ import annotations

import argparse
from pathlib import Path


class Il2CppBinaryPatcher:
    """Patches ARM64 instructions in libil2cpp.so to change default port and protocol."""

    TARGET_OFFSETS = (0x1A334B0, 0x1A33690)
    VIDEO_ADS_OFFSET = 0x1A326E8
    VIDEO_ADS_EXPECTED = bytes.fromhex("760300b4")
    VIDEO_ADS_REPLACEMENT = bytes.fromhex("360200b4")
    DOWNLOAD_COMPLETE_OFFSET = 0x19C141C
    DOWNLOAD_COMPLETE_EXPECTED = bytes.fromhex("c0f90736")
    DOWNLOAD_COMPLETE_REPLACEMENT = bytes.fromhex("1f2003d5")
    OPCODE_MOV_W2_MASK = 0xFFE0001F
    OPCODE_MOV_W2_BASE = 0x52800002

    def __init__(self, so_path: Path) -> None:
        self.so_path = so_path.resolve()

    def _read_binary(self) -> bytearray:
        """Loads shared object into mutable bytearray."""
        if not self.so_path.exists():
            raise FileNotFoundError(f"Biblioteca não encontrada: {self.so_path}")
        with open(self.so_path, "rb") as input_file:
            return bytearray(input_file.read())

    def _assert_target_instruction(self, data: bytearray, offset: int) -> None:
        """Guards against invalid binary version or corrupted offset."""
        current = bytes(data[offset : offset + 4])
        val = int.from_bytes(current, byteorder="little")
        if (val & self.OPCODE_MOV_W2_MASK) != self.OPCODE_MOV_W2_BASE:
            raise ValueError(f"Assinatura inesperada em {hex(offset)}: {current.hex()}")

    def _apply_port_patches(self, data: bytearray, port: int) -> None:
        """Applies MOV W2, #port replacement."""
        replacement = self.encode_mov_w2(port)
        for offset in self.TARGET_OFFSETS:
            self._assert_target_instruction(data, offset)
            data[offset : offset + 4] = replacement

    def _apply_video_ads_patch(self, data: bytearray) -> None:
        """Bypasses null check crash when video ads profile is unconfigured."""
        current = bytes(data[self.VIDEO_ADS_OFFSET : self.VIDEO_ADS_OFFSET + 4])
        if current != self.VIDEO_ADS_EXPECTED:
            return
        data[self.VIDEO_ADS_OFFSET : self.VIDEO_ADS_OFFSET + 4] = self.VIDEO_ADS_REPLACEMENT

    def _apply_download_complete_patch(self, data: bytearray) -> None:
        """Bypasses download wait in SongSelectDataDownloadScreen."""
        current = bytes(data[self.DOWNLOAD_COMPLETE_OFFSET : self.DOWNLOAD_COMPLETE_OFFSET + 4])
        if current != self.DOWNLOAD_COMPLETE_EXPECTED:
            return
        data[self.DOWNLOAD_COMPLETE_OFFSET : self.DOWNLOAD_COMPLETE_OFFSET + 4] = self.DOWNLOAD_COMPLETE_REPLACEMENT

    def _write_binary(self, data: bytearray, output_path: Path | None) -> None:
        """Persists patched bytes to destination file."""
        dest = (output_path or self.so_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as output_file:
            output_file.write(data)

    def patch_port(self, port: int = 9099, output_path: Path | None = None) -> bool:
        """Applies port, ads, and download patches to the binary."""
        data = self._read_binary()
        self._apply_port_patches(data, port)
        self._apply_video_ads_patch(data)
        self._apply_download_complete_patch(data)
        self._write_binary(data, output_path)
        return True

    @staticmethod
    def encode_mov_w2(port: int) -> bytes:
        """Encodes ARM64 MOVZ W2, #imm16 instruction."""
        opcode = 0x52800000 | ((port & 0xFFFF) << 5) | 2
        return opcode.to_bytes(4, byteorder="little")


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch libil2cpp.so default port")
    parser.add_argument("--so", type=Path, required=True, help="Path to libil2cpp.so")
    parser.add_argument("--port", type=int, default=9090, help="New port number")
    parser.add_argument("--output", type=Path, default=None, help="Output file path")
    args = parser.parse_args()

    patcher = Il2CppBinaryPatcher(args.so)
    patcher.patch_port(port=args.port, output_path=args.output)
    print(f"[✓] libil2cpp.so patched com sucesso para porta {args.port}!")


if __name__ == "__main__":
    main()
