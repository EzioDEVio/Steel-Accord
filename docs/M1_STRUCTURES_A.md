# M1 structures (set A): Command Center, Power Plant, Barracks, War Factory

Status: **built in Blender, exported to GLB, previewed in Cycles from the re-imported GLB. Not loaded or tested in Godot**
(instructed not to run it). The other artist is building Airfield, Supply Drop Zone, Radar, Defense Tower and HESCO separately.

Pipeline: same method as the approved pilot (`docs/PILOT3D_STRUCTURES.md`). Primitives are placed in code and tagged
with tileable procedural source surfaces whose colours were sampled from the concept. One smart-projected atlas UV covers
Building + Props. Cycles bakes colour (8 spp, 4096²) and AO (24 spp, 2048², ground plane), and the two are composited
as albedo × (0.28 + 0.72·AO) into one JPEG. The GLB then holds a single Principled BSDF atlas material.
The shared code lives in **`tools/art/bldkit.py`** (new). It is a generalised copy of the pilot's top half plus new helpers.
The pilot script is unchanged.

## Build

```
python3 -I tools/art/bld_<id>_3d.py godot/assets/units3d/<id> --previews docs/screens \
    --concept <incoming2/.../individual_views/<Concept>/<Concept>_overhead.png>
# options: --only rts,front (subset of shots)  --previews-only (re-render the existing GLB)
```
On 2 shared cores, each build plus bake takes about 3–5 min, and each 640×400 preview at 24 spp with OIDN denoise takes about 1 min.
Peak memory is about 3 GB. The machine's memory cgroup is shared with the other artists' jobs, and several runs were
OOM-killed while they ran concurrently. The kit now composites the atlas in row chunks to lower its peak. If a run is killed,
start it again.
The scripts contain no randomness: all noise uses fixed seeds and the Cycles seed is 7. The method is the one whose determinism
was proven byte-for-byte in the pilot. **I did not run a separate determinism check on these four**, to save the shared CPU.

Footprint check (GLB vertex bounds): Building and Props stay inside each slab outline. The Building node is
exactly 26×22, 18×16, 20×16 and 28×22 m.

## Conventions shared by all four
- Origin = centre of the slab's bottom face (Godot Y = 0). The slab top is at 0.25 m. Front = Blender −Y = **Godot +Z**.
- Mesh nodes: `Building` (slab, structure, roof hardware) and `Props` (yard clutter, barriers, fences, tanks, crates).
- Materials: `<P>_<Name>` (the atlas: `CC_CommandCenter`, `PP_PowerPlant`, `BK_Barracks`, `WF_WarFactory`; 4096² JPEG,
  roughness 0.82, back-face culled) and `SA_Team` (plain white strips for team tint). Where a building has
  chain-link fencing it also has `<P>_Fence` (256² RGBA, alpha BLEND, double-sided).
- **Light objects** are separate mesh nodes, each with its own material **`SA_Light_<objectname>`**. That gives literal names
  such as `SA_Light_Light_Status0` (Principled BSDF: base white, emission colour white, emission strength 1).
  The glTF stores emissiveFactor [1,1,1]. Each node's origin is at the lamp centre.
  - `Light_Status*`: small beacon domes near doors or the roof, which the game blinks green, amber or red.
  - `Light_Beacon*`: red aviation-beacon domes on masts, stacks and towers, which the game blinks.
  - `Light_Flood*`: flood-lamp lens boxes, which stay steady. The housings are part of `Building` or `Props`.
  - In the previews **only**, these are tinted green, red and warm white with emission 6 to show the intended look. The GLB itself is white/1.
- **Empties**: `Exit` sits on the ground (Y = 0) about 1 m outside the slab, in front of the main door, gate or bay.
  `RepairBay` (War Factory only) sits on the apron at slab-top height (Y = 0.25).
- Downward faces resting on a surface are deleted. Coincident duplicate faces are avoided, because they bake to black AO.
  The kit's `Part.once()` dedupes shared fence posts.

---

## Command Center (`command_center`)

| Item | Value |
|---|---|
| Generator | `tools/art/bld_command_center_3d.py` |
| Runtime asset | `godot/assets/units3d/command_center/command_center.glb` |
| Previews | `docs/screens/m1_command_center_{rts,front,side,rear,vs_concept}.png` |
| Footprint | slab 26.0 × 22.0 m |
| Heights | HQ roof deck 9.4 m, parapet 10.0 m; annex roof 4.6 m; lattice radar tower to ~15.4 m (radar panel top ~17.7 m, beacon ~18.5 m); antenna masts to ~17.3 m |
| Triangles | Building 5,416 + Props 3,680 + lights 424 = **9,520** |
| Nodes | `Building`, `Props`, `Light_Status0` / `Light_Status1` (lamps either side of the main door), `Light_Status2` (front-right parapet corner), `Light_Beacon0` (radar tower top), `Light_Beacon1` (tallest antenna mast), `Light_Flood0` / `Light_Flood1` (HQ front corners, aimed at the entrance yard), `Exit` (x 3.25, Godot z +12.0) |
| Materials | `CC_CommandCenter`, `SA_Team` (front parapet band, annex fascia), `SA_Light_*` ×7 (no fence) |

