# Terrain tiling fix: Zagros Basin

Client feedback after the Zagros Basin playtest: the ground "just repeated parcels".
Scope: `godot/shaders/terrain_map.gdshader` and the visual part of `godot/scripts/terrain_map.gd` (`build_visual`, `_build_chunk`, new `_noise_rgba`, `_hmap_image`, `_refresh_hmap`).
Gameplay data is untouched: heights, `splat_bytes`, the road mask, slopes, `material_cost` and the raycast.
The Proving Ground uses `terrain.gdshader` through `World.terrain()` and is unaffected.

## What caused the repetition

1. **One noise tile at four scales.** The old shader sampled one 512 px seamless noise texture (`n_detail`) at four world scales, with tile periods of 3.1, 17, 61 and 230 m. All four were axis-aligned and anchored at the origin.
   - The 61 m and 230 m layers carried the sand-tone and clay-patch variation, so the same blob pattern repeated on a fixed grid about 20× across the 1.2 km map. That grid read as parcels from the RTS camera.
   - Because every layer was a scaled copy of the same image, the layers did not decorrelate each other.
2. **Bench facets on the ridges.** The anticline flanks are cut into many 2–6 m limestone benches. On the 2 m height grid the bench risers alias into a regular field of triangular or diamond facets.
   - The splat paints rock on every riser as 1–2 px lines.
   - The strata bands were computed from the per-pixel height (`wpos.y`) of that jagged surface.
   - So every facet got its own colour, and the ridges looked like tiled pyramids (see the left half of `terrain_*_1`).

## What changed

### Shader (`terrain_map.gdshader`)

- **Unique macro layer (`n_macro`).** One RGBA noise texture, 512² and non-repeating, is stretched over the whole map at 2.3 m/px. It carries every variation larger than about 10 m:
  - brightness and hue drift of about ±11 %
  - two-tone sand fields and clay patches
  - pale dust films on low, flat basin floors
  - darker desert-pavement patches
  - scrub-cluster density
  - the warp for material borders

  Nothing at this scale repeats anywhere on the map.
- **Hex-tile detail (`n_detail`).** A seamless 19 m tile packs four independent noises in RGBA, covering 0.7–6 m features. It is sampled with hex-tile blending (Mikkelsen 2022):
  - a triangle grid gives each cell a random rotation and offset
  - three taps are blended with variance-preserving weights
  - `textureGrad` with rotated derivatives avoids mip seams

  The result has no visible period. Fine grain (0.1–0.5 m) is one plain rotated tap. Its period spans only a few pixels at RTS distance, and it fades with view distance.
- **Splat borders.** The splat lookup is warped by ±3 m, and each weight goes through a noisy `breakup()` threshold. Gravel, scrub, riverbed and rock edges become patchy instead of uniform 2 m-raster cross-fades.
- **Bench facets: colour.** Rock weight for colouring reads partly from a blurred splat mip (lod 1.0, blended 50 % after step 2). Strata bands use a smoothed height (mean of the height-texture taps at ±3 m and ±8 m), so they follow contours as broad curved bands rather than outlining facets.
- **Shading normal and slope.** Both come from the height grid uploaded as an R16F texture (`hmap`) and differenced at ±3 m and ±8 m, then blended 80 % with the mesh normal. Slope tint and rock-on-slope use this smoothed slope:
  - steep ground darkens
  - rock gets darker on steep faces
- **Normal map.** Two decorrelated taps at different scales and rotations replace the single 2.2 m tile.
- **Unchanged:** the base material colours, sRGB authoring with the `pow(2.2)` conversion, `sa_fog_shade` fog of war, the map-boundary darkening and the road / rut treatment.

### Script (`terrain_map.gd`, visual part only)

- `_noise_rgba()` packs four FastNoiseLite layers into one RGBA8 `ImageTexture`, so the shader reads four noises in one tap. All textures are generated at load; no image files ship.
- The splat gets a **rendering copy with mipmaps**. Gameplay still reads `splat_bytes`.
- `hmap` is built from `heights.to_byte_array()`, converted natively to R16F. R16F is used because linear filtering of R32F is optional in Vulkan.
- When `flatten()` rebuilds chunks after load, `_build_chunk` schedules one deferred `_refresh_hmap()` (a 1.4 MB re-upload). Flattened building pads therefore shade correctly too.

## Cost

| | Before | After |
|---|---|---|
| Texture taps per terrain pixel | 8 | 19 |
| Extra texture memory | — | about 2 MB |

- The 19 taps are: macro 1, hex detail 3, grain 1, splat 2, roads 1, height 8, normal 2 and fog 1.
- The 8 height taps hit a tiny, cache-friendly R16F texture. The hex blend adds a hash and three small rotations.
- Extra memory: macro 1 MB, detail with mips 1.4 MB, height 0.7 MB, splat mips 0.5 MB. The old 512² `n_detail` is gone.
- For a full-screen terrain on a desktop GPU this is a small cost. It could not be profiled here: the environment only has llvmpipe software rendering, which says nothing about GPU timings.
- **Cheapest optional cut:** drop the ±3 m height taps (−4 taps). The mesh normal already supplies the fine shading.
- **Load time:** `TERRAIN macro+detail noise` measured 1.3–1.4 s, against 0.3 s for the existing normal-noise texture. This was in a contended 2-core VM, where a standalone benchmark of the same calls ran in about 0.4 s. It happens once per match load.

