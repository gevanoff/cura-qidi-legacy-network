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

## Integrity boundary

Remote filename and byte-count verification do not prove content integrity. Automatic network
print start remains disabled. The three matching 64 MiB transfers establish repeatability under the
tested exclusive-access conditions, but important jobs should still be copied directly to removable
USB media unless the retrieved network-uploaded file has been independently hashed.
