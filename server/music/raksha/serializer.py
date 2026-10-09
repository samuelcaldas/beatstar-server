"""High-level serializer and deserializer for Beatstar Raksha charts."""

from __future__ import annotations

from server.music.raksha.beatmap_schema import (
    BeatmapInteractionsTemplate,
    BeatmapStar,
    DragInteractionData,
    FlickDirection,
    InteractionData,
    InteractionPoint,
    InteractionType,
    TapInteractionData,
)
from server.music.raksha.codec import ProtoReader, ProtoWriter, WireType


def decode_interaction_point(data: bytes) -> InteractionPoint:
    """Decodes a single spatial/temporal InteractionPoint."""
    reader = ProtoReader(data)
    point = InteractionPoint()
    while reader.has_more:
        tag_info = reader.read_tag()
        if not tag_info:
            break
        field_num, wire_type = tag_info
        if field_num == 1 and wire_type == WireType.FIXED32:
            point.beat_offset = reader.read_fixed32_float()
        elif field_num == 3 and wire_type == WireType.VARINT:
            point.lane = reader.read_varint()
        else:
            reader.skip_field(wire_type)
    return point


def encode_interaction_point(point: InteractionPoint) -> bytes:
    """Encodes an InteractionPoint into Raksha protobuf bytes."""
    writer = ProtoWriter()
    writer.write_float_field(1, point.beat_offset)
    writer.write_varint_field(3, point.lane)
    return writer.to_bytes()


def decode_tap_interaction(data: bytes) -> TapInteractionData:
    """Decodes TapInteractionData payload."""
    reader = ProtoReader(data)
    tap = TapInteractionData()
    while reader.has_more:
        tag_info = reader.read_tag()
        if not tag_info:
            break
        field_num, wire_type = tag_info
        if field_num == 1 and wire_type == WireType.LENGTH_DELIMITED:
            tap.point = decode_interaction_point(reader.read_bytes())
        elif field_num == 2 and wire_type == WireType.VARINT:
            tap.flick = FlickDirection(reader.read_varint())
        else:
            reader.skip_field(wire_type)
    return tap


def encode_tap_interaction(tap: TapInteractionData) -> bytes:
    """Encodes TapInteractionData into binary bytes."""
    writer = ProtoWriter()
    writer.write_bytes_field(1, encode_interaction_point(tap.point))
    if tap.flick != FlickDirection.NONE:
        writer.write_varint_field(2, int(tap.flick))
    return writer.to_bytes()


def decode_drag_interaction(data: bytes) -> DragInteractionData:
    """Decodes DragInteractionData payload."""
    reader = ProtoReader(data)
    drag = DragInteractionData()
    while reader.has_more:
        tag_info = reader.read_tag()
        if not tag_info:
            break
        field_num, wire_type = tag_info
        if field_num == 1 and wire_type == WireType.LENGTH_DELIMITED:
            drag.points.append(decode_interaction_point(reader.read_bytes()))
        elif field_num == 2 and wire_type == WireType.VARINT:
            drag.flick = FlickDirection(reader.read_varint())
        else:
            reader.skip_field(wire_type)
    return drag


def encode_drag_interaction(drag: DragInteractionData) -> bytes:
    """Encodes DragInteractionData into binary bytes."""
    writer = ProtoWriter()
    for pt in drag.points:
        writer.write_bytes_field(1, encode_interaction_point(pt))
    if drag.flick != FlickDirection.NONE:
        writer.write_varint_field(2, int(drag.flick))
    return writer.to_bytes()


def decode_interaction_item(data: bytes) -> InteractionData:
    """Decodes a single playable note item."""
    reader = ProtoReader(data)
    item = InteractionData()
    while reader.has_more:
        tag_info = reader.read_tag()
        if not tag_info:
            break
        field_num, wire_type = tag_info
        if field_num == 1 and wire_type == WireType.VARINT:
            item.interaction_type = InteractionType(reader.read_varint())
        elif field_num == 3 and wire_type == WireType.LENGTH_DELIMITED:
            item.tap_data = decode_tap_interaction(reader.read_bytes())
        elif field_num == 4 and wire_type == WireType.LENGTH_DELIMITED:
            item.drag_data = decode_drag_interaction(reader.read_bytes())
        elif field_num == 6 and wire_type == WireType.VARINT:
            item.track = reader.read_varint()
        else:
            reader.skip_field(wire_type)
    return item


def encode_interaction_item(item: InteractionData) -> bytes:
    """Encodes a single playable note item."""
    writer = ProtoWriter()
    writer.write_varint_field(1, int(item.interaction_type))
    if item.tap_data:
        writer.write_bytes_field(3, encode_tap_interaction(item.tap_data))
    elif item.drag_data:
        writer.write_bytes_field(4, encode_drag_interaction(item.drag_data))
    if item.track != 1:
        writer.write_varint_field(6, item.track)
    return writer.to_bytes()


def decode_beatmap_interactions(data: bytes) -> BeatmapInteractionsTemplate:
    """Parses a complete Beatstar .bytes chart file into a structured template."""
    reader = ProtoReader(data)
    template = BeatmapInteractionsTemplate()

    while reader.has_more:
        tag_info = reader.read_tag()
        if not tag_info:
            break
        field_num, wire_type = tag_info

        if field_num == 1 and wire_type == WireType.VARINT:
            template.id = reader.read_varint()
        elif field_num == 2 and wire_type == WireType.LENGTH_DELIMITED:
            template.id_label = reader.read_string()
        elif field_num == 5 and wire_type == WireType.LENGTH_DELIMITED:
            # Packed repeated InteractionData messages
            packed_bytes = reader.read_bytes()
            sub_reader = ProtoReader(packed_bytes)
            while sub_reader.has_more:
                item_len = sub_reader.read_varint()
                if item_len > sub_reader.remaining:
                    break
                item_bytes = sub_reader.read_bytes() if hasattr(sub_reader, "_dummy") else sub_reader._data[sub_reader._pos : sub_reader._pos + item_len]
                sub_reader._pos += item_len
                template.interactions.append(decode_interaction_item(item_bytes))
        else:
            # Preserve trailing sections (Stars, multipliers, visual impacts)
            if wire_type == WireType.LENGTH_DELIMITED:
                template.raw_trailing_tags[field_num] = reader.read_bytes()
            else:
                reader.skip_field(wire_type)

    return template


def encode_beatmap_interactions(template: BeatmapInteractionsTemplate) -> bytes:
    """Encodes a BeatmapInteractionsTemplate into binary .bytes format."""
    writer = ProtoWriter()
    writer.write_varint_field(1, template.id)
    writer.write_string_field(2, template.id_label)

    # Pack repeated interaction items
    packed_writer = ProtoWriter()
    for item in template.interactions:
        item_bytes = encode_interaction_item(item)
        packed_writer.write_varint(len(item_bytes))
        packed_writer._buf.extend(item_bytes)

    writer.write_bytes_field(5, packed_writer.to_bytes())

    # Write preserved trailing tags
    for tag_num, raw_bytes in template.raw_trailing_tags.items():
        writer.write_bytes_field(tag_num, raw_bytes)

    return writer.to_bytes()
