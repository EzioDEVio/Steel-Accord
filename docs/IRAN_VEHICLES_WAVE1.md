# Iran ground vehicles, wave 1 (5 vehicles in 3D)

Status: **generated and previewed in Blender 5.2 (Cycles CPU). Not run in Godot by the art agent.**
All five are real 3D geometry with depth from every angle; none is a billboard. They follow the U.S. M2 conventions
(`docs/M2_VEHICLES.md`) so `unit.gd` can load them without code changes.

| id | Concept | GLB | Script | Tris | `track_m_per_v` |
|---|---|---|---|---|---|
| `ir_karrar` | panel 01 | `godot/assets/units3d/ir_karrar/ir_karrar.glb` | `tools/art/veh_ir_karrar_3d.py` | 8,649 | **0.8956** |
| `ir_t72s` | panel 03 | `godot/assets/units3d/ir_t72s/ir_t72s.glb` | `tools/art/veh_ir_t72s_3d.py` | 10,241 | **0.8956** |
| `ir_bmp2` | panel 05 | `godot/assets/units3d/ir_bmp2/ir_bmp2.glb` | `tools/art/veh_ir_bmp2_3d.py` | 8,344 | **0.8355** |
| `ir_boragh` | panel 06 | `godot/assets/units3d/ir_boragh/ir_boragh.glb` | `tools/art/veh_ir_boragh_3d.py` | 6,732 | (wheeled) |
| `ir_engineer_dozer` | panel 12 | `godot/assets/units3d/ir_engineer_dozer/ir_engineer_dozer.glb` | `tools/art/veh_ir_engineer_dozer_3d.py` | 8,321 | **0.8956** |

Concept panels are in `docs/reference/iran_pack/01_ground_vehicle_catalog.png`.
The preview sheets (front, side, rear, top, RTS 52°, close 3/4) are at `docs/screens/<id>_sheet.png`, for example `docs/screens/ir_karrar_sheet.png`.
QA files are in `godot/assets/units3d/<id>/_qa/`, which contains a `.gdignore`:
- `<id>_report.txt` lists the nodes, pivots and triangle counts, and gives the result of the normals check.
- `<id>_backface_rts.png` and `<id>_backface_low_rear.png` are Workbench renders with back-face culling on. An inverted face would show as a hole.

Shared kit: `tools/art/vehkit_ir.py`. It imports `vehkit.py` and the library half of `veh_m88_3d.py` without changing them, so no U.S. script or output was touched.
To regenerate a vehicle, run `python3 tools/art/veh_<id>_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]`.
A run takes about 1.5 minutes without previews and about 3 minutes with them, on 2 shared CPUs.
The scripts are deterministic: they use fixed integer hashes, hold no RNG state and make no network calls.

## Conventions (same as the U.S. roster)
- **Axes and units:** metres. Forward is Blender +Y, which the exporter writes as Godot −Z. Up is +Z. Vehicle left is −X.
- **Root origin:** ground contact under the hull centre.
  - For the dozer, the centre is the hull centre; the blade sticks out in front of it.
- **`Hull`** is static. Its second material slot is `SA_Team`.
- **Tracked vehicles** (karrar, t72s, bmp2, engineer_dozer):
  - `WheelL0..5` and `WheelR0..5`, `IdlerL/R` and `SprocketL/R` have hub origins and spin about local X.
  - `TrackL` and `TrackR` use `SA_TrackScroll` (a 256×512 tile). Each loop holds exactly 16 tiles (96 links, 6 links per tile).
  - The right-side gear is a mirrored copy that shares the left side's UVs.
- **Weapons:**
  - `Turret` has its origin on the yaw axis.
  - `Gun` is a child of `Turret`, with its origin on the trunnion.
  - `Muzzle` is an empty child of `Gun`, at the barrel tip.
- **Materials:**
  - `SA_<Id>` (for example `SA_IrKarrar`) is a Principled BSDF with one embedded 2048² albedo. A PNG copy sits beside each GLB.
  - `SA_Team` is plain grey 0.62.

## Dimensions and nodes

### ir_karrar: Karrar-style MBT
- Hull 6.90 m (nose +3.45 to rear −3.45). With the gun forward it is 9.50 m long (muzzle at y 6.05).
- 3.60 m wide over the skirts. Turret roof at 2.28 m; the RWS reaches about 2.85 m.
- `Turret` pivot (0, 0.35, 1.42). `Gun` trunnion (0, 1.30, 1.90). `Muzzle` y 6.07.
- Road wheels r 0.375 (6 per side). Front idler r 0.27. Rear drive sprocket r 0.31.
- Track loop 14.329 m, 96 links of 0.1493 m.
- Triangles: Hull 1,113 / Turret 1,260 / Gun 428 / tracks 2×1,144 / wheels 188 each / sprockets 464 each.
- Turret: an angular slab with wedge cheek modules, side armour boxes, an open bustle rack with stowed canvas, commander's and gunner's sights, a loader's hatch and smoke dischargers (2×4).
  - The roof RWS is a static part of `Turret`; only the main gun has nodes.
