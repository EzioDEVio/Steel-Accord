# Steel Accord: request tracker (all client requests)

Audit date: 2026-10-22. Source tree: `/home/claude/pzh` at commit `4af01ac` (Godot 4.5.1, game code in `godot/scripts`). This audit was read-only. I checked each status against the code, docs, test scripts and the latest test result files. I did not take the lead's summary on trust.

**Statuses**
- **Done**: implemented and covered by an automated test or an in-game screenshot.
- **Partial**: some of it works. The evidence column says what is missing.
- **Not started**: no code or doc found.
- **Deferred by design**: the brief itself says to wait until a supporting system exists, or the lead deferred it and gave a reason.
- **Superseded**: replaced by a later decision. The main one is ADR-0007, which moved the game from the Zero Hour fork to Godot 4.

**Evidence abbreviations**
- `AB:` = `godot/scripts/autotest_base.gd`. Latest run, QA scenario: 35/35 (`scratchpad/qa/basetest_results.txt`). Base scenario: 18/18 (`/home/claude/sa/bt.log`).
- `AT:` = `godot/scripts/autotest.gd`, the army suite: 22/22 (`/home/claude/sa/at.log`, Windows export under Wine: `wat.log`).
- `AM:` = `godot/scripts/autotest_map.gd`, the map test: 24/24 on the Windows export under Wine (`scratchpad/wmt/basetest_results.txt`).
- `scr:` = `docs/screens/`.

Windows runs were made under Wine, never on a real Windows PC. In-game screenshots come from Godot running on a software renderer (llvmpipe).

**Cross-cutting findings found during the audit** (cited in the rows below):
- (F1) The documents `README.md`, `docs/TASKBOARD.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` and `docs/ECONOMY_SPEC.md` still describe the Zero Hour fork.
- (F2) Fixed after the audit: the main menu read "Development build B1.2" and the skirmish screen said Iran's vehicles were placeholders.
- (F3) The AI's damage is multiplied by difficulty (×0.8 Easy, ×1.15 Hard). Since the audit the difficulty tooltip on the Skirmish screen states it.
- (F4) Fixed after the audit: `docs/M4_TRANSPORT.md` now exists, and losing a loaded transport tells the player how many passengers died.
- (F5) `docs/ASSET_AUDIT_3D.md` is stale. It still lists structures, vehicles and aircraft as "cards", but M1–M3 replaced those with 3D models.
- (F6) There is no B1.6 report doc and no in-game screenshots of the Inspector or the Iranian vehicles in `docs/screens`. The only evidence for them is automated tests.
- (F7) There is no game save/load. `game.gd` saves only `settings.json`.
- (F8) Any infantry unit can capture a derrick by standing next to it. Brief 07 says capture should not be granted silently to every soldier.

---

## 01: Master prompt / project description

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Lead a team of specialist agents; inspect and run their work instead of trusting claims | Partial | Art agents produced the Iran/M2 models (e.g. `docs/IRAN_VEHICLES_WAVE1.md`), and the lead verified them through tests (`AM: iran_roster_models`). TASKBOARD.md has not been updated since 2026-10-21 (F1) |
| 2 | Original standalone title with its own name, not EA's | Done | Title "Steel Accord" (`main_menu.gd:29`); scr:`g13_main_menu.png` |
| 3 | Nine playable sides; any can be player, ally or AI in skirmish | Partial | Only USA and Iran exist (`nations.gd`). Matches are 1v1 only: no allies or teams |
| 4 | Fictional setting; no nation made the villain | Done | `nations.gd` header; GAME_DESIGN.md opening section and §4 |
| 5 | Command Center and builders | Done | `AB: dozer_constructs`, `start_state` |
| 6 | Resources and logistics | Done | `AB: supply_income`; `AM: supply_delivery` |
| 7 | Construction and power | Done | `AB: place_power_plant`, `low_power_state` |
| 8 | Production queues | Done | `AB: queue_units`, `cancel_refund` |
| 9 | Infantry, vehicles and aircraft with counterplay | Done | `AB: roster_spawns_with_models`, `counter_matrix` |
| 10 | Fog of war and scouting | Done | `AT: fog_of_war`. Radar puts enemy units on the minimap (`hud.gd:388`) |
| 11 | Selection box, right-click, control groups, attack-move, hotkeys, camera, minimap | Done | `AT: box_select`, `control_group`, `command_card_attack_move`, `right_drag_scroll`. Minimap click jumps the camera (`hud.gd:242`) |
| 12 | Tech, upgrades, veterancy and support powers | Done | `AB: research_starts`, `veterancy_promotion`; `AT: support_power_carpet`, `support_power_b1` |
| 13 | Skirmish against computer enemies | Done | `AB: ai_attacks`, `victory_when_enemy_destroyed` |
| 14 | Saves | Not started | F7 |
| 15 | Replays | Partial | Commands are logged with their tick number (`AT: command_log`). No replay playback or replay file exists |
| 16 | Eventual competitive multiplayer | Not started | Planned for B5 |
| 17 | Original faction asymmetries | Partial | Iran has its own roster and powers (Shahed strike). It shares all U.S. structures and the U.S. tech tree |
| 18 | Modern, legible interface | Partial | HUD, Inspector and UI scale option exist (`hud.gd`, `inspector.gd`, `ui_kit.gd`). No key remapping and no colour-blind options |
| 19 | Do not copy EA logos, voices, textures, maps, art, music, UI or story | Done | Art is generated by scripts (`tools/art/*.py`); audio is from Pixabay (`content/manifest/audio.json`); credits screen (`main_menu.gd:125-140`) |
| 20 | Use the mechanics brief, but audit its claims against source and manual | Partial | `docs/MECHANICS_REFERENCE_AUDIT.md` exists; it says "Manual not yet cross-checked" |
| 21 | Cash is the spendable resource; power is a separate capacity | Done | `upgrades.gd`/`building_defs.gd` power fields; `AB: low_power_slows_production` |
| 22 | Keep active supply gathering separate from secondary income | Done | CH-47 hauling vs derricks and the Drop Zone: `AM: derrick_income`, `AB: supply_drop_zone_income` |
| 23 | Keep rank-earned support powers separate from constructed superweapons | Partial | Support powers are cooldown cards gated by nation and buildings. There is no commander rank and no superweapon |
| 24 | Do not assume ECS, snap grid, flow fields or rollback | Done | Grid A* (`grid_nav.gd`), no ECS, free placement with footprint checks |
| 25 | Check access to the Windows PC first; never fake a Windows build | Done | RECON.md §1. B1.5 report says "Windows export under Wine", not a real PC |
| 26 | Product branch of the modernized fork with a pinned commit | Superseded | ADR-0007 (Godot); the fork was pinned at `8154df9028e8` before the switch (ADR-0001) |
| 27 | Do not modify the Steam install; keep the known-good test copy | Done | This environment has no access to either. Nothing has been touched |
| 28 | Keep GPL/EA notices and mark modified engine code | Superseded | ADR-0007: no EA code in the Godot game. The Godot MIT licence is credited (`main_menu.gd:131`) |
| 29 | Keep private experiments separate from a distributable built from our own assets | Partial | The Godot export contains no EA data by construction. No clean-folder audit of loaded files has been done |
| 30 | Asset manifest: origin, creator, tool/prompt, edit history, licence, shipping status | Partial | `content/manifest/audio.json`, `us_packs.json`, `aircraft.json`, plus per-model `*_report.json` and generating scripts. No single manifest covers the 3D models or Iranian art. Audio still needs per-item Pixabay URLs before release |
| 31 | Do not clone actors' voices or imitate existing scores | Done | No voice clones and no music. The only voice is the client's Farsi clip, with provenance in `audio.json` |
| 32 | Write an ADR with evidence before a major engine change; wait for approval | Done | `docs/adr/ADR-0007-engine-godot4.md` "Accepted by client" |
| 33 | Keep a task board and a decision log | Partial | Both exist but have not been updated since 2026-10-21 (F1) |
| 34 | RECON.md with evidence, risks, paths and missing inputs | Superseded | `docs/RECON.md` was done for the Zero Hour fork |
| 35 | List the Steam assets the test copy still uses | Superseded | RECON.md §6 (Zero Hour only) |
| 36 | ARCHITECTURE.md plus ADRs: branch, content separation, manifest, pipeline, UI/render, fixed step, AI, save/replay, multiplayer | Partial | ADR-0001..0006 cover Zero Hour; ADR-0007/0008 cover Godot. ARCHITECTURE.md has not been rewritten for Godot (F1) |
| 37 | Define how a clean Windows folder boots without Steam archives | Partial | `build/win/SteelAccord.exe` is a single self-contained export. It has not been tested on a clean real Windows PC, and there is no list of loaded files |
| 38 | Dependency graph and milestone gates | Partial | ARCHITECTURE.md §6 (Zero Hour era) |
| 39 | Don't claim texture upscaling modernizes the renderer | Done | ARCHITECTURE.md §5; ADR-0007 |
| 40 | Pin build dependencies and document repeatable build steps | Partial | Godot 4.5.1 and Blender bpy 5.2 are named in ADR-0007. The Godot export command is not documented; README build steps are for Zero Hour |
| 41 | GAME_DESIGN.md | Partial | `docs/GAME_DESIGN.md` v0.1 still describes Kestrel, USA vs China and Harbor Divide |
| 42 | Nine faction sheets | Partial | One line per side (GAME_DESIGN §4). No full sheets (`docs/factions/` does not exist) |
| 43 | Unit/building counter matrix | Partial | `AB: counter_matrix` and `UnitDefs.ARMOR_MULT` exist; no matrix document |
| 44 | Map specs for five biomes (coastal industrial, dense city, mountain pass, island coast, open) | Partial | The biomes are listed. Only Zagros Basin (mountain/basin) is built: `docs/MAP_ZAGROS_BASIN.md` |
| 45 | Harbor Divide as the first map | Superseded | Built only as a Zero Hour map (`maps/PZ_HarborDivide`, `build/reports/harbordivide_fairness.txt`). Replaced in Godot by Zagros Basin (brief 08) |
| 46 | First two playable sides USA and China | Superseded | The client chose Iran as the second nation (briefs 08/09). China is not started |
| 47 | UI flow and wireframes | Partial | GAME_DESIGN §6 is text only. The implemented menus are the real flow |
| 48 | Original art and audio briefs | Done | GAME_DESIGN §7; `docs/ASSET_GENERATION_README.md` |
| 49 | Acceptance criteria per gate | Done | GAME_DESIGN §8 (Zero Hour-era wording) |
| 50 | At least one inspectable visual design and a map blockout before final art | Done | scr:`pilot3d_*`, `map_zagros_overview.png`, `map_zagros_routes.png` |
| 51 | B1: original menu, test map, building and unit; unit produced, selected, moved, attacks, destroyed | Done | In Godot: scr:`g13_main_menu.png`, `godot_vanguard_*`; `AB: vehicles_produced`; `AT: box_select`, `left_click_move`, `match_end` |
| 52 | B2: separate clean install containing only our content | Partial | No EA data is shipped. A clean-folder file audit has not been done |
| 53 | B2: two playable factions | Partial | USA and Iran are playable. Iran uses U.S. structures; its Avenger/Paladin are placeholders |
| 54 | B2: one original map | Done | Zagros Basin, `AM: map_loads` |
| 55 | B2: economy and construction | Done | `AB: supply_income`, `dozer_constructs` |
| 56 | B2: three combat roles per faction | Done | Both nations have infantry, armour and aircraft (`AM: iran_roster_models`, `AB: roster_spawns_with_models`) |
| 57 | B2: victory/defeat | Done | `AB: victory_when_enemy_destroyed`; scr:`g13_ui_04_end_screen.png` |
| 58 | B2: one functional AI | Done | `AB: ai_builds_and_earns`, `ai_attacks`; `AM: ai_builds_on_terrain` |
| 59 | B2: save/load | Not started | F7 |
| 60 | B3: modernize visual presentation and audio | Partial | 3D models and Pixabay audio are in. No music, no UI sound set, no LODs |
| 61 | B4: remaining sides and maps in tested batches | Partial | Iran is added. Five more sides plus China are missing, and four more maps |
| 62 | B5: multiplayer, spectator/replay, packaging, release checks | Not started | Planned |
| 63 | At each gate: files, build command, environment, logs, screenshots, defects, next ticket | Partial | Gate reports exist: `docs/B1_2_BASE_LOOP.md`, `docs/B1_5_ZAGROS_IRAN.md`, `build/win/README_PLAYTEST.txt`. No B1.6 report (F6) |
| 64 | Proof that the AI gathers, builds, produces, attacks, defends and can win or lose | Partial | Gathering, building, attacking and losing are tested. Defending exists in code (`base_ai.gd:136`) but is untested. An AI win is not tested |
| 65 | Network claims need two separate clients with content hashes | Deferred by design | Multiplayer is held for B5 |
| 66 | B1.1 ticket: Kestrel unit and test map on the Zero Hour engine | Superseded | The kit was built and the client confirmed the map loads. The Kestrel loop was never reported. Replaced by Godot (ADR-0007) |
| 67 | Tell the client when a new unit/map will be on screen | Done | Historical. B1.x builds have been delivered (`build/SteelAccord_*_win64.zip`) |
| 68 | No paid API calls | Done | ADR-0007 "No paid generation services" |
| 69 | No public push, tag, upload or distribution without approval | Done | The client approved pushing to `github.com/EzioDEVio/Steel-Accord`; no tag, public release or upload has been made |
| 70 | No fake buttons or mock menus | Partial | No dead buttons found. Two menu labels are stale (F2) |
| 71 | Engine/platform role: packaging, renderer/UI scaling, save/replay, determinism | Partial | Fixed 30 Hz tick, command log and UI scale exist. Save/replay and a packaging audit are missing |
| 72 | Gameplay systems role: input, commands, economy, production, power, tech, roles, weapons, victory, schemas | Done | `battle.gd`, `unit_defs.gd`, `building_defs.gd`, `upgrades.gd`; AB/AT suites |
| 73 | Faction/balance role: sheets, tech trees, cost/time/counter matrix, matchup tests | Partial | Values are marked PROVISIONAL. No matchup or AI-vs-AI win-rate tests |
| 74 | Map/world role: terrain, routes, elevation, chokepoints, fairness, pathfinding checks | Done | `AM: routes_passable`, `cliffs_block`, `starts_fair` |
| 75 | Visual concept role: art direction, silhouettes, icons, menu art, HUD | Partial | Uses client concept packs and icons. No original loading/menu artwork |
| 76 | 3D tech-art role: materials, meshes, rigs, animation, LODs, budgets, in-game checks | Partial | 68 models load (`AB: all_models_load`). No LODs |
| 77 | Audio role: UI sounds, effects, ambience, music, mixing/looping, licensed voice | Partial | 14 effect clips. No music, no UI sounds, no ambience, no voice acknowledgements |
| 78 | AI role: deterministic build orders, scouting, economy, attack/retreat, per-faction, difficulty tests | Partial | Per-nation unit mixes exist (`base_ai.gd`). No scouting, no retreat, no difficulty tests |
| 79 | UI/UX role: scalable menus, command panel, minimap, production, tooltips, accessibility, remapping, resolution tests | Partial | Remapping, accessibility options and resolution tests are missing |
| 80 | QA role: clean builds, smoke tests, reference validator, save/replay tests, benchmarks, licence audit, package, desync | Partial | Smoke suites exist. `tools/validate_content.py` covers Zero Hour only. Save/replay tests, licence audit and benchmarks are missing |

