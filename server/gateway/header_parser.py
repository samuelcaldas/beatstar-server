"""Parser and validator for client request headers."""

from __future__ import annotations

import json
from server.models.headers import ClientHeader


class HeaderParser:
    """Parses and validates client request headers."""

    @staticmethod
    def parse_dict(data: dict) -> ClientHeader:
        """Parses dictionary into validated ClientHeader."""
        if not isinstance(data, dict):
            raise ValueError("Cabeçalho deve ser um dicionário.")
        return ClientHeader.model_validate(data)

    @staticmethod
    def parse_json(raw_json: bytes | str) -> ClientHeader:
        """Parses JSON bytes into validated ClientHeader."""
        data = json.loads(raw_json)
        return HeaderParser.parse_dict(data)
