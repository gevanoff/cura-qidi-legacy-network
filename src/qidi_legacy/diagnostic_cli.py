from __future__ import annotations

import re
import sys

from . import cli

MOTION_WAIT_TIMEOUT = 30.0
IFAST_SELECTOR_Y = 5.0


def _wait_for_motion(client: object) -> None:
    """Wait for queued motion without changing the normal command timeout."""
    client.command("M400", timeout=MOTION_WAIT_TIMEOUT, retries=1)


def _reported_z(client: object) -> float:
    response = client.command("M114")
    match = re.search(r"(?:^|\s)Z:([-+]?\d+(?:\.\d+)?)", response)
    if not match:
        raise ValueError(f"M114 response did not contain a Z coordinate: {response!r}")
    return float(match.group(1))


def _fine_z_reversal_stress(
    client: object,
    *,
    distance: float,
    cycles: int,
    feed: float,
) -> None:
    """Exercise Cura-style absolute Z hops and explicitly finish at the baseline Z.

    The normal Cura i-Fast G-code runs under G90.  Using G91 here made the
    diagnostic vulnerable to one missed or duplicated UDP motion command leaving
    a permanent +/- hop-size offset.  Absolute targets match the print path more
    closely and make retries idempotent.
    """
    base_z = _reported_z(client)
    hop_z = base_z + distance

    client.command("G90")
    for _ in range(cycles):
        client.command(f"G0 Z{hop_z:g} F{feed:g}")
        client.command(f"G0 Z{base_z:g} F{feed:g}")

    # Make the intended terminal state explicit even if an earlier packet was
    # delayed, duplicated, or acknowledged ambiguously by the legacy UDP path.
    client.command(f"G0 Z{base_z:g} F{feed:g}")
    _wait_for_motion(client)


def _selector_stress(
    client: object,
    *,
    tool: int,
    cycles: int,
    feed: float,
) -> None:
    """Cycle the i-Fast front-corner selector latches and end with the requested nozzle down.

    QIDI's reference i-Fast startup performs nozzle-selection wall contact near the
    front of the machine (Y4-Y6), not at the bed centerline. Use Y5 for both
    latch walls, then return to the center measurement point.
    """
    if tool == 0:
        away_x = cli.IFAST_LEFT_WALL_X
        selected_x = cli.IFAST_RIGHT_WALL_X
    else:
        away_x = cli.IFAST_RIGHT_WALL_X
        selected_x = cli.IFAST_LEFT_WALL_X

    client.command("G90")
    for _ in range(cycles):
        client.command(f"G0 X{away_x:g} Y{IFAST_SELECTOR_Y:g} F{feed:g}")
        _wait_for_motion(client)
        client.command(f"G0 X{selected_x:g} Y{IFAST_SELECTOR_Y:g} F{feed:g}")
        _wait_for_motion(client)

    client.command(f"G0 X{cli.IFAST_CENTER_X:g} Y{cli.IFAST_CENTER_Y:g} F{feed:g}")
    _wait_for_motion(client)


def main() -> int:
    # The normal CLI timeout intentionally remains short so commands that do not
    # produce a prompt reply fail quickly. Only M400 needs a long wait because it
    # returns after the printer has completed queued physical motion.
    cli._wait_for_motion = _wait_for_motion

    # Match Cura's actual G90 absolute Z-hop behavior rather than using G91
    # relative hop pairs over the legacy UDP command channel.
    cli._fine_z_reversal_stress = _fine_z_reversal_stress

    # The i-Fast's selector hardware is reached at the front corners (about Y5),
    # while the paper-gap measurement point remains at the bed center.
    cli._selector_stress = _selector_stress

    # This entry point is dedicated to the guided diagnostic, so callers do not
    # need to repeat the z-test subcommand.
    if len(sys.argv) < 2 or sys.argv[1] != "z-test":
        sys.argv.insert(1, "z-test")

    return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
