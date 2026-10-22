# M2 U.S. ground-vehicle roster in 3D (12 vehicles)

Status: **Generated and previewed in Blender 5.2 (Cycles CPU). Not yet imported or run in Godot.**
Each model uses the same method as the approved M88 pilot (`docs/PILOT3D_VEHICLES.md`): real geometry fitted to the concept silhouettes, with the concept art projected and baked into one albedo atlas per vehicle.
No vehicle is a billboard.

| Vehicle | GLB | Script |
|---|---|---|
| Abrams-style MBT | `godot/assets/units3d/abrams/abrams.glb` | `tools/art/veh_abrams_3d.py` |
| HMMWV .50 cal | `godot/assets/units3d/hmmwv_50cal/hmmwv_50cal.glb` | `tools/art/veh_hmmwv_3d.py hmmwv_50cal` |
| Avenger (HMMWV SAM) | `godot/assets/units3d/avenger/avenger.glb` | `tools/art/veh_hmmwv_3d.py avenger` |
| Bradley-style IFV | `godot/assets/units3d/bradley/bradley.glb` | `tools/art/veh_bradley_3d.py` |
| Paladin-style SPH | `godot/assets/units3d/paladin/paladin.glb` | `tools/art/veh_paladin_3d.py` |
| MRAP (M-ATV style) | `godot/assets/units3d/mrap/mrap.glb` | `tools/art/veh_mrap_3d.py` |
| Stryker-style 8x8 | `godot/assets/units3d/stryker/stryker.glb` | `tools/art/veh_stryker_3d.py` |
| HMMWV TOW | `godot/assets/units3d/hmmwv_tow/hmmwv_tow.glb` | `tools/art/veh_hmmwv_3d.py hmmwv_tow` |
| HMMWV ambulance | `godot/assets/units3d/hmmwv_medical/hmmwv_medical.glb` | `tools/art/veh_hmmwv_3d.py hmmwv_medical` |
| HMMWV (base) | `godot/assets/units3d/hmmwv/hmmwv.glb` | `tools/art/veh_hmmwv_3d.py hmmwv` |
| M113-style APC | `godot/assets/units3d/m113/m113.glb` | `tools/art/veh_m113_3d.py` |
| M777-style towed howitzer | `godot/assets/units3d/m777/m777.glb` | `tools/art/veh_m777_3d.py` |

Shared library: `tools/art/vehkit.py`. It imports the library half of `veh_m88_3d.py` unchanged, so the M88 output is not affected.
The HMMWV-family script also supplies the wheeled chassis and shield/RWS builders that the MRAP and Stryker scripts use.

Regenerate any vehicle with `python3 tools/art/<script> [--out DIR] [--no-previews | --quick] [--previews DIR]`.
Runs are deterministic: there is no RNG state and no network access.
Each run takes about 1 to 1.5 minutes without previews and about 4 to 6 minutes with the preview sheet, on 2 shared CPUs.
QA files go to `$VEH_QA_DIR`, or by default to `godot/assets/units3d/<id>/_qa/` (which has a `.gdignore`).
They are a silhouette overlay per concept view and `<id>_report.txt`.

## Conventions (all 12)
- **Units and axes:** metres. Forward is Blender +Y, which the exporter writes as Godot −Z. Up is +Z, which becomes Godot +Y. Vehicle left is −X.
- **Root origin:** ground contact under the vehicle centre. The centre is the midpoint of the hull length, or of the overall length for the M777.
- **`Hull`:** a static mesh holding the body, belly, bumpers, lights, stowage and return rollers. It also carries the team-colour panels as a second material slot.
- **Tracked vehicles** (abrams, bradley, paladin, m113):
  - `WheelL0..n` / `WheelR0..n`, `SprocketL/R` and `IdlerL/R` have hub origins and spin about **local X**.
  - `TrackL` / `TrackR` use material **`SA_TrackScroll`**. V runs along the belt, and the loop holds a whole number of texture tiles, so it has no seam.
  - In Blender, V increases towards the front on the ground run. The glTF exporter writes V' = 1 − V. When the vehicle drives forward a distance `d`, set `uv1_offset.y -= d / metres_per_V` (the per-vehicle value is listed below). Reverse it for reverse gear; for a pivot turn, use opposite signs on each side.
  - The right-side running gear is a mirrored copy that shares the left side's UVs.
- **Wheeled vehicles:**
  - Wheels are named `WheelFL/FR`, `WheelRL/RR`. The Stryker also has `WheelML/MR` (2nd axle) and `WheelM2L/M2R` (3rd axle). The M777 has `WheelL/WheelR`.
  - Wheels have hub origins and spin about local X.
  - Steering wheels sit under empties `SteerFL/SteerFR` (and `SteerML/SteerMR` on the Stryker). Each empty is placed at the hub; yaw it about local Y in Godot. The wheel's local transform under its empty is the identity.
- **Weapons:**
  - `Turret` has its origin on the yaw axis (the game yaws it about local Y).
  - `Gun` is a child of `Turret`, with its origin on the elevation trunnion (the game pitches it about local X).
  - `Muzzle` is an empty child of `Gun`, placed at the barrel or launch-tube tip.
  - The base HMMWV and the ambulance have no weapon, so they have no Turret/Gun/Muzzle.
- **Materials:**
  - `SA_<Id>` is a Principled BSDF with a single 2048² albedo image.
  - `SA_TrackScroll` is a Principled BSDF with a 256×512 tile.
  - `SA_Team` is plain grey (0.62), with no texture, and is meant to be tinted in game. It is applied to a few strips and panels per vehicle: hull sides, turret sides or bustle, and pods.
