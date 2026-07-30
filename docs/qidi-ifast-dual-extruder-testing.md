# QIDI i-Fast dual-extruder validation plan

This plan validates the Cura machine definition in progressively riskier stages. Do not begin with a large model or dissimilar materials. The initial definition deliberately leaves both Cura extruder offsets at zero because the i-Fast stores its own dual-nozzle calibration; applying an unverified slicer offset could compensate twice.

## Prepare the printer

1. Install the dual-extruder carriage that will be used for testing.
2. Confirm that both nozzles are the same nominal diameter. The initial definitions assume 0.4 mm.
3. Mechanically level the two nozzles according to QIDI's procedure so the inactive nozzle does not drag through the print.
4. Run the printer's built-in double-extruder calibration (`E_calibration.gcode`) and complete **Calibrate E** on the touchscreen until its reference features align.
5. Use two contrasting colors of the same PLA family for early tests. Avoid PLA/PVA, PLA/TPU, or other mixed-material combinations until tool changes are proven.
6. Clean and level the bed. Keep the heated chamber off for PLA unless the filament manufacturer specifically requires otherwise.
7. Reserve enough time to watch every first tool change. Do not leave an early dual-extrusion test unattended.

## Capture a known-good QIDI reference

Before changing Cura compensation or tool-change behavior, slice one small dual-color object in QIDI Print with the same two PLA materials and save the plain `.gcode` file. Preserve:

- the QIDI Print version;
- machine/extruder selection;
- nozzle diameter;
- temperatures and retraction settings;
- whether a prime tower, ooze shield, or wipe structure was enabled;
- the first 150 lines of G-code;
- 100–200 lines surrounding the first `T0`/`T1` tool change;
- the final 100 lines.

This reference will show whether QIDI Print relies only on `T0`/`T1` and firmware-stored offsets or emits additional offset, parking, purge, or temperature commands.

## Stage 1 — definition and slicing only

1. Install the branch resources with Cura closed.
2. Add **QIDI Tech > QIDI i-Fast** as a new printer.
3. Confirm the build volume is 330 × 250 × 320 mm and two extruders appear.
4. Confirm both extruders default to a 0.4 mm nozzle and 1.75 mm filament.
5. Slice a small single-extruder cube with Extruder 1, then with Extruder 2.
6. Inspect the generated G-code before printing:
   - Extruder 1 should use `T0` when a tool selection is needed.
   - Extruder 2 should use `T1`.
   - No unsupported MakerBot-style commands such as `M135`, `M132`, or `G130` should appear.
   - Temperatures should be associated with the intended tool.

## Stage 2 — single-extruder physical tests

Print the same small calibration object separately with each tool.

For each test, record:

- physical nozzle used by `T0` or `T1`;
- first-layer position and direction;
- nozzle and bed temperatures;
- extrusion direction and amount;
- whether the inactive nozzle drags or oozes;
- whether the print ends safely without an unexpected XY move.

Stop immediately if the wrong nozzle heats, the printer homes in an unsafe direction, or an inactive nozzle strikes the bed or model.

## Stage 3 — minimal two-color tool-change test

Use two adjacent or interlocking parts no more than 30 mm across and 2–4 mm tall. Assign one part to each extruder. Enable a small prime tower only after verifying that Cura places it inside the build volume.

Watch and record:

1. Which physical nozzle starts.
2. Commands and motion at the first tool change.
3. Whether the outgoing nozzle retracts sufficiently.
4. Whether the incoming nozzle reaches temperature before extrusion.
5. Whether either nozzle parks or wipes outside the printable area.
6. Whether the two colors meet without a systematic X/Y displacement.
7. Whether the inactive nozzle drags through deposited plastic.

Photograph the top surface with the X and Y directions marked.

## Stage 4 — determine offset ownership

If the printer's built-in calibration is correct and the Cura two-color boundaries align, leave both Cura offsets at zero.

If a consistent displacement remains:

1. Measure the signed X and Y displacement with calipers or a calibration microscope.
2. Repeat the print once to verify the error is reproducible.
3. Compare the Cura G-code with the known-good QIDI Print G-code around tool changes.
4. Determine whether the firmware calibration is being ignored, applied once, or effectively applied twice.
5. Change slicer offsets only after that comparison.

Do not compensate by eye from one print. A wrong sign convention can double the error or push a nozzle outside the safe build area.

## Stage 5 — repeated tool changes

After one tool change is safe, use a short model with 10–20 alternating layers. Evaluate:

- accumulated X/Y alignment error;
- ooze and color contamination;
- prime-tower stability;
- standby temperature behavior;
- retraction and unretraction;
- nozzle collisions with the model;
- cooling-fan behavior for both tools.

## Stage 6 — mixed materials

Only after same-material testing succeeds should PLA/PVA or another mixed pair be attempted. Mixed-material work requires separate validation of temperature, standby temperature, retraction, purge volume, bed adhesion, chamber temperature, and material compatibility.

## Report template

For each test, provide:

- Cura version and branch/plugin version;
- printer firmware version;
- normal or high-temperature dual-extruder carriage;
- nozzle diameters;
- physical mapping of T0 and T1;
- materials and temperatures;
- model and extruder assignments;
- prime tower/ooze shield settings;
- result and photographs;
- generated G-code around the first tool change;
- any touchscreen calibration values changed before the test.
