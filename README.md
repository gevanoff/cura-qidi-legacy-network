# QIDI Legacy Cura

A clean, testable implementation of the legacy QIDI UDP network protocol, plus a Cura 5
output-device plugin targeting printers such as the **QIDI i-Fast**.

## Current milestone

The repository begins with the lowest-risk architecture:

- standalone Python protocol client with no Qt dependency;
- manual-IP handshake, firmware query, status polling, upload, and print-start commands;
- validated binary block framing and resend handling;
- mock UDP printer for repeatable integration tests;
- conservative CLI that uploads without starting a print unless `--start` is explicit;
- Cura API 8 plugin shell for the next phase.

The physical-printer probe is the next gate. Compression to `.gcode.tz` is deliberately
excluded until plain `.gcode` transfer is verified against the i-Fast.

## Development

```bash
python -m venv .venv
. .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest
```

## Safe physical-printer probe

This only performs a handshake and firmware query:

```bash
qidi-legacy probe 192.168.1.123
```

Read current temperatures and status:

```bash
qidi-legacy status 192.168.1.123
```

Upload a G-code file without starting it:

```bash
qidi-legacy upload 192.168.1.123 calibration_cube.gcode
```

Start immediately only when explicitly requested:

```bash
qidi-legacy upload 192.168.1.123 calibration_cube.gcode --start
```

## Project phases

1. Verify commands and responses against the physical i-Fast.
2. Capture any firmware-specific response differences as fixtures and tests.
3. Implement the Cura output device using the tested protocol package.
4. Add the i-Fast machine definition and dual-extruder profile.
5. Add discovery and monitoring after the manual-IP path is stable.

## Attribution

Protocol behavior was informed by publicly available legacy QIDI integrations, including
`alkaes/QidiPrint` and `philltran/cura-qidi-printer-integration`. This project is a new,
separated implementation designed for current Cura 5 architecture and testability.