- **Textures:** the albedo PNGs are embedded in each GLB. A copy sits beside each GLB for inspection.

## Method (differences from the M88 pilot)
1. **Measurement.**
   - Every concept view was read on gridded crops. Side views marked `faces=right` in the manifest are flipped so the nose points left first.
   - Each side view gets one uniform scale, taken from the manifest `length_m` over the hull's pixel length.
   - Top views get their own scale. Where the concept top view disagrees with the side view (turret position, barrel length), Y is rectified piecewise-linearly through landmarks; this was needed for abrams, avenger, bradley and paladin. Where a top view was clearly too wide, an across-scale squeeze is applied; this is stated per vehicle.
2. **Geometry.**
   - Hulls, bodies and turrets come from an **exact boolean intersection** of two prisms: one is the auto-traced side silhouette (alpha contour with wheel discs removed, a morphological opening to drop antennas and rods, then polygon simplification); the other is a hand-measured plan outline from the top view.
   - Guns, launchers, cupolas, running gear, lights, stowage, antennas and rails are primitives placed at measured positions.
3. **3/4 views.** The front-3/4 and rear-3/4 concepts are registered automatically. A pinhole camera (azimuth, elevation, distance, scale, offset, roll) is fitted to each concept silhouette by maximising IoU (grid search followed by Nelder-Mead). The fitted IoU is reported per vehicle.
   - Every texel that faces such a camera is projected into that view and depth-tested in the view's own image space.
   - This replaces the M88's one hand-made homography per plate.
4. **Texture blend.** The side, top and 3/4 projections are normal-weighted. A Cycles AO bake (1024², 16 samples) is multiplied in at 50%, and light procedural grime is added, as on the M88.
   - Options per object: guns that the concept side view draws elevated use the top view only (Paladin, M777). Guns that the concept top view draws traversed use the side view only, and the painted gun is patched out of the top view (HMMWV .50 cal, Bradley).
5. **Rotation-invariant wheels.**
   - Every wheel, sprocket and idler texel is resampled from the side view as a **radial profile**: an average over a ±20° sector at the bottom of the wheel, taken at the texel's radius. AO is not multiplied onto wheels.
   - A spinning wheel therefore never shows the skirt or fender colours baked into its hidden upper half.
   - Tyre treads are procedural rubber.
6. **Tracks.** As on the M88: a procedural link tile whose colours come from the concept's lower track run.

## Known shortcomings (all vehicles)
- **Baked lighting:** the concept art's painted light and shadow is in the albedo, as on the M88. Front and rear faces come from strongly perspective 3/4 views and are noticeably softer and streakier than the sides. The rear views of the Paladin and Stryker are the weakest.
- **AI-art inconsistencies:** the concept views disagree with each other. Geometry follows the side view, and the disagreements are absorbed by top-view rectification, so some roof detail is compressed or stretched.
- **Rest pose:**
  - Turrets and guns are modelled at rest and pointing forward.
  - Concepts that draw the gun traversed or elevated (Paladin, M777, the HMMWV .50 cal top view, the MRAP) cannot texture the gun exactly. Those guns get plain projected colour.
- **Godot import is untested:** double-sidedness, LOD and collision still need checking. No LODs were authored.
- **Preview renders:** Blender Cycles with the Standard view transform, not in-engine captures.
- **National insignia:** none were seen in these concepts except the ambulance red crosses, which were handled as described below. This should still be checked visually before release.


## abrams

- Script: `python3 tools/art/veh_abrams_3d.py` -> `godot/assets/units3d/abrams/abrams.glb` (+ `abrams_albedo.png`, `abrams_track.png`); sheet `docs/screens/m2_abrams_sheet.png`
- **Triangles: 9752**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 1904 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 1008 | - | (0.0, -0.05, 1.74) | (0.0, -0.05, 1.74) |
| `Gun` | mesh | 312 | Turret | (0.0, 1.603, 2.387) | (0.0, 1.653, 0.647) |
| `Muzzle` | empty | 0 | Gun | (0.0, 4.981, 2.387) | (0.0, 3.378, 0.0) |
| `TrackL` | mesh | 1328 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `TrackR` | mesh | 1328 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `WheelL0` | mesh | 188 | - | (-1.62, 2.44, 0.49) | (-1.62, 2.44, 0.49) |
| `WheelL1` | mesh | 188 | - | (-1.62, 1.534, 0.49) | (-1.62, 1.534, 0.49) |
| `WheelL2` | mesh | 188 | - | (-1.62, 0.651, 0.49) | (-1.62, 0.651, 0.49) |
| `WheelL3` | mesh | 188 | - | (-1.62, -0.221, 0.49) | (-1.62, -0.221, 0.49) |
| `WheelL4` | mesh | 188 | - | (-1.62, -1.069, 0.49) | (-1.62, -1.069, 0.49) |
| `WheelL5` | mesh | 188 | - | (-1.62, -1.882, 0.49) | (-1.62, -1.882, 0.49) |
| `WheelL6` | mesh | 188 | - | (-1.62, -2.695, 0.49) | (-1.62, -2.695, 0.49) |
| `WheelR0` | mesh | 188 | - | (1.62, 2.44, 0.49) | (1.62, 2.44, 0.49) |
| `WheelR1` | mesh | 188 | - | (1.62, 1.534, 0.49) | (1.62, 1.534, 0.49) |
| `WheelR2` | mesh | 188 | - | (1.62, 0.651, 0.49) | (1.62, 0.651, 0.49) |
| `WheelR3` | mesh | 188 | - | (1.62, -0.221, 0.49) | (1.62, -0.221, 0.49) |
| `WheelR4` | mesh | 188 | - | (1.62, -1.069, 0.49) | (1.62, -1.069, 0.49) |
| `WheelR5` | mesh | 188 | - | (1.62, -1.882, 0.49) | (1.62, -1.882, 0.49) |
| `WheelR6` | mesh | 188 | - | (1.62, -2.695, 0.49) | (1.62, -2.695, 0.49) |
| `IdlerL` | mesh | 188 | - | (-1.62, 3.66, 0.85) | (-1.62, 3.66, 0.85) |
| `IdlerR` | mesh | 188 | - | (1.62, 3.66, 0.85) | (1.62, 3.66, 0.85) |
| `SprocketL` | mesh | 432 | - | (-1.62, -3.392, 0.93) | (-1.62, -3.392, 0.93) |
| `SprocketR` | mesh | 432 | - | (1.62, -3.392, 0.93) | (1.62, -3.392, 0.93) |

