from __future__ import annotations

import socket
import time
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
        try:
            # A connected UDP socket still sends datagrams, but it makes the OS select
            # one concrete local interface and ephemeral port up front. This avoids the
            # unbound-receive failure seen on Winsock and gives actionable endpoint data
            # when a Windows firewall or route drops the printer's reply.
            self._socket.connect((self._remote_ip, self.port))
            self._socket.settimeout(self.timeout)
        except Exception:
            self._socket.close()
            raise

    @property
    def local_endpoint(self) -> tuple[str, int]:
        host, port = self._socket.getsockname()
        return str(host), int(port)

    def _endpoint_context(self) -> str:
        local_host, local_port = self.local_endpoint
        return (
            f"local {local_host}:{local_port} to remote "
            f"{self._remote_ip}:{self.port}"
        )

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
                    self._socket.recv(self.receive_size)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    # Connected UDP sockets can surface an asynchronous ICMP error here.
                    # A subsequent request gets bounded retries and reports useful context.
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
                try:
                    self._socket.send(payload)
                    response = self._socket.recv(self.receive_size)
                except socket.timeout:
                    if attempt == retries:
                        raise QidiConnectionError(
                            f"no reply from {self.host}:{self.port} after {retries} attempts "
                            f"({self._endpoint_context()})"
                        )
                    continue
                except OSError as exc:
                    if attempt == retries:
                        raise QidiConnectionError(
                            f"UDP request failed after {retries} attempts "
                            f"({self._endpoint_context()}): {exc}"
                        ) from exc
                    continue

                if not response:
                    raise QidiConnectionError(
                        f"empty reply from {self.host}:{self.port} "
                        f"({self._endpoint_context()})"
                    )
                return response
        finally:
            self._socket.settimeout(previous_timeout)
        raise QidiConnectionError(
            f"no valid reply from {self.host}:{self.port} ({self._endpoint_context()})"
        )

    def request_sequence(
        self,
        payload: bytes,
        *,
        start_marker: bytes,
        end_marker: bytes,
        final_prefix: bytes,
        timeout: float = 5.0,
        receive_timeout: float = 0.25,
        max_datagrams: int = 4096,
    ) -> list[bytes]:
        """Collect one unsequenced multipart response through its trailing acknowledgement.

        Packets arriving before ``start_marker`` are ignored because legacy QIDI firmware
        can emit delayed duplicates from the previous command. The trailing acknowledgement
        is required so it cannot be mistaken for a later command's reply.
        """
        if not payload:
            raise ValueError("payload must not be empty")
        if not start_marker or not end_marker or not final_prefix:
            raise ValueError("response markers must not be empty")
        if timeout <= 0 or receive_timeout <= 0:
            raise ValueError("timeouts must be positive")
        if max_datagrams < 1:
            raise ValueError("max_datagrams must be at least 1")

        self.discard_pending()
        previous_timeout = self._socket.gettimeout()
        deadline = time.monotonic() + timeout
        responses: list[bytes] = []
        started = False
        ended = False
        final_received = False
        datagram_count = 0

        try:
            self._socket.send(payload)
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                self._socket.settimeout(min(receive_timeout, max(remaining, 0.001)))
                try:
                    response = self._socket.recv(self.receive_size)
                except socket.timeout:
                    continue
                except OSError as exc:
                    raise QidiConnectionError(
                        f"multipart UDP request failed ({self._endpoint_context()}): {exc}"
                    ) from exc

                datagram_count += 1
                if datagram_count > max_datagrams:
                    raise QidiConnectionError(
                        f"multipart response exceeded {max_datagrams} datagrams"
                    )
                if not response:
                    continue

                if not started:
                    if start_marker not in response:
                        continue
                    started = True

                responses.append(response)
                if end_marker in response:
                    ended = True
                if ended and response.strip().lower().startswith(final_prefix.lower()):
                    final_received = True
                    break
        finally:
            self._socket.settimeout(previous_timeout)

        if not started:
            raise QidiConnectionError(
                f"multipart response did not begin with {start_marker!r} "
                f"({self._endpoint_context()})"
            )
        if not ended:
            raise QidiConnectionError(
                f"multipart response did not contain {end_marker!r} "
                f"({self._endpoint_context()})"
            )
        if not final_received:
            raise QidiConnectionError(
                f"multipart response did not finish with {final_prefix!r} "
                f"({self._endpoint_context()})"
            )
        return responses
