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

## Milestone 2 — Cura 5.13 manual-IP integration

- [ ] manual network configuration UI
- [x] serialized background protocol worker
- [x] Cura GCodeWriter to temporary plain `.gcode`
- [x] upload progress and actionable errors
- [x] optional explicit “upload and start” action
- [ ] Windows Cura 5.13 installation test

## Milestone 3 — i-Fast slicing definitions

- [ ] machine geometry and build plate
- [ ] left/right extruder definitions and offsets
- [ ] single-extruder modes
- [ ] verified start/end G-code
- [ ] baseline PLA/PETG profiles

## Milestone 4 — monitoring and discovery

- [ ] temperature and print-progress polling
- [ ] pause/resume/cancel controls
- [ ] broadcast discovery with manual-IP fallback
- [ ] reconnect behavior and multi-interface tests

## Deferred

- `.gcode.tz` compression
- automatic firmware updates
- undocumented service/control commands not required for printing