- turret pivot (0.0, -0.05, 1.74), gun trunnion (0.0, 1.603, 2.387), muzzle y 4.961
- road wheel r 0.35, idler r 0.29, sprocket r 0.3
- track loop 16.625 m, links 102, link pitch 0.1630 m, metres per V 0.9779 (tile = 6 links)
- front34: az 25.6 el 3.3 dist 165.7 m  scale 97.3 px/m  roll -0.8  silhouette IoU 0.861
- rear34: az 150.3 el 5.8 dist 24.5 m  scale 87.9 px/m  roll 2.0  silhouette IoU 0.884
- side silhouette IoU 0.869
- top silhouette IoU 0.967
- atlas coverage 0.704
- Width follows the concept but is squeezed by sx 0.9 to 3.97 m over the skirts; the concept's top view is 4.4 m, while a real M1 is 3.66 m.
- Top view rectified in Y: the concept turret front sits about 0.5 m further forward than in the side view, and its bustle rack is about 0.4 m shorter.
- The bustle rack is a solid box textured with the side view's basket, not an open frame. The skirts hide the return rollers and the upper road wheels, as in the concept.
- Shortcomings: the turret roof is slightly plain. The RWS and CITV are simple boxes. The front-glacis texture from the front-3/4 view is soft.

## hmmwv_50cal

- Script: `python3 tools/art/veh_hmmwv_3d.py hmmwv_50cal` -> `godot/assets/units3d/hmmwv_50cal/hmmwv_50cal.glb` (+ `hmmwv_50cal_albedo.png`); sheet `docs/screens/m2_hmmwv_50cal_sheet.png`
- **Triangles: 6460**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 2240 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 412 | - | (0.0, -0.15, 1.825) | (0.0, -0.15, 1.825) |
| `Gun` | mesh | 128 | Turret | (0.0, 0.053, 2.388) | (0.0, 0.203, 0.563) |
| `Muzzle` | empty | 0 | Gun | (0.0, 1.524, 2.388) | (0.0, 1.471, 0.0) |
| `SteerFL` | empty | 0 | - | (-1.05, 1.672, 0.464) | (-1.05, 1.672, 0.464) |
| `WheelFL` | mesh | 920 | SteerFL | (-1.05, 1.672, 0.464) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (1.05, 1.672, 0.464) | (1.05, 1.672, 0.464) |
| `WheelFR` | mesh | 920 | SteerFR | (1.05, 1.672, 0.464) | (0.0, 0.0, 0.0) |
| `WheelRL` | mesh | 920 | - | (-1.05, -1.396, 0.464) | (-1.05, -1.396, 0.464) |
| `WheelRR` | mesh | 920 | - | (1.05, -1.396, 0.464) | (1.05, -1.396, 0.464) |

- wheel radius 0.464 m, tyre width 0.33 m, wheel track x +-1.05
- front34: az 26.8 el 3.9 dist 78.8 m  scale 161.0 px/m  roll 0.9  silhouette IoU 0.874
- rear34: az -147.4 el 17.1 dist 158.1 m  scale 140.0 px/m  roll -8.8  silhouette IoU 0.831
- side silhouette IoU 0.946
- top silhouette IoU 0.894
- atlas coverage 0.574
- Concept top view draws the M2 traversed 90 deg across the roof; that strip was patched out of the top view and the gun is textured from the side view only.
- Shortcomings: the shields are flat panels without vision blocks. The rear-3/4 projection is noisy on the tailgate.

## avenger

- Script: `python3 tools/art/veh_hmmwv_3d.py avenger` -> `godot/assets/units3d/avenger/avenger.glb` (+ `avenger_albedo.png`); sheet `docs/screens/m2_avenger_sheet.png`
- **Triangles: 6712**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 1748 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 236 | - | (0.0, -0.522, 1.242) | (0.0, -0.522, 1.242) |
| `Gun` | mesh | 1048 | Turret | (0.0, -0.522, 2.505) | (0.0, 0.0, 1.262) |
| `Muzzle` | empty | 0 | Gun | (-0.95, 0.602, 2.502) | (-0.95, 1.123, -0.003) |
| `SteerFL` | empty | 0 | - | (-1.02, 1.811, 0.518) | (-1.02, 1.811, 0.518) |
| `WheelFL` | mesh | 920 | SteerFL | (-1.02, 1.811, 0.518) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (1.02, 1.811, 0.518) | (1.02, 1.811, 0.518) |
| `WheelFR` | mesh | 920 | SteerFR | (1.02, 1.811, 0.518) | (0.0, 0.0, 0.0) |
| `WheelRL` | mesh | 920 | - | (-1.02, -1.598, 0.518) | (-1.02, -1.598, 0.518) |
| `WheelRR` | mesh | 920 | - | (1.02, -1.598, 0.518) | (1.02, -1.598, 0.518) |

