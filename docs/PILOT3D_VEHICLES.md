# Pilot 3D vehicles: M88 recovery vehicle ("Dozer") and CH-47 heavy-lift helicopter

Status: **pilot art, generated and previewed in Blender (Cycles CPU). Not yet imported or run in Godot.**
The lead integrates them. Both models are real 3D geometry with depth from every angle. Neither is a billboard.

| | M88 (Dozer / builder) | CH-47 |
|---|---|---|
| Script | `tools/art/veh_m88_3d.py` | `tools/art/air_ch47_3d.py` (imports the library half of the M88 script) |
| Output | `godot/assets/units3d/m88/m88.glb` | `godot/assets/units3d/ch47/ch47.glb` |
| Textures (embedded in GLB; PNG copies for inspection) | `m88_albedo.png` 2048², `m88_track.png` 256×512 | `ch47_albedo.png` 2048², `ch47_blade.png` 64×512 |
| Triangles | **11,572** (Hull 5,132, tracks 2×1,224, each road wheel 212, each sprocket 448, MG 128) | **7,202** (Body 6,548, each rotor 327) |
| Budget | ≤ 15k | ≤ 15k |
| Previews | `docs/screens/pilot3d_m88_{front,side,rear,top,rts,close34,scale}.png`, `pilot3d_m88_sheet.png` | `docs/screens/pilot3d_ch47_{front,side,rear,top,rts,close34,side_body}.png`, `pilot3d_ch47_sheet.png` |

Regenerate the models (deterministic: no RNG state, no network). Each run takes about 4–6 minutes on 2 CPUs, most of it spent on previews.
```
python3 tools/art/veh_m88_3d.py godot/assets/units3d/m88            # + previews into docs/screens
python3 tools/art/air_ch47_3d.py godot/assets/units3d/ch47
#   --no-previews   skip renders (~45 s each)      --previews <dir>   other preview folder
```

## Conventions (both models)
- Units are metres. Forward is Blender +Y, which the glTF exporter writes as Godot −Z. Up is +Z in Blender and +Y in Godot.
- All named objects are **top-level nodes** in the GLB, not parented to each other. Recursive `find_child` therefore finds them.
- Materials use a plain Principled BSDF with one base-colour image texture and constant roughness. They contain no custom nodes.

### M88 nodes
| Node | Pivot (Blender coords, m) | Animate |
|---|---|---|
| `Hull` | origin (0,0,0) = ground contact under the vehicle centre (blade tip to hull rear = 8.3 m, centred) | static. Includes the dozer blade, push arms and rams, the A-frame crane boom with hook block, the winches, the stowage and the return rollers |
| `MG` | cupola pintle (−0.726, 0.983, 2.80) | optional yaw about local up |
| `WheelL0..WheelL5`, `WheelR0..WheelR5` | hub, x = ∓1.62, z = 0.496, 0 = front | spin about **local X** |
| `IdlerL`, `IdlerR` | front idler hub (±1.62, 2.787, 0.80) | spin about local X |
| `SprocketL`, `SprocketR` | rear drive sprocket hub (±1.62, −3.54, 0.80) | spin about local X |
| `TrackL`, `TrackR` | origin (0,0,0) | scroll UV.y. Material **`SA_TrackScroll`** |

L = vehicle left = −X. Road wheel radius 0.376 m, idler 0.33 m, sprocket 0.355 m (pitch radius). For equal surface speed, rotation rate = v / r.

**Track UVs.** V runs along the belt, U across it. U layout: 0–0.5 outer tread, 0.5–0.6 outer side, 0.6–0.9 inner face, 0.9–1.0 inner side.
Belt loop length is 15.317 m and holds 96 links of 0.1596 m. The texture tile holds 6 links, so
**1.0 V = 0.9573 m** of track. The loop holds exactly 16 tiles, so the closing seam is invisible.
Along the ground run, Blender V increases towards the front. The glTF exporter writes V' = 1 − V, so in Godot UV.y *decreases* towards the front.
For the vehicle driving forward a distance `d` (m), set `uv1_offset.y -= d / 0.9573` on the track material. Reverse this for reverse gear. For a pivot turn, use opposite signs per side.

### CH-47 nodes
| Node | Pivot (Blender coords, m) | Animate |
|---|---|---|
| `Body` | origin (0,0,0) = wheel-bottom ground contact under the fuselage midpoint | static. Includes sponsons, both pylons, engine nacelles and landing gear (no separate gear nodes) |
| `RotorFront` | front hub (0, 5.621, 5.586) | spin about **local up** (Blender Z = Godot Y) |
| `RotorRear` | rear hub (0, −6.319, 6.005) | spin about local up, **opposite direction** to the front rotor |

Each rotor is one mesh: the hub plus 3 real blades. Blade span runs from 0.8 to 9.15 m (18.3 m diameter). Chord is 0.64 m tapering 15%, with 8°→−4° twist and 2.5° coning.
The rear rotor is clocked 60° relative to the front rotor. The masts are vertical; the real shaft tilt is not modelled.
Fuselage nose to tail is 16.1 m, overall width 3.76 m, rear hub height 6.0 m, and hub spacing 11.94 m (real CH-47 value).

