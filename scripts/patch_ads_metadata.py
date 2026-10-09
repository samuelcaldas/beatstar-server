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

    def __init__(self, metadata_path: Path) -> None:
        self.metadata_path = metadata_path.resolve()

    def _read_metadata(self) -> bytearray:
        """Reads metadata file into a mutable bytearray."""
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.metadata_path}")
        with open(self.metadata_path, "rb") as f:
            return bytearray(f.read())

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
        output_path: Path | None = None,
    ) -> bool:
        """Applies ad unit replacements and writes updated metadata."""
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
