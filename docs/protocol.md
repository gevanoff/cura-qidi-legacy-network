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
