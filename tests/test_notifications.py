from __future__ import annotations

import sys
import types

from cura_plugin.QidiLegacyNetwork.notifications import notify_upload_result


def _fake_winsound(monkeypatch):
    calls: list[tuple[str, object]] = []
    module = types.SimpleNamespace(
        SND_ALIAS=1,
        SND_ASYNC=2,
        SND_NODEFAULT=4,
        MB_ICONASTERISK=64,
        MB_ICONHAND=16,
    )

    def play_sound(alias, flags):
        calls.append(("play", (alias, flags)))

    def message_beep(kind):
        calls.append(("beep", kind))

    module.PlaySound = play_sound
    module.MessageBeep = message_beep
    monkeypatch.setitem(sys.modules, "winsound", module)
    monkeypatch.setattr(sys, "platform", "win32")
    return calls, module


def test_success_uses_windows_information_sound(monkeypatch) -> None:
    calls, module = _fake_winsound(monkeypatch)

    notify_upload_result(success=True)

    assert calls == [
        (
            "play",
            (
                "SystemAsterisk",
                module.SND_ALIAS | module.SND_ASYNC | module.SND_NODEFAULT,
            ),
        )
    ]


def test_failure_uses_windows_critical_sound(monkeypatch) -> None:
    calls, module = _fake_winsound(monkeypatch)

    notify_upload_result(success=False)

    assert calls[0] == (
        "play",
        ("SystemHand", module.SND_ALIAS | module.SND_ASYNC | module.SND_NODEFAULT),
    )


def test_windows_alias_failure_falls_back_to_message_beep(monkeypatch) -> None:
    calls, module = _fake_winsound(monkeypatch)

    def fail_play_sound(alias, flags):
        raise RuntimeError("sound alias unavailable")

    module.PlaySound = fail_play_sound

    notify_upload_result(success=True)

    assert calls == [("beep", module.MB_ICONASTERISK)]
