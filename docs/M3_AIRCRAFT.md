# M3: U.S. aircraft roster in 3D

Status: **3D art generated and previewed in Blender (Cycles CPU). Not yet imported or run in Godot.** The lead integrates them.
All 14 roster aircraft are real 3D geometry with depth from every angle. None of them is a billboard. They use the approved CH-47 pilot method (`docs/PILOT3D_VEHICLES.md`).
The CH-47 and M88 outputs are unchanged.

## Files
| | |
|---|---|
| Shared kit | `tools/art/airkit.py`. It imports the library half of `veh_m88_3d.py` read-only and contains view extraction and frames, builders, the projection shader, the atlas, the fit overlay, previews and the export pipeline. |
| Per-aircraft scripts | `tools/art/air_<id>_3d.py`, for ids `a10 ah64 f16 uh60 f35 fa18 f22 c130 b52 b1 b2 sr71 ac130 c17`. `air_ac130_3d.py` imports the parameterised airframe builder from `air_c130_3d.py`. |
| Models | `godot/assets/units3d/<id>/<id>.glb`. The textures are embedded. `<id>_albedo.png` (2048²) is also written next to it for inspection, plus `<id>_blade.png` (helicopters) or `<id>_prop.png` (turboprops). |
| Previews | `docs/screens/m3_<id>_sheet.png`: front, side, rear, top (ortho), RTS 52° and close 3/4. Cycles CPU, 640×400, 20 samples, denoised. |

Regenerate (deterministic: no RNG state and no network). Each run takes about 1 minute for the model plus about 4 minutes for previews, on 2 shared CPUs.
```
python3 -I tools/art/air_<id>_3d.py                 # -> godot/assets/units3d/<id>/, docs/screens/m3_<id>_sheet.png
#   --no-previews     skip renders       --fit <png>   silhouette-fit overlay (model outline over the concept views)
#   --sheet <png>     other preview path  <out_dir>    other model folder
```

## Method (same as the CH-47 pilot, generalised)
1. **References.** Side views come from the expanded contact sheets (bottom-left cell). The cropped `individual_views` cut off the tail on several aircraft (for example the A-10 fin), so they are not used. The side view is taken as the connected alpha components in that cell.
   - Top views come from the cleaned nose-up sprites `godot/assets/aircraft/<id>/<id>_top.png`. For the AH-64 and UH-60 they come from the blade-free bodies in `godot/assets/us/rotors/`.
   - The F-35 uses `incoming_f35/f35_turnaround.png`: the side is top-right, and the top view is bottom-left, rotated 90° to nose-up.
   - The AC-130 and C-17 use `incoming_airlift/.../*_turnaround.png`. On these sheets the views touch each other, so `sheet_cell(split=4)` erodes the alpha before labelling. The C-17 top view is drawn nose-down and is rotated 180°.
   - Some `front_three_quarter` crops in the expanded pack are truncated PNGs: A-10, B-2 and F-22. None are used.
2. **Frames.** The side view uses one uniform scale, taken from the real length, or for the AH-64 from the rotor radius. It defines world Y and Z. The top view has its own X scale (real span) and a piecewise-linear Y rectification through 2–4 landmarks (nose, canopy / prop plane / spike tips / hub, tail).
   - Several concept top views are much stubbier than their side views: SR-71 length/span 1.18 vs 1.93 real, F-16 1.13 vs 1.52. Without the rectification their wings would sit in the wrong place.
3. **Geometry.** Built from pixel measurements on the views, checked with `--fit` overlays (model silhouette over concept, both views) and iterated.
   - Fuselages are superellipse lofts: side top/bottom lines and top-view half-widths.
   - Canopies are separate lofts.
   - Wings, LERX/chines, stabilisers and fins are NACA-section lofted surfaces. Fins can be canted.
   - Nacelles, tanks, missiles, bombs and gun barrels are bodies of revolution.
   - The B-2 is one spanwise loft whose centre-body contours blend into a thin outer aerofoil.
   - Landing gear is added on every aircraft, gear down. The jet concepts are drawn gear-up.
4. **Texture.** One Smart-UV atlas per aircraft, textured by depth-tested projection.
   - The top view goes on up-facing texels and the side view on ±X texels. The same side image is used on both sides, so the far side is mirrored.
   - The underside gets a blurred top view, darkened.
   - Gear is flat dark grey. Intake faces and nozzle interiors are flat near-black (`dark` parts).
   - A Cycles AO bake is multiplied in at 40–45%, with light mottling and grime.
5. **Rotors and propellers** are built from real thin blade lofts (twist, coning, taper; props use a paddle planform). The hub is at the object origin and the object rotation is identity, so the spin axis is a plain local axis.
   - Helicopter blades are textured with a strip sampled along a blade of `ah64_blades.png` / `uh60_blades.png`.
   - Propellers use a flat dark grey with yellow tips.