## Method
1. **Measure.** Feature positions were read in pixels off gridded copies of the normalised concept cut-outs. These include hull outline, deck heights, wheel centres and radii, blade and boom endpoints, cupola, hatches and stowage.
   - M88: there is one uniform scale per view (side 8.3/816 m/px, top 8.3/760 m/px). The two views agree within about 3 cm on the casemate front and rear and the hull rear, so no rectification was needed.
   - CH-47: the side view is scaled by the real hub spacing (0.02327 m/px). The concept **top view is not proportional to the side view**: its nose section is about 1.9× too long relative to the rotor spacing. It is therefore mapped with a piecewise-linear Y rectification through four landmarks (nose, front hub, rear hub, tail). Its across-scale is 0.030 m/px.
2. **Model.** Geometry is built from extruded side profiles, lofted superellipse sections and primitives fitted to those measurements. The M88 hull, casemate, lower hull and blade are extruded side-view outlines with 2 cm bevels. The CH-47 fuselage is lofted from the measured side top/bottom lines and the measured top-view half-width per row; the sponsons, nacelles and pylons are separate lofts or extrusions. A pure visual hull (intersecting silhouettes) was rejected because the M88 crane overhang would have produced a full-width wall.
3. **UV** is one Smart-UV atlas per model. On the M88, the right-side running gear is a mirrored copy that shares the left-side UVs.
4. **Texture by projection.** A UV-space rasteriser gives each atlas texel its world position and face normal. The colour is a normal-weighted blend (power 3) of:
   - the top view, on up-facing texels;
   - the side view, on ±X-facing texels. The same image is used for both sides, so the far side is correctly mirrored;
   - M88 only: the front-3/4 and rear-3/4 views, rectified by homographies onto the front plate, the blade face and the rear plate.

   Each projection is **depth-tested** against an orthographic depth map of the model. This stops occluded faces (under the boom, under fenders, inner wheel faces) from receiving a copy of what lies above them; texels hidden from every view get the darkened unoccluded blend. Before use, the reference images are alpha-eroded by 2–3 px, then edge-extended, then gain-matched to the side view's mean colour. On top of the projection, a Cycles AO bake (1024², 16 samples, 0.9 m distance) is multiplied in at 50–55%, plus light procedural grime and mottling. The CH-47 rotor blades use their own strip texture, sampled along a blade of the concept overhead view.
5. **Track tile (M88).** The concept art shows the tracks only as a thin, partly hidden strip; sampling it picked up hull tools. The link pattern is therefore procedural: shoe, grouser, rubber pads, end connectors and guide horn. It is coloured with dark and light medians taken from the concept's lower track run.

## Reference inputs used (read-only)
- M88: `godot/assets/us/vehicles/m88/m88_{top,side,front34,rear34}.png` (manifest `content/manifest/us_packs.json` → `vehicles.m88`)
- CH-47: `incoming/a/individual_views/CH-47_Chinook/CH-47_Chinook_side_profile.png` and `..._overhead_game_view.png` (blade texture only). The `a/` and `b/` sets are byte-identical (md5 checked). Also `godot/assets/us/rotors/ch47_body.png` (blade-free top view).
- The CH-47 front- and rear-3/4 concept views were inspected but not projected. They are strongly perspective, and the rear view shows the ramp open.

## Known shortcomings / review items
- **The concept views disagree with each other** (AI art). On the M88, the top view's front-deck winch block extends ~0.5 m further forward than the side view's glacis. On the CH-47, the top-view nose is stretched; it is handled by rectification, but cockpit-roof detail is compressed. Wherever the views disagree, the geometry follows the side view.
- **Texture smearing** appears on faces whose normals no projection covers well. Examples: the M88 blade top lip and boom flanks, the CH-47 pylon front faces, and the nose cap. Here the side view is extended along the depth axis and shows as faint streaks up close. From the 52° RTS camera it is not noticeable.
- **Baked lighting**: the concept art contains painted lighting and shadows, which are now in the albedo. This is acceptable for an RTS camera, but the art does not respond correctly to a moving sun. Any future PBR pass should de-light it.
- **M88 simplifications**: the crane is a single straight boom with no separate A-frame legs (it follows the concept, which shows one beam). There is no rear spade (the concept has none) and no track sag. The boom is static; it is not a separate node, so the game cannot raise it.
- **M88 width**: 3.88 m (blade) / 3.80 m (tracks). This follows the concept's chunky proportions and is wider than the real vehicle's ~3.4–3.7 m.
- **CH-47 landing gear and rear ramp**: the gear is part of `Body` (no retraction, which matches the real aircraft) and the ramp is closed. The rotors are perfectly rigid: no blade droop at rest, no mast tilt.
- **The CH-47 albedo carries the US national star-and-bar insignia** from the concept (sponsons and fuselage). This must be cleared for the fictional setting, or masked if factions need neutral or team markings. **Neither model has team-colour regions yet.**
- **Godot import is untested**: double-sidedness, UV2/lightmap and LOD generation still need checking in Godot. No LODs were authored; Godot's auto-LOD should be acceptable at these triangle counts.
- The previews are Blender Cycles renders with Standard view transform (sun + sky), not in-engine captures.
