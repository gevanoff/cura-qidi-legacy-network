from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .client import QidiLegacyClient
from .discovery import discover
from .exceptions import QidiError, QidiUploadError

IFAST_CENTER_X = 165.0
IFAST_CENTER_Y = 125.0
IFAST_LEFT_WALL_X = 0.0
IFAST_RIGHT_WALL_X = 330.0
IFAST_MOTION_X_LOW = 30.0
IFAST_MOTION_X_HIGH = 300.0
IFAST_MOTION_Y_LOW = 30.0
IFAST_MOTION_Y_HIGH = 220.0


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
        help="guided i-Fast Z, XY-motion, and nozzle-selector diagnostic",
    )
    _add_network_args(z_test)
    z_test.add_argument(
        "--distance",
        type=float,
        default=5.0,
        help="clearance Z travel in mm; positive Z lowers the i-Fast bed (default: 5)",
    )
    z_test.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="number of basic away-and-return Z cycles (default: 3)",
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
    z_test.add_argument(
        "--zhop-cycles",
        type=int,
        default=100,
        help="small 0.2 mm-style Z reversal cycles in the optional ZHOP phase (default: 100)",
    )
    z_test.add_argument(
        "--zhop-distance",
        type=float,
        default=0.2,
        help="small Z reversal distance in mm for the optional ZHOP phase (default: 0.2)",
    )
    z_test.add_argument(
        "--xy-cycles",
        type=int,
        default=10,
        help="rectangular carriage sweeps in the optional MOTION phase (default: 10)",
    )
    z_test.add_argument(
        "--xy-feed",
        type=float,
        default=6000.0,
        help="XY feed rate in mm/min for the optional MOTION phase (default: 6000)",
    )
    z_test.add_argument(
        "--selector-cycles",
        type=int,
        default=3,
        help="automatic wall-to-wall latch cycles in the optional SELECTOR phase (default: 3)",
    )
    z_test.add_argument(
        "--selector-feed",
        type=float,
        default=3600.0,
        help="wall-contact feed rate in mm/min for the SELECTOR phase (default: 3600)",
    )
    return parser


def _wait_for_motion(client: QidiLegacyClient) -> None:
    client.command("M400")


def _relative_z_move(client: QidiLegacyClient, delta: float, feed: float) -> None:
    """Move Z relatively and wait, while always trying to restore absolute positioning."""
    client.command("G91")
    try:
        client.command(f"G0 Z{delta:g} F{feed:g}")
        _wait_for_motion(client)
    finally:
        client.command("G90")


def _absolute_xy_move(
    client: QidiLegacyClient,
    x: float,
    y: float,
    feed: float,
    *,
    wait: bool = True,
) -> None:
    client.command("G90")
    client.command(f"G0 X{x:g} Y{y:g} F{feed:g}")
    if wait:
        _wait_for_motion(client)


def _fine_z_reversal_stress(
    client: QidiLegacyClient,
    *,
    distance: float,
    cycles: int,
    feed: float,
) -> None:
    client.command("G91")
    try:
        for _ in range(cycles):
            client.command(f"G0 Z{distance:g} F{feed:g}")
            client.command(f"G0 Z{-distance:g} F{feed:g}")
        _wait_for_motion(client)
    finally:
        client.command("G90")


def _xy_motion_stress(client: QidiLegacyClient, *, cycles: int, feed: float) -> None:
    client.command("G90")
    for _ in range(cycles):
        client.command(
            f"G0 X{IFAST_MOTION_X_LOW:g} Y{IFAST_MOTION_Y_LOW:g} F{feed:g}"
        )
        client.command(
            f"G0 X{IFAST_MOTION_X_HIGH:g} Y{IFAST_MOTION_Y_LOW:g} F{feed:g}"
        )
        client.command(
            f"G0 X{IFAST_MOTION_X_HIGH:g} Y{IFAST_MOTION_Y_HIGH:g} F{feed:g}"
        )
        client.command(
            f"G0 X{IFAST_MOTION_X_LOW:g} Y{IFAST_MOTION_Y_HIGH:g} F{feed:g}"
        )
    client.command(f"G0 X{IFAST_CENTER_X:g} Y{IFAST_CENTER_Y:g} F{feed:g}")
    _wait_for_motion(client)


