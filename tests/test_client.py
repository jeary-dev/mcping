"""Tests against a tiny fake Minecraft server, so no real server is needed."""
import asyncio
import json

import pytest

from mcping import flatten_text, parse_address, ping
from mcping.protocol import build_packet, decode_varint, encode_string

STATUS = {
    "version": {"name": "1.21.11", "protocol": 774},
    "players": {"max": 20, "online": 2, "sample": [{"name": "czrbyn", "id": "x"}, {"name": "Steve", "id": "y"}]},
    "description": {"text": "§aCorbyn's ", "extra": [{"text": "Server"}, "\n§7Modded"]},
}


async def _read_packet(reader):
    raw = bytearray()
    while True:
        b = await reader.readexactly(1)
        raw += b
        if not b[0] & 0x80:
            break
    length, _ = decode_varint(bytes(raw))
    body = await reader.readexactly(length)
    pid, off = decode_varint(body)
    return pid, body[off:]


async def _fake_server(reader, writer, *, answer_ping=True, status=STATUS):
    await _read_packet(reader)
    await _read_packet(reader)
    writer.write(build_packet(0x00, encode_string(json.dumps(status))))
    await writer.drain()
    if answer_ping:
        pid, payload = await _read_packet(reader)
        writer.write(build_packet(0x01, payload))
        await writer.drain()
    writer.close()


async def _serve(handler):
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    return server, port


def test_ping_online():
    async def run():
        server, port = await _serve(_fake_server)
        async with server:
            return await ping(f"127.0.0.1:{port}", timeout=2)

    s = asyncio.run(run())
    assert s.online and s.error is None
    assert s.version == "1.21.11" and s.protocol == 774
    assert (s.players_online, s.players_max) == (2, 20)
    assert s.player_sample == ["czrbyn", "Steve"]
    assert s.motd == "Corbyn's Server\nModded"
    assert s.latency_ms is not None


def test_ping_without_pong_still_online():
    async def handler(r, w):
        await _fake_server(r, w, answer_ping=False)

    async def run():
        server, port = await _serve(handler)
        async with server:
            return await ping(f"127.0.0.1:{port}", timeout=1)

    s = asyncio.run(run())
    assert s.online and s.latency_ms is None


def test_ping_offline():
    async def run():
        server, port = await _serve(_fake_server)
        server.close()
        await server.wait_closed()
        return await ping(f"127.0.0.1:{port}", timeout=5)

    s = asyncio.run(run())
    assert not s.online
    assert s.error.startswith(("Connection failed", "Timed out"))


def test_ping_garbage_response():
    async def handler(r, w):
        await _read_packet(r)
        await _read_packet(r)
        w.write(b"\xff\xff\xff\xff\xff\xff")
        await w.drain()
        w.close()

    async def run():
        server, port = await _serve(handler)
        async with server:
            return await ping(f"127.0.0.1:{port}", timeout=1)

    s = asyncio.run(run())
    assert not s.online and s.error.startswith("Bad response")


@pytest.mark.parametrize("addr,expected", [
    ("example.com", ("example.com", 25565)),
    ("example.com:25566", ("example.com", 25566)),
    ("192.168.0.120:25566", ("192.168.0.120", 25566)),
    ("[::1]:25570", ("::1", 25570)),
    ("[::1]", ("::1", 25565)),
])
def test_parse_address(addr, expected):
    assert parse_address(addr) == expected


def test_flatten_text_plain_string_strips_codes():
    assert flatten_text("§l§6Hello §rworld") == "Hello world"