## 02: Prompts 2–10 (Recon, Architect, Build follow-ups and mechanics addendum)

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | P2: deeper recon (source map, asset inventory, legal boundary, build commands, risk-ranked ticket; mark facts O/I/U) | Superseded | RECON.md (Zero Hour, with [O] tags) |
| 2 | P3: folder structure, content schema, manifest, reference validator, export pipeline, startup without EA archives | Partial | Godot data lives in `*_defs.gd`. The reference validator is Zero Hour only; Godot has only the `all_models_load` test |
| 3 | P3: AI command boundary and fixed-step simulation | Done | `battle.gd` issue/_execute at 30 Hz; `base_ai.gd:2` uses `Battle.issue()`; `AT: command_log` |
| 4 | P3: interface contract and integration owner for every agent | Partial | Zero Hour-era TASKBOARD.md only |
| 5 | P3: ADRs on the old renderer and multiplayer limits | Done | ADR-0004, ADR-0005, ADR-0007 |
| 6 | P3: present measured evidence and wait for approval before switching engines | Done | ADR-0007, accepted by the client |
| 7 | P4: nine faction sheets (economy, builder, power, tech, silhouettes, counters, support, AI, audio/visual identity) | Partial | Same as 01-#42 |
| 8 | P4: shared rules and counter matrix | Partial | Same as 01-#43 |
| 9 | P4: Harbor Divide design with starts, supplies, routes, pathfinding checks | Superseded | Same as 01-#45 |
| 10 | P4: integrate one unit, one building, one map and a readable HUD/menu for B1 | Done | Same as 01-#51 |
| 11 | P4: don't pass generated images off as engine-ready assets | Done | Concepts were rebuilt as GLB models (`docs/PILOT3D_*.md`, M1–M3 docs) |
| 12 | P5: original unit on an original map in the running engine, with provenance, defs, validation, screenshot | Done | Same as 01-#51. Zero Hour version superseded |
| 13 | P6: boot in a clean Windows folder and finish human-vs-AI using only our content | Partial | Wine run only; no list of loaded files; no recorded human match |
| 14 | P6: check both factions' economy, build order, counterplay, pathing, UI, save/load, victory, manifest, licences | Partial | Save/load is missing; release licence review is pending |
| 15 | P6: show the AI scouting, building, producing, attacking and responding to losses | Partial | `base_ai.gd` has no scouting or loss response; building and attacking are tested |
| 16 | P6: propose the next batch of factions and maps | Not started | No proposal doc found |
| 17 | P6: evidence table (requirement, observation, file/log, result, next fix) | Partial | This tracker covers part of it; it does not record per-requirement observations |
| 18 | P6: keep multiplayer gated until two-client, hash, replay and desync tests | Deferred by design | Held for B5 |
| 19 | P7: MECHANICS_REFERENCE_AUDIT.md with the requested columns | Partial | Columns are present; the manual has not been cross-checked |
| 20 | P7: correct the brief's distinctions (3+9 armies, cash vs power, gatherers, Particle Cannon, three progression tracks, no required sidebar, no flow fields) | Done | Rows of MECHANICS_REFERENCE_AUDIT.md |
| 21 | P7: classify features as B1 / B2 / later competitive / optional | Done | Phase column of the audit |
| 22 | P8: one spendable credit balance | Done | `battle.cash`; `spend()` |
| 23 | P8: finite, contestable deposits | Done | Pile stock (`AM: starts_fair` "$40000"); inspector shows stock |
| 24 | P8: active gatherers that travel and can be intercepted | Done | CH-47 is a killable unit (`AM: supply_delivery`). No dedicated interception test |
| 25 | P8: optional faction-specific secondary income | Partial | Derricks and the Drop Zone exist but are shared by both nations |
| 26 | P8: neutral capturable economic sites | Done | `AM: derrick_capture`, `derrick_changes_owner` |
| 27 | P8: builder construction, production costs/times, power cap | Done | `building_defs.gd`; AB suite |
| 28 | P8: economy spec with units, formulas, rounding and fixed-step behaviour | Partial | `docs/ECONOMY_SPEC.md` v0.1 uses Zero Hour units and values that don't match the Godot game (F1) |
| 29 | P8: rules for raiding, denying, rebuilding and recapturing income sources | Partial | Derrick recapture and structure rebuild work. Derrick destruction and denial rules are not documented |
| 30 | P8: each faction's economic advantage and counterplay | Not started | The spec covers only USA/China (Zero Hour era). No USA/Iran economic difference |
| 31 | P8: mirrored starts with comparable travel to deposits | Done | `AM: starts_fair` (0.1 %) |
| 32 | P8: minimal B2 economy: gather, spend, lose and replace gatherers, contest a neutral, recover from a depleted node | Partial | Gather, spend, contest and replace work. Recovery from a depleted start node is not tested |
| 33 | P8: measure credit conservation, build orders, replacement time, income curve, snowball risk | Not started | No measurement table |
| 34 | P8: expand the other seven sides only after the two-side economy plays | Done | Followed; only two sides so far |
| 35 | P9: weapons, damage tags and armour classes in data | Done | `unit_defs.gd` weapons; `battle._armor_mult` |
| 36 | P9: projectile travel and splash | Done | Arcing artillery shells, `AB: artillery_range_rules` |
| 37 | P9: target priority, sight/fog, movement, pathfinding | Partial | Fog and pathfinding are tested. Target priority rules are not documented or tested |
| 38 | P9: unit veterancy | Done | `veterancy.gd`; `AB: veterancy_promotion` |
| 39 | P9: separate commander rank/ability tree | Not started | — |
| 40 | P9: upgrades researched at buildings | Done | `upgrades.gd`; `AB: research_starts` |
| 41 | P9: optional late-game constructed superweapons | Deferred by design | The brief marks them optional; not built |
| 42 | P9: explicit timing/range/cost/cooldown/damage rules with data validation, no hidden constants | Partial | Values live in defs, but there is no validator. Some constants sit in code (`building.gd` REPAIR_RATE, `game.gd` DIFFICULTY) |
| 43 | P9: first roster shows infantry, vehicle and anti-air counterplay | Done | `AB: counter_matrix` |
| 44 | P9: garrison occupancy and combat rules | Not started | No garrison code |
| 45 | P9: capturable neutral structures | Done | Derricks (see F8) |
| 46 | P9: elevation, chokepoints, alternative routes | Done | Zagros Basin's three passes; `AM: routes_passable` |
| 47 | P9: destructible/repairable bridges only where pathing supports them | Deferred by design | The map has no bridges |
| 48 | P9: destructible cover, props and hazard zones | Not started | Props are static |
| 49 | P9: readable visual/audio cue for selection, impacts, veterancy changes, abilities | Partial | Chevrons (`hud.gd`), "promoted to" message (`battle.gd:736`), FX. No dedicated sound cues for rank-ups or abilities |
| 50 | P9: combat matrix doc, progression table, test scenarios (garrison, cover, elevation sight, cooldown, DoT) | Partial | Only the counter-matrix test exists; no documents |
| 51 | P9: mark unimplemented features as future tickets, not working buttons | Done | Locked states show reasons, e.g. "Requires Advanced Training" (`AB: battle_plans`) |
| 52 | P10: skirmish settings: maps, sides, teams, starting credits, difficulty, victory conditions, AI personalities | Partial | Map, nation and difficulty only (`main_menu.gd`). Cash fixed at $10,000; 1v1; one victory rule; no AI personalities |
| 53 | P10: design a challenge ladder | Not started | — |
| 54 | P10: prepare original campaigns (missions, briefings, triggers, cinematics) | Not started | — |
| 55 | P10: show which systems skirmish, challenges and campaigns share | Not started | — |
| 56 | P10: deterministic AI using the same economy and actions as players | Done | `base_ai.gd:2` uses `Battle.issue()` |
| 57 | P10: disclose scripted or difficulty modifiers | Partial | F3: hidden damage multiplier |
| 58 | P10: local LLM director only later, in single-player | Deferred by design | Not built |
| 59 | P10: multiplayer engineering (hashes, desync, lobbies, reconnect, observers, telemetry, anti-cheat) | Deferred by design | B5. The Zero Hour networking review is superseded |
| 60 | P10: build single-player B2 first | Done | Followed |

