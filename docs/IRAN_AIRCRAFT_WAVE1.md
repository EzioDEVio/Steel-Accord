# Iran aircraft, wave 1: 3D models

**Status:** 3D art has been generated and previewed in Blender (Cycles CPU, bpy 5.2.2).
- It has not yet been imported or run in Godot. The lead integrates it.
- Nothing has been committed.
- The U.S. scripts and outputs are unchanged. `air_ch47_3d.py` and `air_c130_3d.py` are only imported, read-only.

## Files
| | |
|---|---|
| Shared kit | `tools/art/airkit_ir.py` (new). It contains the procedural painter, decals, the `finish_ir` pipeline, the normal-orientation QA and the previews. It imports `airkit.py` read-only. |
| Scripts | `tools/art/air_ir_<x>_3d.py`, for `x` = `f14 f4 su24 ah1j ch47 c130 shahed`. The `shahed` script also writes the rail. |
| Models | `godot/assets/units3d/<id>/<id>.glb` with the textures embedded. Next to each are `<id>_albedo.png` and, where relevant, `<id>_blade.png` / `<id>_prop.png`. |
| Previews | `docs/screens/<id>_sheet.png`: front, side, rear, top (ortho), RTS 52° and close 3/4. Cycles CPU, 640×400, 20 samples, denoised. |

Regenerate deterministically: no global RNG state and no network. Run one at a time. Each takes about 0.5 min for the model plus about 1.5 min for the previews.
```
python3 -I tools/art/air_ir_<x>_3d.py            # -> godot/assets/units3d/<id>/, docs/screens/<id>_sheet.png
#   --no-previews | --quick (3 low-sample views) | --sheet <png> | <out_dir>
```

## Method
The Iran panels (`docs/reference/iran_pack/02_aircraft_and_uav_catalog.png`) are 3/4 perspective renders. They are not projectable views, so this wave does not use the U.S. projection method.
- **Geometry** is authored in metres from real-world proportions with the existing airkit builders: superellipse fuselage lofts, NACA lifting surfaces, bodies of revolution, gear and real thin-blade rotors/props. The panels were used only for silhouette, colour scheme and marking placement.
- **The albedo atlas (2048², 1024² for the Shahed and the rail) is painted procedurally in world space** and then rasterised into one Smart-UV atlas per model:
  - Camouflage comes from deterministic, domain-warped, low-octave 3D noise. It is quantile-thresholded so each colour has a fixed coverage.
  - Schemes:
    - `desert`: sand / brown / green.
    - `desert2`: sand and olive bands, stretched for the CH-47C.
    - `grey`: two-tone grey for the Su-24.
    - `light`: light grey for the Shahed.
  - Fighters have a light-grey underside.
  - Other painted detail:
    - panel lines
    - black radomes (F-14 / F-4 / C-130) and a light radome on the Su-24
    - anti-glare panels
    - glazing with frames
    - cabin windows and door outlines
    - exhaust soot
    - flat gear, stores and intakes
  - A Cycles AO bake is multiplied in at 40–50%, with light grime.
- **Markings.** No text, no calligraphy and no emblem anywhere. No U.S. stars.
  - Roundels are green / white / red concentric rings.
  - Fin flashes are three horizontal stripes: green on top, white, red at the bottom.
- **QA.**
  - The signed volume of every connected mesh island is checked. All islands of every exported mesh are outward: 0 inward on every model (F-14 68 islands, F-4 89, Su-24 65, AH-1J 62, CH-47C 60, C-130 78, Shahed 15, rail 34).
  - Node transforms, materials and bounds were verified by parsing the exported GLB JSON.

## Conventions (same as `docs/M3_AIRCRAFT.md`)
- Units are metres. Forward = Blender +Y = **Godot −Z**. Up = Godot +Y.
- The root origin is at ground contact under the fuselage midpoint.
- All nodes are top-level. Every node has identity rotation, except the rail's `Mount`.
- `Body` has two surfaces: `SA_<ID>` (albedo atlas) and `SA_Team` (plain grey, overridden by `unit.gd`).
- Rotor/prop materials are `SA_<ID>_Blade` / `SA_<ID>_Prop`.
- Material IDs are upper case. For example, `ir_f14` uses `SA_IR_F14`.

## Per-model summary
Coordinates are Blender (x right, y forward, z up). L × span × H is the Body extent.