- wheel radius 0.518 m, tyre width 0.34 m, wheel track x +-1.02
- Avenger: concept top view is ~25% short and pods sit further aft than in the side view -> top projection rectified piecewise in Y (side view wins for geometry); width squeezed (sx 0.70) to 2.23 m.
- front34: az -34.4 el 3.0 dist 109.2 m  scale 144.0 px/m  roll 0.6  silhouette IoU 0.893
- rear34: az -151.2 el 7.0 dist 59.4 m  scale 134.4 px/m  roll -0.5  silhouette IoU 0.906
- side silhouette IoU 0.907
- top silhouette IoU 0.841
- atlas coverage 0.602
- The missile pods and their cross arms form `Gun` (they elevate together). `Muzzle` is at the front of the left pod. The cab, pedestal and right-hand .50 cal belong to `Turret`.
- Shortcomings: the concept views disagree strongly. The top view is about 25% short, and its pods sit further aft than in the side view. As a result the roof and pod-top textures are somewhat compressed.
- The pods are boxes with 4 visible tube ends each.

## bradley

- Script: `python3 tools/art/veh_bradley_3d.py` -> `godot/assets/units3d/bradley/bradley.glb` (+ `bradley_albedo.png`, `bradley_track.png`); sheet `docs/screens/m2_bradley_sheet.png`
- **Triangles: 8516**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 1396 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 1212 | - | (0.0, -0.748, 2.085) | (0.0, -0.748, 2.085) |
| `Gun` | mesh | 220 | Turret | (0.0, 0.506, 2.552) | (0.0, 1.254, 0.467) |
| `Muzzle` | empty | 0 | Gun | (0.0, 2.583, 2.552) | (0.0, 2.077, 0.0) |
| `TrackL` | mesh | 1128 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `TrackR` | mesh | 1128 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `WheelL0` | mesh | 188 | - | (-1.42, 1.985, 0.41) | (-1.42, 1.985, 0.41) |
| `WheelL1` | mesh | 188 | - | (-1.42, 1.224, 0.41) | (-1.42, 1.224, 0.41) |
| `WheelL2` | mesh | 188 | - | (-1.42, 0.463, 0.41) | (-1.42, 0.463, 0.41) |
| `WheelL3` | mesh | 188 | - | (-1.42, -0.298, 0.41) | (-1.42, -0.298, 0.41) |
| `WheelL4` | mesh | 188 | - | (-1.42, -1.06, 0.41) | (-1.42, -1.06, 0.41) |
| `WheelL5` | mesh | 188 | - | (-1.42, -1.821, 0.41) | (-1.42, -1.821, 0.41) |
| `WheelR0` | mesh | 188 | - | (1.42, 1.985, 0.41) | (1.42, 1.985, 0.41) |
| `WheelR1` | mesh | 188 | - | (1.42, 1.224, 0.41) | (1.42, 1.224, 0.41) |
| `WheelR2` | mesh | 188 | - | (1.42, 0.463, 0.41) | (1.42, 0.463, 0.41) |
| `WheelR3` | mesh | 188 | - | (1.42, -0.298, 0.41) | (1.42, -0.298, 0.41) |
| `WheelR4` | mesh | 188 | - | (1.42, -1.06, 0.41) | (1.42, -1.06, 0.41) |
| `WheelR5` | mesh | 188 | - | (1.42, -1.821, 0.41) | (1.42, -1.821, 0.41) |
| `IdlerL` | mesh | 188 | - | (-1.42, -2.963, 0.8) | (-1.42, -2.963, 0.8) |
| `IdlerR` | mesh | 188 | - | (1.42, -2.963, 0.8) | (1.42, -2.963, 0.8) |
| `SprocketL` | mesh | 400 | - | (-1.42, 3.023, 0.78) | (-1.42, 3.023, 0.78) |
| `SprocketR` | mesh | 400 | - | (1.42, 3.023, 0.78) | (1.42, 3.023, 0.78) |

- turret pivot (0.0, -0.748, 2.085), trunnion (0.0, 0.506, 2.552), muzzle y 2.573
- road wheel r 0.3, sprocket (front) r 0.25, idler (rear) r 0.25
- track loop 14.052 m, links 90, link pitch 0.1561 m, metres per V 0.9368 (tile = 6 links)
- front34: az -29.7 el 3.8 dist 26.3 m  scale 104.8 px/m  roll -0.0  silhouette IoU 0.912
- rear34: az -145.1 el 13.4 dist 15.3 m  scale 98.3 px/m  roll -1.6  silhouette IoU 0.906
- side silhouette IoU 0.905
- top silhouette IoU 0.961
- atlas coverage 0.715
- The drive sprocket is at the FRONT and the idler at the rear, as on the real vehicle and in the concept. The 25 mm barrel was patched out of the concept top view, where it is drawn over the front deck.
- Top view rectified in Y: its turret is about 0.4 m further forward, and its barrel overhangs the nose.
- The TOW box is on the turret's left side. Shortcomings: the hull roof shows some dark diagonal streaks inherited from the concept top view. The rear ramp is flat.

## paladin

