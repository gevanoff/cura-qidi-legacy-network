# Legacy QIDI UDP protocol notes

Initial target: QIDI i-Fast with current legacy firmware.

## Known command flow

| Purpose | Command |
|---|---|
| Discovery broadcast | `M99999` |
| Handshake and machine parameters | `M4001` |
| Firmware version | `M4002 ` |
| Status | `M4000` |
| Current filename | `M4006` |
| Begin upload | `M28 <filename>` |
| Finish upload | `M29 <filename>` |
| Start stored print | `M6030 ":<filename>" I1` |
| Pause / resume / cancel | `M25` / `M24` / `M33` |

Transport is UDP, normally port 3000. File blocks contain up to 1280 payload bytes,
followed by a four-byte little-endian file offset, XOR checksum, and marker byte `0x83`.

These notes describe observed legacy behavior and are not an official QIDI protocol specification.

## Observed QIDI i-Fast V3.40 behavior

Physical testing on an i-Fast running firmware `V3.40` confirmed direct UDP access on port 3000,
plain `.gcode` block upload, and the following `M29` success response:

```text
Done saving file!
// network_test.gcode
```

The filename in the second line must match the requested remote filename. Upload creation can fail
with `Error!Cann't create file <filename>` when the printer's removable USB storage is absent or
not mounted.
