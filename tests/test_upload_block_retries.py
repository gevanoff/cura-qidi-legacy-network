from pathlib import Path

import pytest

import qidi_legacy.client as client_module
from qidi_legacy.client import (
    QidiLegacyClient,
    UPLOAD_BLOCK_RETRIES,
    UPLOAD_BLOCK_TIMEOUT,
    UPLOAD_SETTLE_EVERY_BLOCKS,
    UPLOAD_SETTLE_SECONDS,
)
from qidi_legacy.exceptions import QidiConnectionError, QidiUploadError
from qidi_legacy.framing import BLOCK_MARKER, BLOCK_PAYLOAD_SIZE
from qidi_legacy.mock_printer import MockQidiPrinter
from qidi_legacy.transport import UdpTransport


def test_upload_blocks_use_one_longer_transport_attempt(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "integrity.gcode"
    source.write_bytes(("G1 X10 Y10 E1\n" * 300).encode())

    original_request = UdpTransport.request
    observed_block_retries: list[int] = []
    observed_block_timeouts: list[float | None] = []

    def recording_request(self, payload, *, retries=3, timeout=None):
        if payload.endswith(bytes((BLOCK_MARKER,))):
            observed_block_retries.append(retries)
            observed_block_timeouts.append(timeout)
        return original_request(self, payload, retries=retries, timeout=timeout)

    monkeypatch.setattr(UdpTransport, "request", recording_request)

    with MockQidiPrinter() as printer:
        with QidiLegacyClient(
            "127.0.0.1",
            port=printer.port,
            timeout=0.2,
            retries=3,
        ) as client:
            client.connect()
            client.upload_file(source)

    assert observed_block_retries
    assert set(observed_block_retries) == {UPLOAD_BLOCK_RETRIES}
    assert set(observed_block_timeouts) == {UPLOAD_BLOCK_TIMEOUT}
    assert UPLOAD_BLOCK_RETRIES == 1
    assert UPLOAD_BLOCK_TIMEOUT > 2.0


def test_upload_reports_failed_block_offset(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "timeout.gcode"
    source.write_bytes(b"G1 X1 Y1\n" * 300)

    original_request = UdpTransport.request

    def fail_file_block(self, payload, *, retries=3, timeout=None):
        if payload.endswith(bytes((BLOCK_MARKER,))):
            raise QidiConnectionError("simulated missing block acknowledgement")
        return original_request(self, payload, retries=retries, timeout=timeout)

    monkeypatch.setattr(UdpTransport, "request", fail_file_block)

    with MockQidiPrinter() as printer:
        with QidiLegacyClient("127.0.0.1", port=printer.port, timeout=0.2) as client:
            client.connect()
            with pytest.raises(QidiUploadError, match=r"offset 0 of \d+ bytes \(0% complete\)"):
                client.upload_file(source)
        assert printer.state.close_count == 1
        assert printer.state.started_filename is None


def test_upload_periodically_yields_to_printer_storage(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "large.gcode"
    source.write_bytes(b"G" * (BLOCK_PAYLOAD_SIZE * (UPLOAD_SETTLE_EVERY_BLOCKS + 1)))
    observed_sleeps: list[float] = []

    monkeypatch.setattr(client_module.time, "sleep", observed_sleeps.append)

    with MockQidiPrinter() as printer:
        with QidiLegacyClient("127.0.0.1", port=printer.port, timeout=0.2) as client:
            client.connect()
            client.upload_file(source)

    assert observed_sleeps == [UPLOAD_SETTLE_SECONDS]
