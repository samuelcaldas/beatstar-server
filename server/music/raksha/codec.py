"""Bounded Raksha/Protobuf wire primitives; invalid input raises ValueError."""
from __future__ import annotations
import struct


class WireType:
    """Supported Protobuf wire types (groups are deliberately unsupported)."""
    VARINT = 0
    FIXED64 = 1
    LENGTH_DELIMITED = 2
    FIXED32 = 5


class ProtoReader:
    """Read bounded fields without advancing beyond the supplied payload."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    @property
    def remaining(self) -> int:
        """Return unread byte count."""
        return len(self._data) - self._pos

    @property
    def has_more(self) -> bool:
        """Return whether unread bytes remain."""
        return self.remaining > 0

    def take(self, length: int) -> bytes:
        """Consume exactly length bytes or reject a truncated field."""
        if length < 0 or length > self.remaining:
            raise ValueError("Truncated Raksha field")
        result = self._data[self._pos:self._pos + length]
        self._pos += length
        return result

    def read_varint(self) -> int:
        """Decode at most ten bytes as an unsigned 64-bit varint."""
        value = 0
        for index in range(10):
            byte = self.take(1)[0]
            if index == 9 and byte > 1:
                raise ValueError("Varint exceeds 64 bits")
            value |= (byte & 127) << (index * 7)
            if byte < 128:
                return value
        raise ValueError("Varint exceeds ten bytes")

    def read_svarint(self) -> int:
        """Decode a zigzag signed integer."""
        value = self.read_varint()
        return (value >> 1) ^ -(value & 1)

    def read_tag(self) -> tuple[int, int] | None:
        """Read a valid supported tag, or None only at the end of input."""
        if not self.has_more:
            return None
        key = self.read_varint()
        field_number, wire_type = key >> 3, key & 7
        if not 0 < field_number < (1 << 29) or wire_type not in (0, 1, 2, 5):
            raise ValueError("Invalid or unsupported wire tag")
        return field_number, wire_type

    def read_fixed32_float(self) -> float:
        """Read a little-endian float32."""
        return struct.unpack("<f", self.take(4))[0]

    def read_fixed32_uint(self) -> int:
        """Read a little-endian unsigned integer."""
        return struct.unpack("<I", self.take(4))[0]

    def read_fixed64_ulong(self) -> int:
        """Read a little-endian unsigned 64-bit integer."""
        return struct.unpack("<Q", self.take(8))[0]

    def read_bytes(self) -> bytes:
        """Read a length-delimited byte sequence."""
        return self.take(self.read_varint())

    def read_string(self) -> str:
        """Read strictly valid UTF-8; invalid text raises UnicodeDecodeError."""
        return self.read_bytes().decode("utf-8")

    def skip_field(self, wire_type: int) -> None:
        """Consume a supported field while validating its bounds."""
        if wire_type == WireType.VARINT:
            self.read_varint()
            return
        if wire_type == WireType.LENGTH_DELIMITED:
            self.read_bytes()
            return
        if wire_type in (WireType.FIXED32, WireType.FIXED64):
            self.take(4 if wire_type == WireType.FIXED32 else 8)
            return
        raise ValueError("Unsupported wire type")

    def capture_unknown(self, wire_type: int, start_remaining: int) -> bytes:
        """Consume an unknown field, retaining its original tag and value bytes."""
        self.skip_field(wire_type)
        return self._data[len(self._data) - start_remaining:self._pos]


class ProtoWriter:
    """Encode wire primitives and preserve opaque field bytes."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def write_raw(self, payload: bytes) -> None:
        """Append an already encoded payload."""
        self._buf.extend(payload)

    def write_varint(self, value: int) -> None:
        """Encode a bounded integer; signed values use 64-bit two's complement."""
        if not -(1 << 63) <= value < (1 << 64):
            raise ValueError("Integer exceeds wire width")
        value &= (1 << 64) - 1
        while value >= 128:
            self._buf.append((value & 127) | 128)
            value >>= 7
        self._buf.append(value)

    def write_tag(self, field_number: int, wire_type: int) -> None:
        """Write a validated wire tag."""
        if not 0 < field_number < (1 << 29) or wire_type not in (0, 1, 2, 5):
            raise ValueError("Invalid or unsupported wire tag")
        self.write_varint((field_number << 3) | wire_type)

    def write_varint_field(self, field_number: int, value: int) -> None:
        """Write a tag and integer."""
        self.write_tag(field_number, WireType.VARINT)
        self.write_varint(value)

    def write_float_field(self, field_number: int, value: float) -> None:
        """Write a tag and float32."""
        self.write_tag(field_number, WireType.FIXED32)
        self.write_raw(struct.pack("<f", value))

    def write_bytes_field(self, field_number: int, value: bytes) -> None:
        """Write a tag and length-delimited bytes."""
        self.write_tag(field_number, WireType.LENGTH_DELIMITED)
        self.write_varint(len(value))
        self.write_raw(value)

    def write_string_field(self, field_number: int, value: str) -> None:
        """Write a UTF-8 string field."""
        self.write_bytes_field(field_number, value.encode("utf-8"))

    def to_bytes(self) -> bytes:
        """Return the encoded payload."""
        return bytes(self._buf)
