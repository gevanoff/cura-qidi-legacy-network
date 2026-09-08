# QIDI i-Fast Z repeatability diagnostic

The `qidi-legacy` CLI includes two tools for low-level printer diagnosis:

```bash
qidi-legacy command 10.10.22.171 M114
qidi-legacy z-test 10.10.22.171
```

## Raw command mode

`command` sends one G-code command over the legacy QIDI UDP protocol and prints the printer's response.
Multiple shell tokens are joined with spaces, so both forms below are equivalent:

```bash
qidi-legacy command 10.10.22.171 "G0 Z5 F300"
qidi-legacy command 10.10.22.171 G0 Z5 F300
```

Raw commands bypass slicer safety. Do not send motion, heater, EEPROM, calibration, or firmware commands unless you understand their effect on the i-Fast.

## Guided Z test

The guided test is intended for diagnosing a changing nozzle-to-bed gap without altering the printer's stored Z offset.

```bash
qidi-legacy z-test 10.10.22.171 --tool 0 --distance 5 --cycles 3
```

On the i-Fast, positive Z lowers the bed away from the nozzle. The test therefore:

1. asks the operator to establish a known-safe paper gap and fully latch the nozzle being tested;
2. records `M114` as the firmware-reported baseline;
3. lowers the bed by the requested relative distance;
4. pauses for a physical observation;
5. requires the exact word `RETURN` before moving the bed back toward the nozzle;
6. pauses again for a paper-gap comparison;
7. repeats the away-and-return cycle;
8. optionally lowers the bed again and pauses while the operator cycles the mechanical nozzle selector, then returns to the same XY test point and compares the paper gap again.

The script never homes the printer and never changes the stored software Z offset. If the operator declines a `RETURN` prompt after the bed has been lowered, the test aborts with the bed left in the safer, lowered position.

Useful options:

```text
--tool 0       right nozzle / Nozzle 1 / T0
--tool 1       left nozzle / Nozzle 2 / T1
--distance 5   relative Z travel in mm
--cycles 3     number of away-and-return cycles
--feed 300     Z feed rate in mm/min
```

## Interpreting results

`M114` reports the firmware's coordinate belief, not measured physical motion. The useful comparison is therefore between the reported coordinates and the operator's repeated physical paper-gap observations.

- Same reported position and same paper drag: Z return is repeatable for that cycle.
- Same reported position but progressively tighter/looser paper drag: suspect mechanical drift, lost Z motion, or nozzle-selector seating changes.
- Gap changes only after selector cycling: suspect the mechanical dual-nozzle lift/latch mechanism.
- Physical Z travel differs from the commanded distance while `M114` remains numerically correct: suspect Z-drive mechanics or lost steps.

Keep the nozzle cool during paper-gap diagnostics and keep a hand near the printer's stop control whenever returning the bed toward the nozzle.
