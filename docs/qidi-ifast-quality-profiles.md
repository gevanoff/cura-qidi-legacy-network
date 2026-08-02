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

## Initial support baseline

The profile also supplies conservative geometry-independent values that take effect only when support generation is enabled:

| Setting | Value |
|---|---:|
| Support density | 15% |
| Support pattern | Zig Zag |
| Support wall line count | 1 |
| Support interface | Enabled |
| Support interface density | 80% |
| Support interface thickness | 0.6 mm |
| Support interface pattern | Zig Zag |

At the 0.20 mm profile layer height, a 0.6 mm interface produces three dense interface layers. The bulk support remains relatively sparse while the interface provides the surface immediately beneath the model.

The profile deliberately does **not**:

- enable support generation for every model;
- assign either physical extruder as the support or interface extruder;
- set the support top/Z distance;
- assume that ordinary PLA and dedicated PLA support filament require the same separation gap.

Choose the support and support-interface extruders per print only after confirming the physical T0/T1 mapping. Set the support top distance from the support-filament manufacturer's guidance and a physical separation test. Ordinary PLA used against PLA normally needs a non-zero gap; a purpose-designed breakaway support material may permit a smaller gap.

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

For support validation, use a small bridge or overhang coupon rather than a long production print. Confirm that Cura shows 15% support density, an 80% interface, and 0.6 mm interface thickness. Verify the chosen support extruder and top distance manually before slicing. Inspect Preview to confirm that tool changes occur only where intended and that the interface is three layers thick.

If lines are round and separate, correct the printer's physical Z/nozzle calibration rather than continually increasing flow. If lines are flattened correctly but detach, clean the build surface and then tune bed temperature, first-layer speed, or adhesion width one change at a time.

Record the physical result in the pull request before promoting the profile from draft status.
