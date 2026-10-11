"""Protobuf wire codec for SpaceApe binary socket traffic."""

from __future__ import annotations

import time
from typing import Any
from server.models.headers import ClientHeader, ServerHeader

# MD5 fingerprints of the baked TextAssets extracted from data.unity3d in client 36.1.4.9545.
# Observed from CMS Meta Info Received logs and offline MD5 of extracted bytes.
# When the client does not send a matching checksum, we echo the baked MD5 with an
# empty URL so the client treats its bundled copy as current and registers it to RakshaRoot.
BAKED_CONFIG_MD5: dict[str, tuple[str, str]] = {
    "AssetsConfig": ("d6b5fd175ea156082a27fb59bc1759f1", "baked-36.1.4.9545"),
    "AssetsPatchConfig": ("d6fae3b9deed7e1fa81757f65df8699d", "baked-36.1.4.9545"),
    "AudioConfig": ("c350a6f2a3756433c29010b241a680f7", "36.1.4.9545-baked"),
    "BeatmapsConfig": ("4166c5de25073b0b3430559061868d72", "blankBeatmapsConfig"),
    "FontFallbackConfig": ("8a752f4dbc93e597413c70f369d0c62b", "36.1.4.9545-baked"),
    "GameConfig": ("a3f0955c0b89838553709abed1d3c96c", "36.1.4.9545-baked"),
    "LangConfig": ("d84b5d9eae97ffe3fd0e8a0b0134d9e9", "36.1.4.9545-baked"),
    "LiveOpsBundleConfig": ("228b056438e6988316a1403699c4f683", "36.1.4.9545-baked"),
    "LiveOpsCallingCardsConfig": ("e3b99d67fca7142baa3a9d7dfc247d57", "36.1.4.9545-baked"),
    "LiveOpsDeeplinkRewardConfig": ("f488abefd0d27de070a1246c26e3b0d8", "36.1.4.9545-baked"),
    "LiveOpsEmojiConfig": ("192e1678c7b7be977a76944e72623298", "36.1.4.9545-baked"),
    "LiveOpsEventConfig": ("428993c28db4be40e835024dbd3c207e", "36.1.4.9545-baked"),
    "LiveOpsLoadingScreenConfig": ("7d777a8ae4ba71b076213ed078d29ad0", "36.1.4.9545-baked"),
    "LiveOpsProfileIconConfig": ("0abfece60c8b99d5f35d434a75fad853", "36.1.4.9545-baked"),
    "LiveOpsSeasonConfig": ("6121e0ee0a3c1b0a5b43d5a66c0aacd9", "36.1.4.9545-baked"),
    "LiveOpsTrackSkinConfig": ("8e7329d8803691b67d7ce67969bcae8c", "36.1.4.9545-baked"),
    "MusicKitConfig": ("b55449cfab8a344f34074f8c2f1f7037", "36.1.4.9545-baked"),
    "NewsFeed": ("cbbde7e268c5f1c83fd71e1071209fd4", "baked-36.1.4.9545"),
    "NotificationConfig": ("46a66b57c1ac38049ce2175f2185e586", "36.1.4.9545-baked"),
    "ScalingConfig": ("b93609dac5ee71a816886fe733506d1d", "36.1.4.9545-baked"),
    "SongConfig": ("17f9137c9d2e691c6a2457a532b6d426", "36.1.4.9545-baked"),
}


class ProtoWire:
    """Low-level Protocol Buffers wire format serializer and deserializer."""

    @staticmethod
    def encode_varint(value: int) -> bytes:
        buf = bytearray()
        val = value
        while val >= 0x80:
            buf.append((val & 0x7F) | 0x80)
            val >>= 7
        buf.append(val & 0x7F)
        return bytes(buf)

    @staticmethod
    def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
        result, shift, idx = 0, 0, offset
        while idx < len(data):
            b = data[idx]
            idx += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result, idx
            shift += 7
        return result, idx

    @classmethod
    def encode_field(cls, tag: int, wire: int, payload: bytes) -> bytes:
        header = cls.encode_varint((tag << 3) | wire)
        return header + payload

    @classmethod
    def encode_int(cls, tag: int, val: int) -> bytes:
        return cls.encode_field(tag, 0, cls.encode_varint(val))

    @classmethod
    def encode_str(cls, tag: int, val: str) -> bytes:
        raw = val.encode("utf-8")
        return cls.encode_field(tag, 2, cls.encode_varint(len(raw)) + raw)

    @classmethod
    def encode_msg(cls, tag: int, raw: bytes) -> bytes:
        return cls.encode_field(tag, 2, cls.encode_varint(len(raw)) + raw)

    @classmethod
    def decode_fields_list(cls, data: bytes) -> list[tuple[int, int, Any]]:
        """Decodes raw protobuf buffer into list of (tag, wire, value)."""
        entries: list[tuple[int, int, Any]] = []
        idx = 0
        while idx < len(data):
            key, idx = cls.decode_varint(data, idx)
            tag, wire = key >> 3, key & 7
            if wire == 0:
                val, idx = cls.decode_varint(data, idx)
                entries.append((tag, wire, val))
                continue
            if wire == 2:
                length, idx = cls.decode_varint(data, idx)
                entries.append((tag, wire, data[idx : idx + length]))
                idx += length
                continue
            break
        return entries

    @classmethod
    def decode_dict(cls, data: bytes) -> dict[int, Any]:
        """Decodes raw protobuf buffer into dictionary of tags."""
        fields: dict[int, Any] = {}
        for tag, _, val in cls.decode_fields_list(data):
            fields[tag] = val
        return fields