- Script: `python3 tools/art/veh_paladin_3d.py` -> `godot/assets/units3d/paladin/paladin.glb` (+ `paladin_albedo.png`, `paladin_track.png`); sheet `docs/screens/m2_paladin_sheet.png`
- **Triangles: 8312**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 1018 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 806 | - | (0.0, -1.2, 1.671) | (0.0, -1.2, 1.671) |
| `Gun` | mesh | 408 | Turret | (0.0, -0.229, 2.053) | (0.0, 0.971, 0.382) |
| `Muzzle` | empty | 0 | Gun | (0.0, 4.835, 2.053) | (0.0, 5.065, 0.0) |
| `TrackL` | mesh | 1136 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `TrackR` | mesh | 1136 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `WheelL0` | mesh | 188 | - | (-1.5, 2.225, 0.43) | (-1.5, 2.225, 0.43) |
| `WheelL1` | mesh | 188 | - | (-1.5, 1.49, 0.43) | (-1.5, 1.49, 0.43) |
| `WheelL2` | mesh | 188 | - | (-1.5, 0.754, 0.43) | (-1.5, 0.754, 0.43) |
| `WheelL3` | mesh | 188 | - | (-1.5, -0.029, 0.43) | (-1.5, -0.029, 0.43) |
| `WheelL4` | mesh | 188 | - | (-1.5, -0.812, 0.43) | (-1.5, -0.812, 0.43) |
| `WheelL5` | mesh | 188 | - | (-1.5, -1.547, 0.43) | (-1.5, -1.547, 0.43) |
| `WheelL6` | mesh | 188 | - | (-1.5, -2.33, 0.43) | (-1.5, -2.33, 0.43) |
| `WheelR0` | mesh | 188 | - | (1.5, 2.225, 0.43) | (1.5, 2.225, 0.43) |
| `WheelR1` | mesh | 188 | - | (1.5, 1.49, 0.43) | (1.5, 1.49, 0.43) |
| `WheelR2` | mesh | 188 | - | (1.5, 0.754, 0.43) | (1.5, 0.754, 0.43) |
| `WheelR3` | mesh | 188 | - | (1.5, -0.029, 0.43) | (1.5, -0.029, 0.43) |
| `WheelR4` | mesh | 188 | - | (1.5, -0.812, 0.43) | (1.5, -0.812, 0.43) |
| `WheelR5` | mesh | 188 | - | (1.5, -1.547, 0.43) | (1.5, -1.547, 0.43) |
| `WheelR6` | mesh | 188 | - | (1.5, -2.33, 0.43) | (1.5, -2.33, 0.43) |
| `IdlerL` | mesh | 188 | - | (-1.5, -3.028, 0.68) | (-1.5, -3.028, 0.68) |
| `IdlerR` | mesh | 188 | - | (1.5, -3.028, 0.68) | (1.5, -3.028, 0.68) |
| `SprocketL` | mesh | 400 | - | (-1.5, 3.008, 0.72) | (-1.5, 3.008, 0.72) |
| `SprocketR` | mesh | 400 | - | (1.5, 3.008, 0.72) | (1.5, 3.008, 0.72) |

- turret pivot (0.0, -1.2, 1.671), trunnion (0.0, -0.229, 2.053), barrel 5.05 m, muzzle y 4.825
- road wheel r 0.33, sprocket (front) r 0.27, idler (rear) r 0.26
- track loop 14.197 m, links 90, link pitch 0.1577 m, metres per V 0.9465 (tile = 6 links)
- front34: az 23.6 el 5.7 dist 92.3 m  scale 101.9 px/m  roll -0.6  silhouette IoU 0.830
- rear34: az -155.3 el 7.4 dist 35.1 m  scale 97.7 px/m  roll -4.9  silhouette IoU 0.839
- side silhouette IoU 0.785
- top silhouette IoU 0.935
- atlas coverage 0.717
- The concept side view shows the howitzer elevated about 15 deg. The model rests level, and the gun is textured from the top view only, where the barrel is drawn straight.
- Barrel length is measured along the elevated barrel in the side view. Top view rectified in Y: its turret front is about 1 m further forward.
- Shortcomings: the rear-3/4 concept projection makes the turret rear and rear deck streaky. The muzzle brake is simplified.

## mrap

- Script: `python3 tools/art/veh_mrap_3d.py` -> `godot/assets/units3d/mrap/mrap.glb` (+ `mrap_albedo.png`); sheet `docs/screens/m2_mrap_sheet.png`
- **Triangles: 6676**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 2456 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 412 | - | (0.0, -0.45, 2.706) | (0.0, -0.45, 2.706) |
| `Gun` | mesh | 128 | Turret | (0.0, -0.359, 3.078) | (0.0, 0.091, 0.372) |
| `Muzzle` | empty | 0 | Gun | (0.0, 0.598, 3.078) | (0.0, 0.957, 0.0) |
| `SteerFL` | empty | 0 | - | (-1.22, 1.991, 0.677) | (-1.22, 1.991, 0.677) |
| `WheelFL` | mesh | 920 | SteerFL | (-1.22, 1.991, 0.677) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (1.22, 1.991, 0.677) | (1.22, 1.991, 0.677) |
| `WheelFR` | mesh | 920 | SteerFR | (1.22, 1.991, 0.677) | (0.0, 0.0, 0.0) |
| `WheelRL` | mesh | 920 | - | (-1.22, -1.865, 0.677) | (-1.22, -1.865, 0.677) |
| `WheelRR` | mesh | 920 | - | (1.22, -1.865, 0.677) | (1.22, -1.865, 0.677) |

