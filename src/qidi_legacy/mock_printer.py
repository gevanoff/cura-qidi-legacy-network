from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field

from .framing import parse_file_block


@dataclass
class MockPrinterState:
    current_remote_filename: str | None = None
    uploaded: bytearray = field(default_factory=bytearray)
    started_filename: str | None = None
    resend_once_at: int | None = None
    resend_sent: bool = False


class MockQidiPrinter:
    """Minimal UDP emulator for protocol and integration tests."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.port = port
        self.state = MockPrinterState()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((host, port))
        self.port = self._socket.getsockname()[1]
        self._socket.settimeout(0.1)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, name="mock-qidi", daemon=True)

    def start(self) -> "MockQidiPrinter":
        self._thread.start()
        return self

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._socket.close()

    def __enter__(self) -> "MockQidiPrinter":
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.close()

    def _reply(self, message: str | bytes, address: tuple[str, int]) -> None:
        payload = message.encode("utf-8") if isinstance(message, str) else message
        self._socket.sendto(payload, address)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                payload, address = self._socket.recvfrom(65535)
            except socket.timeout:
                continue
            if payload.endswith(bytes((0x83,))):
                self._handle_block(payload, address)
            else:
                self._handle_command(payload.decode("utf-8", errors="replace"), address)

    def _handle_block(self, datagram: bytes, address: tuple[str, int]) -> None:
        try:
            payload, offset = parse_file_block(datagram)
        except ValueError as exc:
            self._reply(f"Error:{exc}", address)
            return

        if (
            self.state.resend_once_at is not None
            and offset >= self.state.resend_once_at
            and not self.state.resend_sent
        ):
            self.state.resend_sent = True
            self._reply(f"resend {self.state.resend_once_at}", address)
            return

        if offset > len(self.state.uploaded):
            self._reply(f"resend {len(self.state.uploaded)}", address)
            return
        end = offset + len(payload)
        if end > len(self.state.uploaded):
            self.state.uploaded.extend(b"\x00" * (end - len(self.state.uploaded)))
        self.state.uploaded[offset:end] = payload
        self._reply("ok", address)

    def _handle_command(self, command: str, address: tuple[str, int]) -> None:
        command = command.strip()
        if command == "M4001":
            self._reply("X:80 Y:80 Z:400 E:95 T:IFAST/330/250/320/0 U:'utf-8'", address)
        elif command.startswith("M4002"):
            self._reply("ok 4.3.13", address)
        elif command == "M4000":
            self._reply("B:25/0 E1:24/0 E2:23/0 D:0/0/1 F:0/0 X:1 Y:2 Z:3 T:0", address)
        elif command == "M4006":
            self._reply("ok 'test.gcode'", address)
        elif command.startswith("M28 "):
            self.state.current_remote_filename = command[4:]
            self.state.uploaded.clear()
            self._reply("ok", address)
        elif command.startswith("M29 "):
            self._reply("ok", address)
        elif command.startswith("M6030 "):
            self.state.started_filename = command
            self._reply("ok", address)
        elif command in {"M24", "M25", "M33"}:
            self._reply("ok", address)
        elif command == "M99999":
            self._reply("ok MAC:00:11:22:33:44:55 NAME:MockQidi", address)
        else:
            self._reply("Error:unknown command", address)
