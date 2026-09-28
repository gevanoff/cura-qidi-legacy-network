from __future__ import annotations

from . import diagnostic_cli


_original_guided_hot_z_test = diagnostic_cli._guided_hot_z_test


def _guided_hot_z_test_with_preflight(client: object, args: object) -> dict[str, object]:
    blocked = diagnostic_cli.cli._hotend_integrity_preflight()
    if blocked is not None:
        return blocked
    return _original_guided_hot_z_test(client, args)


def main() -> int:
    diagnostic_cli._guided_hot_z_test = _guided_hot_z_test_with_preflight
    return diagnostic_cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
