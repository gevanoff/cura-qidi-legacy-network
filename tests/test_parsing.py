from qidi_legacy.parsing import parse_firmware, parse_handshake, parse_status


def test_parse_handshake() -> None:
    info = parse_handshake("X:80 Y:80 Z:400 E:95 T:IFAST/330/250/320/0 U:'utf-8'")
    assert info.machine_type == "IFAST"
    assert (info.x_max, info.y_max, info.z_max) == (330.0, 250.0, 320.0)
    assert info.encoding == "utf-8"


def test_parse_status() -> None:
    status = parse_status("B:25/60 E1:210/215 E2:24/0 D:100/400/0 F:255/0 X:1 Y:2 Z:3 T:42")
    assert status.bed_current == 25
    assert status.bed_target == 60
    assert status.extruder_current == (210, 24)
    assert status.bytes_printed == 100
    assert status.bytes_total == 400
    assert status.is_idle is False
    assert status.elapsed_seconds == 42


def test_parse_firmware() -> None:
    assert parse_firmware("ok 4.3.13") == "4.3.13"
