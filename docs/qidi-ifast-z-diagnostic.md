# QIDI i-Fast hot-state motion and Z repeatability diagnostic

The low-level tools are:

```bash
qidi-legacy command "$QIDI_IP" M114
qidi-z-test "$QIDI_IP"
```

## Critical calibration rule: match the printing thermal state

Nozzle height, leveling, Z-offset checks, and the guided diagnostic must be performed with the printer at the same thermal state used for the actual print.

For a PLA job, that normally means the active nozzle and bed are already at the intended PLA printing temperatures before the final gap is established. For other materials, use that material's actual print temperatures instead.

A cold calibration is not a valid reference for a hot print: the nozzle/hotend assembly and bed change dimension as they heat. A gap that is safe cold can therefore be substantially different once printing temperatures are reached.

Before final leveling or gap verification:

1. home the machine as required by the printer;
2. fully latch the nozzle that will be active;
3. heat the active nozzle and bed to the intended print temperatures;
4. allow them to remain at temperature long enough for the hotend and bed to stabilize;
5. clean the hot nozzle tip so filament ooze cannot falsify the measurement;
6. perform the final leveling/Z-gap adjustment in that hot, stabilized state.

Use a **metal feeler gauge** for hot measurements. Approximately `0.10 mm` is convenient for repeatability, but the exact thickness is less important than using the same gauge and the same drag/contact criterion throughout the test. Do not use paper against a printing-temperature nozzle.

## Raw command mode

`command` sends one G-code command over the legacy QIDI UDP protocol and prints the printer's response. Multiple shell tokens are joined with spaces, so both forms below are equivalent:

```bash
qidi-legacy command "$QIDI_IP" "G0 Z5 F300"
qidi-legacy command "$QIDI_IP" G0 Z5 F300
```

Raw commands bypass slicer safety. Do not send motion, heater, EEPROM, calibration, or firmware commands unless you understand their effect on the i-Fast.

## Guided diagnostic

Run the dedicated hot-state diagnostic with:

```bash
qidi-z-test "$QIDI_IP" --tool 0 --distance 5 --cycles 1
```

The diagnostic itself does **not** set heater temperatures. Configure and stabilize the printer first, then type `HOTREADY` only after the active nozzle and bed are already at the intended print temperatures.

Before starting the script:

- X/Y must already have been homed;
- the intended nozzle must be fully latched;
- the nozzle and bed must be at stabilized print temperatures;
- the carriage should be at `X165 Y125`;
- the hot nozzle tip should be clean;
- establish a repeatable reference using the same metal feeler gauge you will use for every later comparison.

Do not use the stored Z-offset adjustment as a substitute for the temporary movement needed to establish a diagnostic reference point.

On the i-Fast, positive Z lowers the bed away from the nozzle.

## THERMAL: stationary hot-soak phase

Before any motion stress, the diagnostic offers a `THERMAL` phase. It commands **no axis motion**. The printer remains at print temperature for another five minutes while the gauge is removed.

At the end of the hold, the script records another `M114` result and asks you to reinsert the same feeler gauge at the same XY point.

Interpretation:

- unchanged firmware position and unchanged gauge drag: the hot state appears stable over the hold;
- unchanged firmware position but tighter/looser gauge drag: physical thermal drift is occurring despite unchanged commanded coordinates;
- significant drift here makes later mechanical stress phases secondary until the thermal reference is understood.

## Basic hot Z cycle

The basic test records `M114`, lowers the bed by the configured clearance distance, waits for motion completion, then requires the exact word `RETURN` before moving the bed back toward the hot nozzle for another feeler-gauge comparison.

A clean result is the same firmware Z coordinate and the same feeler-gauge drag after the away/return cycle.

## ZHOP

`ZHOP` lowers the bed for clearance, reads the current Z with `M114`, then alternates between two **absolute** Z targets: the baseline and baseline + 0.2 mm by default. It explicitly commands the baseline again before finishing.

This matches Cura's normal `G90` absolute Z-hop behavior. Relative UDP motion was removed after a physical test ended exactly +0.2 mm from its starting Z, showing that a missed or duplicated relative command could permanently bias the diagnostic itself.

Defaults:

```text
--zhop-cycles 100
--zhop-distance 0.2
```

## MOTION

`MOTION` lowers the bed for clearance, then moves the hot carriage repeatedly around a rectangle inside the build area:

```text
X30 Y30
X300 Y30
X300 Y220
X30 Y220
```

The path intentionally stays away from the nozzle selector. It ends at `X165 Y125`, returns the bed only after explicit confirmation, and asks for another hot feeler-gauge comparison.

The default 10-cycle path is about 9.34 m of XY travel. At the default 6000 mm/min feed, nominal motion time alone is about 93 seconds, so the final `M400` wait uses a timeout computed from the commanded path length and feed rate, with margin for acceleration and firmware overhead. The larger timeout is only a maximum wait; `M400` returns as soon as motion actually finishes.

Defaults:

```text
--xy-cycles 10
--xy-feed 6000
```

## SELECTOR

`SELECTOR` lowers the bed for clearance and cycles the physical nozzle selector while the hotend remains at print temperature. It uses the i-Fast's **front selector lane**, approximately `Y5`.

QIDI's own startup sequence uses front-corner positions around `X0 Y6` and `X330 Y4`; selector motion at the bed centerline does not reach the mechanism.

For `--tool 0`, each cycle contacts approximately `X0 Y5` and then `X330 Y5`, ending with the right / Nozzle 1 / T0 nozzle physically latched. For `--tool 1`, the order is reversed. The carriage then returns to `X165 Y125` before the bed is returned for the hot feeler-gauge check.

Defaults:

```text
--selector-cycles 3
--selector-feed 3600
```

## Safety behavior

The script never homes the printer, never changes the stored software Z offset, and does not control heater setpoints. The operator is responsible for establishing and maintaining the desired print temperatures.

Every motion stress phase first lowers the bed by the configured clearance distance. If the operator declines a `RETURN` prompt, the test aborts with the bed left lowered.

The nozzle is intentionally hot during the test. Do not touch the hotend or nozzle. Keep the build plate clear, remove the feeler gauge before automated movement, and reinsert it only when prompted for a stationary measurement.

Normal UDP commands keep the short client timeout. Only `M400` motion-completion barriers receive longer, motion-appropriate timeouts.

## Interpreting results

`M114` reports the firmware's coordinate belief, not measured physical motion. The useful evidence is the combination of firmware coordinates, the repeated metal feeler-gauge measurements, and the controlled thermal state.

- THERMAL changes the physical gap with no commanded motion: investigate thermal expansion/creep and calibration soak time first.
- Basic hot Z returns to the same coordinate and same gauge drag: gross Z return is repeatable at print temperature.
- Absolute hot ZHOP ends at its baseline coordinate but the gauge gap changes: investigate mechanical small-motion repeatability, backlash, binding, or step loss.
- HOT MOTION changes the gap: investigate hotend/carriage settling or vibration-sensitive looseness.
- HOT SELECTOR changes the gap: investigate the dual-nozzle lift/latch mechanism or nozzle seating height at operating temperature.
- All hot tests are stable but a real print still progressively loses clearance: investigate print-time firmware behavior, extrusion forces, model-specific interference, or another condition not reproduced by the diagnostic.
- Physical travel differs from the command while `M114` remains numerically correct: investigate Z-drive mechanics or lost steps.
