from pathlib import Path

from qidi_legacy.client import QidiLegacyClient
from qidi_legacy.mock_printer import MockQidiPrinter


def test_connect_status_upload_and_start(tmp_path: Path) -> None:
    gcode = ("G28\n" + "G1 X10 Y10\n" * 300).encode()
    source = tmp_path / "cube.gcode"
    source.write_bytes(gcode)

    with MockQidiPrinter() as printer:
        printer.state.resend_once_at = 1280
        with QidiLegacyClient("127.0.0.1", port=printer.port, timeout=0.2) as client:
            handshake = client.connect()
            assert handshake.machine_type == "IFAST"
            assert client.firmware_version() == "4.3.13"
            assert client.status().is_idle is True
            remote = client.upload_file(source)
            assert remote == "cube.gcode"
            assert bytes(printer.state.uploaded) == gcode
            assert printer.state.resend_sent is True
            assert client.start_print(remote) == "ok"
            assert printer.state.started_filename == 'M6030 ":cube.gcode" I1'
