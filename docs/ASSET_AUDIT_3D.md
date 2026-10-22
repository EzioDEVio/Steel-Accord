# Asset presentation audit - 2026-10-22 (after the B1.2 playtest QA report)

**Legend:**
- **3D** = real modelled geometry (GLB) that keeps its depth from every camera angle.
- **Card** = concept-art image on a camera-facing quad.
- **Flat sprite** = top-down image on a horizontal quad.

## Converted in this pass (3D pilot set)

| Asset | Now | Moving parts / animation | Grounding | Evidence |
|---|---|---|---|---|
| Supply Depot | 3D (`assets/units3d/supply_depot`) | Construction: the model rises behind a world-space scaffold line (`shaders/build_reveal.gdshader`) | Origin at the foundation; real cast shadows | docs/screens/pilot3d_depot_*, b13_p01_orbit_yaw*, b13_p04/p05 |
| M88 Dozer | 3D (`assets/units3d/m88`) | 12 road wheels plus sprockets and idlers turn with distance travelled; track UVs scroll (0.957 m per tile) | Origin at track contact; real shadows; team ring | pilot3d_m88_*, b13_p08/p09; test `dozer_wheels_and_tracks_animate` |
| CH-47 | 3D (`assets/units3d/ch47`) | Two counter-rotating 3-blade rotors (real blade geometry) | Gear at ground when landed | pilot3d_ch47_*, b13_p06/p07/p12 |
| Rifleman | 3D, skinned, 17-bone humanoid (`assets/units3d/rifleman`) | idle / walk / run / aim / fire / crouch_fire / die; walk and run playback matched to ground speed | Feet at Y = 0; team-coloured patches | pilot3d_rifleman_*, b13_p10/p11; test `rifleman_animation_states` |

## Still not converted (planned order)

| Asset | Current form | Why it is still like this | Next step |
|---|---|---|---|
| Vanguard MBT | 3D (original model, G1) | Already 3D | Re-texture toward the U.S. pack style |
| Command Center, Barracks, Power Plant, War Factory, Airfield, Defense Tower, HESCO, Radar | Card (concept art) | Pilot pipeline only proven on the Depot today | Batch 1 (same pipeline as the Depot, docs/PILOT3D_STRUCTURES.md) |
| HMMWV .50, Avenger, Abrams family, other vehicles | Card with 3 views + mirror | Waiting for pilot approval | Batch 2 (M88 pipeline: silhouette hull + projected concept textures) |
| AT4 gunner and the other 10 personnel roles | Card poses | Waiting for pilot approval | Batch 3 (reuse the rifleman rig and animations; per-role gear and weapons) |
| F-16, F/A-18, F-22, A-10, AH-64, UH-60 | Flat top-down sprite (AH-64 / UH-60 rotors spin) | Waiting for pilot approval | Batch 2 (CH-47 pipeline) |
| B-52, B-1, B-2, SR-71 (support powers) | Flat top-down sprite at high altitude | Seen only from above in a fly-over | Last |
| Supply piles, rubble | Simple 3D boxes | Placeholder | With batch 1 |

**Deliberate 2D (correct use):** HUD icons, portraits, minimap symbols, the placement footprint, selection rings and team rings.

## Scale
All classes follow `docs/SCALE_GUIDE.md`, checked in-game by `scale_ch47_vs_depot`. Captures b13_p07 and b13_p04 show a CH-47 beside the Depot.

## Known issues in the pilot set
- The M88 is a little wider than the real vehicle, and the concept art's painted lighting is baked into the texture.
- The CH-47 texture still carries the U.S. roundel from the concept art. It needs a decision for the fictional setting.
- The rifleman is low-poly and boxy at close zoom; it has a single death direction and no prone pose.
- The construction scaffold is a generic lattice, not modelled scaffolding.
