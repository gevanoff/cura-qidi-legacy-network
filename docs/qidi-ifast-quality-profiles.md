# QIDI i-Fast Cura quality profiles

The repository is the source of truth for the i-Fast machine, extruder, and quality resources installed into Cura 5.13.

## Profile layout

- `cura_resources/definitions/qidi_ifast.def.json` declares the printer and enables machine quality profiles.
- `cura_resources/quality/qidi_ifast/qidi_ifast_normal.inst.cfg` contains machine-wide 0.20 mm Normal settings.
- `cura_resources/quality/qidi_ifast/qidi_ifast_normal_generic_pla.inst.cfg` overlays Generic PLA temperatures.

The installer copies the complete nested resource tree into the selected Cura configuration directory. It does not delete Cura user overrides.

## Initial adhesion baseline

The first profile revision intentionally changes only a small set of first-layer controls:

| Setting | Value |
|---|---:|
| Layer height | 0.20 mm |
| Initial layer height | 0.24 mm |
| Initial layer speed | 18 mm/s |
| Initial layer line width | 120% |
| Adhesion type | Brim |
| Brim width | 8 mm |
| Initial fan speed | 0% |
| Generic PLA print temperature | 200 °C |
| Generic PLA initial print temperature | 200 °C |
| Generic PLA bed temperature | 60 °C |
| Generic PLA initial bed temperature | 65 °C |

These values are a conservative starting point, not a completed physical calibration. Do not add purge moves, nozzle offsets, automatic print start, or unrelated motion settings as part of adhesion tuning.

## Install and activate

Close Cura before installing:

```bash
python scripts/install_cura_plugin.py \
  --cura-config /mnt/c/Users/name/AppData/Roaming/cura/5.13 \
  --host 10.10.22.171 \
  --port 3000
```

After restarting Cura:

1. Select the QIDI i-Fast printer.
2. Select **0.20 mm Normal**.
3. Select **Generic PLA** for the active extruder.
4. Use **Discard changes** when Cura reports retained custom settings that should not override the Git-managed baseline.
5. Check both extruders when performing a dual-extrusion test.

Cura stores UI edits as user-level overrides. Those overrides can take precedence over the files in this repository. The installer deliberately does not remove them.

## Physical validation

Use a small first-layer test before a long print. Confirm:

- the generated G-code requests a 65 °C initial bed and 60 °C regular bed;
- the active nozzle target is 200 °C;
- the brim prints at 18 mm/s with the fan off;
- adjacent first-layer lines touch without severe ridges or gaps;
- the brim remains attached through the first several layers;
- the nozzle does not scrape the build surface.

Inspect generated temperatures with:

```bash
grep -nE '^(M104|M109|M140|M190|T[01])' file.gcode | head -40
```

Expected initial targets include `S200` for the active nozzle and `S65` for the bed. A later bed command should reduce the target to 60 °C.

If lines are round and separate, correct the printer's physical Z/nozzle calibration rather than continually increasing flow. If lines are flattened correctly but detach, clean the build surface and then tune bed temperature, first-layer speed, or adhesion width one change at a time.

Record the physical result in the pull request before promoting the profile from draft status.
