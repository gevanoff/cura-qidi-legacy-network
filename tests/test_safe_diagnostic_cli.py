from __future__ import annotations

from qidi_legacy import safe_diagnostic_cli


def test_safe_entrypoint_delegates_to_shared_diagnostic_main(monkeypatch) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(
        safe_diagnostic_cli.diagnostic_cli,
        "main",
        lambda: seen.append(True) or 0,
    )

    assert safe_diagnostic_cli.main() == 0
    assert seen == [True]