## 03: Master handoff (mechanics)

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Nine sides, any as player, ally or AI | Partial | Same as 01-#3 |
| 2 | Fictional tone; Europe as a coalition | Done | GAME_DESIGN §4 (Europe as a modular coalition) |
| 3 | Core loop (CC, builders, logistics, power, queues, combined arms, fog, controls, tech, veterancy, powers, skirmish AI) | Done | Same as 01-#5…#13 |
| 4 | Saves, replays and multiplayer readiness | Not started | Same as 01-#14…#16 |
| 5 | Legal and content boundaries; independently author everything | Partial | Same as 01-#19 and #30 (manifest incomplete) |
| 6 | Don't pretend to run a Windows build | Done | Same as 01-#25 |
| 7 | Ten specialist roles | Partial | Same as 01-#71…#80 |
| 8 | Faction scale: nine country sides rather than generals | Done | `nations.gd` is built for nine; two exist |
| 9 | Dual constraint: one currency plus power capacity | Done | Same as 01-#21 |
| 10 | Logistics: physical gatherers plus separate secondary income | Done | Same as 01-#22 |
| 11 | Superweapons separate from rank powers and veterancy | Partial | Same as 01-#23 |
| 12 | UI layout modern and scalable, not a required right sidebar | Done | Minimap and Inspector bottom-left, production strip top-left, build panel bottom-right (`hud.gd`) |
| 13 | ECS, flow fields, snap grid and rollback are optional proposals | Done | Same as 01-#24 |
| 14 | Verify map objects (bridges, neutrals, garrisons, props) one by one | Partial | Derricks, piles and props are verified (`AM: props_grounded`, `sites_grounded`); no bridges or garrisons exist |
| 15 | RECON, ARCHITECTURE, GAME_DESIGN and MECHANICS_REFERENCE_AUDIT docs | Partial | All exist; ARCHITECTURE and GAME_DESIGN are stale (F1) |
| 16 | B1 first playable content | Done | Same as 01-#51 |
| 17 | B2 standalone slice (USA & China, clean folder, save/load) | Partial | USA & Iran instead; no clean-folder audit; no save/load |
| 18 | B3–B5 | Partial | Same as 01-#60…#62 |
| 19 | Start now: recon, docs, B1.1 test procedure | Superseded | Zero Hour B1.1 test kit (`tests/b1/`) |

