# QIDI i-Fast Cura quality profiles

The repository is the source of truth for the i-Fast machine, extruder, and quality resources installed into Cura 5.13.

## Profile layout

- `cura_resources/definitions/qidi_ifast.def.json` declares the printer and enables machine quality profiles.
- `cura_resources/quality/qidi_ifast/qidi_ifast_normal.inst.cfg` is the **global** 0.20 mm Reliable quality container. It owns machine-wide geometry, adhesion, and support defaults.
- `cura_resources/quality/qidi_ifast/qidi_ifast_normal_generic_pla.inst.cfg` is the **non-global, material-matched extruder quality** container. It owns Generic PLA temperatures plus extrusion, cooling, retraction, Z-hop, and speed controls.

This split is required by Cura's stack model. For a machine with `has_machine_quality = true` and material support, each `ExtruderStack` selects a non-global quality container matching the machine quality definition, material, and quality type. The global quality container does not reliably provide extruder-scoped controls. Both i-Fast extruders use the same `qidi_ifast` quality definition, so T0 and T1 each receive the Generic PLA overlay whenever that extruder is configured for Generic PLA.

The installer copies the complete nested resource tree into the selected Cura configuration directory. It does not delete Cura user overrides.

## Reliable PLA baseline

The default Normal quality type is intentionally tuned for reliability rather than speed:

| Setting | Value |
|---|---:|
| Profile name | 0.20 mm Reliable |
| Layer height | 0.20 mm |
| Initial layer height | 0.30 mm |
| Initial layer speed | 15 mm/s |
| Initial-layer travel speed | 40 mm/s |
| Slower layers | 4 |
| Initial layer line width | 120% |
| Initial layer flow | 100% |
| Brim flow | 100% |
| Adhesion type | Brim |
| Brim gap | 0 mm |
| Brim width | 10 mm |
| Initial fan speed | 0% |
| Full fan layer | 4 |
| Minimum layer time | 10 s |
| General print / infill speed | 45 mm/s |
| Travel speed | 100 mm/s |
| Wall speed | 30 mm/s |
| Outer wall speed | 25 mm/s |
| Top/bottom speed | 30 mm/s |
| Generic PLA print temperature | 200 °C |
| Generic PLA initial print temperature | 205 °C |
| Generic PLA bed temperature | 60 °C |
| Generic PLA initial bed temperature | 65 °C |

The first revision of this profile used 125% initial line width and 108% initial/brim flow. A physical test began acceptably but then produced raised or loose filament that adhered to the nozzle and was dragged across the plate. Those extrusion multipliers were removed: a reliability profile must not compensate for uncertain physical Z calibration by depositing excess material.

The 0.30 mm initial layer follows Cura's inherited initial-layer height and provides tolerance for small bed-height variation. A 120% line width increases contact area without also increasing flow. Four slower layers provide a gradual transition to normal speed instead of accelerating immediately after the first layer.

## Travel clearance and nozzle-drag prevention

The Generic PLA extruder quality explicitly activates the travel controls that were previously inherited or inactive:

| Setting | Value |
|---|---:|
| Retraction | Enabled |
| Combing | Off |
| Minimum travel for retraction | 1.5 mm |
| Z hop when retracted | Enabled |
| Z-hop height | 0.2 mm |
| Z-hop speed | 5 mm/s |
| Z hop only over collisions | Disabled; hop on every qualifying retracted travel |
| Retract before outer wall | Always |
| Infill before walls | Disabled |

With combing disabled, qualifying travel moves retract rather than dragging an unretracted nozzle through already deposited first-layer lines. A 0.2 mm Z hop matches the height present in QIDI's legacy Cura definition and provides clearance during those moves.

Z hop only protects non-extruding travel. It cannot prevent a collision caused by a first layer that is physically too high, over-extruded, curled, already detached, or produced by the wrong mechanically lowered nozzle. If the nozzle catches material while actively extruding, inspect tool latching, Z gap, plate cleanliness, nozzle cleanliness, temperature, and extrusion consistency before increasing any adhesion multiplier.

## Comparison with legacy QIDI Print resources

QIDI Print 6.5.4 is Cura-based. QIDI's official legacy Cura profile archive contains an `i-fast` definition and a shared `qidi` base definition. The relevant inherited behavior is:

- 20 mm/s initial-layer speed;
- 100 mm/s travel speed;
- 500 mm/s² print and travel acceleration values;
- 8 mm/s print and travel jerk values;
- 0.2 mm configured Z-hop height, while Cura's inherited Z-hop enable switch remains off unless selected;
- combing set to Not in Skin when Z hop is disabled, and Off when Z hop is enabled;
- retract before outer walls;
- avoid supports during travel when combing is active;
- 10-second minimum layer time;
- skirt adhesion by default rather than a brim;
- two long purge lines at Z0.3, one for each nozzle, in the i-Fast start G-code;
- the Generic PLA Fine overlay raises ordinary print speed to 60 mm/s but otherwise relies heavily on Cura's generic material and quality defaults.

This profile is deliberately slower and uses an attached brim. It explicitly enables the legacy 0.2 mm Z hop because the physical failure included nozzle dragging. Startup purge and mechanical nozzle-latching behavior belong to the machine definition rather than the quality profile and are being corrected/validated separately; the quality resources must not attempt to compensate for a machine-state error.

The legacy acceleration and jerk numbers are documented but are not forcibly emitted by this profile. Enabling slicer-generated motion-control commands would change firmware state and requires a separate physical validation.

## Initial support baseline

The global profile also supplies conservative geometry-independent values that take effect only when support generation is enabled:

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

Choose the support and support-interface extruders per print only after the physical tool-switch path has been validated. Set the support top distance from the support-filament manufacturer's guidance and a physical separation test. Ordinary PLA used against PLA normally needs a non-zero gap; a purpose-designed breakaway support material may permit a smaller gap.

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
3. Select **Generic PLA** for each extruder that should receive the reliable PLA extrusion/retraction/speed settings.
4. Use **Discard changes** when Cura reports retained custom settings that should not override the Git-managed baseline.
5. If Cura continues to show old values, remove and re-add the QIDI i-Fast machine rather than editing every setting manually.
6. Check both extruders only when performing a dual-extrusion test.

Cura stores UI edits as user-level overrides. Those overrides can take precedence over the files in this repository. The installer deliberately does not remove them because unrelated user profiles may coexist in the same Cura configuration tree.

## Physical validation

Clean the nozzle exterior while warm, then clean the build plate according to its surface requirements. Start with a small first-layer test saved directly to USB, not a long model. First verify that the machine definition mechanically lowers the same nozzle Cura has selected; only then evaluate the quality profile. Confirm:

- the generated G-code requests a 65 °C initial bed and 60 °C regular bed;
- the active Generic PLA nozzle starts at 205 °C and settles to 200 °C;
- the brim and model first layer print at 15 mm/s;
- first-layer travel moves are limited to 40 mm/s;
- the brim touches the model and is approximately 10 mm wide;
- the fan remains off on the first layer and ramps to full speed at layer 4;
- the first four layers increase speed gradually;
- retracted travel moves contain a 0.2 mm Z hop;
- adjacent first-layer lines touch without raised ridges or gaps;
- the brim remains attached through the first several layers;
- the nozzle does not scrape the build surface or collect filament.

Inspect generated temperatures with:

```bash
grep -nE '^(M104|M109|M140|M190|T[01])' file.gcode | head -40
```

Expected initial targets include `S205` for a Generic PLA active nozzle and `S65` for the bed. Later commands should reduce the targets to 200 °C and 60 °C.

For support validation, use a small bridge or overhang coupon rather than a long production print. Confirm that Cura shows 15% support density, an 80% interface, and 0.6 mm interface thickness. Verify the chosen support extruder and top distance manually before slicing. Inspect Preview to confirm that tool changes occur only where intended and that the interface is three layers thick.

## Failure interpretation

- **Selected nozzle is visibly higher than the inactive nozzle:** stop; the mechanical tool latch is wrong. Fix the machine-definition/tool-state path before changing quality settings.
- **Round, separate first-layer lines:** nozzle is too far from the bed or extrusion is obstructed. Correct physical calibration before profile tuning.
- **Raised ridges, transparent areas, scraping, or filament accumulating on the nozzle:** nozzle is too close, flow is excessive, temperature is too high, or plastic is stuck to the nozzle exterior. Stop and correct the physical condition rather than adding more flow.
- **Lines look properly flattened but detach:** clean the plate, verify bed temperature, and inspect for drafts or cooling that begins too early.
- **The nozzle crosses and catches sound first-layer lines during a travel move:** verify that the active extruder's Generic PLA quality actually has combing off and 0.2 mm Z hop enabled; inspect G-code or Cura Preview for the travel path.
- **The first layer holds but the model later becomes spaghetti:** inspect the sliced preview for unsupported geometry, verify support generation, and confirm the part was not struck by a nozzle or curled edge.

Record the physical result in the pull request before promoting the profile from draft status.
