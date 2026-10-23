

Create the first playable map for Steel Accord in the existing Godot 4.5.1 project.

Before changing files, inspect the current map scene, terrain setup, unit movement,
building placement, resource system, and project renderer. Report the relevant
files and any compatibility risks.

Map concept:
- A fictional RTS sector inspired by Iran’s Zagros foothills and a dry basin.
- Use real public elevation data only for broad terrain shape.
- Invent and relocate all bases, roads, towns, supply sites, oil derricks,
  depots, and military structures. Do not reproduce real military or
  critical-infrastructure locations.
- Aim for an initial playable area around 4–6 km across, scaled as needed for
  RTS pacing.

Implementation:
- Evaluate Terrain3D 1.0.2 for this Godot 4.5.1 project. Test compatibility
  with the project’s renderer and Windows export before committing to it.
- Import a prepared high-bit-depth heightmap; do not use an 8-bit heightmap.
- Create terrain materials for sand, rock, gravel, scrub, dry riverbeds, and roads.
- Add buildable pads, two balanced player start areas, supply sites near both
  starts, contested central supply sites, neutral capturable oil derricks,
  road routes, ridges, valleys, and map boundaries.
- Model supplies as finite resources delivered to a supply center. Model oil
  derricks as capturable sites that provide recurring income.
- Ground every building and prop using a terrain query or downward raycast.
  Reject building placement on steep slopes and prevent floating or buried assets.
- Create suitable terrain collision and navigation. Use different slope and
  movement rules for infantry, wheeled vehicles, and tracked vehicles.
- Keep the map data-driven so resource amounts, capture income, starts, and
  terrain costs can be adjusted without editing scripts.

Acceptance checks:
- Map loads and runs in the game.
- Buildings rest on the terrain; no visible floating or sinking.
- Infantry and vehicles can navigate the intended routes, but steep cliffs block them.
- Both starts have comparable access to resources.
- Oil derricks can be captured and change ownership.
- Supply collection and delivery update the player economy.
- Test in the actual RTS camera and include screenshots plus the files changed.
- Preserve existing gameplay and assets; do not replace working systems without
  explaining the reason and impact.