from __future__ import annotations

import socket
from dataclasses import dataclass, field

from .exceptions import QidiConnectionError


@dataclass(slots=True)
class UdpTransport:
    """Small request/reply UDP transport with bounded retries.

    A single transport instance is intentionally synchronous and must not be shared
    between threads. Cura integration will own it from one worker thread.
    """

    host: str
    port: int = 3000
    timeout: float = 0.5
    receive_size: int = 65535
    _socket: socket.socket = field(init=False, repr=False)
    _remote_ip: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        self._remote_ip = socket.gethostbyname(self.host)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(self.timeout)

    def close(self) -> None:
        self._socket.close()

    def __enter__(self) -> "UdpTransport":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def discard_pending(self) -> None:
        previous_timeout = self._socket.gettimeout()
        self._socket.setblocking(False)
        try:
            while True:
                try:
                    self._socket.recvfrom(self.receive_size)
                except BlockingIOError:
                    break
        finally:
            self._socket.settimeout(previous_timeout)

    def request(self, payload: bytes, *, retries: int = 3, timeout: float | None = None) -> bytes:
        if not payload:
            raise ValueError("payload must not be empty")
        if retries < 1:
            raise ValueError("retries must be at least 1")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be positive")

        self.discard_pending()
        previous_timeout = self._socket.gettimeout()
        self._socket.settimeout(self.timeout if timeout is None else timeout)
        try:
            for attempt in range(1, retries + 1):
                self._socket.sendto(payload, (self._remote_ip, self.port))
                while True:
                    try:
                        response, source = self._socket.recvfrom(self.receive_size)
                    except socket.timeout:
                        if attempt == retries:
                            raise QidiConnectionError(
                                f"no reply from {self.host}:{self.port} after {retries} attempts"
                            )
                        break
                    if source[0] != self._remote_ip:
                        # Ignore unrelated UDP traffic until this attempt times out.
                        continue
                    if not response:
                        raise QidiConnectionError(
                            f"empty reply from {self.host}:{self.port}"
                        )
                    return response
        finally:
            self._socket.settimeout(previous_timeout)
        raise QidiConnectionError(f"no valid reply from {self.host}:{self.port}")
