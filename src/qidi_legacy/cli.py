from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .client import QidiLegacyClient
from .discovery import discover
from .exceptions import QidiError, QidiUploadError


def _client(args: argparse.Namespace) -> QidiLegacyClient:
    return QidiLegacyClient(args.host, port=args.port, timeout=args.timeout, retries=args.retries)


def _add_network_args(command: argparse.ArgumentParser) -> None:
    command.add_argument("host")
    command.add_argument("--port", type=int, default=3000)
    command.add_argument("--timeout", type=float, default=0.5)
    command.add_argument("--retries", type=int, default=3)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe and use a legacy QIDI network printer")
    subparsers = parser.add_subparsers(dest="action", required=True)

    discovery = subparsers.add_parser("discover", help="broadcast-discover compatible printers")
    discovery.add_argument("--port", type=int, default=3000)
    discovery.add_argument("--duration", type=float, default=3.0)

    probe = subparsers.add_parser("probe")
    _add_network_args(probe)

    status = subparsers.add_parser("status")
    _add_network_args(status)

    upload = subparsers.add_parser("upload")
    _add_network_args(upload)
    upload.add_argument("file")
    upload.add_argument("--remote-name")
    upload.add_argument(
        "--start",
        action="store_true",
        help=(
            "disabled: automatic start is unsafe because remote size equality "
            "does not establish content integrity"
        ),
    )

    command = subparsers.add_parser("command", help="send one raw G-code command")
    _add_network_args(command)
    command.add_argument(
        "gcode",
        nargs="+",
        help="G-code to send; multiple shell tokens are joined with spaces",
    )

    z_test = subparsers.add_parser(
        "z-test",
        help="guided i-Fast Z repeatability and nozzle-selector diagnostic",
    )
    _add_network_args(z_test)
    z_test.add_argument(
        "--distance",
        type=float,
        default=5.0,
        help="relative Z travel in mm; positive Z lowers the i-Fast bed (default: 5)",
    )
    z_test.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="number of away-and-return Z cycles (default: 3)",
    )
    z_test.add_argument(
        "--feed",
        type=float,
        default=300.0,
        help="Z travel feed rate in mm/min (default: 300)",
    )
    z_test.add_argument(
        "--tool",
        type=int,
        choices=(0, 1),
        default=0,
        help="nozzle being checked: 0 = right / Nozzle 1, 1 = left / Nozzle 2",
    )
    return parser


def _relative_z_move(client: QidiLegacyClient, delta: float, feed: float) -> None:
    """Move Z relatively while always trying to restore absolute positioning."""
    client.command("G91")
    try:
        client.command(f"G0 Z{delta:g} F{feed:g}")
    finally:
        client.command("G90")


def _prompt_token(message: str, token: str) -> bool:
    try:
        answer = input(message).strip().upper()
    except EOFError:
        return False
    return answer == token


def _prompt_observation(message: str) -> str:
    try:
        return input(message).strip()
    except EOFError:
        return ""