## 04: Gameplay, movement, UI and assets prompts

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Engine starting point is the SAGE fork | Superseded | ADR-0007 |
| 2 | Keep the Steam install and test copy intact; pin the commit | Done | Same as 01-#27; the pin is superseded |
| 3 | Inventory the U.S. asset packs actually present | Done | `docs/ASSET_REVIEW_US_PACKS.md`, `content/manifest/us_packs.json`, `qa_us_packs_2026-10-21.json` |
| 4 | Treat 2D packs as concepts; prove the runtime pipeline before batches | Done | Pilot set first (`docs/PILOT3D_*.md`), then M1–M3 |
| 5 | AT4 shown shoulder-fired in art and animation | Done | scr:`m1_inf_at4_anims.png`; `docs/M1_INFANTRY.md` |
| 6 | P1: manifest with stable IDs, source, provenance, licence, edits, runtime path, status | Partial | Same as 01-#30 |
| 7 | P1: no fake UI; no claims without evidence | Partial | Same as 01-#70 (F2) |
| 8 | P1: match loop (pick faction and map → base → scout → upgrades/abilities → win) | Done | Skirmish menu and AB/AM suites |
| 9 | P2: trace startup, data, GUI, maps, audio, AI, save/replay, network | Superseded | Zero Hour RECON.md |
| 10 | P2: smallest validated pipeline for unit+icon, structure with footprint and construction states, map, sound/UI art | Done | Blender → GLB (`tools/art`), `build_reveal.gdshader`, `tools/map/gen_zagros_basin.py`, `tools/audio` |
| 11 | P2: manifests and missing-reference validation | Partial | Only `AB: all_models_load` (68 models). No Godot reference validator |
| 12 | P3: stable data for factions, starting forces, units, buildings, movement classes, orders | Done | `nations.gd`, `unit_defs.gd`, `building_defs.gd`, `grid_nav.gd` |
| 13 | P3: data for weapons, armour, queues, costs, prerequisites, rally, upgrades, powers, veterancy, maps, victory | Done | `unit_defs.gd`, `upgrades.gd`, `veterancy.gd`, `maps/zagros_basin/map.json` |
| 14 | P3: AI and humans share one command interface | Done | `Battle.issue()` |
| 15 | P3: consistent save and replay; nondeterminism kept off the frame path | Partial | Fixed tick and command log only; F7 |
| 16 | P3: schema examples and a reference validator | Partial | Same as #11 |
| 17 | P4: click-select, drag-select, add/remove modifiers | Done | `AT: box_select`, `select_all`. Shift adds (README_PLAYTEST) |
| 18 | P4: right-click ground to move, enemy to attack, friendly transport to board | Done | `AT: left_click_move` (classic scheme; alternate scheme uses right-click); `AB: board_transport` |
| 19 | P4: move, attack, attack-move, stop, guard orders | Done | `AT: guard_order`, `command_card_attack_move`; stop on S (`commander.gd:89`, untested) |
| 20 | P4: patrol order | Not started | No patrol code |
| 21 | P4: hold-fire order | Not started | — |
| 22 | P4: capture order | Partial | Capture happens by standing next to a derrick; there is no explicit order (F8) |
| 23 | P4: enter/exit transport | Done | `AB: board_transport`, `unload_transport` |
| 24 | P4: garrison | Not started | — |
| 25 | P4: deploy/undeploy where supported | Not started | No deployable units. Correctly, there is no generic Deploy button |
| 26 | P4: repair order | Done | `AB: repair_heals_and_costs` |
| 27 | P4: control groups, shift waypoints, rally points, selection feedback, tooltips | Done | `AT: control_group`, `waypoints`; `AB: rally_point` |
| 28 | P4: formations where practical | Not started | Only scatter (X) exists |
| 29 | P4: configurable hotkeys | Not started | Keys are hard-coded in `commander.gd:80-105` |
| 30 | P4: clear feedback for invalid orders | Done | `hud.flash_message` (e.g. `commander.gd:273,308,352`) |
| 31 | P4: orders respect terrain, obstacles, occupancy, line of sight, fog | Partial | Terrain, slope and fog are respected. Terrain does not block line of sight |
| 32 | P4: infantry states: idle, turn, walk/run, aim, fire, reload, hit-react, suppressed, death, enter/exit | Partial | Idle, walk, run, aim, fire, crouch_fire and die exist (`AB: rifleman_animation_states`). No reload, hit-react, suppression or enter/exit animations |
| 33 | P4: vehicles: acceleration, turning, reverse, spacing, independent turret, damage and destroyed states, repair | Partial | Turrets aim and wheels/tracks animate (`docs/M2_VEHICLES.md`); repair works. No reverse; no damage states verified |
| 34 | P4: TOW, .50 and medical HMMWV as distinct variants with own icons/commands | Done | `hmmwv_tow`, `hmmwv_50cal`, `hmmwv_medical` in `building_defs.gd`; scr:`m2_hmmwv_*_sheet.png` |
| 35 | P4: medical HMMWV is a support unit | Done | Heals infantry (README_PLAYTEST M2) |
| 36 | P4: define which units carry, deploy or garrison; no generic Deploy | Partial | Transports are defined in data (`unit_defs.gd` "transport"); garrison/deploy not defined |
| 37 | P4: evidence and regression tests for select, move, group, attack-move, stop, contextual orders | Partial | AT suite covers these except stop |
| 38 | P5: weapon data: range, damage, cooldown, projectile, targets, effects, sound/VFX | Done | `unit_defs.gd` weapons |
| 39 | P5: fictional armour classes | Done | `UnitDefs.ARMOR_MULT` |
| 40 | P5: target acquisition, line of sight, range, aiming, cooldowns, projectiles, damage feedback, destruction | Done | `AT: f16_missile_strike`, `a10_cannon_fires`; `AB: artillery_range_rules` |
| 41 | P5: role/counter matrix for infantry, AT, vehicles, artillery, air, air defence | Partial | Same as 01-#43 |
| 42 | P5: fairness through cost, time, range, survivability, counters | Partial | Values provisional; no balance runs |
| 43 | P5: consistent fog visibility | Done | `AT: fog_of_war` |
| 44 | P5: validate an attack/damage/counter/destruction loop in a match | Done | `AB: counter_matrix`; `AT: match_end` |
| 45 | P6: show cash separately from power output/use | Done | HUD top centre (`hud.gd:223`); scr:`b12_b02_base_overview.png` |
| 46 | P6: tell apart active collection, stored supply and secondary income | Done | Income/spending trends, pile stock, next drop (`econ_panel.gd`) |
| 47 | P6: supply depot and vehicle loop with limits and feedback | Done | `AB: depot_gives_hauler`, `supply_income` |
| 48 | P6: supply airdrop with cost, cooldown, quantity and landing feedback; not unbounded passive income | Partial | Drop Zone: $2,500 building, $1,000 every 80 s (`building_defs.gd:57`). Income has no cap while the building stands |
| 49 | P6: show costs, income, power changes and insufficient-resource states | Done | `econ_panel.gd` tooltips and disabled reasons |
| 50 | P6: Command Center provides the builder | Done | `building_defs.gd` CC produces dozer |
| 51 | P6: footprint validation on valid terrain, no new snap grid | Done | `AB: placement_rules`; `AM: steep_placement_rejected` |
| 52 | P6: placement preview, valid/invalid state, blocked reason, rotate and cancel | Partial | Rotation is missing; preview and reasons work (scr:`b12_b07`, `b12_b08`) |
| 53 | P6: construction progress, scaffold, completion, interruption | Done | `build_reveal.gdshader`; scr:`b14_m1_construction.png`; `AB: dozer_constructs` |
| 54 | P6: construction queue, prerequisites, repair, sell/cancel with refunds | Done | `AB: sell_refund`, `cancel_refund`; "Requires" tooltips |
| 55 | P6: Corps of Engineers construction yard kept separate from the builder unit | Not started | No construction-yard structure |
| 56 | P6: Barracks infantry, War Factory vehicles, Airfield aircraft; special buildings unlock more | Done | `building_defs.gd` produces lists |
| 57 | P6: queue order, progress, cost, time, cancel/refund, prerequisites, rally, alerts | Done | `AB: queue_units`, `rally_point`; `inspector_building_queue` |
| 58 | P6: reorder queues only if safe | Deferred by design | Not implemented; the brief allows this |
| 59 | P6: distinct structures: CC, Barracks, Depot/Drop Zone, War Factory, Airfield, Radar, Power, Repair Bay, Field Hospital, Gatehouse, HESCO, defences | Partial | 10 kinds (`building_defs.gd:58`). No Repair Bay building (the War Factory repairs), no Field Hospital, no Gatehouse |
| 60 | P6: small base loop with a destroy objective, verified with save/load | Partial | Loop done (AB base 18/18); F7 |
| 61 | P7: aircraft takeoff, travel, attack, return, land, rearm states | Done | `AT: f16_takeoff`, `f16_return_to_pad`, `f16_rearm` |
| 62 | P7: different flight profiles for helicopters and jets | Done | `AT: heli_return_lands_on_pad`; runway takeoff for jets |
| 63 | P7: aircraft move, attack-move, attack and return orders | Done | AT air tests |
| 64 | P7: aircraft patrol and looped routes | Not started | — |
| 65 | P7: edit and display waypoint routes | Partial | Waypoints with lines (`hud.gd`); not editable; no loops |
| 66 | P7: ammunition/rearm rules with remaining capability shown | Done | Inspector ammunition line (`inspector.gd:199`); `AT: f16_rearm` |
| 67 | P7: routes and aircraft state in saves and replays | Not started | F7 |
| 68 | P7: aircraft stay in playable space; never stuck outside | Done | `AB: airfield_pads_on_map`, `aircraft_spawn_on_own_pads` |
| 69 | P7: distinct roles for B-1/B-2/B-52/F-16/F-18/F-22/CH-47/UH-60/AH-64/A-10/SR-71 | Done | Airfield roster plus support powers (`unit_defs.gd` POWERS); scr:`g11_air_*`, `b14_m3_*` |
| 70 | P7: MOAB as a strategic ability with cooldown and warning | Not started | — |
| 71 | P7: Patriot and THAAD as fictional anti-air defences | Not started | — |
| 72 | P7: prove production, route, attack, return, landing/rearm and a defensive response | Done | AT air tests; Defense Tower engages aircraft (`building_defs.gd` desc) |
| 73 | P8: structures with cost, time, footprint, prerequisites, power, role, health | Done | `building_defs.gd` |
| 74 | P8: Construction Yard, Field Hospital, Patriot/THAAD, Gatehouse | Not started | — |
| 75 | P8: HESCO and barriers interact with pathing, placement, fire and sight | Partial | HESCO blocks movement; no cover or sight rules |
| 76 | P8: build preview and reliable placement feedback | Done | Same as #52 (except rotation) |
| 77 | P8: team ownership, damage stages, selection bounds, attack/repair/sell, minimap visibility | Done | Status lights (`building.gd:233`), radar rules (`hud.gd:388`) |
| 78 | P8: Harbor Divide with elevation and sight-blocking checks | Superseded | Zagros Basin replaces it; sight-blocking not checked |
| 79 | P8: validate pathfinding separately for infantry, vehicles and aircraft | Partial | Infantry, wheeled and tracked are tested (`AM: class_slope_rules`). Aircraft fly free |
| 80 | P9: top HUD with cash, power, objectives, status, alerts, menu | Partial | No objectives display |
| 81 | P9: minimap overview, camera jump, indicators, pings | Partial | No map pings |
| 82 | P9: selection panel with identity, portrait, health, count, status, commands | Done | `AB: inspector_unit`, `inspector_group` |
| 83 | P9: contextual command/build panel | Done | `econ_panel.gd`; scr:`b12_b09_production_card.png` |
| 84 | P9: placement ghost, rings, order markers, target cursor, routes, errors | Done | `hud.gd`, `commander.gd` |
| 85 | P9: scaling, contrast, colour-independent team ID, keyboard remap, tooltips | Partial | UI scale and tooltips only |
| 86 | P9: per-selection options (builder, barracks, factory, airfield, combat orders only when valid) | Partial | Patrol, hold-fire, deploy, capture and garrison are missing |
| 87 | P9: support panel with cost/cooldown and targeting | Done | `AT: support_power_carpet` |
| 88 | P9: main menu showing only working items | Partial | Skirmish, Options, Controls, Credits and Exit all work. Label is stale (F2) |
| 89 | P9: match setup: faction, opponent, map, team/start, difficulty | Partial | No team or start-position choice |
| 90 | P9: keyboard and mouse help | Done | Controls screen; F1 help (`hud.gd:482`) |
| 91 | P9: UI tests at target resolutions, long names, full queues, low resources, power loss, alerts, map edges, with recording | Partial | Low power and full apron are tested. No resolution captures, no recording |
| 92 | P10: AI gathers, builds, makes a mixed force, scouts, defends, attacks, reacts to losses, can win/lose | Partial | Same as 01-#64 and 02-#15 |
| 93 | P10: difficulty changes decisions or timing; disclose modifiers; no hidden cheats | Partial | Timing does vary by difficulty; F3 |
| 94 | P10: fog, detection and minimap work the same for player and AI | Partial | Not verified that the AI respects fog (no fog check in `base_ai.gd`) |
| 95 | P10: tech, upgrades, veterancy and rank-earned powers | Partial | No rank-earned powers |
| 96 | P10: victory/defeat per mode | Done | One skirmish mode, `AB: victory_when_enemy_destroyed` |
| 97 | P10: early save/load and replay tests (queues, orders, routes, construction, AI) | Not started | F7 |
| 98 | P10: defer online multiplayer until hash and desync tests exist | Deferred by design | B5 |
| 99 | P11: verify source crops; no contact sheet used as a single unit | Done | `docs/ASSET_REVIEW_US_PACKS.md`, `us_packs.json` |
| 100 | P11: game-ready model, material, rig, animation, icon, effects, audio per asset | Done | M1/M2/M3 docs; `AB: roster_spawns_with_models` |
| 101 | P11: export to a supported format and inspect in-game | Done | GLB; scr:`b14_*` and `m1_*_rts.png` |
| 102 | P11: stable references and provenance in the manifest | Partial | Same as 01-#30 |
| 103 | P11: game data per asset (faction, role, producer, cost, time, health, movement, weapons, upgrades, counters, icon, audio) | Done | `unit_defs.gd`, `building_defs.gd` |
| 104 | P11: UI entries, tooltips, hotkeys, AI use and tests per asset | Partial | No per-unit hotkeys. The AI uses only part of the roster (`base_ai.gd` mixes) |
| 105 | P11: check scale and readability from the game camera, combat, death and minimap | Partial | Only the CH-47 vs Depot scale is tested |
| 106 | P11: expand factions only after USA and China each finish a fair match | Superseded | The client prioritised Iran (briefs 08/09) |
| 107 | P12 B1.1: pin the fork, product branch | Superseded | ADR-0007 |
| 108 | P12 B1.1: unit, icon, defs, test map; prove the loop; validate references; report | Done | Same as 01-#51 |
| 109 | P12 B1.2: CC/builder, supply, power, producer, combat unit, defence, UI; prove the loop and victory | Done | `docs/B1_2_BASE_LOOP.md`; AB base 18/18 |
| 110 | P12 B2: original content only, clean install, every asset reference tested | Partial | Same as 01-#52; `all_models_load` |
| 111 | P12 B2: Harbor Divide | Superseded | Zagros Basin |
| 112 | P12 B2: two factions, economy, construction, 3 roles, victory, competent AI, save/load | Partial | Save/load missing; Iran uses shared structures |
| 113 | P12 B2: complete human-vs-AI match tested | Partial | Automated scripted-vs-AI only; no recorded human match |
| 114 | P12: don't call it standalone before a clean-folder boot | Done | Never labelled standalone |
| 115 | P12 B3–B5 | Partial | Same as 01-#60…#62 |
| 116 | P12: distinguish concept / imported / visible in-game / playable / standalone verified | Partial | Used in the M-docs; no gate table |

