# Architecture

## Design constraint

The legacy QIDI protocol is synchronous request/reply UDP plus a custom block upload format.
Cura is a Qt GUI application. Mixing Qt sockets, Python worker threads, slicing state, and printer
protocol state in one class makes failures difficult to reproduce.

The project therefore has three layers.

## 1. Protocol package

`src/qidi_legacy/` has no Cura or Qt dependency.

- `transport.py`: bounded UDP request/reply transport.
- `framing.py`: upload-block encoding and validation.
- `parsing.py`: tolerant parsing of handshake and status responses.
- `client.py`: printer operations and upload state machine.
- `discovery.py`: optional broadcast discovery.
- `mock_printer.py`: deterministic local emulator.
- `cli.py`: safe physical-printer probe and upload interface.

This layer is the source of truth for all wire behavior.

## 2. Cura adapter

`cura_plugin/QidiLegacyNetwork/` will remain thin. It will translate Cura output-device events into
calls to the protocol package from one serialized worker. It must not duplicate packet framing,
response parsing, retries, or upload state logic.

The first Cura adapter will support manual IP configuration and plain `.gcode` upload. Monitoring,
discovery, and optional print controls come after upload is verified against the physical printer.

## 3. Machine definitions

The i-Fast machine and extruder definitions will be independent from the network adapter. This
allows users to slice for the i-Fast even when they transfer files by USB, while the output-device
plugin can remain focused on networking.

## Safety defaults

- Upload does not start a print unless explicitly requested.
- `.gcode.tz` compression is not implemented in the first milestone.
- Retries and resend requests are bounded.
- Remote filenames reject traversal and firmware-hostile characters.
- Failed uploads attempt to close the remote file handle without masking the original error.
