# M1 3D structures (set B): Airfield, Supply Drop Zone, Radar, Defense Tower, HESCO, parachute crate

Status: **built in Blender (bpy 5.2) and previewed in Cycles from the re-imported GLBs. Not loaded or tested in Godot**
(not run, as instructed). Node names were checked against the lookups in `godot/scripts/building.gd`
(`Pad#`, `RunwayStart/End`, `DropPoint`, `RadarDish`, `Turret`, `Muzzle`, `Light_*` MeshInstance3D surface 0).

The pipeline is the approved pilot one (`bld_supply_depot_3d.py`, unchanged). It is generalised into
`tools/art/bldkit_b.py`, which provides these pieces:
- Procedural primitives tagged with tileable numpy source surfaces.
- New: a **plan canvas**, a painted world-XY ground texture for runway, markings, drop target and pad joints. It is antialiased SDF painting with paint wear.
- One smart-projected atlas over all opaque parts, with a Cycles DIFFUSE + AO bake and a colour×AO JPEG composite.
- One Principled BSDF atlas material per asset, plus a `_2S` double-sided twin used only for parachute canvas.
- `SA_Team`, plain white.
- Chain-link fence quads with alpha blend.
- GLB export.
- Previews rendered from the re-imported GLB.

## Build

```
python3 -I tools/art/bld_<id>_3d.py godot/assets/units3d/<id> --previews docs/screens --concept <..._front_three_quarter.png>
python3 -I tools/art/prop_supply_crate_chute.py godot/assets/units3d/props --previews docs/screens
# options: --previews-only, --only rts,front
```
- **Run times** on 2 shared cores: 1–2.5 min to build and bake, plus about 25 s per 640×400 preview at 24 samples.
- **Airfield memory:** the airfield peaks at about 2.7 GB RSS (4096² atlas + 2400×1760 plan). In this sandbox the build + previews in one process was **OOM-killed** twice by the cgroup. Build it alone, then run `--previews-only`.
- **Determinism:** two builds of the crate prop are byte-identical (md5 `0d758d9f…`). The others use the same seeded code path but were not double-built, to save CPU.

## Conventions (all assets)
- Origin is the footprint centre at ground level.
- Front is Blender −Y = **Godot +Z**. Glb positions below are Godot coordinates.
- Light objects have their origin at the lamp. Each has its own material `SA_Light_<objectname>`, taken literally from the brief, e.g. `SA_Light_Light_Status0`. It has white base, emissive (1,1,1), strength 1.
- Preview renders tint the lights by group: status green, beacon red, flood warm, runway amber. **The tint is preview-only and is not in the GLB.**
- Opaque material `XX_<Name>` is a single atlas JPEG, roughness 0.82, back-face culled.

| id | footprint | height | triangles (opaque + lights) | atlas | GLB |
|---|---|---|---|---|---|
| airfield | 60 × 44 m, slab top 0.2 m | tower 13.1 m roof, beacon ~16.6 m | Building 3,622 + Props 3,362 + 25 lights 652 = **7,636** | 4096² | 2.7 MB |
| drop_zone | 24 × 24 m, raised pad top 0.55 m | mast 10 m | 3,810 + 3,674 + 136 = **7,620** | 2048² | 1.4 MB |
| radar | 12 × 12 m, pad 0.2 m | dish top ~8 m, lattice 12.5 m | Building 5,640 + RadarDish 2,696 + 104 = **8,440** | 2048² | 1.3 MB |
| defense_tower | 8 × 8 m (octagon 7.7 m flat-to-flat) | roof 6.85 m, turret ~8 m, whip 10 m | Building 4,510 + Turret 792 + 104 = **5,406** | 2048² | 1.0 MB |
| hesco | 8 × 4 m segment | 2.2 m (+0.16 m earth) | **5,090** | 2048² | 1.4 MB |
| props/supply_crate_chute | 2 × 2 m crate, 1.47 m tall | canopy apex 9 m, Ø 6.6 m | Crate 534 + Canopy 2,112 = **2,646** | 1024² | 0.4 MB |

The crate is below the 3k floor. It is a prop that may appear many times at once, so I kept it light.

## Node names

### Airfield (`units3d/airfield/airfield.glb`)
- `Building`: slab with the plan texture, arched hangar (door to the front), control tower, ops annex. `Props`: everything else.
- `Pad0`..`Pad3` are parking spot centres on the slab (y = 0.2), about 14 m apart: (5, 14), (19, 14), (5, 0), (19, 0). All four are in the front half.
- `RunwayStart` is at (−28, 0.2, −16.5) and `RunwayEnd` at (28, 0.2, −16.5). The runway is 60 × 10 m along X at the back (z −11.5 … −21.5). Take-off and landing run from Start toward End (+X).
- The taxiway at x 8…16 joins the apron lane (x = 12) to the runway centreline with curved lead-ons. Hold-short markings are painted on it.
- `Light_Runway0..15` are edge lights in pairs along the runway from Start to End: even = front edge (z −11.6), odd = back edge (z −21.4). They export in index order.
- `Light_Status0/1` are on the hangar door piers. `Light_Status2` is at the ops annex door.
- `Light_Beacon0` is the tower antenna mast; `Light_Beacon1` is the hangar ridge.
- `Light_Flood0..3` are twin-head flood poles at the apron corners and the hangar front.
- `SA_Team`: hangar door header band, tower cab band, windsock.

