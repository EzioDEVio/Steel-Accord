# Pilot 3D structure — Supply Depot

Status: **pilot asset built and previewed in Blender (Cycles, re-imported from the exported GLB). Not yet loaded or tested in Godot.**
The current game material code would also replace this asset's textures if it were dropped in unchanged (see "Integration notes").

The client rejected flat building images. This pilot replaces the Supply Depot billboard with a real
3D model that holds up at any camera yaw or tilt, while still looking like the concept sheet
(`incoming2/.../individual_views/Supply_Depot/*.png`).

| Item | Path |
|---|---|
| Generator (deterministic) | `tools/art/bld_supply_depot_3d.py` |
| Runtime asset | `godot/assets/units3d/supply_depot/supply_depot.glb` (3.0 MB, atlas embedded) |
| Previews | `docs/screens/pilot3d_depot_{rts,front,side,rear,top}.png`, `pilot3d_depot_vs_concept.png` |

## Build

```
python3 -I tools/art/bld_supply_depot_3d.py godot/assets/units3d/supply_depot \
    --previews docs/screens --concept <.../Supply_Depot_overhead.png>
# options: --previews-only (re-render existing GLB), --only rts,front (subset of shots)
```
Determinism was checked by running the build twice into different folders. Both GLBs are byte-identical (md5 `55d2d89f…`).
Run times on 2 CPU cores with no GPU: about 2.5 min for the build and texture bakes, and about 1 min per preview shot.

## Dimensions and conventions
- The concrete slab is 22.0 m (X) × 18.0 m (depth) with its top at 0.25 m. The origin is at the centre of the slab's bottom face, at ground level.
- Front (three loading bays, dock, ramp) = Blender −Y = **Godot +Z**. Verified in the exported GLB: the team-colour fascia lies at z = +6.55.
- Warehouse 12.2 × 10 m. Wall top 6.2 m, parapet 6.75 m, front pilasters 7.0 m, rear corner towers 7.4 m.
  Rooftop units reach ~8.2 m and the antenna mast 10.3 m. The loading dock is 1.0 m above the slab.
- GLB nodes: `Building` (slab, warehouse, docks, canopy, roof hardware) and `Props` (crates, pallets,
  containers, drums, Jersey barriers, fence, light poles). These names are stable.

## Triangle count
Building 4,378 + Props 3,904 = **8,282 triangles** (budget 4k–12k).
Downward faces that rest on a surface are deleted. They are never visible, and removing them saves triangles and atlas space.

## Materials (glTF)
| Material | Use | Texture |
|---|---|---|
| `SD_SupplyDepot` | everything opaque | one 4096² JPEG albedo atlas (colour × baked AO), roughness 0.82, back-face culled |
| `SA_Team` | canopy fascia stripe | none (plain white), so the existing team-tint convention can find it |
| `SD_Fence` | chain-link panels | 256² RGBA tiling texture, alpha **BLEND**, double-sided |

Every material is a plain Principled BSDF with image textures, so it survives glTF export with no procedural nodes.
The atlas resolution is about 42 px/m.

## Method
1. **Modelling.** Each part of the model is built from code-placed primitives: boxes, prisms, cylinders and struts. They come from the same `Part` accumulator
   pattern as `bld_command_post.py`. Each primitive is tagged with a *source surface*:
   concrete, slab, olive standing-seam roof, olive ribbed cladding, door slats, corrugated container,
   tarp, ammo crate, pallet, hazard stripes, HVAC panels, glazing, Jersey concrete, metal, yellow paint,
   lamp, rubber. Large architectural blocks get a 35 mm one-segment bevel, so edges catch the light at RTS zoom.
2. **Source textures.** Each surface is a tileable numpy texture made from FFT-filtered noise plus stripe profiles.
   Base colours were sampled from the concept art. Each texture is mapped by a world-space planar `tile` UV chosen from the face's dominant normal,
   which keeps texel size constant and keeps ribs vertical on walls and front-to-back on the roof.
3. **Atlas.** A non-overlapping `atlas` UV is smart-projected and packed over Building and Props together.
   Cycles CPU then bakes two maps: DIFFUSE colour (8 samples) at 4096², and AO (24 samples, 4 m distance, with a ground plane) at 2048².
4. **Composite.** The script multiplies the colour by the AO (`0.28 + 0.72·ao`) in linear space and saves a JPEG at quality 90.
   It then swaps all source materials for `SD_SupplyDepot`, removes the `tile` UV, renames `atlas` to `UVMap`,
   and joins the fence quads into `Props`.
5. **Previews.** The script re-imports the exported GLB and renders it, so the previews show the exported file, not the Blender scene.

## Applying the pipeline to the other 13 structures
- Copy `bld_supply_depot_3d.py` and keep the top half unchanged: the textures, `SURF`, `Part`, the bake, the composite, the export and the previews.
  Replace only the layout section (between "layout constants" and `props = P.build()`) with the new building.
  The surface library already covers most US base vocabulary. A new surface is added as one `t_*()` function plus one `SURF` entry.
- Recommended next step: move the shared top half into `tools/art/sa_structure_kit.py` once a second structure uses it. I kept the pilot self-contained, as the brief asked.
- Per building: block out from the overhead concept (pixel ratios → metres), check `rts` and `vs_concept` renders, then tune.
  Budget about 4–10k triangles. Use a 4096 atlas for large buildings and 2048 for small ones (set `ATLAS`).
- Keep the same conventions: origin at slab bottom centre, front toward Godot +Z, nodes `Building`/`Props`,
  and an `SA_Team` strip somewhere visible.

## Integration notes (for the Godot/lead owner — not done here)
- `godot/scripts/unit_art.gd` `UnitArt.apply()` **replaces every surface material** with the palette shader by
  material name. Unknown names fall back to `SA_Paint`, which would wipe this atlas. Buildings that use this
  pipeline need to keep their imported `SD_*` materials, or the unit shader needs an albedo-texture input.
  It should only override `SA_Team`.
- Fence uses alpha BLEND: at RTS distance it reads as a grey see-through screen, which is intended. If sorting artifacts
  appear against transparent FX, switch to alpha hash in the import settings.
- The footprint and collision/placement size in game data must be set to 22 × 18 m (or the model scaled to the existing
  footprint) by the gameplay owner.

## Known shortcomings
- **Not verified in Godot** (instructed not to run it). Lighting, colour and tonemapping will differ from the Cycles previews.
- No normal or roughness maps. Ribs, slats and planks are painted into the albedo, so they look flat at very close zoom.
  The texel density (~42 px/m) is enough at RTS distance but soft in close-ups.
- AO is baked into the albedo, so it stays in place under any lighting and cannot respond to dynamic shadows. A destroyed or damaged state is not modelled.
- Proportions are a judgment call. The concept implies a lower (~5 m) wall, but the brief asked for a 7–8 m
  building, so the warehouse is a little taller and squarer than the painting. The skylights, vents and HVAC follow the overhead layout.
- The concept's lamps glow. Here the lamps are pale albedo only, with no emissive texture.
- Simplifications: the crates are boxes with no rope handles or stencil text; the fence has no gates or barbed wire;
  and there is no generator or pipework detail on the east yard.
- The LOD is a single mesh. At 8k triangles a second LOD is probably unnecessary, but it has not been measured in game.
