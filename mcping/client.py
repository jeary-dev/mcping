"""Ping a Minecraft Java server using the Server List Ping protocol."""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field

from .protocol import (
    ProtocolError,
    build_packet,
    decode_long,
    decode_string,
    decode_varint,
    encode_long,
    encode_string,
    encode_unsigned_short,
    encode_varint,
)

DEFAULT_PORT = 25565
PROTOCOL_VERSION = -1
_FORMAT_CODES = re.compile(r"§[0-9a-fk-orx]", re.IGNORECASE)

@dataclass
class ServerStatus:
    host: str
    port: int
    online: bool
    latency_ms: float | None = None
    version: str | None = None
    protocol: int | None = None
    players_online: int | None = None
    players_max: int | None = None
    player_sample: list[str] = field(default_factory=list)
    motd: str = ""
    favicon: str | None = None
    error: str | None = None

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

def parse_address(address: str, default_port: int = DEFAULT_PORT) -> tuple[str, int]:
    """'play.example.com:25566' -> ('play.example.com', 25566)."""
    address = address.strip()
    if address.startswith("[") and "]" in address:
        host, _, rest = address[1:].partition("]")
        port = int(rest[1:]) if rest.startswith(":") else default_port
        return host, port
    if address.count(":") == 1:
        host, port_text = address.split(":")
        return host, int(port_text)
    return address, default_port

def flatten_text(component) -> str:
    """Turn a chat component (str or dict with 'text'/'extra') into plain text."""
    if isinstance(component, str):
        return _FORMAT_CODES.sub("", component)
    if isinstance(component, list):
        return "".join(flatten_text(c) for c in component)
    if isinstance(component, dict):
        text = flatten_text(component.get("text", ""))
        text += "".join(flatten_text(c) for c in component.get("extra", []))
        return text
    return ""

async def _read_varint(reader: asyncio.StreamReader) -> int:
    raw = bytearray()
    for _ in range(5):
        byte = await reader.readexactly(1)
        raw += byte
        if not byte[0] & 0x80:
            return decode_varint(bytes(raw))[0]
    raise ProtocolError("VarInt is too long")

async def _read_packet(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    length = await _read_varint(reader)
    if not 0 < length < 2**21:
        raise ProtocolError(f"Unreasonable packet length: {length}")
    body = await reader.readexactly(length)
    packet_id, offset = decode_varint(body)
    return packet_id, body[offset:]

def _parse_status_json(status: ServerStatus, raw: dict) -> None:
    version = raw.get("version") or {}
    players = raw.get("players") or {}
    status.version = flatten_text(version.get("name", "")) or None
    status.protocol = version.get("protocol")
    status.players_online = players.get("online")
    status.players_max = players.get("max")
    status.player_sample = [p.get("name", "") for p in players.get("sample") or [] if p.get("name")]
    status.motd = flatten_text(raw.get("description", "")).strip()
    status.favicon = raw.get("favicon")

async def ping(address: str, timeout: float = 5.0) -> ServerStatus:
    """Ping a server. Never raises for network problems: check `.online` and `.error`."""
    host, port = parse_address(address)
    status = ServerStatus(host=host, port=port, online=False)
    writer = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)

        handshake = (encode_varint(PROTOCOL_VERSION) + encode_string(host)
                     + encode_unsigned_short(port) + encode_varint(1))
        writer.write(build_packet(0x00, handshake))
        writer.write(build_packet(0x00))
        await writer.drain()

        packet_id, payload = await asyncio.wait_for(_read_packet(reader), timeout)
        if packet_id != 0x00:
            raise ProtocolError(f"Expected server response (0x00), got {packet_id:#x}")
        json_text, _ = decode_string(payload)
        _parse_status_json(status, json.loads(json_text))
        status.online = True

        try:
            token = int(time.time() * 1000)
            start = time.perf_counter()
            writer.write(build_packet(0x01, encode_long(token)))
            await writer.drain()
            packet_id, payload = await asyncio.wait_for(_read_packet(reader), timeout)
            if packet_id == 0x01 and decode_long(payload)[0] == token:
                status.latency_ms = round ((time.perf_counter() - start) * 1000, 1)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, ConnectionError, ProtocolError):
            pass
    except asyncio.TimeoutError:
        status.error = "Timed out"
    except (ConnectionError, OSError) as e:
        status.error = f"Connection failed: {e.strerror or e}"
    except (ProtocolError, ValueError, asyncio.IncompleteReadError) as e:
        status.error = f"Bad Response: {e}"
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    return status

def ping_sync(address: str, timeout: float = 5.0) -> ServerStatus:
    """Same as `ping`, for normal (non-async) code."""
    return asyncio.run(ping(address, timeout))