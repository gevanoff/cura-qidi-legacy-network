# Cura QIDI Legacy Network

A clean, testable implementation of the legacy QIDI UDP network protocol, plus a Cura 5
output-device plugin and development machine definitions targeting the **QIDI i-Fast**.

## Current status

The protocol layer has been physically tested on a QIDI i-Fast running firmware V3.40:

- handshake, firmware query, and status polling;
- plain `.gcode` upload with the printer-specific save response;
- touchscreen and network print-start commands;
- Cura-generated uploads from Cura 5.13 on Windows;
- multipart `M20` remote filename and byte-size checking;
- persistent success/failure notifications;
- manual in-Cura printer address and UDP-port configuration.

The legacy network path is **not content-safe**. A wired-Ethernet upload of
`PLA_E_Calibration.gcode` completed normally and passed remote byte-size checking, but the file
copied back from the printer contained a same-length byte splice around lines 595–597. The printer
later rejected the malformed line as illegal G-code. A direct USB copy saved by Cura retained the
correct content after normalizing Windows CRLF line endings to LF.

Because remote size equality cannot detect this failure, the plugin exposes only **Upload to QIDI**.
Automatic network print start is disabled in both Cura and the CLI. Use direct removable USB media
for important jobs and for all machine-definition or dual-extruder validation.

Upload results are announced audibly on Windows. Completion uses the configured
Information/Asterisk sound; failure uses the Critical Stop/Hand sound and requests taskbar
attention. Failure notifications remain visible until dismissed.

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

The legacy application protocol uses UDP with plain, unsequenced acknowledgements. Each 1280-byte
file block includes an offset and XOR checksum, but the firmware does not expose a whole-file hash
or a network readback command.

Observed failure modes include:

- repeated Wi-Fi uploads stopping partway after an acknowledgement was lost;
- a 56,736,598-byte wired-Ethernet upload completing and matching a copied-back file;
- a later wired-Ethernet upload completing with the correct reported size but corrupted content.

Ethernet reduces Wi-Fi-related loss and timeout frequency, but it does not provide an integrity
guarantee. The only currently trusted transfer path is saving the generated G-code directly to a
USB drive and inserting that drive into the printer.

On the i-Fast touchscreen, Ethernet selection is unusual:

1. Open the **Internet** screen.
2. Move the selector from the Wi-Fi symbol to the plug symbol.
3. Check—or re-check—the box beside **Start Operation**.

Changing the selector can deactivate networking until **Start Operation** is checked again. The
wired interface may receive a different DHCP address from Wi-Fi; configure Cura with the wired
address and reserve it in DHCP when possible.

A Windows-saved Cura file may use CRLF line endings while the plugin-generated transfer file uses
LF. Normalize line endings before comparison:

```bash
cmp <(sed 's/\r$//' "$LOCAL") <(sed 's/\r$//' "$REMOTE")
```

To compare a Windows-saved copy with a known Git blob:

```bash
sed 's/\r$//' "$WINDOWS_FILE" | git hash-object --stdin
```

## What remote checking does—and does not—prove

The plugin uses the strongest checks currently available from the printer:

1. Each 1280-byte data block carries its byte offset and XOR checksum.
2. File blocks are transmitted once; an unanswered block aborts rather than being blindly retried.
3. Explicit firmware `resend <offset>` requests remain supported.
4. `M29` must confirm that the destination file was saved.
5. The complete multipart `M20` response and final count acknowledgement must be received.
6. The exact filename must appear remotely.
7. The remote byte count must match the generated local source.

These checks detect truncation and many transfer failures. They **do not establish content
integrity** because a corrupted file can retain exactly the same length. Successful uploads are
therefore described as **size checked**, never checksum verified.

The plugin logs the SHA-256 digest of the exact temporary source generated for each Cura upload.
That digest is diagnostic only; the printer cannot report a corresponding digest for comparison.

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
```

The CLI performs remote filename and byte-size checking but does not start the print. The historical
`--start` option is rejected with an integrity-safety error.

## Cura 5.13 development installation

Close Cura before installing. From WSL, run:

```bash
python scripts/install_cura_plugin.py \
  --cura-config /mnt/c/Users/name/AppData/Roaming/cura/5.13 \
  --host 192.168.1.123 \
  --port 3000
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

- **Upload to QIDI** — transfers the G-code, checks its remote filename and byte count, and never
  starts it automatically.

After installation, change the address without reinstalling:

1. Open **Extensions > QIDI Legacy Network > Configure Printer Address…**.
2. Enter the printer hostname or IP address and UDP port `3000`.
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
