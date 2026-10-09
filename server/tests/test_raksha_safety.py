"""Synthetic regressions for lossless chart editing and malformed wire input."""
import pytest
from server.music.raksha.codec import ProtoReader
from server.music.raksha.serializer import (
    decode_beatmap_interactions, encode_beatmap_interactions,
    decode_interaction_item, encode_interaction_item,
    decode_interaction_point, encode_interaction_point,
)
from server.music.raksha.beatmap_schema import BeatmapInteractionsTemplate, BeatmapStar


@pytest.mark.parametrize("payload", [b"\x0d", b"\x09", b"\x12\x05x", b"\x2a\x02\x05x"])
def test_truncated_chart_is_rejected(payload):
    with pytest.raises(ValueError):
        decode_beatmap_interactions(payload)


@pytest.mark.parametrize("payload", [b"\x00", b"\x0f", b"\x80" * 10 + b"\x00"])
def test_invalid_wire_tag_is_rejected(payload):
    with pytest.raises(ValueError):
        ProtoReader(payload).read_tag()


def test_unknown_item_fields_survive_edit():
    original = b"\x08\x01\x38\x09\x38\x0a"
    item = decode_interaction_item(original)
    assert encode_interaction_item(item) == original
    item.track = 3
    assert b"\x38\x09\x38\x0a" in encode_interaction_item(item)


def test_unknown_nested_point_fields_and_absent_defaults_survive():
    original = b"\x10\x7b\x18\x02"
    point = decode_interaction_point(original)
    assert encode_interaction_point(point) == original
    point.lane = 3
    assert b"\x10\x7b" in encode_interaction_point(point)


def test_repeated_trailing_sections_survive_id_edit():
    original = b"\x08\x01\x12\x01x\x2a\x00\x32\x01a\x32\x01b\x78\x09"
    chart = decode_beatmap_interactions(original)
    assert encode_beatmap_interactions(chart) == original
    chart.id = 2
    encoded = encode_beatmap_interactions(chart)
    assert b"\x32\x01a\x32\x01b\x78\x09" in encoded


def test_unverified_star_edits_are_rejected_not_silently_ignored():
    chart = BeatmapInteractionsTemplate(stars=[BeatmapStar(points_required=100)])
    with pytest.raises(ValueError, match="[Ss]tar"):
        encode_beatmap_interactions(chart)
