# ADR-0008: Built-in heightfield terrain for data-driven maps (Terrain3D not adopted for now)

Status: accepted for B1.5 (Zagros Basin). Revisit if map size or painting needs grow.

## Context
The first playable map (Zagros Basin) needs real elevation: ridges, valleys, passes and cliffs that block.
Requirements: a high-bit-depth heightmap, terrain materials, grounding of every unit / structure / prop through a
terrain query, slope-limited placement, per-movement-class navigation, data in files (no scripts to tune) and an
exported Windows build that runs.

## Options evaluated
1. **Terrain3D 1.0.2 (GDExtension, MIT).** Mature clipmap terrain with a sculpting / painting editor in Godot.
   - What we could verify here: the project's GitHub release archives (prebuilt Windows/Linux binaries) are not
     downloadable from this build environment (HTTP 403 through the proxy). Only the source can be cloned, and
     building it needs godot-cpp plus a Windows cross-compile we cannot test in this environment.
   - Not verified: its renderer compatibility with our Forward+ setup and its behaviour in our Windows export.
   - Cost: a native binary dependency in every build, an editor workflow nobody on the project uses yet, and its own
     collision and height queries that our deterministic grid simulation would have to mirror.
2. **Built-in heightfield (chosen).** `scripts/terrain_map.gd`: a 16-bit R16 heightmap (601 x 601 samples, 2 m) read
   from `maps/<id>/height.r16`; bilinear `height_at`, `normal_at`, slope queries; chunked `ArrayMesh` rendering
   (50 x 50 quads per chunk); `flatten()` for building pads that rebuilds only the touched chunks; a splat-weighted
   material shader with procedural detail (no third-party textures); a road mask baked from `map.json` polylines.
   - One height function feeds rendering, unit grounding, building placement, camera picking (ray-march) and the
     navigation grids, so the visual surface and the simulation cannot disagree.
   - Pure GDScript: identical on Linux and Windows exports; nothing native to ship.

## Decision
Use the built-in heightfield now. Keep the map format (R16 + splat PNG + map.json) engine-neutral so Terrain3D (or
another terrain system) can be adopted later by importing the same files.

## Consequences
- Load time: heights, slope grid and three navigation grids are baked in GDScript at match start (measured in the
  B1.5 report). Large maps would need caching or a native module.
- No in-editor sculpting; maps are generated / edited by `tools/map/gen_zagros_basin.py` and data files.
- No LOD on the mesh (1.4 M triangles for 1.2 km x 1.2 km at 2 m). Acceptable at RTS camera distances; revisit for
  bigger maps.
- Real elevation data (DEM) could not be downloaded here either (403); the Zagros Basin relief is synthetic and
  documented as such. The generator accepts a DEM file when one is supplied.
