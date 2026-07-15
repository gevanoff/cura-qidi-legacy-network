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
MAX_RESEND_REQUESTS = 16
_FORBIDDEN_REMOTE_FILENAME_CHARS = set('"\'´`<>()[]?*\\,;:&%#$!/')


class QidiLegacyClient:
    """Client for the legacy QIDI UDP protocol used by printers such as the i-Fast.

    The client is synchronous by design. Call it from one thread at a time. This keeps
    packet ordering deterministic and makes it suitable for wrapping in a Cura worker.
    """

    def __init__(
        self,
        host: str,
        *,
        port: int = 3000,
        timeout: float = 0.5,
        retries: int = 3,
    ) -> None:
        if retries < 1:
            raise ValueError("retries must be at least 1")
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
        if not command:
            raise ValueError("command must not be empty")
        response = self._request_bytes(
            command.encode(self.encoding, errors="ignore"),
            timeout=timeout,
            retries=retries,
        )
        decoded = response.decode(self.encoding, errors="replace").strip()
        if decoded.lower().startswith("error"):
            raise QidiProtocolError(decoded)
        return decoded

    @staticmethod
    def _require_ok(response: str, operation: str) -> None:
        if not response.lower().startswith("ok"):
            raise QidiProtocolError(f"unexpected response while {operation}: {response!r}")

    @staticmethod
    def _require_file_saved(response: str, remote_filename: str) -> None:
        """Accept the known successful M29 responses without hiding mismatches.

        Some legacy firmware replies with ``ok``. QIDI i-Fast firmware V3.40 instead
        returns two lines: ``Done saving file!`` and ``// <filename>``.
        """
        if response.lower().startswith("ok"):
            return

        lines = [line.strip() for line in response.splitlines() if line.strip()]
        if (
            len(lines) == 2
            and lines[0].casefold() == "done saving file!"
            and lines[1].startswith("//")
            and lines[1][2:].strip() == remote_filename
        ):
            return

        raise QidiProtocolError(
            f"unexpected response while closing remote file: {response!r}"
        )

    @staticmethod
    def _validate_remote_filename(filename: str) -> str:
        filename = filename.strip()
        if not filename or filename in {".", ".."}:
            raise QidiUploadError("remote filename must not be empty")
        if len(filename) > 120:
            raise QidiUploadError("remote filename is longer than 120 characters")
        if any(character in _FORBIDDEN_REMOTE_FILENAME_CHARS for character in filename):
            raise QidiUploadError("remote filename contains a character rejected by QIDI firmware")
        if any(ord(character) < 32 for character in filename):
            raise QidiUploadError("remote filename contains a control character")
        if not filename.lower().endswith(".gcode"):
            filename += ".gcode"
        return filename

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
        response = self.command("M25")
        self._require_ok(response, "pausing print")
        return response

    def resume(self) -> str:
        response = self.command("M24")
        self._require_ok(response, "resuming print")
        return response

    def cancel(self) -> str:
        response = self.command("M33")
        self._require_ok(response, "canceling print")
        return response

    def start_print(self, remote_filename: str) -> str:
        remote_filename = self._validate_remote_filename(remote_filename)
        response = self.command(f'M6030 ":{remote_filename}" I1', timeout=2.0)
        self._require_ok(response, "starting print")
        return response

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

        remote = self._validate_remote_filename(remote_filename or path.name)
        begin = self.command(f"M28 {remote}", timeout=2.0)
        self._require_ok(begin, "creating remote file")

        upload_complete = False
        try:
            offset = 0
            resend_requests = 0
            with path.open("rb") as handle:
                while offset < total:
                    handle.seek(offset)
                    payload = handle.read(BLOCK_PAYLOAD_SIZE)
                    response = self._request_bytes(frame_file_block(payload, offset), timeout=2.0)
                    text = response.decode(self.encoding, errors="replace").strip()
                    if text.lower().startswith("ok"):
                        offset += len(payload)
                        if progress:
                            progress(offset, total)
                        continue

                    resend = re.search(r"resend\s+(\d+)", text, flags=re.IGNORECASE)
                    if resend:
                        resend_requests += 1
                        if resend_requests > MAX_RESEND_REQUESTS:
                            raise QidiUploadError(
                                f"printer exceeded {MAX_RESEND_REQUESTS} resend requests"
                            )
                        requested = int(resend.group(1))
                        if not 0 <= requested < total:
                            raise QidiUploadError(
                                f"invalid resend offset from printer: {requested}"
                            )
                        offset = requested
                        continue

                    raise QidiUploadError(
                        f"printer rejected upload block at {offset}: {text or '<empty>'}"
                    )

            end = self.command(f"M29 {remote}", timeout=2.0)
            self._require_file_saved(end, remote)
            upload_complete = True
            return remote
        finally:
            if not upload_complete:
                # A failed transfer can leave the printer's remote file handle open.
                # Closing it is best-effort and must not mask the original failure.
                try:
                    self.command(f"M29 {remote}", timeout=0.5, retries=1)
                except Exception:
                    pass
