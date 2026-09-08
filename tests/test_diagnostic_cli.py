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


def test_diagnostic_entry_point_inserts_z_test_subcommand(monkeypatch) -> None:
    seen: list[list[str]] = []

    monkeypatch.setattr(sys, "argv", ["qidi-z-test", "printer.local", "--tool", "0"])
    monkeypatch.setattr(
        diagnostic_cli.cli,
        "main",
        lambda: seen.append(list(sys.argv)) or 0,
    )

    assert diagnostic_cli.main() == 0
    assert seen == [["qidi-z-test", "z-test", "printer.local", "--tool", "0"]]
