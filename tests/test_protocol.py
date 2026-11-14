import pytest

from mcping.protocol import (
    ProtocolError,
    build_packet,
    decode_string,
    decode_varint,
    encode_string,
    encode_varint,
)

VARINT_CASES = [
    (0, "00"),
    (1, "01"),
    (127, "7f"),
    (128, "8001"),
    (255, "ff01"),
    (25565, "ddc701"),
    (2097151, "ffff7f"),
    (2147483647, "ffffffff07"),
    (-1, "ffffffff0f"),
    (-2147483648, "8080808008"),
]


@pytest.mark.parametrize("value,hexed", VARINT_CASES)
def test_encode_varint(value, hexed):
    assert encode_varint(value).hex() == hexed


@pytest.mark.parametrize("value,hexed", VARINT_CASES)
def test_decode_varint(value, hexed):
    raw = bytes.fromhex(hexed)
    assert decode_varint(raw) == (value, len(raw))


def test_varint_out_of_range():
    with pytest.raises(ValueError):
        encode_varint(2**31)


def test_varint_too_long():
    with pytest.raises(ProtocolError):
        decode_varint(bytes.fromhex("ffffffffff01"))


def test_varint_truncated():
    with pytest.raises(ProtocolError):
        decode_varint(bytes.fromhex("80"))


def test_string_roundtrip():
    raw = encode_string("Hello §aworld ✓")
    assert decode_string(raw) == ("Hello §aworld ✓", len(raw))


def test_build_packet_frames_length():
    pkt = build_packet(0x00, b"\x01\x02")
    length, offset = decode_varint(pkt)
    assert length == len(pkt) - offset == 3