## 05: B1.2 playtest QA report

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Keep the spinning helicopter rotors | Done | 3D rotors on CH-47/AH-64/UH-60; scr:`import_rotors.png`, `pilot3d_ch47_*` |
| 2 | Audit every asset as 3D, 2.5D, billboard or sprite | Partial | `docs/ASSET_AUDIT_3D.md` exists but is stale (F5) |
| 3 | Real 3D models for buildings, vehicles, aircraft, infantry, defences | Done | `AB: roster_spawns_with_models` ("still image:" empty), `all_models_load` 68 |
| 4 | Rotating/tilting the camera keeps assets consistent with the world | Done | scr:`b13_p01_orbit_yaw*`, `b13_p02/p03_tilt_*`, `b14_m1_base_yaw*` |
| 5 | No floating cutouts at normal or close zoom | Done | scr:`b14_m1_close_*`, `b13_p04` |
| 6 | Keep the generated U.S. designs recognisable | Done | scr:`m1_*_vs_concept.png` |
| 7 | Structures stay where placed, seated on terrain; scaffolds share the ground reference | Done | `AM: structures_on_flattened_ground`; scr:`b14_m1_construction.png` |
| 8 | Vehicles follow terrain with ground contact and contact shadow | Done | `AM: vehicle_drives_on_terrain`, `units_grounded` (0.000 m) |
| 9 | Wheels turn with distance; tracks scroll | Done | `AB: dozer_wheels_and_tracks_animate`. Other vehicles: `docs/M2_VEHICLES.md` (untested) |
| 10 | Infantry idle, walk/run, combat, fire and death states | Done | `AB: rifleman_animation_states`; scr:`m1_inf_*_anims.png` |
| 11 | Pivot, collision, selection ring and shadow share one ground anchor | Done | `AM: units_grounded`; `docs/SCALE_GUIDE.md` |
| 12 | Check: buildings on level and uneven ground while rotating/tilting | Done | `AM: flat_placement_grounded`; scr:`b15_zb_base_*` |
| 13 | Check: Dozer, HMMWV, tank and infantry move without hover, slide, sink or snap | Partial | Dozer, Abrams and rifleman are tested. No HMMWV test; slide/snap not measured |
| 14 | Document a world-scale reference | Done | `docs/SCALE_GUIDE.md` |
| 15 | Fix CH-47 scale against the Supply Depot | Done | `AB: scale_ch47_vs_depot` (18.1 m vs 22.0 m); scr:`b13_p07` |
| 16 | Collision, selection, shadow and rotor extent match the visible hull | Done | SCALE_GUIDE (collision scaled with drawn size) |
| 17 | No camera-dependent scaling | Done | Fixed per-class factors (`UnitDefs.SCALE`) |
| 18 | Compare every aircraft and ground unit against the scale guide | Partial | Only the CH-47 is checked automatically |
| 19 | GLB with Node3D/MeshInstance3D; no single flat plane | Done | `godot/assets/units3d/*/*.glb` |
| 20 | Moving parts: turret, wheels/tracks, rotors, skeletal infantry | Done | M1/M2/M3 docs |
| 21 | Building roots at the foundation; unit roots at ground contact | Done | ASSET_AUDIT_3D "Grounding" |
| 22 | Materials, lighting, shadows, contact shadows and LODs | Partial | No LODs |
| 23 | Flat images only for UI, minimap and decals | Done | ASSET_AUDIT_3D "Deliberate 2D" |
| 24 | Pilot set first, with front/side/rear/top captures | Done | scr:`pilot3d_*` |
| 25 | Four pads defined in Airfield space and converted to world space | Done | `AB: airfield_pads_on_map` |
| 26 | R returns aircraft to a free pad, lands and parks | Done | `AB: aircraft_return_land_on_pad`; `AT: f16_return_to_pad` |
| 27 | When pads are full: wait or queue; no stacking; no flight to the map edge | Done | `AB: full_apron_refuses_more` ("No free pad"); each aircraft owns its pad |
| 28 | No stranded aircraft and no false "landed" | Done | 0.00 m LANDED in test output |
| 29 | Test F-16/A-10/AH-64 after combat, near map edges, after camera rotation | Partial | Return is tested for all three. After-combat and edge/rotation cases have no separate test |
| 30 | Repair action on a damaged friendly building with cost tooltip; start/stop/resume | Done | `AB: repair_heals_and_costs`, `repair_stop` |
| 31 | Repair spends cash; pauses with a reason when cash runs out; disabled at full health | Done | `AB: repair_pauses_without_cash`, `repair_completes_and_disables` |
| 32 | Destroyed building leaves rubble; rebuilt through construction at normal cost and time | Done | `AB: rubble_left`, `rebuild_from_rubble`, `rebuild_completes` |
| 33 | Only friendly structures can be repaired or rebuilt | Done | `battle.rubble_at(gr, team)` (`commander.gd:301`) |
| 34 | UI distinguishes repair from rebuild | Done | Separate actions; "Cannot rebuild …" message |
| 35 | Core loop: preview, power, queues, orders, roles, readable UI | Done | AB/AT suites |
| 36 | Airfield sortie cycle with rearm/repair | Done | `AT: f16_rearm`; pad repair (`inspector.gd:170`) |
| 37 | Replace weak audio with licensed sounds (A-10, jets, rotor, tanks, infantry, weapons, explosions, construction, defences) | Partial | 14 Pixabay clips (`audio.json`). No infantry acknowledgements; no voices except the Farsi shout |
| 38 | Spatialised, balanced mix | Partial | Volume falls off with camera distance (`sfx.gd`). No volume control in Options (`sfx_volume` has no UI) |
| 39 | Rotor audio follows the helicopter's state | Partial | `heli_loop` is attached to helicopters; sync with state not tested |
| 40 | Reproduce each issue, fix at the right level, report steps, files and tests | Partial | Fix list in `build/win/README_PLAYTEST.txt` (B1.4). No reproduction-steps doc |
| 41 | Prioritised plan, then high-priority fixes first | Done | ASSET_AUDIT_3D "planned order"; P0/P1 items done |

## 06: Modern UI, economy and mechanics

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Limited, threatenable supply; visible gatherers and deliveries | Done | Same as 02-#23/#24 |
| 2 | Low power slows production and construction, slows towers, turns radar off; UI says what is impaired | Done | `AB: low_power_state`, `low_power_slows_production`; "(low power)" in HUD |
| 3 | Show cash, income/spending trend, power generated/used, why tasks are blocked | Done | `econ_panel.gd` (income/spending per minute) |
| 4 | Dozer builds and repairs damaged structures | Partial | Repair is a paid building action, not done by the Dozer. EOD engineers repair nearby |
| 5 | Producer buildings have clear roles | Done | `building_defs.gd` |
| 6 | Readable tech tree: locked items, exact requirement, cost | Done | "Requires …" (`econ_panel.gd`, `inspector.gd`) |
| 7 | Upgrades researched at specific buildings | Done | `upgrades.gd` "at" |
| 8 | Each producer has its own queue; global production strip | Done | Production strip top-left (README_PLAYTEST B1.4); `AB: inspector_building_queue` |
| 9 | War Factory repairs vehicles; Barracks heals infantry; Airfield services 4 aircraft | Partial | `AB: war_factory_repairs_vehicle`; Airfield done. The Barracks does not heal (only medic units and ambulances do) |
| 10 | Full aircraft lifecycle with pad occupancy shown | Done | `AB: inspector_airfield_pads` |
| 11 | Transport capacity and compatibility; UI shows passengers, free space, refusal reasons | Done | `unit_defs.gd` transport; "has room for N" (`commander.gd:273`) |
| 12 | Don't silently turn the supply CH-47 into a troop transport | Done | CH-47 has no transport block; UH-60 does air assault |
| 13 | Board, Unload one, Unload all; safe dismount | Partial | `econ_panel.gd:258`, D key; `AB: unload_transport`. The player cannot pick the dismount point |
| 14 | Transport controls only on transport units; .50/TOW are not carriers | Done | Only defs with "transport" get controls |
| 15 | Orders discoverable with icons, labels, tooltips and hotkey hints | Done | `hud.gd` help; command card |
| 16 | Plain-language roles (anti-infantry, anti-armour, etc.) | Done | `role` field shown in the Inspector |
| 17 | Build menu from implemented data only; future content hidden | Done | `Nations.produces`; no dead entries |
| 18 | Data model ready for another faction | Done | Iran added through `nations.gd` |
| 19 | Top bar: cash, trend, power, low-power state, alerts | Done | `hud.gd` |
| 20 | Map: rings, health bars, markers, rally, footprints, pad markers | Done | scr:`g11_air_01_pads_f16_selected.png`, `b12_b07` |
| 21 | Minimap: units, structures, camera rectangle, base, alerts | Partial | Alerts are not shown on the minimap |
| 22 | Selected-object panel updates immediately | Done | `AB: inspector_unit` |
| 23 | Building card sections: Overview, Production, Upgrades, Actions/Service | Done | `inspector.gd:256,304`; `AB: inspector_building_queue` |
| 24 | Clicking a production-strip entry focuses the producer | Done | README_PLAYTEST B1.4 (no automated test) |
| 25 | Tooltips: effect, cost, time, prerequisites, scope, hotkey | Partial | Tooltips exist; hotkeys are not shown on most of them |
| 26 | Responsive sizing: no clipping at common resolutions | Partial | UI scale option (`ui_kit.gd`); no resolution test evidence |
| 27 | Building panel: name, role, health, construction, power, production by category, upgrades, actions, queue, ETA, rally, disabled reason | Partial | All shown except queue reordering |
| 28 | Per-building contents (CC, Depot, Power Plant, Barracks, War Factory, Airfield, defence, Drop Zone) | Done | `inspector.gd`; the Dozer's panel is #43 |
| 29 | Real progress bars for construction, production, research and repair; cooldowns for powers | Done | Inspector ETA; `AB: research_starts` |
| 30 | Consistent queue states (Queued/Working/Paused/Blocked/Complete/Ready); no ETA while blocked | Partial | Only repair shows "Paused: reason". Production states are not labelled consistently |
| 31 | One rule for cash deduction and refunds | Done | Charged when queued, full refund on cancel (`battle.gd:1208,1214`) |
| 32 | Progress bars only move when real progress happens | Done | `AB: low_power_slows_production` |
| 33 | One authoritative economy for UI, AI and production | Done | `battle.cash`, `spend()` |
| 34 | Track supply left at each source and gatherer routes | Done | Inspector supply stock |
| 35 | CH-47 states: Loading, Returning, Unloading, Idle, Damaged, Blocked | Partial | Loading, Returning and Unloading exist (`inspector.gd`). No Damaged or Blocked state |
| 36 | Supply drops only when the structure exists | Done | `drop_zone` building |
| 37 | Costs, times, refunds, prerequisites and power in data, not in UI scripts | Done | `building_defs.gd`, `upgrades.gd` |
| 38 | Dozer catalog shows cost, time, power, prerequisites, footprint, validity | Done | `econ_panel.gd` build buttons |
| 39 | Invalid placement explains why; build starts only after an accepted order | Done | `AB: placement_rules` |
| 40 | Units exit to the rally point; never spawn inside buildings or off the map | Done | `AB: infantry_produced_to_rally` |
| 41 | Upgrades are real state changes with cost, time, prerequisites, scope, effect | Done | `AB: composite_armor_effect` |
| 42 | Never list aircraft at the Barracks | Done | `building_defs.gd` |
| 43 | Repair by ordering a Dozer; panel Repair assigns an idle Dozer | Partial | Same as #4 |
| 44 | Repair must not resurrect a destroyed building | Done | Rubble and rebuild are a separate flow |
| 45 | War Factory repair bay services vehicles one at a time | Partial | Heals every damaged vehicle nearby at once (`building.gd:199`); no occupancy |
| 46 | Airfield repairs, rearms and reserves pads correctly | Done | `AB: aircraft_return_land_on_pad`, `full_apron_refuses_more` |
| 47 | Show service cost, progress, blocked reason, insufficient funds | Partial | Building repair yes. Vehicle and aircraft service is free and has no progress UI |
| 48 | Transport definition: capacity, compatible types, slot size, firing from inside | Partial | Capacity and accepted types only |
| 49 | Infantry board a transport, or the transport picks nearby units | Partial | Infantry → transport click only |
| 50 | Passenger list with occupied/total capacity | Done | Inspector passengers; Unload-one buttons |
| 51 | Embark/disembark animation; documented rule for health, veterancy and orders | Partial | No embark animation; the rule doc is missing (F4) |
| 52 | Define and announce what happens to passengers when a transport dies | Partial | All passengers die (`battle.gd:1544`). The doc is missing (F4); no player message found |
| 53 | Configure HMMWV troop capacity deliberately | Done | HMMWV carries 5, MRAP 4 (`unit_defs.gd:318,338`) |
| 54 | No transport controls on other units | Done | Same as #14 |
| 55 | One source of truth; no duplicate managers | Done | `battle.gd` owns state |
| 56 | P1: implemented/partial/missing matrix with files | Partial | No matrix doc for this brief (this tracker now serves that role) |
| 57 | P7: full-loop QA incl. low funds, low power, blocked placement, full transport, full Airfield, cancels, destroyed producers | Partial | All tested except destroyed producers |
| 58 | Check: every building opens the correct panel | Partial | Only Barracks and Airfield panels are tested |
| 59 | Check: Airfield lists F-16, A-10, AH-64 with real upgrades and four pad states | Done | `AB: inspector_airfield_pads`; Guided Munitions |
| 60 | Check: existing combat, selection, camera, hotkeys and AI still work | Done | AT 22/22, AB 35/35 + 18/18 |
| 61 | Check: no fake controls, queues, upgrades or progress | Partial | Same as 01-#70 (F2) |

