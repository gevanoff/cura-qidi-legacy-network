from pathlib import Path

from qidi_legacy.client import QidiLegacyClient, UPLOAD_BLOCK_RETRIES
from qidi_legacy.framing import BLOCK_MARKER
from qidi_legacy.mock_printer import MockQidiPrinter
from qidi_legacy.transport import UdpTransport


def test_upload_blocks_use_one_transport_attempt(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "integrity.gcode"
    source.write_bytes(("G1 X10 Y10 E1\n" * 300).encode())

    original_request = UdpTransport.request
    observed_block_retries: list[int] = []

    def recording_request(self, payload, *, retries=3, timeout=None):
        if payload.endswith(bytes((BLOCK_MARKER,))):
            observed_block_retries.append(retries)
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
    assert UPLOAD_BLOCK_RETRIES == 1
