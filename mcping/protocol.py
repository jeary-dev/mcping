"""Low-level helpers for the Minecraft network protocol."""

from __future__ import annotations

import struct

class ProtocolError(Exception):
    """The server sent something that doesn't follow the protocol."""

def encode_varint(value: int) -> bytes:
    """Encode a 32-bit signed int as a VarInt."""
    if not -(2**31) <= value < 2**31:
        raise ValueError(f"VarInt out of range: {value}")
    value &= 0xFFFFFFFF
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)

def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode a VarInt from `data` starting at `offset`

    Returns (value, new_offset)
    """
    result = 0
    for i in range(5):
        if offset >= len(data):
            raise ProtocolError("VarInt ended unexpectedly")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << (7 * i)
        if not byte & 0x80:
            if result >= 2**31:
                result -= 2**32
            return result, offset
    raise ProtocolError("VarInt is too long")

def encode_string(text: str) -> bytes:
    raw = text.encode("utf-8")
    return encode_varint(len(raw)) + raw

def decode_string(data: bytes, offset: int = 0) -> tuple[str, int]:
    length, offset = decode_varint(data, offset)
    if length < 0 or offset + length > len(data):
        raise ProtocolError("String length is invalid")
    return data[offset:offset + length].decode("utf-8"), offset + length

def build_packet(packet_id: int, payload: bytes = b"") -> bytes:
    """Frame a packet: [length VarInt][packet id VarInt][payload]."""
    body = encode_varint(packet_id) + payload
    return encode_varint(len(body)) + body

def encode_unsigned_short(value: int) -> bytes:
    return struct.pack(">H", value)

def encode_long(value: int) -> bytes:
    return struct.pack(">q", value)

def decode_long(data: bytes, offset: int = 0) -> tuple[int, int]:
    if offset + 8 > len(data):
        raise ProtocolError("Long ended unexpectedly")
    return struct.unpack(">q", data[offset:offset + 8])[0], offset + 8