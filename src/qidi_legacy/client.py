from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from .exceptions import QidiProtocolError, QidiUploadError
from .framing import BLOCK_PAYLOAD_SIZE, frame_file_block
from .models import HandshakeInfo, PrinterStatus
from .parsing import parse_firmware, parse_handshake, parse_status
from .transport import UdpTransport

ProgressCallback = Callable[[int, int], None]


class QidiLegacyClient:
    """Client for the legacy QIDI UDP protocol used by printers such as the i-Fast."""

    def __init__(
        self,
        host: str,
        *,
        port: int = 3000,
        timeout: float = 0.5,
        retries: int = 3,
    ) -> None:
        self.host = host
        self.port = port
        self.retries = retries
        self.transport = UdpTransport(host, port=port, timeout=timeout)
        self.encoding = "utf-8"
        self.handshake_info: HandshakeInfo | None = None

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "QidiLegacyClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request_bytes(
        self,
        payload: bytes,
        *,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> bytes:
        return self.transport.request(
            payload,
            timeout=timeout,
            retries=self.retries if retries is None else retries,
        )

    def command(
        self,
        command: str,
        *,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> str:
        response = self._request_bytes(
            command.encode(self.encoding, errors="ignore"),
            timeout=timeout,
            retries=retries,
        )
        decoded = response.decode(self.encoding, errors="replace").strip()
        if "Error:Wifi reboot" in decoded or "Error:IP is connected" in decoded:
            raise QidiProtocolError(decoded)
        return decoded

    def connect(self) -> HandshakeInfo:
        response = self.command("M4001")
        info = parse_handshake(response)
        self.encoding = info.encoding
        self.handshake_info = info
        return info

    def firmware_version(self) -> str:
        return parse_firmware(self.command("M4002 ", timeout=2.0, retries=2))

    def status(self) -> PrinterStatus:
        return parse_status(self.command("M4000", timeout=0.5))

    def current_filename(self) -> str | None:
        response = self.command("M4006", timeout=0.5)
        match = re.search(r"'([^']+)'", response)
        return match.group(1) if match else None

    def pause(self) -> str:
        return self.command("M25")

    def resume(self) -> str:
        return self.command("M24")

    def cancel(self) -> str:
        return self.command("M33")

    def start_print(self, remote_filename: str) -> str:
        return self.command(f'M6030 ":{remote_filename}" I1', timeout=2.0)

    def upload_file(
        self,
        local_path: str | Path,
        *,
        remote_filename: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> str:
        path = Path(local_path)
        if not path.is_file():
            raise QidiUploadError(f"file does not exist: {path}")
        total = path.stat().st_size
        if total <= 0:
            raise QidiUploadError("file is empty")

        remote = remote_filename or path.name
        if not remote.lower().endswith(".gcode"):
            remote += ".gcode"

        begin = self.command(f"M28 {remote}", timeout=2.0)
        if "error" in begin.lower():
            raise QidiUploadError(f"printer rejected file creation: {begin}")

        offset = 0
        with path.open("rb") as handle:
            while offset < total:
                handle.seek(offset)
                payload = handle.read(BLOCK_PAYLOAD_SIZE)
                response = self._request_bytes(frame_file_block(payload, offset), timeout=2.0)
                text = response.decode(self.encoding, errors="replace").strip()
                if "ok" in text.lower():
                    offset += len(payload)
                    if progress:
                        progress(offset, total)
                    continue

                resend = re.search(r"resend\s+(\d+)", text, flags=re.IGNORECASE)
                if resend:
                    requested = int(resend.group(1))
                    if not 0 <= requested < total:
                        raise QidiUploadError(f"invalid resend offset from printer: {requested}")
                    offset = requested
                    continue

                raise QidiUploadError(f"printer rejected upload block at {offset}: {text}")

        end = self.command(f"M29 {remote}", timeout=2.0)
        if "error" in end.lower():
            raise QidiUploadError(f"printer rejected file close: {end}")
        return remote
