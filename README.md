# Cura QIDI Legacy Network

A clean, testable implementation of the legacy QIDI UDP network protocol, plus a Cura 5
output-device plugin targeting printers such as the **QIDI i-Fast**.

## Current status

The protocol layer has been physically verified on a QIDI i-Fast running firmware V3.40:

- handshake, firmware query, and status polling;
- plain `.gcode` upload with the printer-specific save response;
- touchscreen and network print start;
- successful completion of real QIDI Print-generated test prints.

The current development milestone is the Cura 5.13 manual-IP output device. Its first build adds
separate **Upload to QIDI** and **Upload and Print** actions and performs network work in a Cura
background job.

## Development

```bash
python -m venv .venv
. .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest
```

## CLI usage

```bash
qidi-legacy probe 192.168.1.123
qidi-legacy status 192.168.1.123
qidi-legacy upload 192.168.1.123 calibration_cube.gcode
qidi-legacy upload 192.168.1.123 calibration_cube.gcode --start
```

Upload does not start a print unless `--start` is explicit.

## Cura 5.13 development installation

Close Cura before installing. From WSL, run:

```bash
python scripts/install_cura_plugin.py \
  --cura-config /mnt/c/Users/paper/AppData/Roaming/cura/5.13 \
  --host 10.10.22.122
```

The installer creates:

```text
C:\Users\paper\AppData\Roaming\cura\5.13\plugins\QidiLegacyNetwork
```

Restart Cura, slice a model, and open the output-action dropdown. The development plugin provides:

- **Upload to QIDI** — transfers the G-code without starting it;
- **Upload and Print** — transfers the G-code and explicitly starts it.

This first build takes the host during installation. A Cura configuration dialog is planned after
the output-device path has been validated in Cura 5.13.

## Project phases

1. Verify commands and responses against the physical i-Fast. **Complete.**
2. Implement and validate the Cura 5.13 manual-IP output device. **In progress.**
3. Add the i-Fast machine definition and dual-extruder profile.
4. Add monitoring, controls, and discovery after the manual-IP path is stable.

## Attribution

Protocol behavior was informed by publicly available legacy QIDI integrations, including
`alkaes/QidiPrint` and `philltran/cura-qidi-printer-integration`. This project is a new,
separated implementation designed for current Cura 5 architecture and testability.
