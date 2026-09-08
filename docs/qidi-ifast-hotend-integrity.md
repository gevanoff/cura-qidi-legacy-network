# QIDI i-Fast hotend integrity preflight

Do not run the guided Z/motion diagnostic or another print while a hotend leak or relative-nozzle-height fault is unresolved.

Before `qidi-z-test` may proceed, verify all of the following:

- molten filament exits only from the nozzle orifice, not from above the nozzle, heater-block threads, heatbreak area, or inside the extruder;
- both hotends are firmly seated and cannot rock or shift vertically in the carriage;
- selecting T0/right makes the right nozzle the lowest physical nozzle;
- selecting T1/left makes the left nozzle the lowest physical nozzle;
- the inactive nozzle has visible clearance above the selected nozzle in both selector states;
- the selector/lift mechanism fully and repeatably reaches both states;
- heater and thermistor wires are clean, secure, unpinched, and undamaged.

The CLI requires the exact token `MECHREADY` after this inspection. It then proceeds to the existing hot-state `HOTREADY` gate.

## Why leakage is a hard stop

A leak above the nozzle can deposit molten filament around the heater block and hotend. That material can flow downward and form a hanging blob below the calibrated metal nozzle tip. The blob can then contact the build plate or print even if the nozzle itself began at a safe Z height.

External melt around the heater block also indicates that the filament path is not sealed correctly. Common causes include a loose or incorrectly seated nozzle/heatbreak interface, a loose/damaged hotend, or a cracked/damaged heatbreak. Correct the mechanical problem before recalibrating Z.

## Inspection order

1. Unload filament if practical.
2. Allow the printer to cool and power it off before close mechanical inspection or touching hotend wiring.
3. Remove covers/silicone sock as appropriate and inspect for plastic above the nozzle threads or around the heater block/heatbreak.
4. Check both hotends for vertical play or a mounting bracket that is not seated flush.
5. Check selector travel with the bed lowered well clear of both nozzles.
6. Repair or replace the leaking/loose hotend before attempting hot leveling or motion tests.
7. Only after the assembly is mechanically sound, heat to actual print temperatures, thermally stabilize, and establish Z with a metal feeler gauge.