| id | Tris (total / Body) | Body L × span × H | Nodes (pivot / position) | Team colour |
|---|---|---|---|---|
| ir_f14 | 6,644 / 6,520 | 19.1 × 10.0 × 4.86 (wings spread: span 19.4) | `WingL` (−2.75, −1.90, 2.25), `WingR` (2.75, −1.90, 2.25): the glove pivots; sweep = rotate about local Z (Blender) = Godot local Y; wings modelled at 20° LE sweep. `Gun` (−0.62, 6.30, 1.62). `Exhaust0/1` (∓1.40, −8.45, 1.85). `Hardpoint0..5`: L glove AAM, L intake tank, L tunnel AAM, R tunnel AAM, R tank, R glove AAM | twin fin caps |
| ir_f4 | 6,936 / 6,936 | 19.7 × 11.7 × 5.0 | `Gun` (0, 9.25, 1.48), under-nose fairing. `Exhaust0/1` (∓0.55, −5.98, 1.55). `Hardpoint0..5`: L wing tank, L inboard twin AAM, L aft fuselage AAM, R aft fuselage AAM, R inboard, R tank | fin cap |
| ir_su24 | 6,032 / 5,952 | 22.6 (+1.1 pitot) × 8.3 (wings spread: span 17.6) × 6.17 | `WingL` (−2.70, −0.90, 3.05), `WingR` (2.70, −0.90, 3.05): glove pivots, wings at 16° sweep. `Gun` (0.48, 3.15, 1.55), belly. `Exhaust0/1` (∓0.62, −10.75, 2.12). `Hardpoint0..3`: L glove missile, L fuselage bomb, R fuselage bomb, R glove missile | fin cap |
| ir_ah1j | 5,676 / 5,060 | 14.3 × 3.3 × 3.55 (rotor Ø 13.4, hub z 4.0) | `RotorMain` hub (0, 0.70, 4.00), 2 blades, spins about Godot local Y. `RotorTail` hub (0.30, −6.45, 3.00), **right** side of fin, local X = shaft. `Gun` = 3-barrel cannon **mesh**, origin at the turret pivot (0, 5.55, 0.52), so the `unit.gd` recoil offset moves the barrels. `Muzzle` (0, 7.11, 0.46). `Hardpoint0..3`: L outer, L inner, R inner, R outer rocket pods | fin cap, elevator tips |
| ir_ch47 | 7,226 / 6,572 | 16.1 × 3.76 × 6.02 (**identical to U.S. ch47**) | `RotorFront` (0, 5.621, 5.586), `RotorRear` (0, −6.319, 6.005): same as U.S. | **added**: 2 thin pylon-top panels |
| ir_c130 | 7,800 / 6,440 (= U.S.) | 29.5 × 38.9 × 12.8 (**identical to U.S. c130**) | `Prop0..3` (L outer, L inner, R inner, R outer), same hubs as U.S., shaft = Godot local Z | fin cap (as U.S.) |
| ir_shahed | 972 / 758 | 3.29 × 2.53 × 0.55 | `Prop0` (0, −1.62, 0.25), 2-blade pusher, shaft = Godot local Z | tip-fin caps |
| ir_shahed_rail | 408 | 4.9 × 2.6 × 2.22 | `Mount` (0, 0.273, 1.428), rotation +20° about X (nose-up, launch toward +Y / Godot −Z). Place the drone's origin at `Mount` with its rotation, and its belly sits on the cradle (see `docs/screens/ir_shahed_rail_sheet.png`) | crate lid stripe |

GLB-level check: the Iranian CH-47/C-130 node translations, rotations and accessor bounds equal the U.S. GLBs exactly. Only the material and image names differ, plus the added `SA_Team` surface on the CH-47.

## Deviations and decisions
- **Not projected from the concepts.** The panels are perspective views, so the albedo is painted procedurally. The result is clean and stylised, with no baked concept lighting. It is less "painterly" than the U.S. models.
- **Swing wings.**
  - Only the F-14 was asked for `WingL`/`WingR`. The Su-24 got the same treatment for consistency.
  - Extra nodes are ignored by `unit.gd`, because it matches nodes by name or prefix.
  - The wings are thin single surfaces with an inner overlap into the glove. A large sweep rotation (above about 45°) will show the wing root passing through the glove / nacelle. That is acceptable at RTS distance and has not been tuned.
- **AH-1J.**
  - `Gun` is a mesh rather than an empty, so the recoil is visible. `Muzzle` is a separate top-level empty, so it does not move with the recoil.
  - The tail rotor is on the right of the fin, following the concept. The AH-64 has it on the left. The `RotorTail` spin sign is untested in Godot.
- **CH-47C.**
  - The geometry is byte-for-byte from the U.S. builder.
  - Two small `SA_Team` panels were added on the pylon tops, because the U.S. model has none.
  - The blades are plain dark with yellow tips. The U.S. blade texture is sampled from U.S. concept art.
- **C-130 props.** Dark blades with white/red tip bands, as on the concept. The U.S. props have yellow tips.
- **Stores** are generic and fictionalised: tanks, AAMs, bombs and rocket pods. They are not exact loadouts.
- **Gear** is always down, as on the U.S. models.
- **Origins.** The Shahed origin is at its lowest point (the lower tip fins), under the midpoint, per the convention. The rail origin is at ground level, with the Y extent centred.
- **Ids.** Script names are `air_ir_<x>_3d.py`. Sheets are `docs/screens/ir_<x>_sheet.png`, so the id prefix is not doubled.

## Known issues / review items
- The wing surfaces are low-poly: 40–62 triangles per wing node. They read fine at RTS zoom. Raise the section counts if closer shots are needed.
- The canopies are single smooth glass lofts with painted frames. There are no cockpit interiors.
- Intakes are dark face plates, not ducts. Nozzles are simple tubes with dark discs.
- `docs/screens/*` previews are Blender Cycles renders, not in-engine captures.
- Untested in Godot:
  - double-sidedness
  - rotor/prop spin direction signs
  - the `Mount` transform usage
  - the scale factor 0.6 at runtime
- Godot `.import` files and `<id>_<id>_albedo.png` extracts exist in the `ir_*` folders except the Shahed / rail. They were created by a Godot import run outside this agent, about 20:42, after the final GLBs were written at about 20:30. Re-import if any model is regenerated.
- `ir_shahed` / `ir_shahed_rail` have not been imported yet.
- The game data (`unit_defs.gd`, nations) does not reference these ids yet. That is for the lead to wire up.