- Gun: mantlet, thermal-sleeve bands, fume extractor and muzzle reference sensor.
- Team colour: strips on both turret side-armour boxes, the rear of the bustle rack, and both skirts.

### ir_t72s: T-72S-style MBT with ERA
- Same chassis as the Karrar (kit `T72` spec), with thin rubber skirts.
- 9.50 m with the gun. Dome roof at about 2.13 m; the cupola MG reaches about 2.45 m.
- `Turret` pivot (0, 0.30, 1.42). `Gun` trunnion (0, 1.10, 1.88). `Muzzle` y 6.07.
- Turret: a lofted cast dome (32 segments, elongated rearwards).
  - About 30 ERA bricks in three bands, with a gap left around the gun.
  - Commander's cupola with a heavy MG (static, part of `Turret`), gunner's sight, IR searchlight, two smoke banks of 4, and stowage boxes on the rear flanks.
- Hull: a 3×11 ERA grid on the glacis and 2×8 ERA bricks on the front of each skirt. At the rear are fuel drums, an unditching beam and a stowed snorkel.
- Triangles: Hull 2,069 / Turret 1,728 / Gun 596.
- Team colour: strips on the turret flank stowage boxes and on both skirts.

### ir_bmp2: BMP-2-style IFV
- Hull 6.72 m (±3.36), 3.15 m wide. Turret roof at 2.13 m; the ATGM tube top is at 2.49 m.
- `Turret` pivot (0, 0.40, 1.62). `Gun` trunnion (0, 1.02, 1.98). `Muzzle` y 4.00.
- The **drive sprocket is at the FRONT** (r 0.25) and the idler at the rear (r 0.26), as on the real layout. Road wheels r 0.33 (6 per side).
- Track loop 13.367 m, 96 links of 0.1392 m, which gives **0.8355 m per V**.
- Hull: a lofted shell with a long shallow ribbed glacis, folded trim vane, driver's hatch and vision block, thin side skirts and firing ports.
  - Also: troop roof hatches, two rear doors, an exhaust and louvres.
- Turret: an octagonal frustum with sights and a roof ATGM tube.
  - The ATGM tube is static and part of `Turret`, so it yaws but does not elevate.
  - Smoke clusters on both sides, plus a rear stowage box.
- Gun: a 30 mm-class autocannon with a muzzle brake, plus a coaxial MG.
- Triangles: Hull 1,388 / Turret 964 / Gun 224.
- Team colour: the turret rear box (rear face and sides) and both hull sides.

### ir_boragh: 8×8 wheeled APC with RWS
- The reference README calls this vehicle "Boragh". The real Boragh is tracked, but panel 06 shows an 8×8, so the model follows the panel as instructed.
- 7.60 m long (±3.80). 2.84 m over the body and 2.98 m over the tyres. Roof at 2.20 m; the RWS reaches about 2.95 m.
- Wheels:
  - r 0.58, tyre width 0.42, rim r 0.33, track ±1.28.
  - Axle y positions: F 2.40, M 1.05, M2 −0.75, R −2.10.
  - The nodes are `WheelFL/FR`, `WheelML/MR`, `WheelM2L/M2R` and `WheelRL/RR`. The first two axles sit under the empties `SteerFL/FR` and `SteerML/MR`, at identity local transforms, like the Stryker.
  - Each wheel is 660 triangles.
- RWS:
  - `Turret` is the base, sensor head, ammo box and a rear smoke bank, with its pivot at (0, 0.10, 2.20).
  - `Gun` is the cradle and a heavy MG, with its trunnion at (0, 0.10, 2.66).
  - `Muzzle` is at y 1.63.
- Hull: a 12-vertex lofted section with a V belly, a narrow lower hull between the wheels and an upper body that overhangs the tyres.
  - The glacis has vision windows. Also modelled: headlight clusters, sensor boxes on the front corners, hatches, a grille, grab rails, the rear ramp and side-door outlines.
- Triangles: Hull 1,076 / Turret 272 / Gun 104.
- Team colour: strips on both upper sides, the rear ramp and the RWS ammo box.