def _guided_z_test(client: QidiLegacyClient, args: argparse.Namespace) -> dict[str, object]:
    if args.distance <= 0:
        raise ValueError("--distance must be positive")
    if args.cycles < 1:
        raise ValueError("--cycles must be at least 1")
    if args.feed <= 0:
        raise ValueError("--feed must be positive")

    nozzle = "right / Nozzle 1 / T0" if args.tool == 0 else "left / Nozzle 2 / T1"
    print(
        "\nGuided QIDI i-Fast Z repeatability test\n"
        "--------------------------------------\n"
        "This test does NOT home the printer and does NOT modify the stored Z offset.\n"
        "Positive Z lowers the i-Fast bed away from the nozzle.\n"
        "Before continuing:\n"
        "  1. Printer must be idle.\n"
        "  2. Nozzle should be cool and the build plate clear.\n"
        f"  3. Fully latch {nozzle}.\n"
        "  4. Put the carriage at a repeatable test point.\n"
        "  5. Establish a SAFE paper gap at the current Z position.\n"
        "The script will only move back toward the nozzle after you explicitly type RETURN.\n"
    )

    if not _prompt_token("Type READY to begin, or anything else to abort: ", "READY"):
        return {"aborted": True, "stage": "before_start"}

    baseline_position = client.command("M114")
    baseline_note = _prompt_observation(
        f"Baseline firmware position: {baseline_position}\n"
        "Describe the paper drag now (for example: light / medium / heavy): "
    )

    cycle_results: list[dict[str, object]] = []
    for cycle in range(1, args.cycles + 1):
        print(
            f"\nCycle {cycle}/{args.cycles}: lowering the bed by {args.distance:g} mm "
            f"at F{args.feed:g}."
        )
        _relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        away_note = _prompt_observation(
            f"Firmware position after moving away: {away_position}\n"
            "Confirm the bed physically moved away. Record any odd sound, hesitation, or measured travel: "
        )

        if not _prompt_token(
            f"Type RETURN to move the bed back toward the nozzle by {args.distance:g} mm; "
            "anything else leaves the bed lowered and aborts: ",
            "RETURN",
        ):
            cycle_results.append(
                {
                    "cycle": cycle,
                    "away_position": away_position,
                    "away_note": away_note,
                    "returned": False,
                }
            )
            return {
                "aborted": True,
                "stage": f"cycle_{cycle}_bed_lowered",
                "baseline_position": baseline_position,
                "baseline_note": baseline_note,
                "cycles": cycle_results,
                "bed_left_lowered": True,
            }

        _relative_z_move(client, -args.distance, args.feed)
        return_position = client.command("M114")
        return_note = _prompt_observation(
            f"Firmware position after return: {return_position}\n"
            "Check the SAME paper gap at the SAME XY point. Describe the drag now: "
        )
        cycle_results.append(
            {
                "cycle": cycle,
                "away_position": away_position,
                "away_note": away_note,
                "return_position": return_position,
                "return_note": return_note,
                "returned": True,
            }
        )

    selector_result: dict[str, object] | None = None
    print(
        "\nOptional nozzle-selector repeatability phase:\n"
        "The script can lower the bed to create clearance, then pause while you cycle the nozzle selector.\n"
        "This is useful for detecting whether the selected hotend settles to a different vertical height."
    )
    if _prompt_token("Type SELECTOR to run this phase, or anything else to finish: ", "SELECTOR"):
        _relative_z_move(client, args.distance, args.feed)
        selector_away_position = client.command("M114")
        print(
            f"Bed is lowered by {args.distance:g} mm. Firmware position: {selector_away_position}\n"
            f"Using the printer controls, switch away from {nozzle} and back to it several times.\n"
            "Finish with the SAME nozzle fully latched, and return the carriage to the SAME XY test point.\n"
            "Do not intentionally change Z."
        )
        selector_note = _prompt_observation(
            "Press Enter when finished, or record anything unusual before continuing: "
        )
        selector_before_return = client.command("M114")

        if not _prompt_token(
            f"Type RETURN to bring the bed back by {args.distance:g} mm; "
            "anything else leaves it safely lowered and aborts: ",
            "RETURN",
        ):
            return {
                "aborted": True,
                "stage": "selector_bed_lowered",
                "baseline_position": baseline_position,
                "baseline_note": baseline_note,
                "cycles": cycle_results,
                "selector": {
                    "away_position": selector_away_position,
                    "before_return_position": selector_before_return,
                    "selector_note": selector_note,
                    "returned": False,
                },
                "bed_left_lowered": True,
            }

        _relative_z_move(client, -args.distance, args.feed)
        selector_return_position = client.command("M114")
        selector_return_note = _prompt_observation(
            f"Firmware position after selector phase return: {selector_return_position}\n"
            "Check the SAME paper gap again. Describe the drag now: "
        )
        selector_result = {
            "away_position": selector_away_position,
            "before_return_position": selector_before_return,
            "selector_note": selector_note,
            "return_position": selector_return_position,
            "return_note": selector_return_note,
            "returned": True,
        }

    return {
        "aborted": False,
        "baseline_position": baseline_position,
        "baseline_note": baseline_note,
        "cycles": cycle_results,
        "selector": selector_result,
        "warning": (
            "M114 reports firmware coordinates only; compare them with the physical paper-gap "
            "observations to detect mechanical drift or lost Z motion"
        ),
    }


def run(args: argparse.Namespace) -> dict[str, object] | list[dict[str, object]]:
    if args.action == "discover":
        return [asdict(item) for item in discover(port=args.port, duration=args.duration)]

    if args.action == "upload" and args.start:
        raise QidiUploadError(
            "automatic network print start is disabled because the legacy QIDI protocol "
            "can store same-size corrupted content that remote byte-count verification "
            "cannot detect; upload without --start or use direct removable USB media"
        )

    with _client(args) as client:
        handshake = client.connect()
        if args.action == "probe":
            return {"handshake": asdict(handshake), "firmware": client.firmware_version()}
        if args.action == "status":
            return asdict(client.status())
        if args.action == "command":
            gcode = " ".join(args.gcode)
            return {"command": gcode, "response": client.command(gcode)}
        if args.action == "z-test":
            return _guided_z_test(client, args)

        def progress(done: int, total: int) -> None:
            print(f"uploaded {done}/{total} bytes", file=sys.stderr, flush=True)

        remote = client.upload_file(
            args.file,
            remote_filename=args.remote_name,
            progress=progress,
            verify_remote_size=True,
        )
        return {
            "uploaded": remote,
            "remote_size_verified": True,
            "content_verified": False,
            "started": False,
            "warning": (
                "remote byte count matched, but content integrity was not verified; "
                "use direct removable USB media for important jobs"
            ),
        }


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except (QidiError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return 130
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