## 07: USA progression and Object Inspector (final consolidated handoff)

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Keep the B1.2 baseline, including the Carpet/Supersonic/Stealth/Paratroopers/Recon cards | Done | `nations.gd` usa powers; `AT: support_power_*` |
| 2 | Keep generated art out of menus until the unit really exists | Done | Same as 06-#17 |
| 3 | Map C&C names to Steel Accord names (no second Supply Center; Power Plant stays) | Done | `building_defs.gd` |
| 4 | Strategic Operations Center, or a module on the Command Center | Done | Module on the CC: Advanced Training and plans at `command_center` (`upgrades.gd`) |
| 5 | Don't relabel the Defense Tower as Patriot | Done | Still "Defense Tower" |
| 6 | Patriot battery once its systems exist | Not started | — |
| 7 | THAAD only if missiles can be intercepted | Deferred by design | No interception system |
| 8 | Field artillery emplacement (optional) | Deferred by design | Optional; not built |
| 9 | MOAB through Carpet Bombing, gated by commander rank | Deferred by design | No rank system; the brief says defer |
| 10 | Commander rank: use the existing system; never add a duplicate | Not started | No commander rank exists |
| 11 | Costs and times in authoritative data; no "$?" | Done | `upgrades.gd` |
| 12 | Capture Structures only for a designated Engineer | Partial | F8 |
| 13 | Medic as a Barracks unit with real healing | Done | `medic`, `ir_medic`; scr:`m1_inf_medic_anims.png` |
| 14 | Barracks as an infantry treatment point (optional) | Not started | — |
| 15 | Flashbangs for Rangers | Not started | — |
| 16 | Exosuits become the "Advanced Combat Armor" research | Partial | `upgrades.gd` adv_armor (−15 %). Its effect is not tested |
| 17 | Advanced Training gives more XP, never instant promotions | Partial | `upgrades.gd` xp×1.5. Researched in `AB: battle_plans`, but the XP effect is not tested |
| 18 | Composite Armor only for compatible armoured units | Done | `AB: composite_armor_effect` (Abrams 100→85, HMMWV .50 unchanged) |
| 19 | HMMWV TOW as a separate variant | Done | `hmmwv_tow` |
| 20 | Vehicle repair at the War Factory showing availability, progress, cost, full state | Partial | Same as 06-#45/#47 |
| 21 | No empty drone category; drones only when implemented | Done | No drone category exists |
| 22 | Drones as real units | Deferred by design | The brief says only once drone mechanics exist; the Shahed exists only as a support power |
| 23 | Vehicle upgrades scoped by tags; UI names the units affected | Done | `SCOPE_TEXT`; `AB: inspector_upgrade_states` |
| 24 | Rocket Pods only on compatible aircraft | Not started | — |
| 25 | Guided Munitions for air-to-ground aircraft, listing eligible units | Partial | `upgrades.gd` scope air_ground; effect not tested |
| 26 | Countermeasures only if missiles lock on | Deferred by design | No missile-lock system |
| 27 | Hardened-Target Munitions | Not started | — |
| 28 | Airfield shows four pads and real aircraft states | Done | `AB: inspector_airfield_pads` |
| 29 | Research tab: armour, training, supply and other upgrades | Done | Research section (`inspector.gd`) |
| 30 | Battle Plans: one at a time, with a switch delay | Done | `AB: battle_plans` (15 s gap) |
| 31 | Intelligence tab connected to Recon Overflight | Not started | Recon is a power card; no Intelligence section and no Recon upgrade |
| 32 | Active plan shown in the HUD and in affected units' inspectors | Done | `hud.gd:462` |
| 33 | Supply Line Efficiency +10 %, without double counting | Partial | `upgrades.gd` income×1.10; not tested |
| 34 | Scout Armor | Deferred by design | Needs scout drones |
| 35 | Hazard Protection | Deferred by design | No hazard damage types |
| 36 | Shared inspector header: name, class, owner, role, health, state, actions | Done | `AB: inspector_unit` |
| 37 | Building inspector fields (health, purpose, queue, upgrades by state, power, services, pads, stock, repair/sell) | Done | `AB: inspector_building_queue`, `inspector_airfield_pads` |
| 38 | Unit inspector: role, order, weapons, veterancy XP and bonuses, upgrade states, ammo, passengers | Done | `inspector.gd:4`; `AB: veterancy_promotion`, `inspector_upgrade_states` |
| 39 | Upgrade states Installed/Available/Researching/Locked; never show "Not implemented" | Done | `AB: inspector_upgrade_states`, `battle_plans` |
| 40 | Group inspector: counts per type, roster opens each unit, no merged upgrade lists | Done | `AB: inspector_group` |
| 41 | Left-click selects and opens; right-click unchanged; empty ground clears; game doesn't pause | Done | `AB: inspector_pin`; AT suite |
| 42 | Inspector readable at 1080p, 1440p and 4K without covering the minimap or panel | Partial | UI scale "Auto" (`ui_kit.gd:120`); no capture at those resolutions |
| 43 | Veterancy separate from commander rank; data-driven thresholds; class-specific bonuses | Done | `veterancy.gd`; `AB: veterancy_promotion` |
| 44 | Support units earn XP from support actions | Done | `unit.gd:933` (healing/repair XP) |
| 45 | Rank-up notification, badge, bonus and next threshold | Done | `battle.gd:736`, chevrons in `hud.gd` |
| 46 | Implementation order (§6 steps 1–9) | Partial | Steps 1–4 done; 5–9 open (items below) |
| 47 | Feature matrix: in source / visible in B1.2 / planned / new | Not started | No matrix doc |
| 48 | Fortifications build category: concrete wall and earth berm | Not started | M9 |
| 49 | Drag-placed wall lines with cost/segment preview and tower anchors | Not started | — |
| 50 | Wall collision, gates, pathfinding for units and AI | Not started | — |
| 51 | Destructible, repairable walls; segment health shown in the Inspector | Not started | — |
| 52 | Infantry garrison a HESCO Fighting Position (two ways to order it) | Not started | — |
| 53 | HESCO capacity, slots, visible occupants, firing ports, cover | Not started | — |
| 54 | Occupants ejected safely when the HESCO is destroyed | Not started | — |
| 55 | Fortification acceptance tests 1–6 | Not started | — |
| 56 | Builder stays visible, selectable, commandable; distinct silhouette and far-zoom icon | Partial | Visible 3D M88/engineer dozer; no far-zoom icon |
| 57 | Builder status control and Find Builder button | Not started | — |
| 58 | Builder inspector: catalog, current target, progress, blocked reason | Partial | Catalog yes; no assigned-target/progress fields |
| 59 | Warning when the builder dies, with a recovery path | Partial | The CC can rebuild a Dozer; no specific warning found |
| 60 | Readable at far zoom: LODs, silhouettes, class icons only when needed | Not started | No LOD or zoom icons (`zoom_max 230`, `rts_camera.gd`) |
| 61 | No physically enlarged distant meshes | Done | Fixed scale factors |
| 62 | Mid/close detail: turrets, wheels, markings, crisp materials | Done | scr:`b14_m1_close_*`, `ir_*_sheet.png` |
| 63 | Contrast in sun, shade and fog; colour-blind-safe team ID | Partial | Team paint and rim light (scr:`b12_tank_team_paint.png`); no colour-blind option |
| 64 | Hover and selection highlights that don't wash out models | Done | Rings (`hud.gd`) |
| 65 | Free orbit, pan and tilt around a selected object at close zoom; recenter | Partial | Middle-drag rotate, tilt 35–75°, Home resets (`rts_camera.gd:92-95`). No focus orbit; min zoom 44 m |
| 66 | Camera never clips terrain or buildings | Done | Camera follows terrain (B1.5 report) |
| 67 | Adjustable camera speed and inversion | Partial | Speed option yes (`ui_kit.gd:104`); no inversion |
| 68 | Readable map layout: routes, build areas, landmarks | Done | Zagros Basin; scr:`map_zagros_routes.png` |
| 69 | Coherent terrain materials; no repetitive fields | Done | Splat shader with 6 materials (ADR-0008) |
| 70 | Balanced lighting; no grey wash; fog of war distinct from haze | Partial | Not checked against the "washed out" playtest note; no before/after evidence |
| 71 | Crisp detail without blur or halos | Partial | Not reviewed systematically |
| 72 | Visual quality settings (quality, shadows, effects) | Not started | Options has no graphics settings |
| 73 | Faction data drives names, palette, roster, assets, doctrine, voices | Partial | `nations.gd` has names, flags, roster and powers. Building names, palette, doctrine/plans and upgrade names are shared |
| 74 | Faction-specific building labels | Not started | Iran uses "War Factory" and "Airfield" |
| 75 | Don't reuse U.S. models or voices as another nation's | Partial | Iran still uses U.S. structures and U.S. Avenger/Paladin (labelled placeholders) |
| 76 | Accessibility options global across factions | Partial | Settings are global; only a few options exist |
| 77 | Presentation acceptance tests 1–7 (far zoom, Find Builder, orbit, light/fog, map, second faction, 1080p–4K) | Partial | Only #6 (second faction loaded through data) is met |
| 78 | Check stale "Defense Tower 84 %" progress | Not started | No investigation recorded |
| 79 | Infantry readable at strategic zoom | Partial | Infantry drawn at 1.3× (SCALE_GUIDE); no far-zoom test |
| 80 | A-10 scale near the Airfield | Partial | Aircraft at 0.6× (SCALE_GUIDE); no specific test |
| 81 | Bomber cinematic: named aircraft, skippable camera focus, returns control | Not started | Strike cards name the aircraft; no camera focus |
| 82 | Pale weapon trails and smoke hard to read | Not started | No change recorded |
| 83 | Small or clipped UI labels and costs | Partial | UI scale option; no measured fix |
| 84 | Volume controls for the player | Done (code) | Options: "Effects volume" slider (`ui_kit.gd`) drives `sfx_volume` |
| 85 | Subtitles for spoken acknowledgements | Not started | No acknowledgements and no subtitles |
| 86 | Distinct voice responses per unit | Not started | — |
| 87 | Clean capture (no editor or OS chrome) | Partial | Screens come from the game's own capture scripts; no promo recording |
| 88 | §10 core loop, transport and Airfield items repeated from 05/06 | Done | Same as 05-#25…#36, 06-#11…#14 |