## Conventions (all models)
- Metres. Forward = Blender +Y = **Godot −Z**. Up = +Z (Godot +Y). The root origin is at ground contact (wheel bottoms) under the fuselage midpoint, which is the midpoint of the side-view nose-to-tail extent.
- All nodes are **top-level** in the GLB. Empties export as plain nodes.
- `Body`: static. It holds the airframe, gear, stores and nacelles. It has two surfaces:
  - `SA_<ID>`: Principled BSDF with one albedo image texture.
  - **`SA_Team`**: a plain grey material for team colour (`unit.gd` overrides it).
- `RotorMain` spins about **local Y in Godot** (Blender Z). `RotorTail`'s **local X is the shaft** (spin about local X). `Prop0..3` spin about **local Z in Godot** (the shaft, pointing forward/back).
- The game must spin each node in place: every one has identity rotation and its origin at the hub.
- Jets: `Exhaust<i>` empties sit at the nozzle exits (for glow/trails). `Gun` is at the cannon muzzle. `Hardpoint<i>` empties are at the store centres or release points.

## Per-aircraft summary (from the final run; Blender coordinates in metres, x right, y forward, z up)
| id | Tris (total / Body) | Body extents L × span × H | Animated nodes (pivot) | Empties | Concept fit / notes |
|---|---|---|---|---|---|
| a10 | 7,048 | 16.3 × 17.2 × 4.45 | — | Gun (0, 8.13, 1.37); Exhaust0/1 (±1.55, −4.85, 3.26); Hardpoint0–7 (wing stores, L outboard → R outboard) | Good. Twin engines, twin fins, GAU barrel, 2 AAM + 4 bombs |
| ah64 | 5,928 / 5,212 | 16.3 × 7.1 × 6.06 (rotor Ø 14.6) | RotorMain hub (0, 1.71, 4.71); RotorTail hub (−0.42, −7.38, 4.05), shaft = local X | Gun (0, 7.09, 1.16); Hardpoint0–3 (stub-wing stores) | Good. Mast-top radome, nose sensor, chin gun, 2 rocket pods, 2×4 missiles |
| f16 | 5,874 | 15.3 × 10.0 × 5.08 | — | Gun (−0.62, 3.46, 1.88); Exhaust0 (0, −7.57, 1.78); Hardpoint0–5 | Good. Tip AAMs, 2 AAMs, 2 tanks, chin intake |
| uh60 | 4,850 / 4,134 | 15.4 × 4.5 × 3.9 (rotor Ø 16.4) | RotorMain (0, 1.89, 3.77); RotorTail (−0.42, −6.63, 4.08), shaft = local X | Gun (−1.75, 4.55, 1.53) door gun | Good. Engine hump, stabilator, tail pylon |
| f35 | 4,298 | 16.0 × 10.8 × 5.34 | — | Gun (−1.15, 2.60, 3.02); Exhaust0 (0, −7.30, 2.11); Hardpoint0–3 (bays) | Good. Canted twin fins; deeper than the real aircraft (follows the concept) |
| fa18 | 5,866 | 17.2 × 14.0 × 5.45 | — | Gun (0, 8.10, 2.17); Exhaust0/1 (±0.57, −8.60, 1.97); Hardpoint0–6 (5 = R tip, 6 = centre tank) | Good. LEX, canted fins, 6 AAMs + tank |
| f22 | 4,354 | 19.8 × 13.4 × 5.6 | — | Gun (1.25, 3.16, 2.95); Exhaust0/1 (±0.67, −8.93, 1.98); Hardpoint0–3 (bays) | Good planform. 2D nozzles are simple boxes |
| c130 | 7,800 / 6,440 | 29.5 × 38.9 × 12.8 | Prop0–3 hubs (±9.75 / ±4.83, 4.58, 4.59–4.80), shaft = local Z (Godot) | — | Good. 4-blade props, sponsons. Used by `battle.gd` supply drop |
| b52 | 7,270 | 48.1 × 55.8 × 14.0 | — | Exhaust0–7 (pod exits); Hardpoint0/1 (bay), 2/3 (inner-wing pylons) | Good. 4 twin pods; concept fin shorter than real |
| b1 | 6,494 | 44.7 × 41.9 × 11.7 | — | Exhaust0–3 (−12.52 aft); Hardpoint0–2 (bays, front → rear) | Good. Fixed intermediate sweep, blended glove |
| b2 | 4,012 | 21.0 × 52.4 × 5.15 | — | Exhaust0–3 (upper-surface slots); Hardpoint0/1 (bays) | Good. Saw-tooth trailing edge, engine humps. Team panels near the wingtips |
| sr71 | 4,742 | 31.9 × 16.9 × 8.17 | — | Exhaust0/1 (±4.28, −15.18, 2.52) | Fair. Recognisable chines, spikes and canted fins; nacelles oversized (concept), tall gear |
| ac130 | 8,516 / 7,156 | 29.6 × 43.3 × 13.5 | Prop0–3 hubs (±13.2 / ±6.86, 6.36, 5.04–5.32), shaft = local Z (Godot) | Gun0–2 left-side muzzles (front → rear) | Good. Guns, sensor ball, under-wing tanks; airframe builder shared with the C-130 |
| c17 | 7,330 | 52.9 × 52.7 × 18.1 | — | Exhaust0–3 (engine exits) | Good. Anhedral wing, winglets, T-tail, sponsons |

