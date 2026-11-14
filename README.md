# mcping

Check the status of any **Minecraft Java Edition** server from the command line or from Python.

It speaks the real [Server List Ping](https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping) protocol, the same thing the Multiplayer screen does, so it works on **vanilla, Paper, Fabric, Forge/NeoForge and proxies** with nothing installed on the server.

```
$ mcping play.example.com 192.168.0.120:25566
● play.example.com:25565  ONLINE  23.4 ms
  Version : Paper 1.21.11 (protocol 774)
  Players : 12/100
            Steve, Alex
  MOTD    : Welcome to Example SMP!
● 192.168.0.120:25566  OFFLINE  (Timed out)
```

## Install

```bash
pip install git+https://github.com/jeary-dev/mcping
```

Requires Python 3.10+. No dependencies.

## Command line

```bash
mcping example.com                  # default port 25565
mcping example.com:25566 other.net  # several servers at once (pinged in parallel)
mcping example.com --json           # machine-readable output
mcping example.com -t 2             # 2 second timeout
```

The exit code is `0` if every server is online and `1` otherwise, so it works in scripts:

```bash
mcping myserver.net || echo "Server is down!"
```

## Python library

```python
import asyncio
from mcping import ping

status = asyncio.run(ping("example.com:25565"))

if status.online:
    print(f"{status.players_online}/{status.players_max} players, {status.latency_ms} ms")
    print(status.motd)
else:
    print("Offline:", status.error)
```

`ping()` is async (ideal for bots and web apps). For normal scripts use `ping_sync()`.
It never raises for network problems: check `status.online` and `status.error`.

`ServerStatus` fields: `host`, `port`, `online`, `latency_ms`, `version`, `protocol`, `players_online`, `players_max`, `player_sample`, `motd`, `favicon`, `error`.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The tests run against a small fake Minecraft server, so no real server or internet connection is needed.

## Roadmap

- [x] Core protocol + CLI
- [ ] SRV record support (`_minecraft._tcp` DNS lookups)
- [ ] Discord bot: `/status`, live status message, up/down alerts
- [ ] Optional Paper plugin for TPS, memory and join/leave events
- [ ] Fabric mod version of the plugin

## License

MIT