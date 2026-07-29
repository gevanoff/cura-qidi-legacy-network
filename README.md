# Cura QIDI Legacy Network

A clean, testable implementation of the legacy QIDI UDP network protocol, plus a Cura 5
output-device plugin and development machine definitions targeting the **QIDI i-Fast**.

## Current status

The protocol layer has been physically verified on a QIDI i-Fast running firmware V3.40:

- handshake, firmware query, and status polling;
- plain `.gcode` upload with the printer-specific save response;
- touchscreen and network print start;
- successful completion of real QIDI Print-generated test prints;
- Cura-generated upload and print-start from Cura 5.13 on Windows;
- byte-identical file readback after disabling unsafe automatic file-block retries;
- remote filename and byte-size verification through the printer's multipart `M20` listing;
- a 56,736,598-byte Cura job transferred successfully over wired Ethernet and matched the locally
  saved G-code after normalizing Windows CRLF line endings to LF.

The Cura integration provides separate **Upload to QIDI** and **Upload and Print** actions and
performs network work in a Cura background job. Before reporting success or starting a print, it
requires the uploaded filename to appear in the remote file list with the same byte count as the
local G-code generated for transfer.

Upload results are also announced audibly on Windows. Verified completion uses the configured
Information/Asterisk sound; failure uses the Critical Stop/Hand sound and requests taskbar
attention. Failure notifications remain visible until the user dismisses them.

## Initial QIDI i-Fast machine definition

The development installer now adds a visible **QIDI Tech > QIDI i-Fast** Cura machine with:

- a conservative 330 × 250 × 320 mm dual-extrusion build volume;
- two 0.4 mm extruders using 1.75 mm filament;
- Marlin-flavor G-code;
- heated-bed support;
- minimal start/end G-code without unvalidated XY purge or parking moves;
- zero slicer-side nozzle offsets while firmware calibration ownership is tested.

The definition intentionally uses Cura's generic material and quality profiles at this stage. PLA,
PETG, standby-temperature, purge, and retraction overrides will be added only after physical tests.
The printer advertises a wider single-nozzle envelope, but that is not exposed until carriage modes
and safe limits can be represented without allowing invalid dual-nozzle placement.

A staged validation plan and a small two-part checkerboard model are included in:

- `docs/qidi-ifast-dual-extruder-testing.md`
- `test_models/dual_checker/`

## Network transport reliability

The legacy application protocol uses UDP with plain, unsequenced acknowledgements. Repeated Wi-Fi
attempts to upload a 56,736,598-byte G-code file stopped partway after the printer failed to
acknowledge a block. Extending the acknowledgement window and adding light pacing did not make that
Wi-Fi path dependable.

The same substantial job subsequently completed over wired Ethernet. The printer's `M20` listing
reported the expected remote size, and a file copied back from its USB storage matched the separately
saved Cura G-code after line-ending normalization. This is strong evidence that Ethernet is the
preferred network transport, although one successful large transfer does not prove that the legacy
UDP service can never fail.

On the i-Fast touchscreen, Ethernet selection is unusual:

1. Open the **Internet** screen.
2. Move the selector from the Wi-Fi symbol to the plug symbol.
3. Check—or re-check—the box beside **Start Operation**.

Changing the selector can deactivate networking until **Start Operation** is checked again. The
wired interface may receive a different DHCP address from Wi-Fi; configure Cura with the wired
address and reserve it in DHCP when possible.

For large, long-running, or important jobs, wired Ethernet is recommended over Wi-Fi. Direct USB
remains the most conservative fallback. A network timeout closes the partial remote file and never
starts the print.

A Windows-saved Cura file may use CRLF line endings while the plugin's generated transfer file uses
LF. This makes raw sizes and hashes differ even when the G-code is equivalent. Compare such files
with line endings normalized, for example:

```bash
cmp <(sed 's/\r$//' "$LOCAL") <(sed 's/\r$//' "$REMOTE")
```

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
qidi-legacy discover --duration 8
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

The installer creates or updates:

```text
C:\Users\name\AppData\Roaming\cura\5.13\plugins\QidiLegacyNetwork
C:\Users\name\AppData\Roaming\cura\5.13\definitions\qidi_ifast.def.json
C:\Users\name\AppData\Roaming\cura\5.13\extruders\qidi_ifast_extruder_0.def.json
C:\Users\name\AppData\Roaming\cura\5.13\extruders\qidi_ifast_extruder_1.def.json
```

Restart Cura, add **QIDI Tech > QIDI i-Fast**, slice a model, and open the output-action dropdown.
The development plugin provides:

- **Upload to QIDI** — transfers the G-code, verifies its remote size, and does not start it;
- **Upload and Print** — transfers and verifies the G-code before explicitly starting it.

After installation, change the address without reinstalling:

1. Open **Extensions > QIDI Legacy Network > Configure Printer Address…**.
2. Enter the printer hostname or IP address and UDP port 3000.
3. Select **Save**.

The plugin validates and atomically saves the configuration, removes the old output devices, and
registers replacement upload actions immediately. Automatic discovery remains a later enhancement;
manual address management is the primary configuration path.

## Project phases

1. Verify commands and responses against the physical i-Fast. **Complete.**
2. Implement and validate the Cura 5.13 network output device. **Validated over wired Ethernet with
   a 56.7 MB job; Wi-Fi is not recommended for large transfers.**
3. Add in-Cura address management. **Complete and physically validated.**
4. Add the i-Fast machine definition and dual-extruder profiles. **Initial definition and test assets
   implemented; physical slicing and printer validation pending.**
5. Add automatic discovery and multi-interface handling.
6. Add monitoring and controls after the connection and profile paths are stable.

## Attribution

Protocol behavior was informed by publicly available legacy QIDI integrations, including
`alkaes/QidiPrint` and `philltran/cura-qidi-printer-integration`. This project is a new,
separated implementation designed for current Cura 5 architecture and testability.
