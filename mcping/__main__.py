"""Command line: `mcping <address> [address ...]`"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from . import __version__
from .client import ServerStatus, ping

def _print_status(s: ServerStatus) -> None:
    if not s.online:
        print(f"\033[31m●\033[0m {s.address}  OFFLINE  ({s.error})")
        return
    latency = f"{s.latency_ms} ms" if s.latency_ms is not None else "?"
    print(f"\033[32m●\033[0m {s.address}  ONLINE  {latency}")
    print(f"  Version : {s.version} (protocol {s.protocol})")
    print(f"  Players : {s.players_online}/{s.players_max}")
    if s.player_sample:
        print(f"            {', '.join(s.player_sample)}")
    if s.motd:
        for line in s.motd.splitlines():
            print(f"  MOTD    : {line}")

async def _run(addresses: list[str], timeout: float) -> list[ServerStatus]:
    return await asyncio.gather(*(ping(a, timeout) for a in addresses))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mcping", description="Check Minecraft Java server status.")
    parser.add_argument("addresses", nargs="+", help="host or host:port (default port 25565)")
    parser.add_argument("-t", "--timeout", type=float, default=5.0, help="seconds to wait (default 5)")
    parser.add_argument("--json", action="store_true", help="output JSON instead of text")
    parser.add_argument("--version", action="version", version=f"mcping {__version__}")
    args = parser.parse_args(argv)

    results = asyncio.run(_run(args.addresses, args.timeout))
    if args.json:
        data = [asdict(r) | {"favicon": bool(r.favicon)} for r in results]
        print(json.dumps(data if len(data) > 1 else data[0], indent=2))
    else:
        for r in results:
            _print_status(r)
    return 0 if all(r.online for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())