- wheel radius 0.677 m, tyre width 0.42 m, wheel track x +-1.22
- MRAP: roof weapon = shielded gunner ring with MG (concept shows a manned shield turret rather than an unmanned RWS); Turret yaws, Gun pitches.
- front34: az 33.8 el 3.6 dist 103.7 m  scale 120.1 px/m  roll 0.9  silhouette IoU 0.886
- rear34: az -147.1 el 5.9 dist 104.5 m  scale 117.3 px/m  roll -2.8  silhouette IoU 0.912
- side silhouette IoU 0.900
- top silhouette IoU 0.854
- atlas coverage 0.568
- The roof weapon is a shielded gunner ring with an MG. The concept shows a manned shield turret, not an unmanned RWS. `Turret` yaws and `Gun` pitches the MG. The spare tyre on the tailgate is static, part of `Hull`.
- Shortcomings: the shields are flat panels. The concept MG is drawn angled up, so its texture is approximate.

## stryker

- Script: `python3 tools/art/veh_stryker_3d.py` -> `godot/assets/units3d/stryker/stryker.glb` (+ `stryker_albedo.png`); sheet `docs/screens/m2_stryker_sheet.png`
- **Triangles: 8696**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 1904 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 160 | - | (0.35, -0.141, 2.357) | (0.35, -0.141, 2.357) |
| `Gun` | mesh | 104 | Turret | (0.35, -0.141, 3.062) | (0.0, 0.0, 0.704) |
| `Muzzle` | empty | 0 | Gun | (0.35, 1.165, 3.062) | (0.0, 1.306, 0.0) |
| `SteerFL` | empty | 0 | - | (-1.31, 1.972, 0.61) | (-1.31, 1.972, 0.61) |
| `WheelFL` | mesh | 816 | SteerFL | (-1.31, 1.972, 0.61) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (1.31, 1.972, 0.61) | (1.31, 1.972, 0.61) |
| `WheelFR` | mesh | 816 | SteerFR | (1.31, 1.972, 0.61) | (0.0, 0.0, 0.0) |
| `SteerML` | empty | 0 | - | (-1.31, 0.723, 0.61) | (-1.31, 0.723, 0.61) |
| `WheelML` | mesh | 816 | SteerML | (-1.31, 0.723, 0.61) | (0.0, 0.0, 0.0) |
| `SteerMR` | empty | 0 | - | (1.31, 0.723, 0.61) | (1.31, 0.723, 0.61) |
| `WheelMR` | mesh | 816 | SteerMR | (1.31, 0.723, 0.61) | (0.0, 0.0, 0.0) |
| `WheelM2L` | mesh | 816 | - | (-1.31, -0.808, 0.61) | (-1.31, -0.808, 0.61) |
| `WheelM2R` | mesh | 816 | - | (1.31, -0.808, 0.61) | (1.31, -0.808, 0.61) |
| `WheelRL` | mesh | 816 | - | (-1.31, -2.057, 0.61) | (-1.31, -2.057, 0.61) |
| `WheelRR` | mesh | 816 | - | (1.31, -2.057, 0.61) | (1.31, -2.057, 0.61) |

- wheel radius 0.610 m, tyre width 0.42 m, wheel track x +-1.31
- Stryker: width squeezed to 2.6 m body / 3.0 m over tyres (concept top view 2.9 / 3.4 m).
- front34: az -27.3 el 4.3 dist 49.1 m  scale 120.1 px/m  roll 0.6  silhouette IoU 0.898
- rear34: az 148.1 el 6.2 dist 21.5 m  scale 111.6 px/m  roll 2.4  silhouette IoU 0.907
- side silhouette IoU 0.915
- top silhouette IoU 0.910
- atlas coverage 0.562
- 8 wheels: `WheelFL/FR`, `WheelML/MR`, `WheelM2L/M2R`, `WheelRL/RR`. The first two axles steer, under `SteerFL/FR` and `SteerML/MR`.
- RWS: `Turret` is the base, sensor box and ammo box; `Gun` is the cradle and MG.
- Shortcomings: the front and rear faces come from the 3/4 views and are streaky. The slat or bin details on the sides are texture only, apart from a few boxes.

## hmmwv_tow

- Script: `python3 tools/art/veh_hmmwv_3d.py hmmwv_tow` -> `godot/assets/units3d/hmmwv_tow/hmmwv_tow.glb` (+ `hmmwv_tow_albedo.png`); sheet `docs/screens/m2_hmmwv_tow_sheet.png`
- **Triangles: 6610**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 2506 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 188 | - | (0.0, -0.423, 1.841) | (0.0, -0.423, 1.841) |
| `Gun` | mesh | 236 | Turret | (0.0, -0.423, 2.264) | (0.0, 0.0, 0.423) |
| `Muzzle` | empty | 0 | Gun | (0.0, 0.55, 2.324) | (0.0, 0.973, 0.06) |
| `SteerFL` | empty | 0 | - | (-1.0, 1.68, 0.477) | (-1.0, 1.68, 0.477) |
| `WheelFL` | mesh | 920 | SteerFL | (-1.0, 1.68, 0.477) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (1.0, 1.68, 0.477) | (1.0, 1.68, 0.477) |
| `WheelFR` | mesh | 920 | SteerFR | (1.0, 1.68, 0.477) | (0.0, 0.0, 0.0) |
| `WheelRL` | mesh | 920 | - | (-1.0, -1.317, 0.477) | (-1.0, -1.317, 0.477) |
| `WheelRR` | mesh | 920 | - | (1.0, -1.317, 0.477) | (1.0, -1.317, 0.477) |