## 08: Zagros Basin (Iran) map prompt

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Inspect the map, terrain, movement, placement, resources and renderer; report files and risks first | Done | `docs/MAP_ZAGROS_BASIN.md`, ADR-0008 |
| 2 | Fictional Zagros-foothills/basin sector | Done | `maps/zagros_basin`; scr:`b15_zb_overview.png` |
| 3 | Real public elevation for broad shape only | Partial | The DEM could not be downloaded (403), so the relief is synthetic. The generator accepts a DEM (ADR-0008) |
| 4 | Invent all bases, roads, towns, supplies and derricks | Done | `tools/map/gen_zagros_basin.py` |
| 5 | Playable area of about 4–6 km, scaled for RTS pace | Partial | 1.2 × 1.2 km. Scaled down deliberately (MAP_ZAGROS_BASIN.md) |
| 6 | Evaluate Terrain3D 1.0.2, including the Windows export | Done | ADR-0008: evaluated, binaries not downloadable, not adopted; built-in heightfield used instead |
| 7 | High-bit-depth heightmap | Done | R16 601×601 (`height.r16`) |
| 8 | Sand, rock, gravel, scrub, dry riverbed and road materials | Done | `shaders/terrain_map.gdshader` splat |
| 9 | Buildable pads, two balanced starts, base and central supplies, derricks, roads, ridges, valleys, boundaries | Done | `AM: starts_from_map`, `starts_fair`, `sites_grounded` |
| 10 | Finite supplies delivered to a supply center | Done | `AM: supply_delivery` |
| 11 | Capturable derricks with recurring income | Done | `AM: derrick_capture`, `derrick_income` |
| 12 | Ground everything through a terrain query; no floating or buried assets | Done | `AM: units_grounded`, `props_grounded` (0.000 m) |
| 13 | Reject placement on steep slopes | Done | `AM: steep_placement_rejected` |
| 14 | Collision and navigation with different slope rules per class | Done | `AM: class_slope_rules`, `cliffs_block` |
| 15 | Resources, capture income, starts and terrain costs in data | Done | `maps/zagros_basin/map.json` |
| 16 | Check: map loads and runs | Done | `AM: map_loads` (Wine export too) |
| 17 | Check: no floating or sinking buildings | Done | `AM: structures_on_flattened_ground` |
| 18 | Check: routes passable, cliffs block | Done | `AM: routes_passable`, `cliffs_block` |
| 19 | Check: comparable resource access for both starts | Done | `AM: starts_fair` |
| 20 | Check: derricks change owner | Done | `AM: derrick_changes_owner` |
| 21 | Check: supply delivery updates the economy | Done | `AM: supply_delivery` |
| 22 | Check: RTS-camera screenshots and changed files | Done | scr:`b15_zb_*`; `docs/B1_5_ZAGROS_IRAN.md` |
| 23 | Preserve existing gameplay | Done | Proving Ground map kept; QA 24/24, base 18/18, army 22/22 (B1.5 report) |

## 09: Iran arsenal handoff

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Read the README and six sheets as concept art only | Done | `docs/reference/iran_pack/` |
| 2 | Don't break existing USA assets, mechanics, UI or scenes | Done | AB/AT regression suites |
| 3 | Data-driven faction with its own unit and building definitions | Partial | `nations.gd` covers units. There are no Iranian building definitions |
| 4 | Never treat a whole contact sheet as one object | Done | Separate GLB per panel (`godot/assets/units3d/ir_*`) |
| 5 | Real 3D meshes with consistent scale and ground contact | Done | `AM: iran_roster_models`; scr:`ir_*_sheet.png` |
| 6 | Vehicles, sheet 01: Karrar, T-72S, BMP-2, Boragh, engineer vehicle | Done | `docs/IRAN_VEHICLES_WAVE1.md`; `AM: iran_roster_models` |
| 7 | Vehicles, sheet 01: Zulfiqar, Chieftain, BTR-60, M113, Raad-1, M109, Fajr launcher | Not started | Wave 2. Avenger and Paladin remain U.S. placeholders |
| 8 | Aircraft, sheet 02: F-14, F-4, Su-24, AH-1J, CH-47C, C-130, Shahed-136 | Done | `docs/IRAN_AIRCRAFT_WAVE1.md`; `AM: iran_shahed_strike`, `iran_roster_models` |
| 9 | Aircraft, sheet 02: F-5, F-7, MiG-29, Mirage F1, Su-22 | Not started | — |
| 10 | Missile/air-defence sheet 03 (Fateh, Khordad-3, radar truck, etc.) | Not started | — |
| 11 | Troop roles, sheet 04 | Partial | Rifleman, RPG, MG, medic, sniper, engineer, IRGC SF, paratrooper done (`docs/IRAN_INFANTRY.md`). Basij reserve, squad leader, officer, tank crew, pilot and air-defence operator missing |
| 12 | Medic with Red Crescent marking | Partial | No emblem modelled; needs an approved design (IRAN_INFANTRY.md:118) |
| 13 | Rank-insignia sheet not presented as an official chart | Done | Not used in the game |
| 14 | Installations, sheet 06 (HQ, barracks, hangar, airfield, depot, yard, checkpoint, radar) | Not started | Iran uses U.S. structures |
| 15 | Report the asset mapping and 3D-vs-sprite decision before changing files | Done | IRAN_*_WAVE1.md and IRAN_INFANTRY.md mapping tables (3D chosen). Their status lines are stale |
| 16 | Small, testable steps; report changed files and tests | Partial | Commits per asset (`git log` 4accaa8…e14863f); no B1.6 report (F6) |
| 17 | Don't publish or release anything | Partial | Same as 01-#69 |

## 10: UI Inspector panels, Iran and Skirmish setup

