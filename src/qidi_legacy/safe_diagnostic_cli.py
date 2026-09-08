from __future__ import annotations

import sys

from . import diagnostic_cli


_original_guided_hot_z_test = diagnostic_cli._guided_hot_z_test


def _guided_hot_z_test_with_preflight(client: object, args: object) -> dict[str, object]:
    print(
        "\nQIDI i-Fast hotend-integrity preflight\n"
        "------------------------------------\n"
        "Do NOT continue if any of the following are unresolved:\n"
        "  - molten filament appears from above/around the nozzle or heater block rather than only the nozzle orifice;\n"
        "  - either hotend/nozzle can rock, shift vertically, or is not firmly seated in the carriage;\n"
        "  - the selected/active nozzle is not physically the lowest nozzle;\n"
        "  - the inactive nozzle does not have visible clearance above the active nozzle;\n"
        "  - the selector/lift mechanism does not fully and repeatably latch both nozzle states;\n"
        "  - heater or thermistor wires are contaminated, damaged, pinched, or displaced.\n"
        "\n"
        "Inspect and repair these conditions before running Z, motion, or selector stress tests.\n"
        "A leak can build a hanging PLA blob that becomes the lowest point and strikes the bed even when the metal nozzle was initially calibrated correctly.\n"
    )

    if not diagnostic_cli.cli._prompt_token(
        "Type MECHREADY only after the hotend is leak-free, rigid, correctly seated, and the active nozzle is the lowest point; anything else aborts: ",
        "MECHREADY",
    ):
        return {
            "aborted": True,
            "stage": "hotend_integrity_preflight",
            "reason": (
                "diagnostic blocked until hotend leakage, mounting, and relative nozzle-height "
                "conditions are corrected"
            ),
        }

    return _original_guided_hot_z_test(client, args)


def main() -> int:
    diagnostic_cli._guided_hot_z_test = _guided_hot_z_test_with_preflight
    return diagnostic_cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
