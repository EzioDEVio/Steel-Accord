# B2 — standalone vertical slice, plus fixes from the client's playtest (brief 11)

Environment: Linux container, Godot 4.5.1 (headless and software-rendered). The Windows export was run under Wine, which is not a real Windows PC. Performance numbers below come from a 2-CPU container shared with other jobs: compare them with each other, not with your PC.

## B2 gate checklist

| B2 requirement | Status | Evidence |
|---|---|---|
| Separate clean installation | Done (Wine) | `docs/B2_STANDALONE_AUDIT.md`: the clean folder holds only `SteelAccord.exe`; the traced run opened nothing outside it except Wine/system files and user data; no EA/Steam path touched |
| Only our licensed / shipped content | **Not met** | Only 24 of 503 shipped assets are marked shippable in a manifest. 302 are dev-only (mainly the U.S. art projected from the client-supplied AI concept sheets, and audio clips whose sources still need recording), and 177 have no manifest entry yet. See the audit's blocker list |
| Two playable factions | Done | USA and Iran |
| One original map | Done | Zagros Basin (plus the flat Proving Ground) |
| Economy, construction | Done | QA / base suites |
| Three combat roles per faction | Done | Infantry, armour, air (and anti-armour infantry) for both |
| Victory / defeat | Done | `AB: victory_when_enemy_destroyed`; civilian buildings never count |
| One functional AI | Done | Builds, earns, scouts, remembers what it has seen, attacks, defends, retreats, occupies buildings; can win and lose |
| Save / load | Done | See below |
| Recorded human-vs-AI match | Not done here | Needs a person at a PC; automated runs only |

## Save and load (new)

- **Where:** pause menu (Save Game, Load Game), main menu (Load Game), F5 quick save, F9 quick load. Files go in `user://saves/*.sav` (on Windows: `%APPDATA%\Godot\app_userdata\Steel Accord\saves`).
- **What is saved:** every unit and structure with its orders, path, target, health, veterancy, ammunition, pad, taxi state and hauler state, plus passengers and occupants. Also production queues, research, battle plans, cash, income history, power-up cooldowns, the fog of war, derricks, supply piles, rubble, terrain levelled by construction, the AI's state, control groups and the camera.
- **Not saved:** shots, bombs and support aircraft that are in the air at that moment.
- **Implementation:** `scripts/save_game.gd`. Unit ids are preserved, so every cross-reference survives. Unit ids are now never reused; before, boarding could cause duplicate ids.
- **Tests:**
  - `AB: save_writes_and_reads`, `load_restores_state` (identical fingerprint), `load_restores_links` (transport passengers, group 4, a unit's move goal, the CC still blocking pathing) and `play_continues_after_load`.
  - `AM: garrison_survives_save_load`.
  - **End to end:** a second launch loads the QA save from the main menu into a fresh match and compares fingerprints: `LOADTEST true … differences: none`, `RESULT 1/1`.

## Playtest findings (brief 11)

| Finding | Fix | Evidence |
|---|---|---|
| Game slow and sluggish | Removed multi-second hitches from path smoothing (quadratic → linear), AI site search and footprint checks (read the grids directly). Unit spacing now uses a spatial hash instead of all pairs, and idle target scans are staggered. Added a **Graphics quality** option (Low/Medium/High; the old fixed setup is High; the default is now Medium) and an **FPS counter** (Options) | Profiler (`prof` argument), same base match on Zagros. Worst physics frame in the opening: 4,311 ms → 285 ms. Mean simulation cost 8.2 → 5.1 ms/tick. Separation at 41 units 5.6 → 1.6 ms/tick. Your GPU cost cannot be measured here; please try Medium/Low and report the FPS shown |
| Aircraft fly through hills | Aircraft and support flights look 3 s ahead along their path, climb early (jets 45 m/s, helicopters 22 m/s), descend slowly, and never go below the ground under them | `AM: aircraft_clear_terrain`: over the highest (80 m) ridge, lowest clearance AH-64 9 m, F-16 16 m |
| Map looks like repeated parcels | Terrain shader anti-tiling (specialist pass) | `docs/TERRAIN_TILING.md`, `docs/screens/terrain_before_*` / `terrain_after_*` |
| Map needs buildings, centres, hospitals; troops occupy them; hospitals heal | 5 original civilian building types. Zagros has 21 of them: 14 village houses, 4 apartment blocks, 2 civic centres and 1 contested hospital in the basin. Infantry enter them (click the building); occupants fire from the windows with +15% range and can't be shot. The building changes side while occupied and goes back to neutral when empty. When it is destroyed the occupants get out at half health. The hospital heals 3%/s. The panel shows an occupant tile for each soldier and Evacuate (D) | `AM: civic_buildings_placed`, `garrison_enter`, `garrison_fires_from_inside`, `hospital_heals` (36 → 74 health in 10 s), `garrison_ejected_when_destroyed`; models in `docs/screens/civic_models_sheet.png` |
| Jets taxi through the hangar | Jets follow the taxiway: pad → lane between the pad columns → runway → backtrack to the take-off end → take off. After landing they reverse the route. The airfield did not need enlarging | `AB: jet_taxi_avoids_hangar`: 0 ground positions inside the hangar/tower block during take-off and landing |

## AI (B2)

- **Knowledge:** it targets only enemy structures its units have seen (remembered) and enemy units in sight now. Before, it knew everything.
- **Scouting:** every ~75 s a fast unit drives past your base, the derricks and the map centre. Test: `AB: ai_scouts_and_remembers`.
- **Retreat:** attackers below 30% health fall back to the War Factory or the base. A wave that loses more than 60% is called off and the next wave is two units bigger. Test: `AB: ai_retreats_when_hurt`.
- **Garrisons:** it occupies civilian buildings near its base with spare infantry.

## Test results (Linux)

QA 41/41, base 19/19, army 22/22, map 31/31, end-to-end load 1/1. Wine results for the B2 build are in the build notes.

## Open items and risks

- **Licensing:** most of the art and audio is not cleared for release (the audit's blocker list). This is the main thing B2 still needs, and the decisions are yours. Do we commission or produce replacement U.S. art? Can you provide the sources for the audio clips and the Farsi shout?
- **Shutdown crash under Wine:** the exported exe crashed on exit after the test finished (page fault). It is not seen on Linux, and it is unknown whether it happens on Windows.
- **No human-vs-AI recording yet.**
- **Performance on your GPU is unmeasured;** use the FPS counter.
