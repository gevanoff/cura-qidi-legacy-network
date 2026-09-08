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


def test_z_test_moves_away_and_returns_only_after_confirmation(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    answers = iter(["READY", "light", "moved normally", "RETURN", "light", "SKIP"])
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    args = cli.build_parser().parse_args(
        ["z-test", "10.10.22.171", "--cycles", "1", "--distance", "5"]
    )

    result = cli.run(args)

    assert fake.commands == [
        "M114",
        "G91",
        "G0 Z5 F300",
        "G90",
        "M114",
        "G91",
        "G0 Z-5 F300",
        "G90",
        "M114",
    ]
    assert result["aborted"] is False
    assert result["baseline_note"] == "light"
    assert result["cycles"] == [
        {
            "cycle": 1,
            "away_position": "X:100.00 Y:100.00 Z:2.00",
            "away_note": "moved normally",
            "return_position": "X:100.00 Y:100.00 Z:3.00",
            "return_note": "light",
            "returned": True,
        }
    ]
    assert result["selector"] is None


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
        "G90",
        "M114",
    ]
    assert result["aborted"] is True
    assert result["bed_left_lowered"] is True
    assert result["stage"] == "cycle_1_bed_lowered"


def test_z_test_selector_phase_pauses_with_clearance(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    answers = iter(
        [
            "READY",
            "light",
            "normal",
            "RETURN",
            "light",
            "SELECTOR",
            "selector cycled",
            "RETURN",
            "light",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    args = cli.build_parser().parse_args(
        ["z-test", "10.10.22.171", "--cycles", "1", "--distance", "3"]
    )

    result = cli.run(args)

    assert fake.commands == [
        "M114",
        "G91",
        "G0 Z3 F300",
        "G90",
        "M114",
        "G91",
        "G0 Z-3 F300",
        "G90",
        "M114",
        "G91",
        "G0 Z3 F300",
        "G90",
        "M114",
        "M114",
        "G91",
        "G0 Z-3 F300",
        "G90",
        "M114",
    ]
    assert result["aborted"] is False
    assert result["selector"]["selector_note"] == "selector cycled"
    assert result["selector"]["returned"] is True