- wheel radius 0.477 m, tyre width 0.32 m, wheel track x +-1.0
- HMMWV TOW: Gun = launch tube + sight (pitch); Muzzle at the tube mouth. Width squeezed sx 0.83 (concept top view 2.66 m).
- front34: az -28.6 el 1.8 dist 83.3 m  scale 167.8 px/m  roll -1.2  silhouette IoU 0.854
- rear34: az -151.2 el 0.3 dist 54.6 m  scale 153.5 px/m  roll 1.5  silhouette IoU 0.857
- side silhouette IoU 0.911
- top silhouette IoU 0.864
- atlas coverage 0.588
- `Gun` is the TOW launch tube plus its sight and guidance box, and it pitches. `Turret` is the roof ring, pedestal and low shields. The spare tyre is on the tailgate (static).
- Shortcomings: the TOW tube top takes its colour from the top view, which is yellow-tan.

## hmmwv_medical

- Script: `python3 tools/art/veh_hmmwv_3d.py hmmwv_medical` -> `godot/assets/units3d/hmmwv_medical/hmmwv_medical.glb` (+ `hmmwv_medical_albedo.png`); sheet `docs/screens/m2_hmmwv_medical_sheet.png`
- **Triangles: 6404**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 2100 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `SteerFL` | empty | 0 | - | (-1.0, 1.849, 0.533) | (-1.0, 1.849, 0.533) |
| `WheelFL` | mesh | 1076 | SteerFL | (-1.0, 1.849, 0.533) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (1.0, 1.849, 0.533) | (1.0, 1.849, 0.533) |
| `WheelFR` | mesh | 1076 | SteerFR | (1.0, 1.849, 0.533) | (0.0, 0.0, 0.0) |
| `WheelRL` | mesh | 1076 | - | (-1.0, -1.418, 0.533) | (-1.0, -1.418, 0.533) |
| `WheelRR` | mesh | 1076 | - | (1.0, -1.418, 0.533) | (1.0, -1.418, 0.533) |

- wheel radius 0.533 m, tyre width 0.33 m, wheel track x +-1.0
- HMMWV ambulance: the concept's red-cross emblems (protected emblem) were removed from all four projection sources (replaced by the surrounding white panel colour) and replaced by plain SA_Team squares on both sides, the roof and the rear doors. No weapon -> no Turret/Gun/Muzzle.
- front34: az -35.4 el 10.8 dist 42.6 m  scale 143.0 px/m  roll 0.7  silhouette IoU 0.950
- rear34: az -146.2 el 9.6 dist 14.4 m  scale 130.4 px/m  roll -0.1  silhouette IoU 0.923
- side silhouette IoU 0.959
- top silhouette IoU 0.898
- atlas coverage 0.644
- **Red crosses removed.** The concept carries red-cross emblems on the sides, roof, hood, front and rear. The red cross is a protected emblem, so every saturated-red region of 1000 px or more in all four projection sources was replaced by the surrounding white panel colour.
- Neutral white panels therefore remain where the crosses were. Plain `SA_Team` squares were added on both sides, the roof and the rear doors. No cross shape exists in geometry or texture.
- No weapon, so there are no Turret/Gun/Muzzle nodes.
- Shortcomings: the front face of the box body is dark and soft, from the front-3/4 projection.

## hmmwv

- Script: `python3 tools/art/veh_hmmwv_3d.py hmmwv` -> `godot/assets/units3d/hmmwv/hmmwv.glb` (+ `hmmwv_albedo.png`); sheet `docs/screens/m2_hmmwv_sheet.png`
- **Triangles: 6456**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 2152 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `SteerFL` | empty | 0 | - | (-0.98, 1.731, 0.476) | (-0.98, 1.731, 0.476) |
| `WheelFL` | mesh | 1076 | SteerFL | (-0.98, 1.731, 0.476) | (0.0, 0.0, 0.0) |
| `SteerFR` | empty | 0 | - | (0.98, 1.731, 0.476) | (0.98, 1.731, 0.476) |
| `WheelFR` | mesh | 1076 | SteerFR | (0.98, 1.731, 0.476) | (0.0, 0.0, 0.0) |
| `WheelRL` | mesh | 1076 | - | (-0.98, -1.524, 0.476) | (-0.98, -1.524, 0.476) |
| `WheelRR` | mesh | 1076 | - | (0.98, -1.524, 0.476) | (0.98, -1.524, 0.476) |

- wheel radius 0.476 m, tyre width 0.32 m, wheel track x +-0.98
- HMMWV base: soft-top troop carrier, no weapon -> no Turret/Gun/Muzzle nodes.
- front34: az -30.7 el 6.9 dist 15.5 m  scale 175.3 px/m  roll -0.6  silhouette IoU 0.937
- rear34: az -159.6 el 4.3 dist 102.3 m  scale 166.9 px/m  roll -1.3  silhouette IoU 0.912
- side silhouette IoU 0.975
- top silhouette IoU 0.898
- atlas coverage 0.618
- Base troop carrier with a soft top. Canvas bows and straps are modelled as thin strips. No weapon, so there are no Turret/Gun/Muzzle nodes.

## m113

