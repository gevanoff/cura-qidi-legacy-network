from __future__ import annotations

from . import diagnostic_cli


def main() -> int:
    # The shared qidi_legacy.cli z-test dispatch now enforces the MECHREADY
    # hotend-integrity preflight for every entry point. Do not wrap the guided
    # test here or the safety prompt would run twice.
    return diagnostic_cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