### ir_engineer_dozer: combat engineer / recovery vehicle (Iranian builder)
- Same chassis as the Karrar and T-72S, with plain skirts.
- Blade cutting edge at y 3.98, teeth to about 4.22. Blade tip to hull rear is about 7.6 m.
- Blade 3.70 m wide. Casemate roof at 2.32 m. The crane boom tip is at (1.05, 3.05, 3.70).
- `Hull` is static, as on the M88. It includes:
  - the curved moldboard with back ribs, end plates, steel cutting edge and 9 teeth
  - the push arms and lift rams
  - the crane turntable, two-stage boom, ram, chain and hook
  - the front winch drum, spare track links, a rear stowage cage and the casemate.
- Small MG mount: `Turret` (pivot (−0.70, −0.55, 2.32)), then `Gun` (trunnion (−0.68, −0.40, 2.62)), then `Muzzle` (y 0.63).
  - The game may ignore these nodes if the builder has no weapon.
- **track_m_per_v = 0.8956.** The M88's value is 0.9573; the dozer's differs because the chassis is different.
- Triangles: Hull 2,337 / Turret 92 / Gun 44.
- Team colour: both casemate sides, both skirts, and the top of the crane boom.

## Texturing method (different from the U.S. roster)
The Iranian concept panels are single perspective renders, so **nothing is projected from them.**
1. While the geometry is built, every primitive is stamped with a **paint tag**: camo, skirt, ERA, barrel, metal, rubber, glass, lens, red lens, steel, canvas, grille, chain, olive.
   - The tag is an integer face attribute named `satag`. It is removed before export.
2. Every albedo texel is painted procedurally from its world position, normal, tag and object:
   - **Camouflage:** three tones, sand / olive / brown. The colours were sampled from the concept panels with k-means. The pattern is 3D value-noise fBm with hard edges in a sheared domain, so the blotches slant along the hull.
   - **Plate detail:** seams at listed planes, regular seams and bolt rows on skirts, louvres, door and hatch outlines.
   - **Wheels:** painted rotation-invariantly around the hub, with rubber tyres, bolt circles and dark sprocket teeth.
   - **Weathering:** dust low on the hull, vertical streaks, and dust on up-facing surfaces.
   - **National colours:** small green / white / red horizontal-stripe decals (see "Flags" below).
3. A Cycles **AO** bake is multiplied in. A Cycles **bevel-normal edge** bake lightens convex edges (worn paint) but not creases, which keeps the models crisp at RTS zoom.
   - The bakes are 1024², upsampled to the 2048² atlas.
4. Tracks use the kit's procedural link tile in neutral dark steel and dust colours.

**Flags:** each vehicle carries 2 or 3 small flag decals (0.36–0.42 × 0.20–0.26 m) on its hull or turret sides or its rear plate. They are plain stripes, with no emblem and no text.
**Normals:** after building, every mesh is cleaned of degenerate faces and its normals are recalculated. The report checks the signed volume of every connected component of every exported mesh and looks for zero-length normals; all five vehicles pass. The back-face-culled Workbench renders show no holes.

## Deviations, known issues, notes for integration
- **Not tested in Godot.** Import, LODs and collision still need checking in game. No LODs were authored.
  - A Godot import ran in the shared repo at about 20:43, while the final art runs were in progress. It left `*.import` files and extracted `<id>_<id>_albedo.png` / `_track.png` copies behind.
    - The Boragh (20:46) and dozer (20:48) GLBs were exported after that import, and the BMP-2 has no `.glb.import` yet.
    - **Re-import all five before judging them in game.**
- **Static secondary weapons:** the Karrar's RWS, the T-72S cupola MG and the BMP-2 ATGM tube are static parts of `Turret`. They yaw with it but have no nodes of their own.
- **Smoothing:** the Boragh and BMP-2 hull lofts use a 12° auto-smooth angle so the faceted plates stay crisp. Everything else uses 33–50°.
- **Concept differences:**
  - The concepts are perspective AI renders, so proportions come from real-world dimensions, not from measurement.
  - The Karrar turret is a simplified slab with wedge modules. The T-72S dome ERA is a regular brick pattern and does not copy the concept's layout.
  - The dozer's crane is stowed in a raised pose, as in the concept, so it adds height to the silhouette.
- **Shared UVs:** the right running gear shares the left side's UVs, so the right road wheels are mirror images of the left (which is not visible in play).
- The sheet naming is `docs/screens/<id>_sheet.png`. Because the ids already start with `ir_`, the files are `ir_karrar_sheet.png` and so on, not `ir_ir_karrar_sheet.png`.
- Suggested `UnitDefs` keys: `"model3d": "res://assets/units3d/<id>/<id>.glb"`, with `"track_m_per_v"` taken from the table above for the tracked vehicles.
