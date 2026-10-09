"""Retain opaque wire sections; byte roundtrip is not native compatibility."""
from pydantic import BaseModel, Field, PrivateAttr


class PreservedModel(BaseModel):
    """Carry unknown fields and original encoding alongside understood fields."""
    raw_fields: list[bytes] = Field(default_factory=list, repr=False)
    _source: bytes | None = PrivateAttr(default=None)
    _baseline: bytes | None = PrivateAttr(default=None)

    def remember(self, source: bytes, canonical: bytes):
        """Remember original bytes and canonical state for unchanged roundtrips."""
        self._source = source
        self._baseline = canonical
        return self

    def encode_preserved(self, canonical: bytes) -> bytes:
        """Return original bytes if unchanged, otherwise canonical plus unknowns."""
        complete = canonical + b"".join(self.raw_fields)
        if self._source is not None and complete == self._baseline:
            return self._source
        return complete
