from pathlib import Path

import pytest

from qidi_legacy.client import MAX_RESEND_REQUESTS, QidiLegacyClient
from qidi_legacy.exceptions import QidiProtocolError, QidiUploadError
from qidi_legacy.mock_printer import MockQidiPrinter


def test_remote_filename_rejects_path_traversal(tmp_path: Path) -> None:
    source = tmp_path / "safe.gcode"
    source.write_text("G28\n")
    with MockQidiPrinter() as printer:
        with QidiLegacyClient("127.0.0.1", port=printer.port, timeout=0.2) as client:
            client.connect()
            with pytest.raises(QidiUploadError, match="rejected"):
                client.upload_file(source, remote_filename="../unsafe.gcode")


def test_upload_aborts_after_bounded_resends_and_closes_file(tmp_path: Path) -> None:
    source = tmp_path / "cube.gcode"
    source.write_bytes(b"G1 X1\n" * 500)
    with MockQidiPrinter() as printer:
        printer.state.resend_forever_at = 0
        with QidiLegacyClient("127.0.0.1", port=printer.port, timeout=0.2) as client:
            client.connect()
            with pytest.raises(QidiUploadError, match=str(MAX_RESEND_REQUESTS)):
                client.upload_file(source)
        assert printer.state.close_count == 1


def test_ifast_save_response_rejects_wrong_filename() -> None:
    with pytest.raises(QidiProtocolError, match="closing remote file"):
        QidiLegacyClient._require_file_saved(
            "Done saving file!\r\n// other.gcode",
            "expected.gcode",
        )