The C-5 (optional) was not built.

Triangle budget: all models are under the ceilings (15k for fighters and helicopters, 20k for large aircraft). The F-35, F-22, UH-60, AH-64, SR-71 and B-2 are below the lower 6k figure. That is ample for the RTS camera. If a denser look is wanted, the segment counts in the scripts (`seg=`, section counts) can be raised.

## Insignia (roundels) — not decided for the fictional setting
The concept art carries U.S. star-and-bar roundels. Per instructions, the projected art is kept as is: no insignia was painted, removed or replaced.
Roundels are visible on:
- **A-10**: forward fuselage sides and right wing top.
- **AH-64**: tail boom sides.
- **F-16**: right wing top.
- **UH-60**: tail boom sides.
- **F-35**: both wing tops and forward fuselage sides.
- **F/A-18**: left wing top and forward fuselage sides.
- **F-22**: right wing top and fin outer faces.
- **B-52**: right wing top and aft fuselage sides.
- **B-1**: right wing top and forward fuselage sides.
- **B-2**: left outer wing top and aft body sides.

The side-view art is projected onto both sides, so each fuselage or fin roundel appears on both sides, mirrored on the right side.
The underside is a blurred, darkened copy of the top view, so a faint smudge of each wing-top roundel also appears underneath.
On the C-130, AC-130, C-17 and SR-71 concepts no clear national roundel was seen, apart from small light marks that read as stencils. This has not been audited at pixel level.

If the setting needs neutral markings, there are two routes:
- Mask those regions in the scripts (paint a sampled base colour over the roundel pixel boxes of the reference before projection), then regenerate.
- Ask the visual concept agent for roundel-free references.

## Known shortcomings / review items
- **Concept inconsistency.** The AI concept views disagree with each other and with the real aircraft. Geometry follows the side view and the rectified top view. As a result:
  - F-35, F-22, F/A-18 and SR-71 are deeper and taller than the real aircraft: about 5.2–5.6 m and 8.1 m overall height, against 4.4–5.1 m and 5.6 m real.
  - The B-52 fin is shorter than real.
  - The AC-130 nacelles sit further outboard than on the C-130 concept.
- **Side views are not orthographic.** The concept side views show the far-side fin, engine or tail rotor displaced by perspective. Only the near item is modelled, and the far one can leave a faint ghost in the projected texture (A-10 fins and engines, F-22 / F/A-18 fins).
- **Texture smearing.** Faces that no projection covers well show stretched side-view colour: nose caps, nacelle fronts, wing-tip caps, F-16 nozzle rim. It is invisible from the RTS camera and visible in the close 3/4 shots. The painted lighting of the concepts is baked into the albedo, as on the CH-47.
- **Simplifications**
  - **Intakes:** no inlet ducts. The F-35 / F-22 side intakes are painted only. The F-16 and F/A-18 have simple box/loft intakes with dark faces.
  - **Fixed parts:** the B-1 wing sweep is fixed at the concept's intermediate sweep, and it has no sweep node. Control surfaces are not separate nodes. Gear is not retractable (always down, as instructed).
  - **Omitted parts:**
    - No B-52 outrigger wheels.
    - No ventral fins on the F/A-18 / F-22.
    - The F-16 ventral fins are thin slabs.
  - **Rotors and props:** rotor blades are rigid (no droop) and masts are vertical. Props are 4-blade (the concept shows 4).
- **Stores.** The A-10, F-16 and F/A-18 carry stores matching their concepts. The AH-64 has two rocket pods and two 4-missile racks. The F-35, F-22, B-1 and B-2 have `Hardpoint` empties at internal-bay positions. The SR-71, C-130 and C-17 have no hardpoints. The UH-60 has a left door gun (`Gun`), and the AC-130 has three left-side guns (`Gun0..2`).
- **Team colour** is small, as requested: fin tips (all finned aircraft), stabiliser tips (AH-64, UH-60, C-17), and wing-tip panels on the B-2.
- **Godot import is untested**: double-sidedness, LOD generation, and the rotor/prop spin direction signs in game. The previews are Blender Cycles renders (Standard view transform, sun + sky), not in-engine captures.
- `battle.gd` already loads `res://assets/units3d/c130/c130.glb` for the supply-drop flyover when it exists. That model now exists, so the drop now shows the 3D C-130 (untested in Godot).