Layout from the concept:
- Fortified two-storey HQ block in weathered grey cast concrete. It has a battered (sloped) base, battered buttresses
  at the corners and door piers, and a string course. A lit clerestory window band wraps the front and east sides.
- The steel entrance door sits on a stepped landing with railings, a canopy and two door lamps.
- On the HQ roof: a satellite dish on a pedestal, a 4-leg lattice tower carrying a tilted radar panel, three antenna masts,
  comms cabinets, an HVAC unit and a perimeter railing.
- A lower operations annex to the west carries five twin-fan condenser units, a ladder, railings and a door with an awning.
- Olive generator shelters stand front-left and at the rear. East of the HQ is a tarp shelter with ammo pallets and a cluster of grey equipment boxes.
- Perimeter: tall concrete T-wall/Jersey blocks with a sandbag wall behind them along the front and the front half of each side,
  and HESCO bastions along the rear half and the back. The door gap is flanked by short sandbag bunkers.

Known shortcomings:
- The HQ concrete is a little lighter and cleaner than the gritty concept painting, and there are no decals, stencils or damage.
- The satellite dish faces the default sun and reads very white in previews, much as in the concept.
- The rear generator shelter is simpler than the concept's.
- The sandbag wall is an extruded profile with a painted bag pattern, not individual bags.
- The concept's door has an arched head, which is modelled square.

## Power Plant (`power_plant`)

| Item | Value |
|---|---|
| Generator | `tools/art/bld_power_plant_3d.py` |
| Runtime asset | `godot/assets/units3d/power_plant/power_plant.glb` |
| Previews | `docs/screens/m1_power_plant_{rts,front,side,rear,vs_concept}.png` |
| Footprint | slab 18.0 × 16.0 m |
| Heights | generator hall wall top 6.3 m, parapet 6.8 m (pilasters 7.05 m); roof vent boxes ~7.5 m; roof exhaust stacks ~9.8 m; generator modules ~3.1 m + silencers to ~4.3 m |
| Triangles | Building 1,888 + Props 5,018 + lights 424 = **7,330** |
| Nodes | `Building`, `Props`, `Light_Status0` (above the hall door), `Light_Status1` / `Light_Status2` (front outer corner of each generator module), `Light_Beacon0` / `Light_Beacon1` (rear-corner roof exhaust stacks), `Light_Flood0` / `Light_Flood1` (hall front roof corners) |
| Materials | `PP_PowerPlant`, `SA_Team` (hall parapet band, generator front strips), `SA_Light_*` ×7, `PP_Fence` |

Layout from the concept:
- A beige precast-concrete generator hall with chamfered corner pilasters and a darker plinth. The front has two big louvres
  and a central door under a concrete hood with a lamp. The sides and rear also carry louvres, and the rear adds conduits,
  cabinets and a personnel door.
- On the roof: two raised louvred vent boxes with grating tops, two exhaust stacks and a hatch.
- Two olive diesel generator modules sit in front, each on a skid with a hazard band, a radiator louvre front, side louvres,
  a horizontal silencer and a vertical exhaust outlet. Cable bundles run from each module to wall junction boxes.
- East side: two horizontal olive fuel tanks on concrete saddles, with yellow pipework and a ladder.
- West side: electrical cabinets and a transformer.
- A central steel-grating walkway with yellow edge lines leads to the door. The perimeter is a concrete kerb with
  concrete pillars and chain-link panels. The front stays open, with short concrete walls and yellow bollards.

Known shortcomings:
- The generator lids read flatter than the concept's panelled tops, and the cable bundles are straight polylines, not sagging curves.
- The roof stacks are taller than in the concept, to carry the beacons the brief asks for.

## Barracks (`barracks`)

| Item | Value |
|---|---|
| Generator | `tools/art/bld_barracks_3d.py` |
| Runtime asset | `godot/assets/units3d/barracks/barracks.glb` |
| Previews | `docs/screens/m1_barracks_{rts,front,side,rear,vs_concept}.png` |
| Footprint | slab 20.0 × 16.0 m |
| Heights | wings: ground floor to 3.3 m, wall top 6.2 m, coping 6.62 m; rooftop condensers ~7.2 m; beacon mast ~8.8 m; entrance block ~4.2 m; utility block ~3.6 m |
| Triangles | Building 5,346 + Props 1,568 + lights 344 = **7,258** |
| Nodes | `Building`, `Props`, `Light_Status0` / `Light_Status1` (lamps either side of the entrance door), `Light_Status2` (above the entrance canopy, on the fascia), `Light_Beacon0` (short mast on the east wing roof), `Light_Flood0` / `Light_Flood1` (on the gate pillars, aimed at the gate), `Exit` (x 0, Godot z +9.0, in front of the open gate) |
| Materials | `BK_Barracks`, `SA_Team` (front fascia of each wing coping, entrance-block fascia), `SA_Light_*` ×6, `BK_Fence` |

