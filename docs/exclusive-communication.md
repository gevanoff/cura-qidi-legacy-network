# Exclusive communication requirement

The QIDI i-Fast legacy UDP service must be treated as a single-client, single-operation interface.

Physical testing showed that concurrent Cura Monitor polling disrupted uploads performed by both
native Windows and WSL clients. Transfers repeatedly stopped after a few hundred KiB when Cura was
running. With Cura and other QIDI clients closed, three separate 64 MiB uploads completed and all
three retrieved files matched the local source SHA-256.

## Cura behavior

- A Cura upload receives exclusive access before its worker starts.
- Monitor polling stops and no new status worker is scheduled during the upload.
- An already-running status request may finish first; the shared protocol lock makes the upload
  wait for it, and its result is discarded once upload-exclusive mode has begun.
- Monitoring resumes after the upload unless the user separately requested a manual pause.
- A manual pause blocks Cura uploads and polling until communication is resumed.

## External tools

Before using QIDI Print, `qidi-legacy`, or another client:

1. In Cura, select **Extensions > QIDI Legacy Network > Pause Cura Communication for External Tools**.
2. Wait a few seconds for any in-flight status request to finish.
3. Use only one external client at a time.
4. Resume Cura communication after the external client has finished.

Cura cannot coordinate with QIDI Print or arbitrary external processes, so the operator must enforce
exclusive access across applications.

## Cura import safety

The exclusive-access wrapper deliberately adds no new Qt signals or `pyqtProperty` definitions to
Cura's existing `PrinterOutputDevice` meta-object. Communication state is exposed through the
Python extension menu, while the Monitor view continues to use only the properties supplied by the
physically validated base output device.

The wrapper also waits until the wrapped Qt base constructor has run before assigning instance
state. Its early `_update()` override uses a class-level sentinel while the base constructor is
running. This avoids touching the wrapped QObject before Qt initialization is complete.

## Integrity validation

Three exclusive-access 64 MiB uploads were retrieved from the printer and matched the source
SHA-256 exactly.

A later Cura-generated production file provided an additional end-to-end check:

- Two independently retrieved transfer copies were each 28,380,348 bytes.
- Both contained 880,428 LF line endings, no CRLF sequences, and had SHA-256
  `44db1b2ad6f61bee6c44360af604744c9eb7edf888b9ee8b96c90e05e685b0dc`.
- Cura's ordinary Windows local-save copy was 29,260,776 bytes because it contained the same
  880,428 line endings encoded as CRLF.
- Replacing CRLF with LF in the local-save copy produced exactly the transferred bytes and the same
  SHA-256.

Therefore the apparent size and hash difference between the transfer source and Cura's Windows
local save was newline representation, not transfer corruption. Hash comparisons must be made
against the exact LF-form byte stream prepared by the plugin, or after explicitly normalizing the
local-save copy from CRLF to LF.

## Integrity boundary

The physical tests establish repeatable byte-perfect transfer under the tested exclusive-access
conditions. The printer still reports only filename and byte count; it does not compute or return a
content hash. Automatic network print start therefore remains disabled, and the plugin logs the
SHA-256 of the exact LF-form source bytes it uploads so a retrieved file can be independently
verified.
