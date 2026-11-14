"""mcping - check the status of any Minecraft Java server."""
from .client import ServerStatus, flatten_text, parse_address, ping, ping_sync

__all__ = ["ServerStatus", "ping", "ping_sync", "parse_address", "flatten_text"]
__version__ = "0.1.0"