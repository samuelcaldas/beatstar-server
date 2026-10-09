"""Untrusted serialized TextAsset and output-lifecycle regression tests."""
import struct
import pytest
from scripts.extract_baked_assets import parse_text_asset_payload, extract_assets


def serialized_asset(name, payload=b"BKHDtest"):
    encoded = name.encode()
    return struct.pack("<I", len(encoded)) + encoded + b"\0" * (-len(encoded) % 4) + struct.pack("<I", len(payload)) + payload


@pytest.mark.parametrize("name", ["../../outside", "/absolute", "..\\outside", "", ".", ".."])
def test_asset_names_cannot_control_output_paths(name):
    with pytest.raises(ValueError):
        parse_text_asset_payload(serialized_asset(name))


def test_short_payload_is_not_silently_accepted():
    with pytest.raises(ValueError):
        parse_text_asset_payload(serialized_asset("safe")[:-3])


def test_missing_source_does_not_publish_a_success_catalog(tmp_path):
    output = tmp_path / "result"
    with pytest.raises(ValueError):
        extract_assets(tmp_path / "missing", output)
    assert not output.exists()


def test_existing_output_is_never_overwritten(tmp_path):
    output = tmp_path / "result"
    output.mkdir()
    (output / "keep").write_bytes(b"original")
    with pytest.raises(ValueError):
        extract_assets(tmp_path / "missing", output)
    assert (output / "keep").read_bytes() == b"original"


def test_directory_budget_stops_consuming_entries(tmp_path, monkeypatch):
    from scripts.extract_baked_assets import validate_source

    def endless_entries(self, pattern):
        for _ in range(4097):
            yield tmp_path
        raise AssertionError("Traversal continued past the entry budget")

    monkeypatch.setattr(type(tmp_path), "rglob", endless_entries)
    with pytest.raises(ValueError, match="entry limit"):
        validate_source(tmp_path, tmp_path / "output")


def test_nonregular_input_is_rejected_before_parsing(tmp_path):
    import os
    from scripts.extract_baked_assets import validate_source

    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(ValueError, match="non-regular"):
        validate_source(tmp_path, tmp_path / "output")