Layout from the concept:
- Two long two-storey wings run front to back. Each has a tan block ground floor, an olive ribbed upper floor, a concrete
  floor band, olive roof coping, a tan roof deck and three condensers. There are windows on all faces and doors to the
  courtyard on both floors.
- Steel stairs climb the front of each wing to a corner landing. Upper walkways with railings run the length of the courtyard side,
  a walkway bridge links the wings at the rear, and an outer side stair rises to an upper door on each wing.
- A single-storey entrance block with a corrugated roof, double door, small canopy and lamps stands at the front.
  A utility block with a corrugated roof stands at the rear.
- The courtyard has a peaked olive shade sail on four posts, four picnic tables and lockers.
- The chain-link perimeter has a front double gate between tan pillars. The gate leaves are modelled open, folded back against
  the inside of the front fence. Concrete kerb blocks line the front, and green bins and lockers stand along the walls.

Known shortcomings:
- The many warm wall lights in the concept are baked albedo patches, not emissive. Only the six listed lights are emissive.
- The wings are a little wider and shorter than in the concept so that they fit the 20 × 16 m footprint.
- The fence is see-through alpha. At a steep angle the gate leaves read as thin frames.

## War Factory (`war_factory`)

| Item | Value |
|---|---|
| Generator | `tools/art/bld_war_factory_3d.py` |
| Runtime asset | `godot/assets/units3d/war_factory/war_factory.glb` |
| Previews | `docs/screens/m1_war_factory_{rts,front,side,rear,vs_concept}.png` |
| Footprint | slab 28.0 × 22.0 m (hall 18.4 × 14.2 m, west annex 6.6 × 10 m) |
| Heights | eaves 8.0 m, vault crown 11.4 m, spine 11.95 m, spine ventilators ~13 m, beacons ~13.1 m; bay openings 6.8 × 6.4 m |
| Triangles | Building 3,790 + Props 1,646 + lights 424 = **5,860** |
| Nodes | `Building`, `Props`, `Light_Status0` / `Light_Status1` (on the bay lintel, outer side of each bay), `Light_Status2` (west annex door), `Light_Beacon0` / `Light_Beacon1` (short masts at the front and rear ends of the roof spine), `Light_Flood0` / `Light_Flood1` (above each bay, aimed down at the apron), `Exit` (in front of the west bay, x −1.4, Godot z +12.0), `RepairBay` (in front of the east bay, x 7.4, Godot z +8.0, Y 0.25) |
| Materials | `WF_WarFactory`, `SA_Team` (band on the bay lintel), `SA_Light_*` ×7 (no fence) |

Layout from the concept:
- An olive barrel-vault vehicle hall with a standing-seam roof. A raised darker spine carries four ventilators, and two framed
  skylight strips run either side of it in three sections each, with eave ventilators along both sides.
- A tan concrete arch coping runs along both gables. Big battered tan buttress wedges stand at the front corners, with more
  buttresses along the east side, rear and corners, and two rising above the annex roof on the west.
- The front gable has two large open vehicle bays with raised roll-up door housings, guide rails, a concrete lintel beam and
  a central concrete pier, with yellow bollards at each bay.
- The bays have modelled interiors (inward-facing room, crane runways, floor lane lines). A yellow gantry crane bridge with a
  hoist hangs just behind the west bay header. Red machinery, racking, pallets and a workbench sit inside.
- To the west is a flat-roofed tan annex with condensers, a large duct into the hall, louvres, doors and side pipework,
  plus a tank on a yellow-railed platform. An olive lean-to canopy covers crates, pallets and drums.
- The apron has drain grates and yellow lane lines.

Known shortcomings:
- The vault is a true circular arc, which is rounder than the concept's flatter, almost gabled roof. I chose this per the brief's "barrel-vault / arched roof".
- The bay interiors are in shadow. The yellow crane is clearly visible from the front and only partly visible at the standard RTS angle.
- The concept's roof also has small vent boxes along the eaves at close spacing, and here there are only three per side.
- There is no vehicle inside the bays.

---

## Integration notes (for the Godot/lead owner, not done here)
- Same caveat as the pilot: `UnitArt.apply()` must keep the imported atlas materials (`CC_*`, `PP_*`, `BK_*`, `WF_*`,
  `*_Fence`). It should override only `SA_Team` and recolour or animate the `SA_Light_*` materials by node name.
- Light nodes are direct children of the scene root, alongside `Building` and `Props`. Blink them by changing the
  emission colour or energy of their own material, or by toggling visibility.
- Game data needs footprints and collision of 26×22 (CC), 18×16 (PP), 20×16 (Barracks) and 28×22 (War Factory),
  or the model must be scaled to the existing footprints.
- `Exit` empties sit outside the slab. Spawn code should read their global position and not assume a fixed offset.
- Someone else ran a Godot import while this work was in progress. It left `.import` files and extracted albedo/chain-link textures
  in all four asset folders. These scripts do not write those files. The GLBs were re-exported afterwards, so a reimport is needed to
  refresh the extracted textures. Godot normally does this on its own when a GLB changes.
