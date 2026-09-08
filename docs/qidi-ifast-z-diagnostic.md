# QIDI i-Fast motion and Z repeatability diagnostic

The `qidi-legacy` CLI includes two tools for low-level printer diagnosis:

```bash
qidi-legacy command "$QIDI_IP" M114
qidi-legacy z-test "$QIDI_IP"
```

## Raw command mode

`command` sends one G-code command over the legacy QIDI UDP protocol and prints the printer's response. Multiple shell tokens are joined with spaces, so both forms below are equivalent:

```bash
qidi-legacy command "$QIDI_IP" "G0 Z5 F300"
qidi-legacy command "$QIDI_IP" G0 Z5 F300
```

Raw commands bypass slicer safety. Do not send motion, heater, EEPROM, calibration, or firmware commands unless you understand their effect on the i-Fast.

## Guided diagnostic

The guided test is intended for diagnosing a changing nozzle-to-bed gap without altering the printer's stored Z offset.

```bash
qidi-legacy z-test "$QIDI_IP" --tool 0 --distance 5 --cycles 3
```

Before starting, X/Y must already have been homed. Fully latch the nozzle being tested, move to the repeatable center-bed point `X165 Y125`, and establish a light but clearly detectable paper drag using ordinary Z jogging. Do not use the stored Z-offset adjustment as the test positioning control.

On the i-Fast, positive Z lowers the bed away from the nozzle. The basic test:

1. records `M114` as the firmware-reported baseline;
2. lowers the bed by the requested relative distance;
3. waits for the motion to finish with `M400`;
4. pauses for a physical observation;
5. requires the exact word `RETURN` before moving the bed back toward the nozzle;
6. pauses again for a paper-gap comparison;
7. repeats the away-and-return cycle.

If those large Z cycles are repeatable, the CLI offers three more targeted phases.

### ZHOP

`ZHOP` lowers the bed by the normal clearance distance, then performs repeated small `+0.2/-0.2 mm` Z reversals before returning to the same paper-gap test point. This more closely resembles the repeated Z-hop reversals in the current Cura reliability profile than a few large 5 mm moves do.

Defaults:

```text
--zhop-cycles 100
--zhop-distance 0.2
```

### MOTION

`MOTION` lowers the bed for clearance, then moves the carriage repeatedly around a rectangle inside the build area:

```text
X30 Y30
X300 Y30
X300 Y220
X30 Y220
```

The path intentionally stays away from `X0` and `X330`, so it does not actuate the nozzle selector. It ends at `X165 Y125`, returns the bed only after explicit confirmation, and asks for another paper-gap comparison. This tests whether ordinary print-like XY motion or vibration changes nozzle height.

Defaults:

```text
--xy-cycles 10
--xy-feed 6000
```

### SELECTOR

`SELECTOR` no longer requires slow touchscreen jogging. With the bed lowered for clearance, the script automatically drives the carriage to both physical latch walls at the same general speed class used by the i-Fast startup profile.

For `--tool 0`, each cycle contacts `X0` and then `X330`, ending with the right / Nozzle 1 / T0 nozzle physically latched. For `--tool 1`, the order is reversed so the left / Nozzle 2 / T1 nozzle is left latched. The carriage then returns to `X165 Y125` before the bed is returned for the paper-gap check.

Defaults:

```text
--selector-cycles 3
--selector-feed 3600
```

The selector phase tests the physical lift/latch mechanism only; it does not heat or extrude filament and does not need to change logical Cura tool state.

## Safety behavior

The script never homes the printer and never changes the stored software Z offset. Every diagnostic stress phase first lowers the bed by the configured clearance distance. If the operator declines a `RETURN` prompt, the test aborts with the bed left in the safer lowered position.

All individual diagnostic moves are followed by, or grouped behind, `M400` before the script asks for a physical observation, so the observation is made after the queued motion completes.

Useful options:

```text
--tool 0               right nozzle / Nozzle 1 / T0
--tool 1               left nozzle / Nozzle 2 / T1
--distance 5           clearance Z travel in mm
--cycles 3             basic away-and-return cycles
--feed 300             Z feed rate in mm/min
--zhop-cycles 100      small reversal pairs
--zhop-distance 0.2    small reversal distance in mm
--xy-cycles 10         print-like XY sweep cycles
--xy-feed 6000         XY stress feed rate in mm/min
--selector-cycles 3    wall-to-wall mechanical latch cycles
--selector-feed 3600   selector-wall feed rate in mm/min
```

## Interpreting results

`M114` reports the firmware's coordinate belief, not measured physical motion. The useful comparison is therefore between reported coordinates and repeated physical paper-gap observations.

- Basic Z cycles repeat with the same paper drag: gross Z return is repeatable under light-load, cool conditions.
- Basic Z is stable but ZHOP changes the gap: investigate small-motion Z reversal, backlash, binding, or step loss.
- Z phases are stable but MOTION changes the gap: investigate hotend/carriage mechanical settling or vibration-sensitive looseness.
- Gap changes only after SELECTOR: investigate the dual-nozzle lift/latch mechanism or nozzle seating height.
- All cool tests are stable but a real print still progressively loses clearance: thermal effects, heater-related hotend movement, firmware behavior during a print, or another print-specific condition become more likely.
- Physical travel differs from the command while `M114` remains numerically correct: investigate Z-drive mechanics or lost steps.

Keep the nozzle cool during these initial paper-gap diagnostics and keep a hand near the printer's stop control whenever returning the bed toward the nozzle.