## Step 2: bench geometry in the map generator

The shader work left the ridge facets faintly visible through cast shadows, SSAO and silhouettes, because they were real triangles in the heightfield. So the benches were reshaped at the source in `tools/map/gen_zagros_basin.py`. The game reads that data; the shader cannot change it.

- **Bench profile (`terrace()`).**
  - Before: 6.5 / 7 m steps, with the riser in the top 38 % of each step (smoothstep) and blended 70 %. That gave a riser every 6–7 m across the flank, only 1–2 grid cells wide.
  - After: 12 / 13 m steps, with a smootherstep riser over 55 % of each step (zero slope and curvature at the tread edges, so bench edges are rounded), blended 60 %.
  - Each bench now spans several grid cells.
  - Constants: `TERRACE_STEP`, `TERRACE_RISER`, `TERRACE_MIX`.
- **Gullies.** The down-dip gully noise had features of 9 / 16 m along strike. Crossed with the bench lines, it formed a checkerboard: the diamond pattern. It is now 16 / 26 m (`GULLY_LAM`).
- **Effect.** A hillshade high-pass measure on the ridges dropped from 0.255 to 0.134; it is the share of shading variance at wavelengths under about 3 grid cells.
- **What the outputs kept.**
  - `map.json` is identical except `props`: starts, pads, piles, derricks, roads, the `civic` list (7 entries), movement, notes and prop types. Prop counts per type are unchanged; only placements follow the new heights.
  - The generator's own checks are unchanged:
    - fairness 0.00 %
    - the same route lengths for every class and route
    - barriers: infantry crosses only by the goat trail, vehicles only through the passes, and nothing crosses with everything blocked
  - Passable fraction rose slightly (infantry 0.841 → 0.867, tracked 0.800 → 0.821; wheeled is unchanged) because the treads are broader. Cells over 38° fell from 57 462 to 48 011.
- **Regenerated** the normal way:
  - `python3 -I tools/map/gen_zagros_basin.py`: height.r16, splat.png, map.json, height_preview.png, the fairness report and `docs/screens/map_zagros_*.png`
  - `python3 -I tools/map/make_previews.py`: the Skirmish preview; the Proving Ground preview came out byte-identical
  - Before the change, the unmodified generator reproduced the committed files byte for byte, so every output difference comes from this change.
- **Shader follow-up.**
  - `breakup()` uses a wider ramp. The sharp threshold drew straight-edged polygon patches out of the bilinear 2 m splat.
  - The rock-mip blur is lighter (lod 1.0 at 50 %), since the new splat has far fewer thin riser lines.
- **Captures:** `terrain_after_1b.png` and `terrain_after_3b.png`, with the same cameras as pairs 1 and 3.

## Verification

- **Captures.** `mapshots terrainonly` (new mode; existing modes unchanged) renders five fixed terrain cameras. They cover zoom 65–230 and pitch 38–70°.
  - Before and after were run with identical arguments.
  - Pairs: `docs/screens/terrain_before_<n>.png` / `terrain_after_<n>.png` (shader only). Pairs 1 and 3 also have `terrain_after_<n>b.png` (shader plus new bench geometry).
  - `mapshots terrainfast` is the same five cameras with no bases or units, for quick iteration.
- **Tests.** `maptest map=zagros_basin nation1=iran` gave RESULT 31/31 on the regenerated map, including:
  - `starts_fair`
  - `routes_passable`
  - `cliffs_block`: 760 cliff points, 0 open for vehicles
  - `class_slope_rules`
  - `props_grounded`: 922 props, 0.000 m off the ground
  - `civic_buildings_placed`

## Remaining issues

- **Cross-hatch on steep faces.** This is a fine diagonal weave with a period of about 3 px, visible in every capture. Two tests (`docs/screens/terrain_hatch_test.png`):
  - Raising the sun's `shadow_normal_bias` from 0.6 to 1.6 did not remove it. It only brightened the faces because self-shadowing dropped.
  - Turning off the terrain normal map did not remove it either.

  So it is neither shadow acne nor the material. The most likely sources are the SSAO or soft-shadow filter pattern, possibly specific to llvmpipe software rendering. `World.environment()` was left unchanged. Next step: check on a real GPU, then try `ssao_*` or `soft_shadow_filter_quality`.
- **Silhouettes.** Bench silhouettes still show the 2 m triangle edges at the closest zoom. That is inherent to a 2 m grid without LOD or tessellation.
- **Strata contrast.** The strata bands are broader and more visible than the old fine stripes. If they read too strongly in play, lower the `0.35` factor on the strata line in the shader.
- **Haze.** Washed-out distant contrast comes from the environment fog and aerial perspective, not from the material.
