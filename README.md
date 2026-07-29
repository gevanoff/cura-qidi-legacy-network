# Cura QIDI Legacy Network

A clean, testable implementation of the legacy QIDI UDP network protocol, plus a Cura 5
output-device plugin targeting printers such as the **QIDI i-Fast**.

## Current status

The protocol layer has been physically verified on a QIDI i-Fast running firmware V3.40:

- handshake, firmware query, and status polling;
- plain `.gcode` upload with the printer-specific save response;
- touchscreen and network print start;
- successful completion of real QIDI Print-generated test prints;
- Cura-generated upload and print-start from Cura 5.13 on Windows;
- byte-identical file readback after disabling unsafe automatic file-block retries;
- remote filename and byte-size verification through the printer's multipart `M20` listing.

The Cura integration provides separate **Upload to QIDI** and **Upload and Print** actions and
performs network work in a Cura background job. Before reporting success or starting a print, it
requires the uploaded filename to appear in the remote file list with the same byte count as the
local G-code.

Upload results are also announced audibly on Windows. Verified completion uses the configured
Information/Asterisk sound; failure uses the Critical Stop/Hand sound and requests taskbar
attention. Failure notifications remain visible until the user dismisses them.

## Large-file limitation

Network uploads over this legacy UDP protocol are a convenience feature, not a fully reliable
replacement for direct USB transfer. Smaller files have completed and verified successfully, but
repeated uploads of a 56,736,598-byte G-code file stopped partway after the printer failed to
acknowledge a data block. Longer acknowledgement windows and light pacing improved diagnostics but
did not establish reliable large-file transfer.

There is not yet a validated file-size cutoff. For large, long-running, or important prints, save
the G-code directly to a USB flash drive, safely eject it from the computer, insert it into the
printer, and start the job from the printer touchscreen. A network timeout leaves the partial
remote file closed and never starts the print.

This project should not imply that successful small-file testing guarantees reliable transfer of
large jobs. Community users should treat network upload as optional convenience and retain direct
USB as the dependable path.

## Upload safety chain

The legacy protocol does not expose a cryptographic whole-file checksum or file download command.
The Cura plugin therefore uses the strongest remotely available verification chain:

1. Each 1280-byte data block carries its byte offset and XOR checksum.
2. File data blocks are transmitted once; an unanswered block aborts the upload rather than being
   retried against unsequenced `ok` replies.
3. Explicit firmware `resend <offset>` requests remain supported.
4. `M29` must confirm that the destination file was saved.
5. The plugin collects the complete multipart `M20` response through `End file list` and its final
   `ok L:<count>` acknowledgement.
6. The exact remote filename must be present.
7. The remote byte count must match the local source-file size.
8. **Upload and Print** sends `M6030` only after every preceding check succeeds.

A matching size is not a cryptographic checksum, so the UI describes the result as **remote size
verified** rather than checksum verified.

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
  --cura-config /mnt/c/Users/name/AppData/Roaming/cura/5.13 \
  --host 192.168.1.123
```

The installer creates:

```text
C:\Users\name\AppData\Roaming\cura\5.13\plugins\QidiLegacyNetwork
```

Restart Cura, slice a model, and open the output-action dropdown. The development plugin provides:

- **Upload to QIDI** — transfers the G-code, verifies its remote size, and does not start it;
- **Upload and Print** — transfers and verifies the G-code before explicitly starting it.

The current development installer takes the host during installation. An in-Cura configuration and
discovery dialog is planned so users can update or rediscover the printer without reinstalling.

## Project phases

1. Verify commands and responses against the physical i-Fast. **Complete.**
2. Implement and validate the Cura 5.13 network output device. **Validated for smaller files on the
   i-Fast V3.40; large-file reliability remains limited.**
3. Add in-Cura address management and MAC-based rediscovery.
4. Add the i-Fast machine definition and dual-extruder profile.
5. Add monitoring and controls after the connection and profile paths are stable.

## Attribution

Protocol behavior was informed by publicly available legacy QIDI integrations, including
`alkaes/QidiPrint` and `philltran/cura-qidi-printer-integration`. This project is a new,
separated implementation designed for current Cura 5 architecture and testability.