The client said screenshots and a CNCNZ reference page were attached, but only the text of the brief reached the project. No screenshots or reference page exist in the repo, so items that depend on them were judged from the text alone.

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Report existing UI, faction data, selection, queues, upgrades and their files before editing | Not started | No report for this brief yet |
| 2 | Use CNCNZ only as an organisation pattern; copy no data | Done | No CNCNZ data in the source |
| 3 | Left-click opens or updates one consistent inspector; right-click unchanged | Done | `AB: inspector_unit`, `inspector_pin`; AT suite |
| 4 | Unit inspector: faction name, type, role, portrait/icon, owner | Done | `inspector.gd:24-48,150` |
| 5 | Unit inspector: health, state/order, weapons/loadout | Done | `inspector.gd:168-199` |
| 6 | Unit inspector: upgrade states and veterancy with bonuses | Done | `AB: inspector_upgrade_states`, `veterancy_promotion` |
| 7 | Abilities, cooldowns, service and transport state only when implemented | Done | Passengers, pad and ammo lines (`inspector.gd`) |
| 8 | Building inspector: name, purpose, health, operational state, power, prerequisites | Done | `AB: inspector_building_queue` output |
| 9 | Building inspector: production, queue, progress, blocked reason | Done | Same |
| 10 | Upgrades in their own section, apart from production | Done | Production and Research sections (`inspector.gd:256-304`) |
| 11 | One authoritative state; never both "idle" and "engaging" | Done | One `_state()` string (`inspector.gd:168-172`) |
| 12 | War Factory panel: vehicles, costs, prerequisites, queue, upgrades | Done | `inspector.gd`; Composite Armor shown |
| 13 | Airfield panel: aircraft separate from research; four pads; real states | Done | `AB: inspector_airfield_pads` |
| 14 | Barracks panel: infantry and upgrades; medical services only if real | Done | `AB: inspector_building_queue` (Barracks) |
| 15 | Command Center panel: builder availability, construction, command functions | Done (code, 3196ef6) | Inspector "Services: Builders N (working / available)"; in-game capture pending |
| 16 | Other buildings get panels matching their purpose | Done | Power, depot stock, drop timer, defence (`inspector.gd`) |
| 17 | Overview / Production / Upgrades / Services sections | Done | `inspector.gd:256,304` |
| 18 | Each item shows icon, name, cost, prerequisite, real progress or lock reason | Partial | Command card: icon buttons with cost, tooltip prerequisites/lock reasons, Production and Upgrades in separate tabs (3196ef6); research cards have no icons yet |
| 19 | Consistent typography, spacing, contrast; panels don't overlap | Partial | `ui_kit.gd` theme; no overlap test across resolutions |
| 20 | Hover tooltips on icon-only controls | Done | `tooltip_text` in `econ_panel.gd`/`hud.gd`/`inspector.gd` |
| 21 | Skirmish: player slots | Partial | Slot table (Player 1 / Player 2, army, colour, team, control) in `main_menu.gd`; still 1v1 only |
| 22 | Skirmish: faction/army choice | Done | Nation pickers (`main_menu.gd:79`) |
| 23 | Skirmish: player colour | Done (code, 3196ef6) | Colour pickers (never equal); `UnitDefs.team_color()` drives HUD, minimap, rings; capture `skirmish_1080` |
| 24 | Skirmish: teams | Partial | Team column shown (Team 1 / Team 2); allied teams need more than 2 slots |
| 25 | Skirmish: map preview and selection | Done (code, 3196ef6) | `maps/<id>/preview.png` from `tools/map/make_previews.py` + map facts |
| 26 | Skirmish: starting resources | Done (code, 3196ef6) | $5k / $10k / $20k → `battle._spawn_bases` |
| 27 | Skirmish: game speed | Done (code, 3196ef6) | 75 / 100 / 125 % via `Engine.time_scale` (reset on menu) |
| 28 | Skirmish: match rules | Partial | The one implemented rule is shown (destroy all); no other rules exist yet |
| 29 | Skirmish: launch and back actions | Done | "Start Match" (`main_menu.gd:95`) and menu navigation |
| 30 | Skirmish screen scales cleanly | Partial | UI scale; no captures |
| 31 | Iran uses its own terminology and roster, not U.S. labels or upgrade names | Done (code, 3196ef6) | `Nations.label()`: Command Headquarters, Armour Works, Air Base, Reactive Armour Kits, doctrines, etc.; capture pending |
| 32 | Inspector and layout shared across nations | Done | One `inspector.gd` for both nations |
| 33 | Test: select an Iranian soldier, Karrar, tactical vehicle, aircraft, Airfield, War Factory, Barracks, CC | Not started | The inspector tests use the U.S. side only |
| 34 | Test: panels update live (health, orders, queue, upgrades, pads) | Partial | Queue ETA and pads are tested on U.S. objects; no Iranian test |
| 35 | Test: 1080p, 1440p and 4K layouts | Not started | No captures |
| 36 | Test: inspection doesn't break selection, right-click, hotkeys or camera | Done | AT 22/22 with the Inspector present |
| 37 | Before/after screenshots, changed files, unsupported fields | Not started | — |

## Chat requests

| # | Request | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Spinning helicopter rotors | Done | Same as 05-#1 |
| 2 | Tanks visible against the terrain | Done | Team paint and rim light, scr:`b12_tank_team_paint.png`, `b15_zb_tanks_on_slope.png`. Far-zoom readability open (07-#60) |
| 3 | Add the supplied audio (A-10 etc.) | Done | `content/manifest/audio.json` (14 clips; `a10_cannon` from the client's Pixabay file); `AT: a10_cannon_fires` |
| 4 | Real 3D models instead of flat cards | Done | Same as 05-#3 |
| 5 | Fix grounding and scale (Chinook too big) | Done | Same as 05-#8, #15 |
| 6 | Aircraft park on Airfield pads | Done | Same as 05-#26 |
| 7 | Repair and rebuild | Done | Same as 05-#30…#32 |
| 8 | AT4 animated like the rifleman | Done | Shared rig and animations; scr:`m1_inf_at4_anims.png` |
| 9 | Buildings must not float or move with the cursor | Done | Same as 05-#7; scr:`b14_m1_base_yaw*` |
| 10 | Flashing status lights on buildings | Done | `building.gd:233` (green / blinking amber / red, beacons); scr:`b14_m1_close_*` |
| 11 | Supply Drop Zone | Done | `AB: supply_drop_zone_income`; scr:`b14_m1_close_drop_zone.png` |
| 12 | Airfield redesigned with a runway | Done | scr:`m1_airfield_*`, `b14_m3_airfield_close.png`; `AT: f16_takeoff` |
| 13 | Full War Factory roster in 3D (tanks, medic HMMWV, MRAP, Paladin, …) | Done | 12 vehicles; `AB: roster_spawns_with_models`; scr:`m2_*_sheet.png` |
| 14 | All aircraft in 3D | Done | `docs/M3_AIRCRAFT.md`; scr:`m3_*_sheet.png` |
| 15 | Vehicles repaired at the War Factory, aircraft at the Airfield | Done | `AB: war_factory_repairs_vehicle`; `AT: f16_rearm` |
| 16 | Paratroopers with parachutes | Done | `AB: paratroopers_land`; scr:`m1_inf_paratrooper_chute.png` |
| 17 | Air assault and troop transports | Done | `AB: air_assault_board`, `air_assault_unload`, `board_transport` |
| 18 | Milestones delivered per push | Done | Builds `build/SteelAccord_B1_2…B1_6_win64.zip`; per-milestone commits |
| 19 | Keep the U.S. star on U.S. aircraft | Done | `nations.gd` header; B1.5 report |
| 20 | Iran faction with its own troops and a beard/moustache/shaven mix | Done | `AM: ai_nation_roster` (beard 28 / moustache 8 / shaven 9); scr:`ir_faces.png` |
| 21 | Iranian flag | Done | `AM: nation_flag`; scr:`flags.png` |
| 22 | IRGC special unit | Done | `irgc_sf`; scr:`ir_irgc_sf_*` |
| 23 | Farsi battle shout when Iranians attack | Done | `AM: iran_battle_cry` (14 s cooldown per side) |
| 24 | Iranian vehicles and aircraft from the arsenal pack | Partial | Wave 1 done (same as 09-#6, #8). Wave 2 and Iranian structures missing; Avenger/Paladin are placeholders |

---

## Summary

| Document | Done | Partial | Not started | Deferred | Superseded |
|---|---|---|---|---|---|
| 01: Master prompt / project description | 33 | 35 | 4 | 1 | 7 |
| 02: Prompts 2–10 (Recon, Architect, Build follow-ups and mechanics addendum) | 25 | 19 | 9 | 5 | 2 |
| 03: Master handoff (mechanics) | 9 | 8 | 1 | 0 | 1 |
| 04: Gameplay, movement, UI and assets prompts | 56 | 39 | 13 | 2 | 6 |
| 05: B1.2 playtest QA report | 32 | 9 | 0 | 0 | 0 |
| 06: Modern UI, economy and mechanics | 41 | 20 | 0 | 0 | 0 |
| 07: USA progression and Object Inspector (final consolidated handoff) | 32 | 24 | 25 | 7 | 0 |
| 08: Zagros Basin (Iran) map prompt | 21 | 2 | 0 | 0 | 0 |
| 09: Iran arsenal handoff | 8 | 5 | 4 | 0 | 0 |
| 10: UI Inspector panels, Iran and Skirmish setup | 26 | 7 | 4 | 0 | 0 |
| Chat requests | 23 | 1 | 0 | 0 | 0 |
| **Total** | **306** | **169** | **60** | **15** | **16** |

### The 10 most important open items
1. **No save/load.** It is required for B2, and the briefs ask for save/replay tests early (F7).
2. **No standalone check.** Nothing has been tested in a clean folder or on a real Windows PC. The Windows build ran only under Wine, and there is no list of files the game loads.
3. **Replays and multiplayer are missing.** Only the command log exists.
4. **Fortifications are not built:** walls, berms, gates and HESCO garrisoning (07 §8).
5. **The builder is hard to find.** There is no Find Builder or builder status control, no far-zoom icons or LODs, and no free orbit around a selected object (07 §9).
6. **Skirmish setup is still 1 vs 1.** Colours, starting cash, game speed, the victory rule and a map preview were added in 3196ef6 and the AI damage modifier is now disclosed in the difficulty tooltip; more player slots, allied teams and AI scouting are still missing.
7. **Iran is only partly its own faction.** It now uses its own names for structures, research and plans (3196ef6), but its structures share the U.S. 3D models. Wave 2 (Raad-1, Fajr, Khordad-3, Fateh, Iranian buildings) is missing, and Avenger/Paladin are still placeholders.
8. **Accessibility and options are thin.** An effects-volume slider and an interface-size option exist, but there is no key remapping, subtitles, colour-blind option or graphics settings, and 1440p/4K captures are still being made.
9. **Planned systems are not started.** Commander rank (which also gates MOAB), Patriot, capture done by a designated engineer only (F8), patrol and hold-fire orders, and a bomber camera.
10. **Several documents are out of date.** ARCHITECTURE, TASKBOARD, DECISIONS, README, ECONOMY_SPEC, GAME_DESIGN and ASSET_AUDIT_3D still describe the old engine or older builds, and there is no B1.6 report (F1, F5, F6). The stale menu labels and the missing transport doc are fixed (F2, F4).
