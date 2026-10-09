"""Low-level Raksha Protobuf wire codec for SpaceApe binary protocols."""

from __future__ import annotations

import struct
from typing import Any


class WireType:
    """Protobuf wire type constants matching SpaceApe WireType enum."""

    VARINT = 0
    FIXED64 = 1
    LENGTH_DELIMITED = 2
    START_GROUP = 3
    END_GROUP = 4
    FIXED32 = 5
    SIGNED_VARINT = 8


class ProtoReader:
    """Reads fields from a binary Protobuf/Raksha payload."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    @property
    def remaining(self) -> int:
        """Returns remaining unread bytes in buffer."""
        return len(self._data) - self._pos

    @property
    def has_more(self) -> bool:
        """Checks if reader has more bytes available."""
        return self._pos < len(self._data)

    def read_varint(self) -> int:
        """Decodes an unsigned varint from the stream."""
        result = 0
        shift = 0
        while True:
            if self._pos >= len(self._data):
                raise ValueError("Unexpected end of stream while reading varint")
            byte = self._data[self._pos]
            self._pos += 1
            result |= (byte & 0x7F) << shift
            shift += 7
            if not (byte & 0x80):
                break
        return result

    def read_svarint(self) -> int:
        """Decodes a zigzag-encoded signed varint."""
        val = self.read_varint()
        return (val >> 1) ^ (-(val & 1))

    def read_tag(self) -> tuple[int, int] | None:
        """Reads field number and wire type tag, or None if end of stream."""
        if not self.has_more:
            return None
        key = self.read_varint()
        field_number = key >> 3
        wire_type = key & 0x07
        return field_number, wire_type

    def read_fixed32_float(self) -> float:
        """Reads a 32-bit floating point number."""
        if self._pos + 4 > len(self._data):
            raise ValueError("Buffer underflow reading float32")
        val = struct.unpack("<f", self._data[self._pos : self._pos + 4])[0]
        self._pos += 4
        return val

    def read_fixed32_uint(self) -> int:
        """Reads a 32-bit unsigned integer."""
        if self._pos + 4 > len(self._data):
            raise ValueError("Buffer underflow reading uint32")
        val = struct.unpack("<I", self._data[self._pos : self._pos + 4])[0]
        self._pos += 4
        return val

    def read_fixed64_ulong(self) -> int:
        """Reads a 64-bit unsigned integer."""
        if self._pos + 8 > len(self._data):
            raise ValueError("Buffer underflow reading ulong64")
        val = struct.unpack("<Q", self._data[self._pos : self._pos + 8])[0]
        self._pos += 8
        return val

    def read_bytes(self) -> bytes:
        """Reads a length-delimited byte chunk."""
        length = self.read_varint()
        if self._pos + length > len(self._data):
            raise ValueError(f"Buffer underflow reading {length} bytes (have {self.remaining})")
        chunk = self._data[self._pos : self._pos + length]
        self._pos += length
        return chunk

    def read_string(self) -> str:
        """Reads a UTF-8 encoded length-delimited string."""
        raw = self.read_bytes()
        return raw.decode("utf-8", errors="replace")

    def skip_field(self, wire_type: int) -> None:
        """Skips a field according to its wire type."""
        if wire_type == WireType.VARINT:
            self.read_varint()
        elif wire_type == WireType.FIXED64:
            self._pos += 8
        elif wire_type == WireType.LENGTH_DELIMITED:
            length = self.read_varint()
            self._pos += length
        elif wire_type == WireType.FIXED32:
            self._pos += 4
        else:
            raise ValueError(f"Unsupported wire type to skip: {wire_type}")


class ProtoWriter:
    """Serializes fields into a binary Protobuf/Raksha payload."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def write_varint(self, value: int) -> None:
        """Encodes an unsigned integer as a varint."""
        if value < 0:
            value = (1 << 64) + value
        while True:
            byte = value & 0x7F
            value >>= 7
            if value > 0:
                self._buf.append(byte | 0x80)
            else:
                self._buf.append(byte)
                break

    def write_tag(self, field_number: int, wire_type: int) -> None:
        """Writes the field tag header."""
        key = (field_number << 3) | (wire_type & 0x07)
        self.write_varint(key)

    def write_varint_field(self, field_number: int, value: int) -> None:
        """Writes tag + varint value."""
        self.write_tag(field_number, WireType.VARINT)
        self.write_varint(value)

    def write_float_field(self, field_number: int, value: float) -> None:
        """Writes tag + 32-bit float value."""
        self.write_tag(field_number, WireType.FIXED32)
        self._buf.extend(struct.pack("<f", value))

    def write_bytes_field(self, field_number: int, value: bytes) -> None:
        """Writes tag + length-delimited byte chunk."""
        self.write_tag(field_number, WireType.LENGTH_DELIMITED)
        self.write_varint(len(value))
        self._buf.extend(value)

    def write_string_field(self, field_number: int, value: str) -> None:
        """Writes tag + length-delimited UTF-8 string."""
        self.write_bytes_field(field_number, value.encode("utf-8"))

    def to_bytes(self) -> bytes:
        """Returns the serialized payload bytes."""
        return bytes(self._buf)
