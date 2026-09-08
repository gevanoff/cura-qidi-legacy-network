from __future__ import annotations

import sys

from . import cli

MOTION_WAIT_TIMEOUT = 30.0


def _wait_for_motion(client: object) -> None:
    """Wait for queued motion without changing the normal command timeout."""
    client.command("M400", timeout=MOTION_WAIT_TIMEOUT, retries=1)


def main() -> int:
    # The normal CLI timeout intentionally remains short so commands that do not
    # produce a prompt reply fail quickly. Only M400 needs a long wait because it
    # returns after the printer has completed queued physical motion.
    cli._wait_for_motion = _wait_for_motion

    # This entry point is dedicated to the guided diagnostic, so callers do not
    # need to repeat the z-test subcommand.
    if len(sys.argv) < 2 or sys.argv[1] != "z-test":
        sys.argv.insert(1, "z-test")

    return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