def _selector_stress(
    client: QidiLegacyClient,
    *,
    tool: int,
    cycles: int,
    feed: float,
) -> None:
    """Cycle the i-Fast's physical wall latches, ending with the requested nozzle down."""
    if tool == 0:
        away_x = IFAST_LEFT_WALL_X
        selected_x = IFAST_RIGHT_WALL_X
    else:
        away_x = IFAST_RIGHT_WALL_X
        selected_x = IFAST_LEFT_WALL_X

    client.command("G90")
    for _ in range(cycles):
        client.command(f"G0 X{away_x:g} Y{IFAST_CENTER_Y:g} F{feed:g}")
        _wait_for_motion(client)
        client.command(f"G0 X{selected_x:g} Y{IFAST_CENTER_Y:g} F{feed:g}")
        _wait_for_motion(client)
    client.command(f"G0 X{IFAST_CENTER_X:g} Y{IFAST_CENTER_Y:g} F{feed:g}")
    _wait_for_motion(client)


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


def _return_from_clearance(
    client: QidiLegacyClient,
    args: argparse.Namespace,
    *,
    stage: str,
) -> tuple[bool, str | None, str | None]:
    if not _prompt_token(
        f"Type RETURN to bring the bed back toward the nozzle by {args.distance:g} mm; "
        "anything else leaves it lowered and aborts: ",
        "RETURN",
    ):
        return False, None, None

    _relative_z_move(client, -args.distance, args.feed)
    position = client.command("M114")
    note = _prompt_observation(
        f"Firmware position after return: {position}\n"
        f"At X{IFAST_CENTER_X:g} Y{IFAST_CENTER_Y:g}, compare the SAME paper gap after {stage}. "
        "Describe the drag: "
    )
    return True, position, note