class ProtoCodec:
    """High-level SpaceApe RPC protobuf header and payload codec."""

    @classmethod
    def decode_client_header(cls, raw: bytes) -> ClientHeader:
        """Parses ClientServerMessageHeader protobuf into ClientHeader model."""
        fields = ProtoWire.decode_dict(raw)
        ver = fields.get(1, b"").decode("utf-8", errors="ignore")
        svc = fields.get(2, b"").decode("utf-8", errors="ignore")
        rpc = fields.get(3, b"").decode("utf-8", errors="ignore")
        return ClientHeader(
            version=ver or "36.1.4.9545",
            service=svc or "userservice",
            rpcthing=rpc or "rpc-0",
            supports_compression=bool(fields.get(6, 0)),
        )

    @classmethod
    def encode_server_header(cls, client_header: ClientHeader) -> bytes:
        """Serializes ServerClientMessageHeader with GW_OK (1) status mirroring rpcthing."""
        now_ms = int(time.time() * 1000)
        parts = [
            ProtoWire.encode_str(1, client_header.version),
            ProtoWire.encode_int(2, now_ms),
            ProtoWire.encode_str(3, client_header.rpcthing),
            ProtoWire.encode_int(5, 1),
            ProtoWire.encode_str(10, client_header.service),
        ]
        return b"".join(parts)

    @classmethod
    def decode_batch_request(
        cls, body_bytes: bytes
    ) -> tuple[int, list[tuple[int, int, bytes]]]:
        """Parses BatchRequest returning batch_id and list of (req_id, rpc_type, req_body)."""
        entries = ProtoWire.decode_fields_list(body_bytes)
        batch_id = 1
        requests: list[tuple[int, int, bytes]] = []
        for tag, wire, val in entries:
            if tag == 1 and wire == 0:
                batch_id = int(val)
                continue
            if tag == 5 and wire == 2 and isinstance(val, (bytes, bytearray)):
                req_fields = ProtoWire.decode_dict(val)
                req_id = int(req_fields.get(1, 1))
                rpc_type = int(req_fields.get(3, 1))
                req_body = req_fields.get(4, b"")
                requests.append((req_id, rpc_type, req_body))
        if not requests:
            requests.append((1, 1, b""))
        return batch_id, requests

    @classmethod
    def encode_batch_response(
        cls, batch_id: int, responses: list[tuple[int, int, bytes]]
    ) -> bytes:
        """Serializes standard BatchResponse acknowledging client requests."""
        now_ms = int(time.time() * 1000)
        parts = [
            ProtoWire.encode_int(1, batch_id),
            ProtoWire.encode_int(2, now_ms),
        ]
        for req_id, rpc_type, body_data in responses:
            resp_payload = b"".join([
                ProtoWire.encode_int(1, req_id),
                ProtoWire.encode_int(3, rpc_type),
                ProtoWire.encode_msg(5, body_data),
            ])
            parts.append(ProtoWire.encode_msg(5, resp_payload))
        return b"".join(parts)

    @classmethod
    def encode_sharpla_response(cls, save_count: int = 1) -> bytes:
        """Serializes ExecuteSharplaBatchResp with status Ok (1)."""
        return b"".join([
            ProtoWire.encode_int(1, 1),
            ProtoWire.encode_str(2, ""),
            ProtoWire.encode_int(3, save_count),
        ])

    @classmethod
    def encode_sync_response(cls, player_name: str = "Player") -> bytes:
        """Serializes SyncResp containing MyProfileTO with IL2CPP Raksha tags.

        ftueFlags at proto field 25 carries all known FtueFlag IDs so that
        UserFtueFlags.IsSkipTutorialFlagSet() returns true and Unity skips the
        intro questionnaire flow (whose asset bundles may not be locally cached).
        GameConfig 36.1.4.9545 contains exactly two FtueFlag entries:
          id=1  idLabel="ftue-beatmaps"
          id=2  idLabel="ftue-intro"
        FtueFlagsTO.Flags_id (proto field 1, repeated uint) carries these IDs.
        """
        camp_bytes = b"".join([
            ProtoWire.encode_str(1, "US"),
            ProtoWire.encode_str(2, "default"),
        ])
        loc_bytes = ProtoWire.encode_msg(1, camp_bytes)
        # FtueFlagsTO: mark both known flags as set so the FTUE skip path fires.
        ftue_flags_content = (
            ProtoWire.encode_int(1, 1)   # Flags_id: ftue-beatmaps (id=1)
            + ProtoWire.encode_int(1, 2) # Flags_id: ftue-intro    (id=2)
        )
        profile_parts = [
            ProtoWire.encode_str(4, player_name),
            ProtoWire.encode_msg(5, b""),
            ProtoWire.encode_msg(11, b""),
            ProtoWire.encode_msg(14, b""),
            ProtoWire.encode_msg(25, ftue_flags_content),  # ftueFlags (FtueFlagsTO)
            ProtoWire.encode_msg(26, b""),                 # ftueCounters (FtueCountersTO)
            ProtoWire.encode_msg(36, b""),
            ProtoWire.encode_msg(52, b""),
            ProtoWire.encode_int(55, 1),
            ProtoWire.encode_msg(58, b""),
            ProtoWire.encode_msg(59, b""),
            ProtoWire.encode_msg(60, b""),
            ProtoWire.encode_msg(61, b""),
            ProtoWire.encode_msg(64, b""),
            ProtoWire.encode_msg(69, b""),
            ProtoWire.encode_msg(70, b""),
            ProtoWire.encode_msg(75, b""),
            ProtoWire.encode_msg(77, b""),
            ProtoWire.encode_msg(79, b""),
            ProtoWire.encode_msg(80, b""),
            ProtoWire.encode_msg(82, loc_bytes),
            ProtoWire.encode_msg(89, b""),
            ProtoWire.encode_msg(90, b""),
            ProtoWire.encode_msg(91, b""),
            ProtoWire.encode_msg(92, b""),
            ProtoWire.encode_msg(96, b""),
            ProtoWire.encode_msg(97, b""),
        ]
        profile_bytes = b"".join(profile_parts)
        return b"".join([
            ProtoWire.encode_msg(7, profile_bytes),
            ProtoWire.encode_int(8, 0),
            ProtoWire.encode_int(9, 0),
        ])

    @classmethod
    def decode_cms_request(cls, body_bytes: bytes) -> dict[str, dict]:
        """Parses CMS batch request body into a mapping from config name to metadata.

        Each value carries the version string, checksum, and variant the client
        already holds for that config type.
        """
        items: dict[str, dict] = {}
        for tag, wire, val in ProtoWire.decode_fields_list(body_bytes):
            if tag != 1 or not isinstance(val, bytes):
                continue
            sub = ProtoWire.decode_dict(val)
            name = sub.get(1, b"").decode("utf-8", errors="ignore")
            version = sub.get(2, b"").decode("utf-8", errors="ignore")
            hash_val = sub.get(3, b"").decode("utf-8", errors="ignore")
            variant_raw = sub.get(4, b"")
            variant = variant_raw.decode("utf-8", errors="ignore") if isinstance(variant_raw, bytes) else ""
            if name:
                items[name] = {"version": version, "hash": hash_val, "variant": variant}
        return items

    @classmethod
    def merge_cms_resources(
        cls, server_resources: list[dict], client_items: dict[str, dict]
    ) -> list[dict]:
        """Merges server catalog with client-reported metadata.

        Strategy (observed from CMS Meta Info Received logs and IL2CPP dump):
        - The client validates each config by comparing the server-returned checksum
          (MD5 hex) against the MD5 of its baked TextAsset from data.unity3d.
        - When they match, the client registers the baked copy to RakshaRoot and
          skips any download. When they don't match, the config stays unregistered
          ('X is not registered to raksha root' error at runtime).
        - Only HTTPS URLs are safe to serve: Unity 2022.x blocks UnityWebRequest
          over HTTP regardless of the Android network security config.
        - Therefore: always echo the baked MD5 (from BAKED_CONFIG_MD5) with an empty
          URL. The client accepts its bundled copy, registers it, and plays.
        """
        merged: list[dict] = []
        for resource in server_resources:
            name = resource.get("name", "")
            url = resource.get("url", "")
            server_hash = resource.get("hash", "")
            client_info = client_items.get(name, {})
            variant = client_info.get("variant", "")

            is_real_binary = bool(
                url.startswith("https://")
                and url.endswith(".bin")
                and server_hash
                and "hash_" not in server_hash
            )
            if is_real_binary:
                # Real HTTPS binary: let the client download and verify it.
                version_str = client_info.get("version", resource.get("version", ""))
                if not isinstance(version_str, str):
                    version_str = str(version_str)
                merged.append({
                    "name": name,
                    "url": url,
                    "hash": server_hash,
                    "version_str": version_str,
                    "variant": variant,
                    "_has_binary": True,
                })
                continue

            # Fallback: serve the baked MD5 so the client uses its embedded copy.
            baked_md5, baked_version = BAKED_CONFIG_MD5.get(name, ("", "1"))
            # Use client's version string when available (it must round-trip);
            # fall back to the baked version extracted from the TextAsset.
            version_str = client_info.get("version") or baked_version or resource.get("version", "1")
            if not isinstance(version_str, str):
                version_str = str(version_str)
            # Echo the client's hash when present; fall back to the baked MD5
            # for clients that did not report one.
            effective_hash = client_info.get("hash") or baked_md5 or server_hash
            merged.append({
                "name": name,
                "url": "",
                "hash": effective_hash,
                "version_str": version_str,
                "variant": variant,
                "_unchanged": True,
                "_baked_md5": bool(baked_md5),
            })
        return merged

    @classmethod
    def encode_cms_resource_item(cls, resource: dict) -> bytes:
        """Serializes a single CMSMetaInfo response item.

        Field layout matches the Raksha CMSMetaInfo schema observed in client traffic:
          1: type      (string) — config name, e.g. "GameConfig"
          2: version   (string) — baked version string, e.g. "36.1.4.9545-baked"
          3: checksum  (string) — MD5 hex hash the client should validate
          4: variant   (string) — locale variant such as "en", or empty
          5: url       (string) — HTTPS download URL; empty means no download needed
        """
        name = resource.get("name", "")
        version_str = resource.get("version_str", "")
        hash_val = resource.get("hash", "")
        variant = resource.get("variant", "")
        url = resource.get("url", "")
        return b"".join([
            ProtoWire.encode_str(1, name),
            ProtoWire.encode_str(2, version_str),
            ProtoWire.encode_str(3, hash_val),
            ProtoWire.encode_str(4, variant),
            ProtoWire.encode_str(5, url),
        ])

    @classmethod
    def encode_cms_response(cls, resources: list[dict]) -> bytes:
        """Serializes CMS GetBundles response containing a list of resource items."""
        parts: list[bytes] = []
        for resource in resources:
            item_bytes = cls.encode_cms_resource_item(resource)
            parts.append(ProtoWire.encode_msg(1, item_bytes))
        return b"".join(parts)

    @classmethod
    def decode_user_request(cls, body_bytes: bytes) -> dict[str, Any]:
        """Parses userservice BaseReq for AllInOneLogin."""
        fields = ProtoWire.decode_dict(body_bytes)
        req_id = fields.get(1, 1)
        req_type = fields.get(2, 7)
        login_bytes = fields.get(112, b"")
        login_fields = ProtoWire.decode_dict(login_bytes) if login_bytes else {}
        cinta = login_fields.get(4, b"").decode("utf-8", errors="ignore")
        return {
            "id": req_id,
            "type": req_type,
            "all_in_one_login": {"cinta": cinta or None},
        }

    @classmethod
    def encode_user_response(
        cls, req_id: int, ticket: str, clide: str, cinta: str
    ) -> bytes:
        """Serializes userservice BaseResp containing RespAllInOneLogin."""
        expiry = int(time.time() * 1000) + 86400000 * 30
        login_payload = b"".join([
            ProtoWire.encode_str(1, ticket),
            ProtoWire.encode_str(2, clide),
            ProtoWire.encode_int(3, expiry),
            ProtoWire.encode_str(4, cinta),
        ])
        return b"".join([
            ProtoWire.encode_int(1, req_id),
            ProtoWire.encode_int(2, 7),
            ProtoWire.encode_int(3, 200),
            ProtoWire.encode_str(7, clide),
            ProtoWire.encode_msg(112, login_payload),
        ])
