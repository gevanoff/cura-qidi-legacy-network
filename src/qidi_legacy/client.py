from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable

from .exceptions import QidiConnectionError, QidiProtocolError, QidiUploadError
from .framing import BLOCK_PAYLOAD_SIZE, frame_file_block
from .models import HandshakeInfo, PrinterStatus, RemoteFile
from .parsing import parse_firmware, parse_handshake, parse_status
from .transport import UdpTransport

ProgressCallback = Callable[[int, int], None]
MAX_RESEND_REQUESTS = 16
UPLOAD_BLOCK_RETRIES = 1
UPLOAD_BLOCK_TIMEOUT = 10.0
UPLOAD_SETTLE_EVERY_BLOCKS = 64
UPLOAD_SETTLE_SECONDS = 0.01
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
        upload_block_timeout: float = UPLOAD_BLOCK_TIMEOUT,
        upload_settle_every_blocks: int = UPLOAD_SETTLE_EVERY_BLOCKS,
        upload_settle_seconds: float = UPLOAD_SETTLE_SECONDS,
    ) -> None:
        if retries < 1:
            raise ValueError("retries must be at least 1")
        if upload_block_timeout <= 0:
            raise ValueError("upload block timeout must be positive")
        if upload_settle_every_blocks < 0:
            raise ValueError("upload settle interval must not be negative")
        if upload_settle_seconds < 0:
            raise ValueError("upload settle delay must not be negative")
        self.host = host
        self.port = port
        self.retries = retries
        self.upload_block_timeout = upload_block_timeout
        self.upload_settle_every_blocks = upload_settle_every_blocks
        self.upload_settle_seconds = upload_settle_seconds
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

    def list_files(self) -> list[RemoteFile]:
        responses = self.transport.request_sequence(
            b"M20",
            start_marker=b"Begin file list",
            end_marker=b"End file list",
            final_prefix=b"ok L:",
            timeout=5.0,
        )

        files: list[RemoteFile] = []
        collecting = False
        expected_count: int | None = None
        for response in responses:
            text = response.decode(self.encoding, errors="replace")
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line == "Begin file list":
                    collecting = True
                    continue
                if line == "End file list":
                    collecting = False
                    continue
                count_match = re.fullmatch(r"ok\s+L:(\d+)", line, flags=re.IGNORECASE)
                if count_match:
                    expected_count = int(count_match.group(1))
                    continue
                if not collecting:
                    continue

                try:
                    name, size_text = line.rsplit(maxsplit=1)
                    size = int(size_text)
                except (ValueError, TypeError) as exc:
                    raise QidiProtocolError(
                        f"malformed M20 file-list entry: {line!r}"
                    ) from exc
                if size < 0:
                    raise QidiProtocolError(f"negative remote file size: {line!r}")
                files.append(RemoteFile(name=name, size=size))

        if expected_count is None:
            raise QidiProtocolError("M20 response omitted its final file count")
        if expected_count != len(files):
            raise QidiProtocolError(
                f"M20 reported {expected_count} entries but returned {len(files)}"
            )
        return files

    def verify_remote_file_size(self, remote_filename: str, expected_size: int) -> RemoteFile:
        if expected_size < 0:
            raise ValueError("expected size must not be negative")
        remote_filename = self._validate_remote_filename(remote_filename)
        files = self.list_files()

        matches = [item for item in files if item.name == remote_filename]
        if not matches:
            matches = [
                item for item in files if item.name.casefold() == remote_filename.casefold()
            ]
        if not matches:
            raise QidiUploadError(
                f"uploaded file was not found in remote listing: {remote_filename}"
            )
        if len(matches) != 1:
            raise QidiUploadError(
                f"remote listing contains multiple matches for {remote_filename}"
            )

        remote = matches[0]
        if remote.size != expected_size:
            raise QidiUploadError(
                f"remote size verification failed for {remote_filename}: "
                f"local {expected_size} bytes, remote {remote.size} bytes"
            )
        return remote

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
        verify_remote_size: bool = False,
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

        remote_file_closed = False
        try:
            offset = 0
            block_count = 0
            resend_requests = 0
            with path.open("rb") as handle:
                while offset < total:
                    handle.seek(offset)
                    payload = handle.read(BLOCK_PAYLOAD_SIZE)
                    # File-block replies are plain, unsequenced ``ok`` datagrams. Retrying
                    # the same block can leave a delayed acknowledgement in the socket and
                    # let the following block advance on the wrong reply. Commands may use
                    # bounded retries, but an unanswered file block must fail closed. Large
                    # files get a longer acknowledgement window plus periodic settling time
                    # so slow USB flushes do not look like a lost response.
                    try:
                        response = self._request_bytes(
                            frame_file_block(payload, offset),
                            timeout=self.upload_block_timeout,
                            retries=UPLOAD_BLOCK_RETRIES,
                        )
                    except QidiConnectionError as exc:
                        percent = int(offset * 100 / total)
                        raise QidiUploadError(
                            "upload block acknowledgement timed out at "
                            f"offset {offset} of {total} bytes ({percent}% complete); "
                            "the partial remote file was closed and the print was not started. "
                            f"{exc}"
                        ) from exc

                    text = response.decode(self.encoding, errors="replace").strip()
                    if text.lower().startswith("ok"):
                        offset += len(payload)
                        block_count += 1
                        if progress:
                            progress(offset, total)
                        if (
                            offset < total
                            and self.upload_settle_every_blocks
                            and block_count % self.upload_settle_every_blocks == 0
                            and self.upload_settle_seconds
                        ):
                            time.sleep(self.upload_settle_seconds)
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
            remote_file_closed = True
            if verify_remote_size:
                self.verify_remote_file_size(remote, total)
            return remote
        finally:
            if not remote_file_closed:
                # A failed transfer can leave the printer's remote file handle open.
                # Closing it is best-effort and must not mask the original failure.
                try:
                    self.command(f"M29 {remote}", timeout=0.5, retries=1)
                except Exception:
                    pass
