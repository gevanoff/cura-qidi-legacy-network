# QIDI i-Fast Cura quality profiles

The repository is the source of truth for the i-Fast machine, extruder, and quality resources installed into Cura 5.13.

## Profile layout

- `cura_resources/definitions/qidi_ifast.def.json` declares the printer and enables machine quality profiles.
- `cura_resources/quality/qidi_ifast/qidi_ifast_normal.inst.cfg` contains the machine-wide 0.20 mm Reliable settings.
- `cura_resources/quality/qidi_ifast/qidi_ifast_normal_generic_pla.inst.cfg` overlays Generic PLA temperatures.

The installer copies the complete nested resource tree into the selected Cura configuration directory. It does not delete Cura user overrides.

## Reliable PLA baseline

The default Normal quality type is intentionally tuned for reliability rather than speed:

| Setting | Value |
|---|---:|
| Profile name | 0.20 mm Reliable |
| Layer height | 0.20 mm |
| Initial layer height | 0.28 mm |
| Initial layer speed | 15 mm/s |
| Initial-layer travel speed | 75 mm/s |
| Initial layer line width | 125% |
| Initial layer flow | 108% |
| Brim flow | 108% |
| Adhesion type | Brim |
| Brim gap | 0 mm |
| Brim width | 10 mm |
| Initial fan speed | 0% |
| Full fan layer | 4 |
| General print / infill speed | 45 mm/s |
| Wall speed | 30 mm/s |
| Outer wall speed | 25 mm/s |
| Top/bottom speed | 30 mm/s |
| Generic PLA print temperature | 205 °C |
| Generic PLA initial print temperature | 210 °C |
| Generic PLA bed temperature | 60 °C |
| Generic PLA initial bed temperature | 65 °C |

The thicker first layer tolerates small bed-height variation better than the prior generic baseline. The combination of slower deposition, modest first-layer over-extrusion, a wider attached brim, and delayed cooling is intended to keep the first several layers anchored while avoiding extreme compensation values.

This profile cannot correct a dirty build surface, a loose bed, a clogged nozzle, or incorrect physical nozzle height. Do not keep increasing flow when first-layer lines remain round and separate; recalibrate the bed/nozzle gap instead.

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
2. Select **0.20 mm Reliable**.
3. Select **Generic PLA** for the active extruder.
4. Use **Discard changes** when Cura reports retained custom settings that should not override the Git-managed baseline.
5. If Cura continues to show old values, remove and re-add the QIDI i-Fast machine rather than editing every setting manually.
6. Check both extruders only when performing a dual-extrusion test.

Cura stores UI edits as user-level overrides. Those overrides can take precedence over the files in this repository. The installer deliberately does not remove them because unrelated user profiles may coexist in the same Cura configuration tree.

## Physical validation

Start with a small first-layer test, not a long model. Confirm:

- the generated G-code requests a 65 °C initial bed and 60 °C regular bed;
- the active nozzle starts at 210 °C and settles to 205 °C;
- the brim and model first layer print at 15 mm/s;
- the brim touches the model and is approximately 10 mm wide;
- the fan remains off on the first layer and ramps to full speed at layer 4;
- adjacent first-layer lines touch without severe ridges or gaps;
- the brim remains attached through the first several layers;
- the nozzle does not scrape the build surface.

Inspect generated temperatures with:

```bash
grep -nE '^(M104|M109|M140|M190|T[01])' file.gcode | head -40
```

Expected initial targets include `S210` for the active nozzle and `S65` for the bed. Later commands should reduce the targets to 205 °C and 60 °C.

For support validation, use a small bridge or overhang coupon rather than a long production print. Confirm that Cura shows 15% support density, an 80% interface, and 0.6 mm interface thickness. Verify the chosen support extruder and top distance manually before slicing. Inspect Preview to confirm that tool changes occur only where intended and that the interface is three layers thick.

## Failure interpretation

- **Round, separate first-layer lines:** nozzle is too far from the bed or extrusion is obstructed. Correct physical calibration before profile tuning.
- **Transparent, deeply ridged, or scraping lines:** nozzle is too close. Increase the physical gap before printing again.
- **Lines look properly flattened but detach:** clean the plate, verify bed temperature, and inspect for drafts or cooling that begins too early.
- **The first layer holds but the model later becomes spaghetti:** inspect the sliced preview for unsupported geometry, verify support generation, and confirm the part was not struck by a nozzle or curled edge.

Record the physical result in the pull request before promoting the profile from draft status.