def _guided_z_test(client: QidiLegacyClient, args: argparse.Namespace) -> dict[str, object]:
    if args.distance <= 0:
        raise ValueError("--distance must be positive")
    if args.cycles < 1:
        raise ValueError("--cycles must be at least 1")
    if args.feed <= 0:
        raise ValueError("--feed must be positive")
    if args.zhop_cycles < 1:
        raise ValueError("--zhop-cycles must be at least 1")
    if args.zhop_distance <= 0:
        raise ValueError("--zhop-distance must be positive")
    if args.xy_cycles < 1:
        raise ValueError("--xy-cycles must be at least 1")
    if args.xy_feed <= 0:
        raise ValueError("--xy-feed must be positive")
    if args.selector_cycles < 1:
        raise ValueError("--selector-cycles must be at least 1")
    if args.selector_feed <= 0:
        raise ValueError("--selector-feed must be positive")

    nozzle = "right / Nozzle 1 / T0" if args.tool == 0 else "left / Nozzle 2 / T1"
    print(
        "\nGuided QIDI i-Fast motion/Z repeatability test\n"
        "---------------------------------------------\n"
        "This test does NOT home the printer and does NOT modify the stored Z offset.\n"
        "Positive Z lowers the i-Fast bed away from the nozzle.\n"
        "Before continuing:\n"
        "  1. Printer must be idle and X/Y must already have been homed.\n"
        "  2. Nozzle should be cool and the build plate clear.\n"
        f"  3. Fully latch {nozzle}.\n"
        f"  4. Put the carriage at X{IFAST_CENTER_X:g} Y{IFAST_CENTER_Y:g}.\n"
        "  5. Establish a SAFE paper gap at the current Z position.\n"
        "The script only returns from a lowered-clearance position after you type RETURN.\n"
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
            f"\nBasic Z cycle {cycle}/{args.cycles}: lowering the bed by {args.distance:g} mm "
            f"at F{args.feed:g}."
        )
        _relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        away_note = _prompt_observation(
            f"Firmware position after moving away: {away_position}\n"
            "Confirm the bed physically moved away. Record any odd sound, hesitation, or measured travel: "
        )

        returned, return_position, return_note = _return_from_clearance(
            client, args, stage=f"basic Z cycle {cycle}"
        )
        cycle_results.append(
            {
                "cycle": cycle,
                "away_position": away_position,
                "away_note": away_note,
                "return_position": return_position,
                "return_note": return_note,
                "returned": returned,
            }
        )
        if not returned:
            return {
                "aborted": True,
                "stage": f"cycle_{cycle}_bed_lowered",
                "baseline_position": baseline_position,
                "baseline_note": baseline_note,
                "cycles": cycle_results,
                "bed_left_lowered": True,
            }

    optional_results: dict[str, object] = {}

    print(
        "\nOptional fine Z-reversal phase:\n"
        f"This lowers the bed {args.distance:g} mm for clearance, then performs "
        f"{args.zhop_cycles} pairs of +/-{args.zhop_distance:g} mm Z moves.\n"
        "This more closely exercises the repeated small Z-hop reversals used during a print."
    )
    if _prompt_token("Type ZHOP to run it, or anything else to skip: ", "ZHOP"):
        _relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        _fine_z_reversal_stress(
            client,
            distance=args.zhop_distance,
            cycles=args.zhop_cycles,
            feed=args.feed,
        )
        stressed_position = client.command("M114")
        stress_note = _prompt_observation(
            f"Fine-Z stress finished. Before: {away_position}; after: {stressed_position}\n"
            "Visually confirm the bed is still safely clear. Record any sound or motion anomaly: "
        )
        returned, return_position, return_note = _return_from_clearance(
            client, args, stage="fine Z-reversal stress"
        )
        optional_results["zhop"] = {
            "away_position": away_position,
            "stressed_position": stressed_position,
            "stress_note": stress_note,
            "return_position": return_position,
            "return_note": return_note,
            "returned": returned,
        }
        if not returned:
            return {
                "aborted": True,
                "stage": "zhop_bed_lowered",
                "baseline_position": baseline_position,
                "baseline_note": baseline_note,
                "cycles": cycle_results,
                "optional": optional_results,
                "bed_left_lowered": True,
            }

    print(
        "\nOptional XY-motion stress phase:\n"
        f"This lowers the bed {args.distance:g} mm, then makes {args.xy_cycles} fast rectangular "
        "carriage sweeps while staying away from both nozzle-selector walls.\n"
        "It tests whether ordinary print-like carriage motion or vibration changes the nozzle height."
    )
    if _prompt_token("Type MOTION to run it, or anything else to skip: ", "MOTION"):
        _relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        _xy_motion_stress(client, cycles=args.xy_cycles, feed=args.xy_feed)
        stressed_position = client.command("M114")
        stress_note = _prompt_observation(
            f"XY stress finished at X{IFAST_CENTER_X:g} Y{IFAST_CENTER_Y:g}. "
            f"Firmware position: {stressed_position}\n"
            "Record any looseness, clicking, nozzle movement, or other anomaly you noticed: "
        )
        returned, return_position, return_note = _return_from_clearance(
            client, args, stage="XY-motion stress"
        )
        optional_results["motion"] = {
            "away_position": away_position,
            "stressed_position": stressed_position,
            "stress_note": stress_note,
            "return_position": return_position,
            "return_note": return_note,
            "returned": returned,
        }
        if not returned:
            return {
                "aborted": True,
                "stage": "motion_bed_lowered",
                "baseline_position": baseline_position,
                "baseline_note": baseline_note,
                "cycles": cycle_results,
                "optional": optional_results,
                "bed_left_lowered": True,
            }

    print(
        "\nOptional automatic nozzle-selector phase:\n"
        f"This lowers the bed {args.distance:g} mm, then automatically traverses between the two "
        f"latch walls {args.selector_cycles} times at F{args.selector_feed:g}.\n"
        f"It ends with {nozzle} physically latched, then returns to X{IFAST_CENTER_X:g} "
        f"Y{IFAST_CENTER_Y:g} for the paper-gap comparison."
    )
    if _prompt_token("Type SELECTOR to run it, or anything else to finish: ", "SELECTOR"):
        _relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        _selector_stress(
            client,
            tool=args.tool,
            cycles=args.selector_cycles,
            feed=args.selector_feed,
        )
        stressed_position = client.command("M114")
        stress_note = _prompt_observation(
            f"Selector cycling finished with {nozzle} latched and the carriage centered.\n"
            f"Firmware position: {stressed_position}\n"
            "Record any incomplete latch, odd sound, or visibly different nozzle position: "
        )
        returned, return_position, return_note = _return_from_clearance(
            client, args, stage="automatic selector cycling"
        )
        optional_results["selector"] = {
            "away_position": away_position,
            "stressed_position": stressed_position,
            "stress_note": stress_note,
            "return_position": return_position,
            "return_note": return_note,
            "returned": returned,
        }
        if not returned:
            return {
                "aborted": True,
                "stage": "selector_bed_lowered",
                "baseline_position": baseline_position,
                "baseline_note": baseline_note,
                "cycles": cycle_results,
                "optional": optional_results,
                "bed_left_lowered": True,
            }

    return {
        "aborted": False,
        "baseline_position": baseline_position,
        "baseline_note": baseline_note,
        "cycles": cycle_results,
        "optional": optional_results,
        "warning": (
            "M114 reports firmware coordinates only; compare them with the physical paper-gap "
            "observations to detect mechanical drift or lost motion"
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
