from __future__ import annotations

import sys

import pytest

from qidi_legacy import diagnostic_cli


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float | None, int | None]] = []

    def command(
        self,
        command: str,
        *,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> str:
        self.calls.append((command, timeout, retries))
        if command == "M114":
            return "ok C: X:165.000 Y:125.000 Z:6.000000 E:0.000"
        return "ok"


def test_motion_wait_uses_dedicated_long_timeout() -> None:
    fake = FakeClient()

    diagnostic_cli._wait_for_motion(fake)

    assert fake.calls == [("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1)]


def test_absolute_zhop_stress_returns_explicitly_to_baseline() -> None:
    fake = FakeClient()

    diagnostic_cli._fine_z_reversal_stress(fake, distance=0.2, cycles=2, feed=300)

    assert fake.calls == [
        ("M114", None, None),
        ("G90", None, None),
        ("G0 Z6.2 F300", None, None),
        ("G0 Z6 F300", None, None),
        ("G0 Z6.2 F300", None, None),
        ("G0 Z6 F300", None, None),
        ("G0 Z6 F300", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
    ]


def test_reported_z_rejects_malformed_m114() -> None:
    fake = FakeClient()
    fake.command = lambda *args, **kwargs: "ok no coordinates"  # type: ignore[method-assign]

    try:
        diagnostic_cli._reported_z(fake)
    except ValueError as exc:
        assert "did not contain a Z coordinate" in str(exc)
    else:
        raise AssertionError("expected malformed M114 response to fail")


def test_default_xy_motion_timeout_covers_full_queued_path() -> None:
    distance = diagnostic_cli._xy_motion_distance(10)
    timeout = diagnostic_cli._xy_motion_timeout(10, 6000)

    assert distance == pytest.approx(9340.15, abs=0.1)
    assert timeout > 150
    assert timeout < 160


def test_xy_motion_stress_uses_computed_timeout_and_recenters() -> None:
    fake = FakeClient()

    diagnostic_cli._xy_motion_stress(fake, cycles=1, feed=6000)

    expected_timeout = diagnostic_cli._xy_motion_timeout(1, 6000)
    assert fake.calls == [
        ("G90", None, None),
        ("G0 X30 Y30 F6000", None, None),
        ("G0 X300 Y30 F6000", None, None),
        ("G0 X300 Y220 F6000", None, None),
        ("G0 X30 Y220 F6000", None, None),
        ("G0 X165 Y125 F6000", None, None),
        ("M400", expected_timeout, 1),
    ]


def test_selector_stress_uses_front_lane_and_recenters_for_t0() -> None:
    fake = FakeClient()

    diagnostic_cli._selector_stress(fake, tool=0, cycles=1, feed=3600)

    assert fake.calls == [
        ("G90", None, None),
        ("G0 X0 Y5 F3600", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
        ("G0 X330 Y5 F3600", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
        ("G0 X165 Y125 F3600", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
    ]


def test_selector_stress_uses_front_lane_and_recenters_for_t1() -> None:
    fake = FakeClient()

    diagnostic_cli._selector_stress(fake, tool=1, cycles=1, feed=3600)

    assert fake.calls == [
        ("G90", None, None),
        ("G0 X330 Y5 F3600", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
        ("G0 X0 Y5 F3600", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
        ("G0 X165 Y125 F3600", None, None),
        ("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1),
    ]


def test_diagnostic_entry_point_inserts_z_test_subcommand_and_patches_helpers(monkeypatch) -> None:
    seen: list[list[str]] = []

    monkeypatch.setattr(sys, "argv", ["qidi-z-test", "printer.local", "--tool", "0"])
    monkeypatch.setattr(
        diagnostic_cli.cli,
        "main",
        lambda: seen.append(list(sys.argv)) or 0,
    )

    assert diagnostic_cli.main() == 0
    assert seen == [["qidi-z-test", "z-test", "printer.local", "--tool", "0"]]
    assert diagnostic_cli.cli._wait_for_motion is diagnostic_cli._wait_for_motion
    assert diagnostic_cli.cli._fine_z_reversal_stress is diagnostic_cli._fine_z_reversal_stress
    assert diagnostic_cli.cli._xy_motion_stress is diagnostic_cli._xy_motion_stress
    assert diagnostic_cli.cli._selector_stress is diagnostic_cli._selector_stress
