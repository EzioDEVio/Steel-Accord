# B1.5 — Zagros Basin map + Iran (second nation)

Status: playable in the Windows build; automated acceptance passes on Linux and on the Windows export under Wine.
All gameplay values are PROVISIONAL.

## What is playable
- **Map choice and nations** in the Skirmish menu: Proving Ground (flat) or Zagros Basin; United States or Iran for
  each side (`Game.settings.map`, `nation0`, `nation1`).
- **Zagros Basin** (fictional sector; synthetic relief — see `docs/MAP_ZAGROS_BASIN.md`): 1200 × 1200 m heightfield,
  ridges/cliffs/passes, roads, 936 props, 7 supply piles, 4 capturable oil derricks, two point-symmetric starts.
- **Iran**: own 3D infantry (rifleman, RPG, MG, medic, sniper, engineer, IRGC Special Forces, paratrooper) with the
  U.S. rig and animations; deterministic grooming mix (full beard / moustache / clean-shaven by unit id; IRGC bearded);
  Iranian flag at the Command Center and on captured derricks. AI plays Iran with its own roster.
- U.S. aircraft keep their national stars (user direction).

## Engine changes
| Area | Files |
|---|---|
| Heightfield terrain (R16 + splat + roads, chunked mesh, flatten, ray-march picking) | `scripts/terrain_map.gd`, `shaders/terrain_map.gdshader`, ADR `docs/adr/ADR-0008-terrain-heightfield.md` |
| Map-driven bounds / fog size / starts / piles / props (MultiMesh) / derricks | `scripts/battle.gd` |
| Per-class navigation (slope limits + material costs; cliffs solid) | `scripts/grid_nav.gd` (`apply_terrain`, `path_cost`) |
| Grounding: units, structures (footprint levelled), props, piles, crates, bombs, shells, debris; vehicle tilt | `scripts/battle.gd`, `scripts/unit.gd` |
| Placement: rejects ground steeper than `building_max_slope_deg` | `battle.placement_problem` |
| Terrain speed (material cost and slope per class) | `battle.terrain_speed_mult`, `unit._steer_to` |
| Camera follows terrain; picking on terrain | `scripts/rts_camera.gd`, `scripts/commander.gd` |
| Minimap hill-shade, derrick markers | `scripts/hud.gd` |
| Nations, Iranian unit defs, AI mixes per nation | `scripts/nations.gd`, `scripts/unit_defs.gd`, `scripts/base_ai.gd`, `scripts/econ_panel.gd`, `scripts/building.gd` |
| Menu | `scripts/main_menu.gd`, `scripts/game.gd` |
| Export includes `*.r16`; splat imported as Image | `export_presets.cfg`, `maps/zagros_basin/splat.png.import` |
| Tests / review | `scripts/autotest_map.gd` (`maptest`), `scripts/mapshots.gd` (`mapshots`) |

## Acceptance (maptest, Zagros Basin, AI = Iran) — Linux 21/21, Windows export under Wine 21/21 (identical numbers)
map loads (2.5–3 s incl. nav bake) · units / structures / props / sites grounded (0.000 m) · routes for infantry,
wheeled, tracked · cliffs blocked · wheeled > tracked > infantry impassable cells · fairness: equal piles/cash/derricks,
A* travel cost to own sites within 0.1 % · steep placement rejected · flat placement levelled · derrick capture (9 s),
income, ownership change · CH-47 supply delivery · Abrams drives on terrain with tilt · AI builds 9 grounded
structures, captures derricks, trains Iranian infantry with mixed grooming · Iranian flag.

Regression: QA (noai) 24/24, base 18/18, army 22/22 on Linux.

## Screenshots (in-game, RTS camera, Godot Forward+ on a software renderer)
`docs/screens/b15_zb_*.png` — bases, Iranian infantry, tank column in the central pass, ridges, overview, derricks.

## Known limits / open items
- Iran vehicles and aircraft wait for the Iran art pack (the zip received was the U.S. airlift pack again). War
  Factory uses shared placeholder vehicles; the Iranian Airfield offers nothing yet; CH-47 hauler shared.
- String-pulled routes can differ ~10 % in length between the two sides (A* tie-breaking); travel cost is equal.
- Flags are simplified; the Iranian medic has no protective emblem (needs an approved design).
- Terrain has no LOD; maps are authored by `tools/map/gen_zagros_basin.py`, not in an editor.
