# Roadmap

## Milestone 1 — protocol proof

- [x] UDP request/reply transport
- [x] handshake, firmware, and status parsing
- [x] binary upload framing
- [x] bounded resend handling
- [x] mock printer and integration tests
- [x] conservative command-line client
- [x] physical i-Fast handshake/status verification
- [x] physical plain-G-code upload and print verification

## Milestone 2 — Cura 5.13 network integration

- [x] manual network configuration UI
- [x] serialized background protocol worker
- [x] Cura GCodeWriter to temporary plain `.gcode`
- [x] upload progress and actionable errors
- [x] optional explicit “upload and start” action
- [x] Windows Cura 5.13 installation and transfer tests
- [x] physical validation of live in-Cura address changes

## Milestone 3 — i-Fast slicing definitions

- [x] initial 330 × 250 × 320 mm dual-extrusion geometry
- [x] two 0.4 mm / 1.75 mm extruder definitions
- [x] conservative Marlin start/end G-code baseline
- [x] development installer support for Cura definition and extruder resources
- [x] staged dual-extrusion validation plan and checkerboard test model
- [ ] confirm T0/T1 physical nozzle mapping
- [ ] verify single-extruder operation through each nozzle
- [ ] compare Cura and QIDI Print tool-change G-code
- [ ] determine whether firmware calibration fully owns nozzle offsets
- [ ] validate repeated tool changes and prime-tower behavior
- [ ] add explicit single-extruder modes if required by Cura or firmware behavior
- [ ] baseline PLA profiles
- [ ] baseline PETG profiles
- [ ] mixed-material PLA/PVA validation

## Milestone 4 — monitoring and discovery

- [ ] temperature and print-progress polling
- [ ] pause/resume/cancel controls
- [ ] broadcast discovery with manual-IP fallback
- [ ] reconnect behavior and multi-interface tests

## Deferred

- Wi-Fi-interface warnings
- `.gcode.tz` compression
- automatic firmware updates
- undocumented service/control commands not required for printing