- Script: `python3 tools/art/veh_m113_3d.py` -> `godot/assets/units3d/m113/m113.glb` (+ `m113_albedo.png`, `m113_track.png`); sheet `docs/screens/m2_m113_sheet.png`
- **Triangles: 6076**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 1040 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 260 | - | (0.155, 0.276, 2.013) | (0.155, 0.276, 2.013) |
| `Gun` | mesh | 88 | Turret | (0.066, 0.329, 2.575) | (-0.088, 0.052, 0.563) |
| `Muzzle` | empty | 0 | Gun | (0.066, 1.525, 2.575) | (0.0, 1.196, 0.0) |
| `TrackL` | mesh | 816 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `TrackR` | mesh | 816 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `WheelL0` | mesh | 188 | - | (-1.12, 1.4, 0.385) | (-1.12, 1.4, 0.385) |
| `WheelL1` | mesh | 188 | - | (-1.12, 0.722, 0.385) | (-1.12, 0.722, 0.385) |
| `WheelL2` | mesh | 188 | - | (-1.12, 0.078, 0.385) | (-1.12, 0.078, 0.385) |
| `WheelL3` | mesh | 188 | - | (-1.12, -0.661, 0.385) | (-1.12, -0.661, 0.385) |
| `WheelL4` | mesh | 188 | - | (-1.12, -1.366, 0.385) | (-1.12, -1.366, 0.385) |
| `WheelR0` | mesh | 188 | - | (1.12, 1.4, 0.385) | (1.12, 1.4, 0.385) |
| `WheelR1` | mesh | 188 | - | (1.12, 0.722, 0.385) | (1.12, 0.722, 0.385) |
| `WheelR2` | mesh | 188 | - | (1.12, 0.078, 0.385) | (1.12, 0.078, 0.385) |
| `WheelR3` | mesh | 188 | - | (1.12, -0.661, 0.385) | (1.12, -0.661, 0.385) |
| `WheelR4` | mesh | 188 | - | (1.12, -1.366, 0.385) | (1.12, -1.366, 0.385) |
| `IdlerL` | mesh | 188 | - | (-1.12, -2.098, 0.58) | (-1.12, -2.098, 0.58) |
| `IdlerR` | mesh | 188 | - | (1.12, -2.098, 0.58) | (1.12, -2.098, 0.58) |
| `SprocketL` | mesh | 400 | - | (-1.12, 2.111, 0.55) | (-1.12, 2.111, 0.55) |
| `SprocketR` | mesh | 400 | - | (1.12, 2.111, 0.55) | (1.12, 2.111, 0.55) |

- cupola (Turret) pivot (0.155, 0.276, 2.013), MG trunnion y 0.329 z 2.575, muzzle y 1.515
- road wheel r 0.285, sprocket (front) r 0.22, idler (rear) r 0.21
- track loop 10.168 m, links 66, link pitch 0.1541 m, metres per V 0.9244 (tile = 6 links)
- front34: az -34.3 el 8.3 dist 15.0 m  scale 140.5 px/m  roll -0.1  silhouette IoU 0.924
- rear34: az -145.6 el 12.7 dist 138.5 m  scale 134.8 px/m  roll -2.1  silhouette IoU 0.929
- side silhouette IoU 0.896
- top silhouette IoU 0.958
- atlas coverage 0.781
- `Turret` is the commander's cupola ring with the gun shield, and `Gun` is the MG.
- Five road wheels; the drive sprocket is at the front and the idler at the rear.
- The belly between the tracks is extended down to 0.45 m to close the see-through gaps between the wheels, matching the concept.
- Shortcomings: the hatches are texture only. The trim vane is a thin bar.

## m777

- Script: `python3 tools/art/veh_m777_3d.py` -> `godot/assets/units3d/m777/m777.glb` (+ `m777_albedo.png`); sheet `docs/screens/m2_m777_sheet.png`
- **Triangles: 6424**

| Node | Type | Tris | Parent | World pos (Blender m) | Local pos |
|---|---|---|---|---|---|
| `Hull` | mesh | 2456 | - | (0.0, 0.0, 0.0) | (0.0, 0.0, 0.0) |
| `Turret` | mesh | 316 | - | (0.0, -1.6, 0.95) | (0.0, -1.6, 0.95) |
| `Gun` | mesh | 1292 | Turret | (0.0, -2.25, 1.45) | (0.0, -0.65, 0.5) |
| `Muzzle` | empty | 0 | Gun | (0.0, 4.76, 1.45) | (0.0, 7.01, 0.0) |
| `WheelL` | mesh | 1180 | - | (-1.369, -1.086, 0.61) | (-1.369, -1.086, 0.61) |
| `WheelR` | mesh | 1180 | - | (1.369, -1.086, 0.61) | (1.369, -1.086, 0.61) |

- carriage-top (Turret) pivot (0.0, -1.6, 0.95), trunnion (0.0, -2.25, 1.45), barrel 7.00 m from trunnion, muzzle y 4.750
- wheel r 0.61, axle y -1.086, track +-1.369
- side silhouette IoU 0.401
- top silhouette IoU 0.597
- atlas coverage 0.543
- Modelled deployed: the trails are spread as in the concept top view, the spades are down, and the front firing platform is lowered. The gun rests level.
- There is no engine, so there are no Track, Sprocket or Idler nodes. The wheels are `WheelL`/`WheelR`, with hub origins.
- `Turret` is the carriage top (yaw) and `Gun` is the cradle, barrel and recoil system (pitch).
- Scale: top view, muzzle to spade = 9.5 m (manifest), which gives a wheel track of 2.74 m.
- The concept side and 3/4 views show the barrel elevated about 15 deg. The 3/4 views are therefore not projected, and the gun and carriage top use the top view only.
- Silhouette IoU is low (side 0.40, top 0.60) because the concept gun is elevated and the parts are thin.
- **Weakest of the twelve.** The carriage and trail structure is a simplified box/beam interpretation and is less faithful than the other vehicles. Triangles stay modest because the object is spindly.
