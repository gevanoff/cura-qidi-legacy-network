from __future__ import annotations

import builtins

from qidi_legacy import safe_diagnostic_cli


def test_preflight_blocks_diagnostic_without_mechready(monkeypatch) -> None:
    monkeypatch.setattr(builtins, "input", lambda prompt: "STOP")

    result = safe_diagnostic_cli._guided_hot_z_test_with_preflight(object(), object())

    assert result["aborted"] is True
    assert result["stage"] == "hotend_integrity_preflight"
    assert "leakage" in result["reason"]


def test_preflight_delegates_after_mechready(monkeypatch) -> None:
    sentinel = {"aborted": False, "delegated": True}
    seen: list[tuple[object, object]] = []
    client = object()
    args = object()

    monkeypatch.setattr(builtins, "input", lambda prompt: "MECHREADY")
    monkeypatch.setattr(
        safe_diagnostic_cli,
        "_original_guided_hot_z_test",
        lambda passed_client, passed_args: seen.append((passed_client, passed_args)) or sentinel,
    )

    result = safe_diagnostic_cli._guided_hot_z_test_with_preflight(client, args)

    assert result is sentinel
    assert seen == [(client, args)]
