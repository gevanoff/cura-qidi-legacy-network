# Cura 5.13 development installation

Target installation:

- Cura version: 5.13.0
- Windows configuration directory: `C:\Users\paper\AppData\Roaming\cura\5.13`
- Printer: QIDI i-Fast at `10.10.22.122:3000`

## Install from WSL

Close Cura, activate the project virtual environment, and run:

```bash
cd ~/cura-qidi-legacy-network
source .venv/bin/activate
python scripts/install_cura_plugin.py \
  --cura-config /mnt/c/Users/paper/AppData/Roaming/cura/5.13 \
  --host 10.10.22.122
```

The installer copies the Cura adapter and vendors the tested `qidi_legacy` protocol package into
the user plugin directory. Restart Cura after every plugin update.

## First load check

After restarting Cura:

1. Slice a small model with the temporary Custom FFF printer.
2. Open the output-action dropdown beside the normal save button.
3. Confirm that **Upload to QIDI** and **Upload and Print** are listed.
4. Use **Upload to QIDI** first.
5. Confirm the uploaded file appears on the i-Fast and start it from the touchscreen.
6. Test **Upload and Print** only after the upload-only action succeeds.

## Log location

Cura's log is normally under the version directory's `cura.log` file. When reporting a load or
runtime failure, include lines containing `QidiLegacyNetwork`, `QIDI Legacy Network`, `Traceback`,
or `ERROR`.

From WSL:

```bash
grep -nE 'QidiLegacyNetwork|QIDI Legacy Network|Traceback|ERROR' \
  /mnt/c/Users/paper/AppData/Roaming/cura/5.13/cura.log | tail -200
```

## Removal

Close Cura and remove:

```bash
rm -rf /mnt/c/Users/paper/AppData/Roaming/cura/5.13/plugins/QidiLegacyNetwork
```
