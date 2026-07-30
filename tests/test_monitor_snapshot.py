from types import SimpleNamespace

from cura_plugin.QidiLegacyNetwork.monitor_snapshot import MonitorSnapshot


def status(**overrides):
    values = {
        "is_idle": None,
        "bytes_printed": None,
        "bytes_total": None,
        "bed_current": None,
        "bed_target": None,
        "extruder_current": (None, None),
        "extruder_target": (None, None),
        "x": None,
        "y": None,
        "z": None,
        "elapsed_seconds": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_snapshot_maps_printing_status_and_progress() -> None:
    snapshot = MonitorSnapshot.from_status(
        status(
            is_idle=False,
            bytes_printed=250,
            bytes_total=1000,
            bed_current=59.5,
            bed_target=60.0,
            extruder_current=(202.0, 98.0),
            extruder_target=(205.0, 100.0),
            x=12.0,
            y=34.0,
            z=5.6,
            elapsed_seconds=90,
        ),
        filename="dual-test.gcode",
    )

    assert snapshot.printer_state == "Printing"
    assert snapshot.progress_percent == 25.0
    assert snapshot.filename == "dual-test.gcode"
    assert snapshot.extruder_current == (202.0, 98.0)


def test_snapshot_maps_idle_and_missing_progress() -> None:
    snapshot = MonitorSnapshot.from_status(status(is_idle=True))

    assert snapshot.printer_state == "Idle"
    assert snapshot.progress_percent is None
    assert snapshot.filename is None


def test_snapshot_clamps_invalid_progress_range() -> None:
    over = MonitorSnapshot.from_status(
        status(is_idle=False, bytes_printed=1200, bytes_total=1000)
    )
    under = MonitorSnapshot.from_status(
        status(is_idle=False, bytes_printed=-5, bytes_total=1000)
    )

    assert over.progress_percent == 100.0
    assert under.progress_percent == 0.0
