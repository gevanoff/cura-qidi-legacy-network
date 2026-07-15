# QIDI i-Fast hardware test plan

The first physical-printer test should establish protocol compatibility without moving or heating
the printer.

## Preconditions

1. Record the i-Fast firmware version shown on the printer.
2. Give the printer a stable DHCP reservation or static address.
3. Close QIDI Print so only one client is communicating with the printer.
4. Keep the computer and printer on the same LAN for the first test.
5. Install the project in a virtual environment with `python -m pip install -e '.[dev]'`.

## Gate 1: non-invasive probe

```bash
qidi-legacy probe PRINTER_IP
```

Expected result: JSON containing a raw `M4001` response, parsed dimensions/machine type, encoding,
and firmware returned by `M4002`.

This command does not upload, heat, home, or start a print.

## Gate 2: status

```bash
qidi-legacy status PRINTER_IP
```

Expected result: current and target temperatures, position, print byte counts, and elapsed time.
No movement or heating is requested.

## Gate 3: upload without printing

Create or select a small reviewed `.gcode` file. Then run:

```bash
qidi-legacy upload PRINTER_IP path/to/test.gcode
```

The command uploads and closes the file but does not start it. Confirm on the printer that the file
appears with the expected size/name.

## Gate 4: controlled print start

Only after the uploaded file is visible and its G-code has been reviewed:

```bash
qidi-legacy upload PRINTER_IP path/to/test.gcode --start
```

Stay at the printer with the power switch accessible. The initial file should use conservative
speeds and temperatures and should not depend on dual-extruder behavior.

## Failure evidence

Capture the following without editing it:

- complete CLI stdout/stderr;
- printer firmware version;
- operating system;
- whether QIDI Print was running;
- the first 50 and last 50 lines of the test G-code;
- a Wireshark capture filtered with `udp.port == 3000 && ip.addr == PRINTER_IP`, when available.

Do not publish captures containing unrelated LAN traffic. Redact MAC addresses before attaching a
capture to a public issue.