### Supply Drop Zone (`units3d/drop_zone/drop_zone.glb`)
- `DropPoint` is at (−2.6, 0.55, −0.4), on the pad surface at the centre of the yellow ring and white cross.
- `Building` covers the pad, barrier blocks, ramp, fence, office container and mast. `Props` covers chute bundles, crates and tripod floods.
- `Light_Status0` is at the office door, `Light_Status1` on the gate post. `Light_Beacon0` is the mast top. `Light_Flood0..3` are the corner tripods, aimed at the target.
- `SA_Team`: office band and mast pennant.

### Radar (`units3d/radar/radar.glb`)
- `RadarDish` holds the turntable, yoke, 5.7 m dish tilted 30°, and feed. Its origin is **on the vertical spin axis** at (2.1, 3.5, −2.0), the pedestal top.
- To spin it, rotate the node about its local Y. The fence and the building roof clear the dish's sweep.
- `Building` covers the pad, fence (joined in), ops building, pedestal + catwalk, lattice tower, whip mast and cabinets.
- `Light_Status0` is at the door, `Light_Status1` on a cabinet. `Light_Beacon0` tops the lattice tower and `Light_Beacon1` the whip mast. `Light_Flood0` is the wall flood and `Light_Flood1` the pole flood.
- `SA_Team`: building parapet stripe, pedestal band, turntable band.

### Defense Tower (`units3d/defense_tower/defense_tower.glb`)
- `Turret` is a remote weapon station: 2×2 missile pod, sensor head, MG. Its origin is **on the yaw axis** at (0, 6.97, 0.25). At rest it aims at Godot +Z.
- `Muzzle` is a child of `Turret` at local (0.82, 0.95, 0.84), the centre of the tube mouths.
- `Building`: battered octagonal bastion with buttresses, louvres, door, 3-high sandbag ring on the deck, octagonal shaft, glazed cab, roof railing, radome mast, searchlight.
- `Light_Status0` is at the bastion door, `Light_Status1` at the tower door. `Light_Beacon0` is the whip mast; `Light_Flood0` is the searchlight lens.
- `SA_Team`: cab band and turret ring.

### HESCO (`units3d/hesco/hesco.glb`)
- `Building` is the whole segment, with these parts:
  - **Front row:** 8 cells (1.0 × 1.05 × 2.2 m) of mesh + geotextile, with lumpy earth tops.
  - **Rear row:** 8 lower cells at 1.1 m, forming a fire step.
  - **Earth ramp** behind the step.
  - **Joints:** coil joint posts.
  - **Small dressing:** a few sandbags.
- Cells end exactly at x = ±4, so segments tile along X.
- `Light_Status0/1` are small perimeter lamps on stakes at the back.
- `SA_Team`: front placard and a marker tape.

### Parachute crate (`units3d/props/supply_crate_chute.glb`)
- `Crate` has its origin at the crate bottom centre. It is a strapped 2 × 2 pallet of olive and tan crates with corner boards, a team ID panel, and 4 risers up to the clevis.
- `Canopy` has its origin at the **suspension point** (0, 2.6, 0). It has 16 alternating olive and sand gores, an apex vent and seam tapes, plus 16 suspension lines. Scaling or hiding this node collapses or removes the canopy cleanly. The canvas uses the double-sided `SC_SupplyCrateChute_2S`.
- No lights.

## Previews
- `docs/screens/m1_{airfield,drop_zone,radar,defense_tower,hesco}_{rts,front,side,top}.png` + `m1_<id>_vs_concept.png`. Each `vs_concept` shows the RTS render beside the concept's front three-quarter view.
- `docs/screens/m1_crate_{rts,front,side,top}.png`. Its `side` shot is from below, to show the canopy underside. There is no concept sheet for the crate.

## Known shortcomings
- **Not verified in Godot.**
  - Lighting and tonemapping will differ from Cycles.
  - `UnitArt.apply()` / the reveal shader must keep the imported atlas materials. The same integration note applies as for the depot.
  - Light materials export as double-sided (Blender default). This is harmless because the game overrides them.
- **Airfield:**
  - **Design changes from the concept:** this is a redesign, not the concept layout. The hangar door faces the front, the tower stands at the far left, and the runway is very short (stylised).
  - **Hangar look:**
    - The roof's olive is darker and more uniform than the concept's.
    - The open door shows a dark interior with only a few props.
    - The front gable piers are simple slabs.
  - **No aircraft-sized clearance check** was done against the game's aircraft models. The pads are 14 m apart and the circles are 10 m in diameter.
- **Radar dish:**
  - It is a solid shell with painted and raised ribs, where the concept shows an open truss mesh.
  - Its AO was baked at the rest pose, so the contact darkening stays fixed while it spins.
- **Defense tower:**
  - The bastion is a little lower and less chunky than the concept.
  - The turret sits on the roof centre, not on the concept's corner pillar, so the game can aim one turret over 360°.
- **Drop zone:**
  - Chute bundles are lumpy lofts with painted camo and cords. They read well at RTS distance but lack the concept's heavy folds up close.
  - The mast top crops in the RTS preview; the side and front shots show it.
- **HESCO:**
  - The wire mesh is painted into the albedo; there is no alpha or normal map.
  - Segments tile cleanly along X. The ends have no corner or end piece, so an open end shows a cell's rounded side.
- **General:**
  - No normal or roughness maps.
  - The single LOD has not been measured in game.
  - Fences use alpha BLEND, as on the depot.
