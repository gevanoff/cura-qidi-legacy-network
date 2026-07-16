# Cura 5.13 development installation

Target installation:

- Cura version: 5.13.0
- Windows configuration directory: `C:\Users\paper\AppData\Roaming\cura\5.13`
- Printer: QIDI i-Fast at `10.10.22.122:3000`

## Install from WSL

Close Cura, activate the project virtual environment, and run:

```bash
cd ~/cura-qidi-legacy-network
git switch agent/cura-5-13-output-device
git pull --ff-only
source .venv/bin/activate
python scripts/install_cura_plugin.py \
  --cura-config /mnt/c/Users/paper/AppData/Roaming/cura/5.13 \
  --host 10.10.22.122
```

The installer replaces the existing development plugin, copies the Cura adapter, and vendors the
verified `qidi_legacy` protocol package into the user plugin directory. Restart Cura after every
plugin update.

## First load check

After restarting Cura:

1. Confirm **Extensions > QIDI Legacy Network** exists.
2. Select **Refresh Output Devices** from that menu if the output button still says only
   **Save to Disk**.
3. Slice a small model with the temporary Custom FFF printer.
4. Confirm the primary output action becomes **Upload to QIDI**.
5. Open its dropdown and confirm **Upload and Print** and the normal file-save action are listed.
6. Use **Upload to QIDI** first.
7. Confirm the uploaded file appears on the i-Fast and start it from the touchscreen.
8. Test **Upload and Print** only after the upload-only action succeeds.

The plugin registers on Cura's active-machine and main-window lifecycle signals and performs a
second delayed startup synchronization. A manual refresh removes and recreates both QIDI devices,
emits a fresh output-device change, and selects the safer upload-only destination.

## Expected log entries

A successful synchronization includes the active machine, all output-device IDs, and the active
selection. For example:

```text
QIDI output-device sync for machine QIDI i-Fast Temporary: expected=['qidi_legacy_upload',
'qidi_legacy_upload_and_print'] manager=[...] active=qidi_legacy_upload success=True
QIDI Legacy Network ready for 10.10.22.122:3000 after startup fallback
```

## Log location

Cura's log is normally under the version directory's `cura.log` file. When reporting a load or
runtime failure, include lines containing `QidiLegacyNetwork`, `QIDI Legacy Network`, `QIDI output`,
`Traceback`, or `ERROR`.

From WSL:

```bash
grep -nE 'QidiLegacyNetwork|QIDI Legacy Network|QIDI output|Traceback|ERROR' \
  /mnt/c/Users/paper/AppData/Roaming/cura/5.13/cura.log | tail -250
```

## Removal

Close Cura and remove:

```bash
rm -rf /mnt/c/Users/paper/AppData/Roaming/cura/5.13/plugins/QidiLegacyNetwork
```
