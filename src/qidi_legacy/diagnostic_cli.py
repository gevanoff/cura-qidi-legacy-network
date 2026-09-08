from __future__ import annotations

import math
import re
import sys
import time

from . import cli

MOTION_WAIT_TIMEOUT = 30.0
MOTION_TIMEOUT_MARGIN = 15.0
MOTION_TIMEOUT_MULTIPLIER = 1.5
IFAST_SELECTOR_Y = 5.0
THERMAL_HOLD_SECONDS = 300.0
SUGGESTED_GAUGE_MM = 0.10


def _wait_for_motion(client: object, *, timeout: float = MOTION_WAIT_TIMEOUT) -> None:
    """Wait for queued motion without changing the normal command timeout."""
    client.command("M400", timeout=timeout, retries=1)


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
    """Exercise Cura-style absolute Z hops and explicitly finish at the baseline Z."""
    base_z = _reported_z(client)
    hop_z = base_z + distance

    client.command("G90")
    for _ in range(cycles):
        client.command(f"G0 Z{hop_z:g} F{feed:g}")
        client.command(f"G0 Z{base_z:g} F{feed:g}")

    client.command(f"G0 Z{base_z:g} F{feed:g}")
    _wait_for_motion(client)


def _xy_motion_distance(cycles: int) -> float:
    """Return the commanded XY path length for the diagnostic motion phase."""
    center_to_corner = math.hypot(
        cli.IFAST_CENTER_X - cli.IFAST_MOTION_X_LOW,
        cli.IFAST_CENTER_Y - cli.IFAST_MOTION_Y_LOW,
    )
    horizontal = cli.IFAST_MOTION_X_HIGH - cli.IFAST_MOTION_X_LOW
    vertical = cli.IFAST_MOTION_Y_HIGH - cli.IFAST_MOTION_Y_LOW

    return (
        center_to_corner
        + cycles * (horizontal + vertical + horizontal)
        + max(0, cycles - 1) * vertical
        + center_to_corner
    )


def _xy_motion_timeout(cycles: int, feed: float) -> float:
    """Choose an M400 timeout from commanded distance and nominal feed rate."""
    if cycles < 1:
        raise ValueError("cycles must be at least 1")
    if feed <= 0:
        raise ValueError("feed must be positive")

    nominal_seconds = _xy_motion_distance(cycles) / (feed / 60.0)
    return max(
        MOTION_WAIT_TIMEOUT,
        nominal_seconds * MOTION_TIMEOUT_MULTIPLIER + MOTION_TIMEOUT_MARGIN,
    )


def _xy_motion_stress(client: object, *, cycles: int, feed: float) -> None:
    """Run print-like XY sweeps and allow enough time for all queued motion."""
    client.command("G90")
    for _ in range(cycles):
        client.command(
            f"G0 X{cli.IFAST_MOTION_X_LOW:g} Y{cli.IFAST_MOTION_Y_LOW:g} F{feed:g}"
        )
        client.command(
            f"G0 X{cli.IFAST_MOTION_X_HIGH:g} Y{cli.IFAST_MOTION_Y_LOW:g} F{feed:g}"
        )
        client.command(
            f"G0 X{cli.IFAST_MOTION_X_HIGH:g} Y{cli.IFAST_MOTION_Y_HIGH:g} F{feed:g}"
        )
        client.command(
            f"G0 X{cli.IFAST_MOTION_X_LOW:g} Y{cli.IFAST_MOTION_Y_HIGH:g} F{feed:g}"
        )
    client.command(f"G0 X{cli.IFAST_CENTER_X:g} Y{cli.IFAST_CENTER_Y:g} F{feed:g}")
    _wait_for_motion(client, timeout=_xy_motion_timeout(cycles, feed))


def _selector_stress(
    client: object,
    *,
    tool: int,
    cycles: int,
    feed: float,
) -> None:
    """Cycle the i-Fast front-corner selector latches and end with the requested nozzle down."""
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


def _thermal_hold(seconds: float) -> None:
    """Hold the printer stationary while the operator maintains print temperatures."""
    time.sleep(seconds)


