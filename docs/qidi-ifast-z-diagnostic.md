# QIDI i-Fast motion and Z repeatability diagnostic

The low-level tools are:

```bash
qidi-legacy command "$QIDI_IP" M114
qidi-z-test "$QIDI_IP"
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
qidi-z-test "$QIDI_IP" --tool 0 --distance 5 --cycles 1
```

Before starting, X/Y must already have been homed. Fully latch the nozzle being tested, move to the repeatable center-bed point `X165 Y125`, and establish a light but clearly detectable paper drag using ordinary Z jogging. Do not use the stored Z-offset adjustment as the test positioning control.

On the i-Fast, positive Z lowers the bed away from the nozzle. The basic test records `M114`, lowers the bed by the configured clearance distance, waits for motion completion, then requires the exact word `RETURN` before moving the bed back toward the nozzle for another paper-gap comparison.

If the large Z cycle is repeatable, the CLI offers three more targeted phases.

### ZHOP

`ZHOP` lowers the bed for clearance, reads the current Z with `M114`, then alternates between two **absolute** Z targets: the baseline and baseline + 0.2 mm by default. It explicitly commands the baseline again before finishing.

This matches Cura's normal `G90` absolute Z-hop behavior more closely than the earlier relative `G91` stress test. Relative UDP motion was removed after a physical test ended exactly +0.2 mm from its starting Z, showing that a missed or duplicated relative command could permanently bias the diagnostic itself.

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

The path intentionally stays away from the nozzle selector. It ends at `X165 Y125`, returns the bed only after explicit confirmation, and asks for another paper-gap comparison.

Defaults:

```text
--xy-cycles 10
--xy-feed 6000
```

### SELECTOR

`SELECTOR` lowers the bed for clearance and automatically cycles the physical nozzle selector using the i-Fast's **front selector lane**, approximately `Y5`. QIDI's own startup sequence uses front-corner positions around `X0 Y6` and `X330 Y4`; selector motion at the bed centerline does not reach the mechanism.

For `--tool 0`, each cycle contacts approximately `X0 Y5` and then `X330 Y5`, ending with the right / Nozzle 1 / T0 nozzle physically latched. For `--tool 1`, the order is reversed. The carriage then returns to `X165 Y125` before the bed is returned for the paper-gap check.

Defaults:

```text
--selector-cycles 3
--selector-feed 3600
```

## Safety behavior

The script never homes the printer and never changes the stored software Z offset. Every stress phase first lowers the bed by the configured clearance distance. If the operator declines a `RETURN` prompt, the test aborts with the bed left lowered.

Normal UDP commands keep the short client timeout. Only `M400` motion-completion barriers receive a longer timeout.

## Interpreting results

`M114` reports the firmware's coordinate belief, not measured physical motion. Compare reported coordinates with repeated physical paper-gap observations.

- Basic Z returns to the same coordinate and same paper drag: gross Z return is repeatable under cool, unloaded conditions.
- Absolute ZHOP ends at its baseline coordinate but the paper gap changes: investigate mechanical small-motion repeatability, backlash, binding, or step loss.
- MOTION changes the gap: investigate hotend/carriage settling or vibration-sensitive looseness.
- SELECTOR changes the gap: investigate the dual-nozzle lift/latch mechanism or nozzle seating height.
- All cool tests are stable but a real print still progressively loses clearance: thermal effects, heater-related hotend movement, print-time firmware behavior, or another print-specific condition become more likely.
- Physical travel differs from the command while `M114` remains numerically correct: investigate Z-drive mechanics or lost steps.

Keep the nozzle cool during these initial paper-gap diagnostics and keep a hand near the printer's stop control whenever returning the bed toward the nozzle.
