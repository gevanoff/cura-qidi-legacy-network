from __future__ import annotations

import sys

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
        return "ok"


def test_motion_wait_uses_dedicated_long_timeout() -> None:
    fake = FakeClient()

    diagnostic_cli._wait_for_motion(fake)

    assert fake.calls == [("M400", diagnostic_cli.MOTION_WAIT_TIMEOUT, 1)]


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


def test_diagnostic_entry_point_inserts_z_test_subcommand_and_patches_selector(monkeypatch) -> None:
    seen: list[list[str]] = []

    monkeypatch.setattr(sys, "argv", ["qidi-z-test", "printer.local", "--tool", "0"])
    monkeypatch.setattr(
        diagnostic_cli.cli,
        "main",
        lambda: seen.append(list(sys.argv)) or 0,
    )

    assert diagnostic_cli.main() == 0
    assert seen == [["qidi-z-test", "z-test", "printer.local", "--tool", "0"]]
    assert diagnostic_cli.cli._selector_stress is diagnostic_cli._selector_stress
