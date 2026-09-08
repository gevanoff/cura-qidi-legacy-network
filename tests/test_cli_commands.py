from __future__ import annotations

import builtins

from qidi_legacy import cli


class FakeClient:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self._m114_counter = 0

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def connect(self) -> object:
        return object()

    def command(self, command: str) -> str:
        self.commands.append(command)
        if command == "M114":
            self._m114_counter += 1
            return f"X:100.00 Y:100.00 Z:{self._m114_counter:.2f}"
        return "ok"


def test_command_joins_shell_tokens_and_sends_one_raw_command(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    args = cli.build_parser().parse_args(
        ["command", "10.10.22.171", "G0", "Z5", "F300"]
    )

    result = cli.run(args)

    assert fake.commands == ["G0 Z5 F300"]
    assert result == {"command": "G0 Z5 F300", "response": "ok"}


def test_z_test_requires_ready_before_sending_motion(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    monkeypatch.setattr(builtins, "input", lambda prompt: "NO")
    args = cli.build_parser().parse_args(
        ["z-test", "10.10.22.171", "--cycles", "1"]
    )

    result = cli.run(args)

    assert result == {"aborted": True, "stage": "before_start"}
    assert fake.commands == []


def test_relative_z_move_waits_and_restores_absolute_mode() -> None:
    fake = FakeClient()

    cli._relative_z_move(fake, 5, 300)

    assert fake.commands == ["G91", "G0 Z5 F300", "M400", "G90"]


def test_z_test_moves_away_and_returns_only_after_confirmation(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    answers = iter(
        [
            "READY",
            "light",
            "moved normally",
            "RETURN",
            "light",
            "SKIP",
            "SKIP",
            "SKIP",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    args = cli.build_parser().parse_args(
        ["z-test", "10.10.22.171", "--cycles", "1", "--distance", "5"]
    )

    result = cli.run(args)

    assert fake.commands == [
        "M114",
        "G91",
        "G0 Z5 F300",
        "M400",
        "G90",
        "M114",
        "G91",
        "G0 Z-5 F300",
        "M400",
        "G90",
        "M114",
    ]
    assert result["aborted"] is False
    assert result["baseline_note"] == "light"
    assert result["cycles"][0]["returned"] is True
    assert result["cycles"][0]["return_note"] == "light"
    assert result["optional"] == {}


def test_z_test_abort_after_away_move_leaves_bed_lowered(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    answers = iter(["READY", "light", "moved normally", "STOP"])
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    args = cli.build_parser().parse_args(
        ["z-test", "10.10.22.171", "--cycles", "1", "--distance", "2"]
    )

    result = cli.run(args)

    assert fake.commands == [
        "M114",
        "G91",
        "G0 Z2 F300",
        "M400",
        "G90",
        "M114",
    ]
    assert result["aborted"] is True
    assert result["bed_left_lowered"] is True
    assert result["stage"] == "cycle_1_bed_lowered"


def test_fine_z_stress_returns_to_absolute_mode() -> None:
    fake = FakeClient()

    cli._fine_z_reversal_stress(fake, distance=0.2, cycles=2, feed=300)

    assert fake.commands == [
        "G91",
        "G0 Z0.2 F300",
        "G0 Z-0.2 F300",
        "G0 Z0.2 F300",
        "G0 Z-0.2 F300",
        "M400",
        "G90",
    ]


def test_xy_motion_stress_avoids_selector_walls_and_recenters() -> None:
    fake = FakeClient()

    cli._xy_motion_stress(fake, cycles=1, feed=6000)

    assert fake.commands == [
        "G90",
        "G0 X30 Y30 F6000",
        "G0 X300 Y30 F6000",
        "G0 X300 Y220 F6000",
        "G0 X30 Y220 F6000",
        "G0 X165 Y125 F6000",
        "M400",
    ]
    assert all("X0 " not in command and "X330 " not in command for command in fake.commands)


def test_selector_stress_cycles_walls_and_ends_with_t0_latched() -> None:
    fake = FakeClient()

    cli._selector_stress(fake, tool=0, cycles=2, feed=3600)

    assert fake.commands == [
        "G90",
        "G0 X0 Y125 F3600",
        "M400",
        "G0 X330 Y125 F3600",
        "M400",
        "G0 X0 Y125 F3600",
        "M400",
        "G0 X330 Y125 F3600",
        "M400",
        "G0 X165 Y125 F3600",
        "M400",
    ]


def test_selector_stress_cycles_walls_and_ends_with_t1_latched() -> None:
    fake = FakeClient()

    cli._selector_stress(fake, tool=1, cycles=1, feed=3600)

    assert fake.commands == [
        "G90",
        "G0 X330 Y125 F3600",
        "M400",
        "G0 X0 Y125 F3600",
        "M400",
        "G0 X165 Y125 F3600",
        "M400",
    ]


def test_z_test_selector_phase_is_automatic(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    answers = iter(
        [
            "READY",
            "light",
            "normal",
            "RETURN",
            "light",
            "SKIP",
            "SKIP",
            "SELECTOR",
            "selector looked normal",
            "RETURN",
            "light",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    args = cli.build_parser().parse_args(
        [
            "z-test",
            "10.10.22.171",
            "--cycles",
            "1",
            "--distance",
            "3",
            "--selector-cycles",
            "1",
        ]
    )

    result = cli.run(args)

    selector = result["optional"]["selector"]
    assert selector["stress_note"] == "selector looked normal"
    assert selector["returned"] is True
    assert "G0 X0 Y125 F3600" in fake.commands
    assert "G0 X330 Y125 F3600" in fake.commands
    assert "G0 X165 Y125 F3600" in fake.commands
