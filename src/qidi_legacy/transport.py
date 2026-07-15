from __future__ import annotations

import socket
from dataclasses import dataclass

from .exceptions import QidiConnectionError


@dataclass(slots=True)
class UdpTransport:
    host: str
    port: int = 3000
    timeout: float = 0.5
    receive_size: int = 65535

    def __post_init__(self) -> None:
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
        if retries < 1:
            raise ValueError("retries must be at least 1")
        self.discard_pending()
        previous_timeout = self._socket.gettimeout()
        self._socket.settimeout(self.timeout if timeout is None else timeout)
        try:
            for attempt in range(1, retries + 1):
                self._socket.sendto(payload, (self.host, self.port))
                try:
                    response, source = self._socket.recvfrom(self.receive_size)
                except socket.timeout:
                    if attempt == retries:
                        raise QidiConnectionError(
                            f"no reply from {self.host}:{self.port} after {retries} attempts"
                        )
                    continue
                if source[0] != socket.gethostbyname(self.host):
                    continue
                return response
        finally:
            self._socket.settimeout(previous_timeout)
        raise QidiConnectionError(f"no valid reply from {self.host}:{self.port}")
