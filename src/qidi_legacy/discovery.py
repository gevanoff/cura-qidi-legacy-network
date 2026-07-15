from __future__ import annotations

import socket
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscoveredPrinter:
    address: str
    name: str | None
    raw: str


def discover(*, port: int = 3000, duration: float = 3.0) -> list[DiscoveredPrinter]:
    """Discover legacy QIDI printers via the M99999 UDP broadcast command."""
    found: dict[str, DiscoveredPrinter] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 0))
        sock.settimeout(0.2)
        deadline = time.monotonic() + duration
        next_send = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_send:
                sock.sendto(b"M99999", ("255.255.255.255", port))
                next_send = now + 0.75
            try:
                payload, source = sock.recvfrom(4096)
            except socket.timeout:
                continue
            message = payload.decode("utf-8", errors="replace").strip()
            if "ok MAC:" not in message:
                continue
            name = None
            for token in message.split():
                if token.startswith("NAME:"):
                    name = token.partition(":")[2] or None
                    break
            found[source[0]] = DiscoveredPrinter(source[0], name, message)
    return sorted(found.values(), key=lambda printer: printer.address)