def _return_from_clearance_hot(
    client: object,
    args: object,
    *,
    stage: str,
) -> tuple[bool, str | None, str | None]:
    if not cli._prompt_token(
        f"Type RETURN to bring the bed back toward the hot nozzle by {args.distance:g} mm; "
        "anything else leaves it lowered and aborts: ",
        "RETURN",
    ):
        return False, None, None

    cli._relative_z_move(client, -args.distance, args.feed)
    position = client.command("M114")
    note = cli._prompt_observation(
        f"Firmware position after return: {position}\n"
        f"At X{cli.IFAST_CENTER_X:g} Y{cli.IFAST_CENTER_Y:g}, reinsert the SAME metal "
        f"feeler gauge after {stage}. Describe its drag/contact now: "
    )
    return True, position, note


def _guided_hot_z_test(client: object, args: object) -> dict[str, object]:
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
        "\nGuided QIDI i-Fast HOT motion/Z repeatability test\n"
        "-------------------------------------------------\n"
        "This test does NOT home the printer and does NOT modify the stored Z offset.\n"
        "Positive Z lowers the i-Fast bed away from the nozzle.\n"
        "All gap measurements must be made at the same thermal state used for printing.\n"
        "Before continuing:\n"
        "  1. Printer must be idle and X/Y must already have been homed.\n"
        f"  2. Heat {nozzle} and the bed to the intended PRINT temperatures.\n"
        "  3. Hold those temperatures long enough for the hotend and bed to stabilize.\n"
        f"  4. Fully latch {nozzle}.\n"
        f"  5. Put the carriage at X{cli.IFAST_CENTER_X:g} Y{cli.IFAST_CENTER_Y:g}.\n"
        "  6. Clean/wipe the hot nozzle tip so ooze cannot falsify the gap measurement.\n"
        f"  7. Establish a repeatable reference with a METAL feeler gauge "
        f"(~{SUGGESTED_GAUGE_MM:.2f} mm is convenient).\n"
        "Do not use paper against a printing-temperature nozzle. Avoid touching the hotend.\n"
        "The script only returns from a lowered-clearance position after you type RETURN.\n"
    )

    if not cli._prompt_token(
        "Type HOTREADY only after nozzle and bed are hot and thermally stabilized; "
        "anything else aborts: ",
        "HOTREADY",
    ):
        return {"aborted": True, "stage": "before_hot_start"}

    baseline_position = client.command("M114")
    baseline_note = cli._prompt_observation(
        f"Baseline firmware position: {baseline_position}\n"
        "Describe the metal feeler-gauge drag/contact and record nozzle/bed temperatures: "
    )

    thermal_result: dict[str, object] | None = None
    print(
        "\nOptional stationary thermal-stability phase:\n"
        f"No axes will move. Keep nozzle and bed at print temperatures for another "
        f"{THERMAL_HOLD_SECONDS / 60:g} minutes, then compare the same gauge gap.\n"
        "Remove the gauge during the hold."
    )
    if cli._prompt_token("Type THERMAL to run it, or anything else to skip: ", "THERMAL"):
        thermal_start_position = client.command("M114")
        _thermal_hold(THERMAL_HOLD_SECONDS)
        thermal_end_position = client.command("M114")
        thermal_note = cli._prompt_observation(
            f"Stationary hold complete. Start: {thermal_start_position}; "
            f"end: {thermal_end_position}\n"
            "Reinsert the SAME metal gauge at the SAME XY point. Describe drag/contact and "
            "record nozzle/bed temperatures now: "
        )
        thermal_result = {
            "seconds": THERMAL_HOLD_SECONDS,
            "start_position": thermal_start_position,
            "end_position": thermal_end_position,
            "note": thermal_note,
        }

    cycle_results: list[dict[str, object]] = []
    for cycle in range(1, args.cycles + 1):
        print(
            f"\nBasic HOT Z cycle {cycle}/{args.cycles}: lowering the bed by "
            f"{args.distance:g} mm at F{args.feed:g}."
        )
        cli._relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        away_note = cli._prompt_observation(
            f"Firmware position after moving away: {away_position}\n"
            "Confirm the bed physically moved away. Record any odd sound or hesitation: "
        )

        returned, return_position, return_note = _return_from_clearance_hot(
            client, args, stage=f"basic hot Z cycle {cycle}"
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
                "thermal": thermal_result,
                "cycles": cycle_results,
                "bed_left_lowered": True,
            }

    optional_results: dict[str, object] = {}

    print(
        "\nOptional HOT Z-hop phase:\n"
        f"This lowers the bed {args.distance:g} mm for clearance, then performs "
        f"{args.zhop_cycles} absolute Z-hop cycles of {args.zhop_distance:g} mm while hot."
    )
    if cli._prompt_token("Type ZHOP to run it, or anything else to skip: ", "ZHOP"):
        cli._relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        cli._fine_z_reversal_stress(
            client,
            distance=args.zhop_distance,
            cycles=args.zhop_cycles,
            feed=args.feed,
        )
        stressed_position = client.command("M114")
        stress_note = cli._prompt_observation(
            f"HOT Z-hop stress finished. Before: {away_position}; after: {stressed_position}\n"
            "Confirm the bed is still safely clear and record any anomaly: "
        )
        returned, return_position, return_note = _return_from_clearance_hot(
            client, args, stage="hot Z-hop stress"
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
                "thermal": thermal_result,
                "cycles": cycle_results,
                "optional": optional_results,
                "bed_left_lowered": True,
            }

    print(
        "\nOptional HOT XY-motion stress phase:\n"
        f"This lowers the bed {args.distance:g} mm, then makes {args.xy_cycles} fast rectangular "
        "carriage sweeps while the hotend remains at print temperature."
    )
    if cli._prompt_token("Type MOTION to run it, or anything else to skip: ", "MOTION"):
        cli._relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        cli._xy_motion_stress(client, cycles=args.xy_cycles, feed=args.xy_feed)
        stressed_position = client.command("M114")
        stress_note = cli._prompt_observation(
            f"HOT XY stress finished at X{cli.IFAST_CENTER_X:g} Y{cli.IFAST_CENTER_Y:g}. "
            f"Firmware position: {stressed_position}\n"
            "Record any looseness, clicking, nozzle movement, or other anomaly: "
        )
        returned, return_position, return_note = _return_from_clearance_hot(
            client, args, stage="hot XY-motion stress"
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
                "thermal": thermal_result,
                "cycles": cycle_results,
                "optional": optional_results,
                "bed_left_lowered": True,
            }

    print(
        "\nOptional HOT automatic nozzle-selector phase:\n"
        f"This lowers the bed {args.distance:g} mm, then traverses the front selector lane "
        f"{args.selector_cycles} times at F{args.selector_feed:g}.\n"
        f"It ends with {nozzle} latched, then returns to X{cli.IFAST_CENTER_X:g} "
        f"Y{cli.IFAST_CENTER_Y:g} for the hot gauge comparison."
    )
    if cli._prompt_token("Type SELECTOR to run it, or anything else to finish: ", "SELECTOR"):
        cli._relative_z_move(client, args.distance, args.feed)
        away_position = client.command("M114")
        cli._selector_stress(
            client,
            tool=args.tool,
            cycles=args.selector_cycles,
            feed=args.selector_feed,
        )
        stressed_position = client.command("M114")
        stress_note = cli._prompt_observation(
            f"HOT selector cycling finished with {nozzle} latched and carriage centered.\n"
            f"Firmware position: {stressed_position}\n"
            "Record any incomplete latch, odd sound, or visibly different nozzle position: "
        )
        returned, return_position, return_note = _return_from_clearance_hot(
            client, args, stage="hot selector cycling"
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
                "thermal": thermal_result,
                "cycles": cycle_results,
                "optional": optional_results,
                "bed_left_lowered": True,
            }

    return {
        "aborted": False,
        "thermal_state_required": True,
        "baseline_position": baseline_position,
        "baseline_note": baseline_note,
        "thermal": thermal_result,
        "cycles": cycle_results,
        "optional": optional_results,
        "warning": (
            "M114 reports firmware coordinates only; interpret them together with repeated metal "
            "feeler-gauge measurements made at the same stabilized print temperatures"
        ),
    }


def main() -> int:
    cli._wait_for_motion = _wait_for_motion
    cli._fine_z_reversal_stress = _fine_z_reversal_stress
    cli._xy_motion_stress = _xy_motion_stress
    cli._selector_stress = _selector_stress
    cli._return_from_clearance = _return_from_clearance_hot
    cli._guided_z_test = _guided_hot_z_test

    if len(sys.argv) < 2 or sys.argv[1] != "z-test":
        sys.argv.insert(1, "z-test")

    return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
