# Silent network-transfer corruption incident — 2026-07-28

During physical validation of the QIDI i-Fast machine definition, `PLA_E_Calibration.gcode` was saved locally from Cura to removable USB media and also uploaded through the legacy QIDI UDP output device over wired Ethernet.

The USB-saved file retained the expected G-code content, with Windows CRLF line endings. The file copied back from the printer had the same overall byte count used by remote-size verification but contained corrupted, same-length content around lines 595–597. For example, the expected line:

```gcode
G1 X198.575 Y184.838 E31.79693
```

became:

```gcode
G1 X203.988 Y185.3731.79693
```

The printer correctly rejected the malformed result as illegal G-code at line 597.

## Consequences

- Remote byte-size equality does not establish content integrity.
- Wired Ethernet reduces timeout frequency but does not eliminate silent corruption.
- `Upload and Print` must not be used until a stronger integrity guarantee or verified readback is available.
- Machine-definition and dual-extruder tests should use direct removable USB media for the time being.

This incident is intentionally documented on the machine-definition branch because it changes the physical-validation procedure, but the transport fix belongs in a separate branch and pull request.
