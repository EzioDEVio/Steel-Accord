# Map: Zagros Basin (2 players)

Fictional sector for Steel Accord, inspired by the *character* of the Zagros foothills: long NW–SE fold ridges and a dry alluvial basin. Every settlement, road, supply site, derrick and base is invented, and nothing reproduces a real military or critical-infrastructure location.

**The terrain is synthetic.** No elevation data was available when the map was authored (no network), so the heightfield is procedural. The generator accepts a real DEM later (see [Using a real DEM](#using-a-real-dem)).

| Preview | File |
|---|---|
| Overview: colour, sites, roads, passes | `docs/screens/map_zagros_overview.png` |
| Height, 5 m contours | `docs/screens/map_zagros_height.png` |
| Splat channels and slope | `docs/screens/map_zagros_splat.png` |
| Route proof per movement class | `docs/screens/map_zagros_routes.png` |
| Blender perspective render, 52° RTS camera near start A (preview render, **not** an in-game screenshot) | `docs/screens/map_zagros_rts.png` |
| Props contact sheet | `docs/screens/props_sheet.png` |

## Scale

- The playable area is 1200 × 1200 game metres (x and z from −600 to +600). It represents about 5 km of terrain, compressed for RTS pacing.
- Relief is exaggerated for the RTS camera:
  - basin floor: about 1–6 m
  - start valleys: about 14 m (flattened bases at 14.09 m)
  - inner anticlines: up to about 60–68 m
  - outer ridges in the SW and NE corners: about 70 m
- `height_scale` = 80 m.

## Design

- **Structure.** The fold axes run NW–SE (35° from +X in map space; +z is south). A wide, flat dry basin runs corner to corner through the centre. Each start sits in its own higher valley, behind a line of en-echelon whaleback anticlines.
  - The anticlines plunge into rounded noses. The gaps between noses are the **passes**: the natural Zagros way for routes to cross a fold belt.
  - Anticline flanks are layered limestone benches. The risers are steeper than 38°, and some cliffs are steeper than 60°.
- **Starts.**
  - A (team 0) is at (0, 470), facing 0° (north).
  - B (team 1) is at (0, −470), facing 180°.
  - Each start has a flat disc of 100 m radius (about 200 m across). Height range is 0.03 m and maximum slope 2.3°.
- **Symmetry.** Every gameplay feature is point-symmetric under (x, z) → (−x, −z). The heightfield is exactly symmetric on the grid. The only asymmetric detail is ±0.7 m of cosmetic noise on cliffs steeper than 44°, which are impassable anyway.
- **Three routes between the starts.** Each player's inner ridge has three passes: one beside the base, one in the centre, and one far down the valley. Crest positions on A's side:

| Pass | A side (crest x, z) | B side (mirror) | Floor | Notes |
|---|---|---|---|---|
| Central | (−7, 263) | (7, −263) | 52 m wide, about 4° | Direct N–S main road; opens straight into the base (a "main ramp") |
| A east / B west | (306, 469) | (−306, −469) | 40 m | About 200 m from the owner's base |
| A west / B east | (−293, 50) | (293, −50) | 40 m | Far flank, about 450 m down the valley past the village |
| Goat trail (infantry only) | (−147, 169) | (147, −169) | 9 m wide ramp at about 31.5° | Infantry-only shortcut; too steep for tracked (28°) and wheeled (18°) units |

- **Route lengths.** The west route (A west pass → basin → B's world-west pass) and the east route are mirror images, about 1.37–1.64 km depending on class. The central route is about 0.99 km.
- **Economy.**
  - Home supply piles: 2 per side, 20 000 each, at 101–143 m (path) from the start.
  - Home derrick: 1 per side, 89–110 m from the start.
  - Contested supply piles: 3 at 30 000. One is at the centre (0, 0), on a gravel bar in the main wadi. The other two are at (∓330, ∓215) on the flank routes.
  - Contested derricks: 2, at the NW and SE ends of the basin (∓470, ∓330). Each is far from its "near" player and reachable along the basin road.
- **Build pads.** There are 10 flattened rectangles: 3 per side (`owner_hint` 0/1) and 4 contested (`owner_hint` −1).
  - The contested pads are 2 open-basin pads at (∓218, ∓45) and 2 pass-mouth pads at (±160, ±150).
- **Landmarks.**
  - A village of 7 houses with palms in each start valley, at (−235, 300) and its mirror, on the far-flank road.
  - Walled-compound ruins on a low whaleback hill west and east of the centre, plus ruins at each flank crossing.
  - A pylon line along the basin.
  - Date palms along the wadis.
  - Talus rock clusters at the feet of the cliffs.
- **Wadis.** A meandering trunk wadi runs along the basin axis, with tributaries from each pass mouth and from ridge gullies. They are shallow (1.4–2.3 m) with 13° banks, so they are cosmetic plus a riverbed movement cost. Roads cross on fords.
- **Alluvial fans.** Gravel fans spread at every pass mouth and gully mouth.

## Verification (generated: `godot/maps/zagros_basin/fairness_report.txt` / `.json`)

The method below mirrors `terrain_map.gd`:

- **Slope** is computed exactly as `normal_at` does: central differences over ±1 sample on the quantised u16 heights.
- **Grid and movement.** The grid is 8-connected with 2 m cells and no corner cutting. A cell is passable when its slope ≤ `max_slope_deg`.
- **Edge cost** = length × mean cell cost. Cell cost is the splat-weighted material cost (sand = remainder), blended to the road cost by a road mask with the same falloff as `_bake_roads`.
- **Dijkstra** comes from `scipy.sparse.csgraph`.

**Fairness.** For the home sites, the table compares A→own site with B→own site. For the contested sites, it compares A→site with B→the mirrored site.

| Class | Home pile 0 | Home pile 1 | Home derrick | Centre pile | Flank pile pair | Far derrick pair | Worst diff |
|---|---|---|---|---|---|---|---|
| Infantry | 101.4 / 101.4 | 120.7 / 120.7 | 110.2 / 110.2 | 444.5 / 444.5 | 787.4 / 787.4 | 975.6 / 975.6 | 0.00 % |
| Wheeled | 62.3 / 62.3 | 142.3 / 142.3 | 88.8 / 88.8 | 272.2 / 272.2 | 508.8 / 508.8 | 632.8 / 632.8 | 0.00 % |
| Tracked | 90.2 / 90.2 | 123.1 / 123.1 | 105.8 / 105.8 | 395.9 / 395.9 | 739.1 / 739.1 | 900.7 / 900.7 | 0.00 % |

Values are cost-metres. The limit is 3 %, and the measured worst case is 0.00 % because the gameplay terrain and splat are exactly symmetric.

**Routes.** Each check runs A→B with only that route's two passes open. The other passes are blocked with 105 m discs on their crests; the goat trails are blocked with 60 m discs.

| Class (max slope) | West | Central | East |
|---|---|---|---|
| Infantry (38°) | OK, 1369 m | OK, 983 m | OK, 1369 m |
| Wheeled (18°) | OK, 1636 m | OK, 990 m | OK, 1636 m |
| Tracked (28°) | OK, 1541 m | OK, 990 m | OK, 1541 m |

**Barriers.**

- With all six passes blocked, wheeled and tracked units are **disconnected**: the ridges block vehicles.
- With all six passes blocked, infantry stay connected, but only through the goat trails.
- With the goat trails also blocked, infantry are **disconnected**: the cliffs steeper than 38° stop them.

There are 57 462 cells steeper than 38° and 47 757 steeper than 45°. The maximum slope is 78°.

Passable fraction: infantry 0.84, tracked 0.80, wheeled 0.75.

**Flatness.**

- Starts: height range 0.03 m, maximum slope 2.31°.
- All 10 build pads: height range 0.0 m, maximum slope 0.0° over the whole rectangle, including the edge samples that `footprint_stats` reads.
- Roads (mask > 0.9): maximum slope 17.66°, 99th percentile 8.4°. All roads are passable for wheeled units, but the maximum is close to the 18° limit.

## B3: town, industry, roads, railway (2026-10-23)

Everything below is generated by `tools/map/gen_zagros_basin.py` (layout constants `EXTRA_ROADS_A`, `CIVIC_A`,
`COMPOUNDS_A`, `INFRA_A`, `RAIL_A_CTRL`, `VALLEY_WADI_A`; B side = point mirror) and checked by `validate_layout()`
(LAYOUT section of the fairness report: 0 problems) plus `autotest_map.gd`.

**Layout (A side; B is the point mirror).**
* *Town* in A's valley around (-280, 300): an axis-aligned street grid (high street z = 300, street h2 z = 345,
  h3 z = 255, cross streets x = -320 / -262, civic-centre street z = 355) crossed by the diagonal west main road.
  Covered market, school, two apartment blocks, civic centre, 9 houses, three walled compounds, water tower, fuel station
  at the pass-side exit, cell tower, radio mast; a dry riverbed crosses the west road on a three-arch bridge where the
  road leaves the town for the west pass. Two outlying farmsteads on dirt tracks. The town platform is flattened in the
  (t, s) strike frame so it never cuts the ridges or the goat trail.
* *Industrial zone* in the basin east of A's central-pass mouth (around (215, 245)): sawtooth factory with office,
  two warehouses, chimney, silos, fuel tanks in a bund, concrete hardstand, fence with a gate on the basin-road side,
  paved access road and yard road.
* *Railway*: two point-symmetric branch lines (a single symmetric line would have to pass through the centre supply
  pile). Each runs ~770 m along the basin foot of its side's inner ridge, from a tunnel portal in the west ridge
  segment, across both pass mouths (level crossings), over a two-arch bridge at a gully and a second one at the central
  gully, then east and south into a N-S freight yard (main line, siding with two wagons, platform, station, container
  stacks, gantry crane) that ends in the east portal. Max formation grade 2.5 %. Portals: concrete headwall with a dark
  recess; the cut slot closes 1.5 m behind the face and the ground rises 11-13 m over 6 m behind it. Tunnels are not
  traversable (a blocker line across each mouth).
* *Static train*: locomotive + 4 wagons (tank, box, flat with containers, tank) standing in the yard in front of the
  east portal. Decision: **static, indestructible scenery that blocks movement** (a `blockers` polyline, radius 2.2 m)
  - not a unit, not destructible, no gameplay effect besides blocking the track it stands on.
* *Roads*: 4 main roads (centre-line markings), 6 town streets + 2 industrial roads per side (kerbs), 5 dirt tracks per
  side (derricks, farmsteads, radio mast). Paved carriageways are drawn by `map_infra.gd` strips (asphalt, lane
  markings, kerbs/gutters); shoulders, dirt tracks, ballast staining and concrete hardstand come from `surface.png`
  in the terrain shader. Power-line conductors are strung between the existing pylons at load.
* *Road speed* (client decision): on a paved road ground units move at base speed x (1 + road_speed_bonus):
  wheeled +20 %, tracked and infantry +10 %; dirt tracks give half of that (`movement.<class>.road_speed_bonus`,
  `dirt_share` in map.json; `battle.terrain_speed_mult`). Off road the old material / slope factors apply. Identical
  for both sides; pathfinding costs are unchanged except that dirt tracks count as half a road.

**New map.json keys**: `surface_file` (surface.png, RGBA8 1 m/px: R paved road with 3 m shoulder falloff, G dirt
track, B rail ballast, A hardstand), `rail` {gauge_m, lines[{name, points, portals[{pos, front}]}], sidings},
`blockers` (walls, fences, train, platform, portal mouths), `hardstand`, `power_lines`, `corridors` (pass and goat
trail centre lines with floor half widths, for tests), `zones` (camera / test anchors); roads gained `surface`, `cls`,
`markings`, `kerbs`; civic entries gained `yaw_deg` (always 0 for now: civic models are not rotated).

## Files and formats

All files are in `godot/maps/zagros_basin/` (= `res://maps/zagros_basin/`).

| File | Format |
|---|---|
| `height.r16` | 601 × 601 little-endian uint16, row-major. Row 0 = z −600, column 0 = x −600, 2 m spacing. Metres = value / 65535 × `height_scale`. |
| `height_preview.png` | 8-bit greyscale, for humans only. |
| `splat.png` | RGBA8 601 × 601 on the same grid (pixel (col, row) = (x, z) sample). R = rock, G = gravel/scree, B = scrub, A = dry riverbed, sand = 1 − sum (the sum is always ≤ 1). Roads are **not** in the splat. |
| `splat.png.import` | Godot import settings: lossless, no mipmaps, `fix_alpha_border=false`, `detect_3d/compress_to=0`. Godot's default `fix_alpha_border=true` overwrites the RGB of pixels with alpha < 20 (that is, every non-riverbed pixel) within 4 px of riverbed pixels. That would corrupt the rock/gravel/scrub weights along every wadi. |
| `map.json` | Layout and gameplay data (schema below). |
| `fairness_report.txt` / `.json` | Verification output. The JSON also holds route polylines per class (`route_paths`). |

Props are in `godot/assets/units3d/props/`. Textures are embedded in each GLB, and the conventions follow `bldkit_b`: metres, origin on the ground, Blender −Y = Godot +Z, Principled BSDF with one baked albedo × AO atlas, and the `SA_Team` material left plain.

| GLB | Tris | Size (m) | Nodes |
|---|---|---|---|
| `oil_derrick.glb` | 3190 | 10 × 15.4 (with open gate) × 6.7 | `Base` (pad, fence, tank with SA_Team band, gearbox team plates); `WalkingBeam` (origin at the saddle bearing, rock about local X; SA_Team stripe) with children `HorseHead` and `Pitman`; `Crank` (origin at the gearbox axle, spin about local X); `Flag` empty at the flag-pole top |
| `village_house.glb` | 1390 | 8.7 × 8.7 × 5.2 | `House` |
| `ruin.glb` | 1804 | 14.6 × 12 × 4.8 | `Ruin` |
| `rock_cluster.glb` | 2640 | 6.3 × 4.6 × 1.6 | `Rocks` |
| `date_palm.glb` | 1088 | 8 × 8.4 × 10.2 | `Palm` (fronds use the double-sided `DP_DatePalm_2S`) |
| `scrub.glb` | 1834 | 1.8 × 2.1 × 1.0 | `Scrub` |
| `pylon.glb` | 2652 | 10.4 × 5.2 × 21.7 | `Pylon` + empties `Wire_0..2` (conductor points) and `Earth_0..1`; the line runs along local Z (Godot) |

**Derrick animation hint (not baked).**

- Spin `Crank` continuously by θ.
- Set the beam angle to `asin(1.0 · sin θ / 2.2)`. The crank pins point to −Y at rest.
- `Pitman` rides with the beam. The game may re-aim it at the crank pins.

Houses, walls and the ruin continue 0.5 m below their origin so they sit on uneven ground without gaps.

### map.json schema (as written)

```jsonc
{
  "name": "Zagros Basin", "id": "zagros_basin", "version": 1,
  "size_m": [1200, 1200],
  "grid": {"samples": 601, "spacing_m": 2.0, "origin": [-600, -600], "height_file": "height.r16",
           "height_format": "...", "splat_file": "splat.png",
           "splat_channels": {"r": "rock", "g": "gravel", "b": "scrub", "a": "riverbed", "remainder": "sand"}},
  "height_scale": 80.0,
  "water_level": null,
  "players": 2,
  "symmetry": "point (x, z) -> (-x, -z)",
  "starts": [{"team": 0, "pos": [x, z], "facing_deg": 0.0}, {"team": 1, "pos": [x, z], "facing_deg": 180.0}],
  "start_flat_radius_m": 100.0,
  "build_pads": [{"center": [x, z], "size": [w_x, d_z], "owner_hint": 0 | 1 | -1}],      // axis-aligned rectangles
  "supply_piles": [{"id": "pile_a0", "pos": [x, z], "cash": 20000, "contested": false}],
  "oil_derricks": [{"id": "derrick_a0", "pos": [x, z], "income": 100, "every_s": 10, "capture_s": 8,
                    "radius_m": 12, "contested": false}],
  "roads": [{"name": "central|west|east|basin", "width_m": 9.0, "points": [[x, z], ...]}],   // ~14 m point spacing
  "props": [{"type": "village_house|ruin|rock_cluster|date_palm|scrub|pylon", "pos": [x, z], "yaw_deg": 0.0, "scale": 1.0}],
  "prop_types": {"<type>": {"glb": "res://assets/units3d/props/<type>.glb", "footprint_m": [w, d], "blocks": true}},
  "movement": {
    "infantry": {"max_slope_deg": 38, "cost": {"sand": 1.0, "gravel": 1.1, "rock": 1.6, "riverbed": 1.2, "scrub": 1.1, "road": 0.9}},
    "wheeled":  {"max_slope_deg": 18, "cost": {"sand": 1.35, "gravel": 1.2, "rock": 4.0, "riverbed": 1.5, "scrub": 1.4, "road": 0.55}},
    "tracked":  {"max_slope_deg": 28, "cost": {"sand": 1.1, "gravel": 1.0, "rock": 2.2, "riverbed": 1.25, "scrub": 1.1, "road": 0.8}}
  },
  "building_max_slope_deg": 8,
  "notes": "..."
}
```

**Conventions.**

- `facing_deg` and `yaw_deg` are Godot `rotation_degrees.y`: 0 = facing −Z, 90 = facing −X. Props on B's half are point mirrors of A's half, with yaw + 180.
- Heights are not stored per site. Sample the heightfield.
- The `"wall"` prop type is reserved in `prop_types` (no asset yet) and is not placed. Walls are part of the house and ruin meshes.
- Prop counts: scrub 660, rock_cluster 176, date_palm 64, village_house 14, pylon 12, ruin 10.

## Tools and how to tweak

- `python3 -I tools/map/gen_zagros_basin.py` regenerates every map file, the reports and the four plots. It is deterministic (fixed seeds; a byte-identical rerun was verified) and takes about 10 s.
  - Add `--albedo <png>` for the render colour map.
  - Add `--no-plots` to skip the plots.
- Layout constants are at the top of the script:
  - `START_A`, `START_R`
  - `PASSES_A`: crest position along strike, pass-axis skew, nose gap, nose length
  - `PASS_FLOOR`
  - `GOAT_A`, `HILL_A`
  - `BUILD_PADS_A`, `PILES_A`, `PILES_C_HALF`, `DERRICKS_A`, `DERRICKS_C_HALF`, `VILLAGE_A`
  - `road_polylines()`
  - `MOVEMENT`
- Define everything for side A only. B is created by the point mirror.
- After any change, read `fairness_report.txt`. Routes, barriers, fairness and flatness are re-checked on every run.
- `python3 -I tools/map/render_zagros_rts.py godot/maps/zagros_basin <albedo.png> <out.png> [--target x,z --dist m --yaw deg]` renders the Blender preview: the terrain mesh, all props as collection instances, and a 52° camera.
- `python3 -I tools/art/prop_<name>.py godot/assets/units3d/props [--previews <dir>]` rebuilds a prop. `prop_zb_common.py` holds the shared surfaces and organic helpers. `prop_zb_sheet.py` builds the contact sheet.

### Using a real DEM

`--dem <file.tif|.tiff|.hgt|.png>` loads any of these:

- a GeoTIFF (read with tifffile; first band)
- SRTM `.hgt` (big-endian int16; voids filled)
- a 16-bit greyscale PNG

The DEM is assumed north-up. Options:

- `--dem-crop fx0,fz0,fx1,fz1` crops a fractional window.
- The DEM is resampled bilinearly to 601², normalised (2nd–99.5th percentile) to 2 … 2 + `--dem-relief` (default 62) game metres.
- It is blended with the procedural base by `--dem-weight` (default 1 = replace).

All gameplay carving is still applied on top: passes, trail, flattening, roads and symmetrisation. The authored layout may not suit a given DEM, so check the route and barrier report and move the passes and sites to match.

## Known limits and notes for integration

- **Not run in Godot here** (outside this ticket's scope). The formats match `terrain_map.gd` as read. Points the lead should check:
  - `export_presets.cfg` has `include_filter="*.json"` only. `*.r16` is not a Godot resource, so it must be added to the include filter or the exported build will be missing `height.r16`.
  - My hand-written `splat.png.import` has no `uid`. Godot should add one on the first import. Confirm that `fix_alpha_border` stays false.
- **`bldkit_b` defect found (not fixed there; outside this ticket's files).** In `Part.frustum`, `quad` and `loft`, faces on open islands keep zero normals. The planar "tile" UV then projects along X and the texture smears into stripes. `prop_zb_common.py` patches `K.orient_islands` to call `bm.normal_update()` first. Other `bldkit_b` assets that use `frustum` slabs (for example ground pads) may have the same striping.
- **Resolution.** The heightfield is 2 m per sample, so cliff risers are one or two cells wide. Up close they look soft; the shader adds procedural detail.
- **Preview renders.** The RTS render is a Blender preview using a colour map that approximates `terrain_map.gdshader`; it is not in-game output. Supply piles have no mesh in it.

### B3 verification (2026-10-24, Linux, shared 2-CPU machine)
* `maptest map=zagros_basin nation1=iran`: RESULT 36/36 (31 existing + roads_connect, road_grade, rail_train_portals,
  buildings_clear_of_infra, road_speed_bonus). Quick modes: `b3only`, `civonly`.
* `basetest aifast`: 19/19. `test` (army, Proving Ground): 21/22, `match_end` fails; it fails the same way with this
  branch's scripts reverted to the base commit, so it is not caused by B3 (pre-existing or load-dependent; open).
* Rendered 1080p (Xvfb software rasteriser, frame times not meaningful): overview 205 draw calls / 674 k primitives,
  town 215 / 720 k, industry + portal + train 218 / 754 k.
