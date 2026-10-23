# Steel Accord — Request Tracker

Oct 22, 2026 · @Ezio

Every request from the 10 handoff briefs and the chat, checked against the code and the latest test runs: 327 done, 164 partial, 57 not started, 15 deferred by design, 16 superseded.

## Summary

**Statuses:** Done = implemented and covered by an automated test or an in-game screenshot. Partial = some of it works; the evidence column says what is missing. Not started = no code found. Deferred = the brief itself says to wait for a supporting system, or it was deferred with a stated reason. Superseded = replaced by a later decision (mainly the move from the Zero Hour fork to Godot 4).

Windows checks ran under Wine, not on a real Windows PC. Evidence codes: AB = base/QA test suite, AT = army suite, AM = map test, scr = docs/screens.

| Document | Done | Partial | Not started | Deferred | Superseded |
| --- | --- | --- | --- | --- | --- |
| 01: Master prompt / project description | 33 | 35 | 4 | 1 | 7 |
| 02: Prompts 2–10 (Recon, Architect, Build follow-ups and mechanics addendum) | 25 | 19 | 9 | 5 | 2 |
| 03: Master handoff (mechanics) | 9 | 8 | 1 | 0 | 1 |
| 04: Gameplay, movement, UI and assets prompts | 56 | 39 | 13 | 2 | 6 |
| 05: B1.2 playtest QA report | 32 | 9 | 0 | 0 | 0 |
| 06: Modern UI, economy and mechanics | 43 | 18 | 0 | 0 | 0 |
| 07: USA progression and Object Inspector (final consolidated handoff) | 34 | 23 | 24 | 7 | 0 |
| 08: Zagros Basin (Iran) map prompt | 21 | 2 | 0 | 0 | 0 |
| 09: Iran arsenal handoff | 8 | 5 | 4 | 0 | 0 |
| 10: UI Inspector panels, Iran and Skirmish setup | 32 | 5 | 0 | 0 | 0 |
| 11: Zero Hour-style control bar | 11 | 0 | 2 | 0 | 0 |
| Chat requests | 23 | 1 | 0 | 0 | 0 |
| **Total** | **327** | **164** | **57** | **15** | **16** |

**The 10 most important open items**

1. **No save/load.** It is required for B2, and the briefs ask for save/replay tests early.
2. **No standalone check.** Nothing has been tested in a clean folder or on a real Windows PC. The Windows build ran only under Wine, and there is no list of files the game loads.
3. **Replays and multiplayer are missing.** Only the command log exists.
4. **Fortifications are not built:** walls, berms, gates and HESCO garrisoning (07 §8).
5. **The builder is hard to find.** No Find Builder or builder status control, no far-zoom icons or LODs, no free orbit around a selected object (07 §9).
6. **Skirmish setup is still 1 vs 1.** Colours, starting cash, game speed, the victory rule and a map preview were added, and the AI damage modifier is now shown in the difficulty tooltip; more player slots, allied teams and AI scouting are missing.
7. **Iran is only partly its own faction.** It now uses its own names for structures, research and plans, but its structures share the U.S. 3D models. Wave 2 (Raad-1, Fajr, Khordad-3, Fateh, Iranian buildings) is missing, and Avenger/Paladin are still placeholders.
8. **Accessibility and options are thin.** An effects-volume slider and an interface-size option exist; there is no key remapping, subtitles, colour-blind option or graphics settings, and dropdown lists don't scale up at 4K
9. **Planned systems are not started.** Commander rank (which also gates MOAB), Patriot, capture by a designated engineer only, patrol and hold-fire orders, a bomber camera.
10. **Several documents are out of date.** ARCHITECTURE, TASKBOARD, DECISIONS, README, ECONOMY\_SPEC, GAME\_DESIGN and ASSET\_AUDIT\_3D still describe the old engine or older builds, and there is no B1.6 report. The stale menu labels and the missing transport doc are fixed.

## 01: Master prompt / project description

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Lead a team of specialist agents; inspect and run their work instead of trusting claims | Partial | Art agents produced the Iran/M2 models (e.g. `docs/IRAN_VEHICLES_WAVE1.md`), and the lead verified them through tests (`AM: iran_roster_models`). TASKBOARD.md has not been updated since 2026-10-21 |
| 2 | Original standalone title with its own name, not EA's | Done | Title "Steel Accord" (`main_menu.gd`); scr:`g13_main_menu.png` |
| 3 | Nine playable sides; any can be player, ally or AI in skirmish | Partial | Only USA and Iran exist (`nations.gd`). Matches are 1v1 only: no allies or teams |
| 4 | Fictional setting; no nation made the villain | Done | `nations.gd` header; GAME\_DESIGN.md opening section and §4 |
| 5 | Command Center and builders | Done | `AB: dozer_constructs`, `start_state` |
| 6 | Resources and logistics | Done | `AB: supply_income`; `AM: supply_delivery` |
| 7 | Construction and power | Done | `AB: place_power_plant`, `low_power_state` |
| 8 | Production queues | Done | `AB: queue_units`, `cancel_refund` |
| 9 | Infantry, vehicles and aircraft with counterplay | Done | `AB: roster_spawns_with_models`, `counter_matrix` |
| 10 | Fog of war and scouting | Done | `AT: fog_of_war`. Radar puts enemy units on the minimap |
| 11 | Selection box, right-click, control groups, attack-move, hotkeys, camera, minimap | Done | `AT: box_select`, `control_group`, `command_card_attack_move`, `right_drag_scroll`. Minimap click jumps the camera |
| 12 | Tech, upgrades, veterancy and support powers | Done | `AB: research_starts`, `veterancy_promotion`; `AT: support_power_carpet`, `support_power_b1` |
| 13 | Skirmish against computer enemies | Done | `AB: ai_attacks`, `victory_when_enemy_destroyed` |
| 14 | Saves | Not started | No game save/load; only settings are stored |
| 15 | Replays | Partial | Commands are logged with their tick number (`AT: command_log`). No replay playback or replay file |
| 16 | Eventual competitive multiplayer | Not started | Planned for B5 |
| 17 | Original faction asymmetries | Partial | Iran has its own roster and powers (Shahed strike). It shares the U.S. structure models and tech tree (own names) |
| 18 | Modern, legible interface | Partial | HUD, Inspector and UI scale option exist. No key remapping and no colour-blind options |
| 19 | Do not copy EA logos, voices, textures, maps, art, music, UI or story | Done | Art generated by scripts (`tools/art/*.py`); audio from Pixabay (`content/manifest/audio.json`); credits screen |
| 20 | Use the mechanics brief, but audit its claims against source and manual | Partial | `docs/MECHANICS_REFERENCE_AUDIT.md` exists; it says "Manual not yet cross-checked" |
| 21 | Cash is the spendable resource; power is a separate capacity | Done | Power fields in `building_defs.gd`; `AB: low_power_slows_production` |
| 22 | Keep active supply gathering separate from secondary income | Done | CH-47 hauling vs derricks and the Drop Zone: `AM: derrick_income`, `AB: supply_drop_zone_income` |
| 23 | Keep rank-earned support powers separate from constructed superweapons | Partial | Support powers are cooldown cards gated by nation and buildings. No commander rank and no superweapon |
| 24 | Do not assume ECS, snap grid, flow fields or rollback | Done | Grid A\* (`grid_nav.gd`), no ECS, free placement with footprint checks |
| 25 | Check access to the Windows PC first; never fake a Windows build | Done | RECON.md §1. Reports say "Windows export under Wine", not a real PC |
| 26 | Product branch of the modernized fork with a pinned commit | Superseded | ADR-0007 (Godot); the fork was pinned at `8154df9028e8` before the switch (ADR-0001) |
| 27 | Do not modify the Steam install; keep the known-good test copy | Done | This environment has no access to either. Nothing has been touched |
| 28 | Keep GPL/EA notices and mark modified engine code | Superseded | ADR-0007: no EA code in the Godot game. Godot MIT licence credited |
| 29 | Keep private experiments separate from a distributable built from our own assets | Partial | The Godot export contains no EA data by construction. No clean-folder audit of loaded files yet |
| 30 | Asset manifest: origin, creator, tool/prompt, edit history, licence, shipping status | Partial | `content/manifest/audio.json`, `us_packs.json`, `aircraft.json`, per-model reports and generating scripts. No single manifest covers the 3D models or Iranian art. Audio needs per-item Pixabay URLs before release |
| 31 | Do not clone actors' voices or imitate existing scores | Done | No voice clones and no music. The only voice is the client's Farsi clip, with provenance in `audio.json` |
| 32 | Write an ADR with evidence before a major engine change; wait for approval | Done | `docs/adr/ADR-0007-engine-godot4.md` "Accepted by client" |
| 33 | Keep a task board and a decision log | Partial | Both exist but have not been updated since 2026-10-21 |
| 34 | RECON.md with evidence, risks, paths and missing inputs | Superseded | `docs/RECON.md` was done for the Zero Hour fork |
| 35 | List the Steam assets the test copy still uses | Superseded | RECON.md §6 (Zero Hour only) |
| 36 | ARCHITECTURE.md plus ADRs: branch, content separation, manifest, pipeline, UI/render, fixed step, AI, save/replay, multiplayer | Partial | ADR-0001..0006 cover Zero Hour; ADR-0007/0008 cover Godot. ARCHITECTURE.md not yet rewritten for Godot |
| 37 | Define how a clean Windows folder boots without Steam archives | Partial | `SteelAccord.exe` is a single self-contained export. Not tested on a clean real Windows PC; no list of loaded files |
| 38 | Dependency graph and milestone gates | Partial | ARCHITECTURE.md §6 (Zero Hour era) |
| 39 | Don't claim texture upscaling modernizes the renderer | Done | ARCHITECTURE.md §5; ADR-0007 |
| 40 | Pin build dependencies and document repeatable build steps | Partial | Godot 4.5.1 and Blender 5.2 named in ADR-0007. The Godot export command is not documented; README build steps are for Zero Hour |
| 41 | GAME\_DESIGN.md | Partial | `docs/GAME_DESIGN.md` v0.1 still describes Kestrel, USA vs China and Harbor Divide |
| 42 | Nine faction sheets | Partial | One line per side (GAME\_DESIGN §4). No full sheets |
| 43 | Unit/building counter matrix | Partial | `AB: counter_matrix` and `UnitDefs.ARMOR_MULT` exist; no matrix document |
| 44 | Map specs for five biomes (coastal industrial, dense city, mountain pass, island coast, open) | Partial | Biomes listed. Only Zagros Basin (mountain/basin) is built: `docs/MAP_ZAGROS_BASIN.md` |
| 45 | Harbor Divide as the first map | Superseded | Built only as a Zero Hour map. Replaced in Godot by Zagros Basin (brief 08) |
| 46 | First two playable sides USA and China | Superseded | The client chose Iran as the second nation (briefs 08/09). China not started |
| 47 | UI flow and wireframes | Partial | GAME\_DESIGN §6 is text only. The implemented menus are the real flow |
| 48 | Original art and audio briefs | Done | GAME\_DESIGN §7; `docs/ASSET_GENERATION_README.md` |
| 49 | Acceptance criteria per gate | Done | GAME\_DESIGN §8 (Zero Hour-era wording) |
| 50 | At least one inspectable visual design and a map blockout before final art | Done | scr:`pilot3d_*`, `map_zagros_overview.png`, `map_zagros_routes.png` |
| 51 | B1: original menu, test map, building and unit; unit produced, selected, moved, attacks, destroyed | Done | Godot: scr:`g13_main_menu.png`; `AB: vehicles_produced`; `AT: box_select`, `left_click_move`, `match_end` |
| 52 | B2: separate clean install containing only our content | Partial | No EA data is shipped. A clean-folder file audit has not been done |
| 53 | B2: two playable factions | Partial | USA and Iran are playable. Iran uses U.S. structure models; its Avenger/Paladin are placeholders |
| 54 | B2: one original map | Done | Zagros Basin, `AM: map_loads` |
| 55 | B2: economy and construction | Done | `AB: supply_income`, `dozer_constructs` |
| 56 | B2: three combat roles per faction | Done | Both nations have infantry, armour and aircraft (`AM: iran_roster_models`, `AB: roster_spawns_with_models`) |
| 57 | B2: victory/defeat | Done | `AB: victory_when_enemy_destroyed`; scr:`g13_ui_04_end_screen.png` |
| 58 | B2: one functional AI | Done | `AB: ai_builds_and_earns`, `ai_attacks`; `AM: ai_builds_on_terrain` |
| 59 | B2: save/load | Not started | No game save/load |
| 60 | B3: modernize visual presentation and audio | Partial | 3D models and Pixabay audio are in. No music, no UI sound set, no LODs |
| 61 | B4: remaining sides and maps in tested batches | Partial | Iran added. Five more sides plus China missing, and four more maps |
| 62 | B5: multiplayer, spectator/replay, packaging, release checks | Not started | Planned |
| 63 | At each gate: files, build command, environment, logs, screenshots, defects, next ticket | Partial | Gate reports: `docs/B1_2_BASE_LOOP.md`, `docs/B1_5_ZAGROS_IRAN.md`, `README_PLAYTEST.txt`. No B1.6 report yet |
| 64 | Proof that the AI gathers, builds, produces, attacks, defends and can win or lose | Partial | Gathering, building, attacking and losing are tested. Defending exists in code but is untested. An AI win is not tested |
| 65 | Network claims need two separate clients with content hashes | Deferred | Multiplayer is held for B5 |
| 66 | B1.1 ticket: Kestrel unit and test map on the Zero Hour engine | Superseded | The kit was built and the map loaded; replaced by Godot (ADR-0007) |
| 67 | Tell the client when a new unit/map will be on screen | Done | B1.x builds delivered (`SteelAccord_*_win64.zip`) |
| 68 | No paid API calls | Done | ADR-0007 "No paid generation services" |
| 69 | No public push, tag, upload or distribution without approval | Done | Pushes go only to the approved `EzioDEVio/Steel-Accord` repo; no tag, public release or upload |
| 70 | No fake buttons or mock menus | Done | No dead buttons found; the two stale menu labels were fixed |
| 71 | Engine/platform role: packaging, renderer/UI scaling, save/replay, determinism | Partial | Fixed 30 Hz tick, command log and UI scale exist. Save/replay and a packaging audit are missing |
| 72 | Gameplay systems role: input, commands, economy, production, power, tech, roles, weapons, victory, schemas | Done | `battle.gd`, `unit_defs.gd`, `building_defs.gd`, `upgrades.gd`; AB/AT suites |
| 73 | Faction/balance role: sheets, tech trees, cost/time/counter matrix, matchup tests | Partial | Values marked PROVISIONAL. No matchup or AI-vs-AI win-rate tests |
| 74 | Map/world role: terrain, routes, elevation, chokepoints, fairness, pathfinding checks | Done | `AM: routes_passable`, `cliffs_block`, `starts_fair` |
| 75 | Visual concept role: art direction, silhouettes, icons, menu art, HUD | Partial | Uses client concept packs and icons. No original loading/menu artwork |
| 76 | 3D tech-art role: materials, meshes, rigs, animation, LODs, budgets, in-game checks | Partial | All models load (`AB: all_models_load`). No LODs |
| 77 | Audio role: UI sounds, effects, ambience, music, mixing/looping, licensed voice | Partial | 15 effect clips. No music, UI sounds, ambience or voice acknowledgements |
| 78 | AI role: deterministic build orders, scouting, economy, attack/retreat, per-faction, difficulty tests | Partial | Per-nation unit mixes and research exist (`base_ai.gd`). No scouting, retreat or difficulty tests |
| 79 | UI/UX role: scalable menus, command panel, minimap, production, tooltips, accessibility, remapping, resolution tests | Partial | Remapping, accessibility options and resolution tests are missing |
| 80 | QA role: clean builds, smoke tests, reference validator, save/replay tests, benchmarks, licence audit, package, desync | Partial | Smoke suites exist. The content validator covers Zero Hour only. Save/replay tests, licence audit and benchmarks are missing |

## 02: Prompts 2–10 (Recon, Architect, Build follow-ups and mechanics addendum)

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | P2: deeper recon (source map, asset inventory, legal boundary, build commands, risk-ranked ticket; mark facts O/I/U) | Superseded | RECON.md (Zero Hour, with \[O\] tags) |
| 2 | P3: folder structure, content schema, manifest, reference validator, export pipeline, startup without EA archives | Partial | Godot data lives in `*_defs.gd`. The reference validator is Zero Hour only; Godot has only the `all_models_load` test |
| 3 | P3: AI command boundary and fixed-step simulation | Done | `battle.gd` issue/\_execute at 30 Hz; the AI uses `Battle.issue()`; `AT: command_log` |
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
| 14 | P6: check both factions' economy, build order, counterplay, pathing, UI, save/load, victory, manifest, licences | Partial | Save/load missing; release licence review pending |
| 15 | P6: show the AI scouting, building, producing, attacking and responding to losses | Partial | No scouting or loss response; building and attacking are tested |
| 16 | P6: propose the next batch of factions and maps | Not started | No proposal doc |
| 17 | P6: evidence table (requirement, observation, file/log, result, next fix) | Partial | This tracker covers part of it; no per-requirement observations |
| 18 | P6: keep multiplayer gated until two-client, hash, replay and desync tests | Deferred | Held for B5 |
| 19 | P7: MECHANICS\_REFERENCE\_AUDIT.md with the requested columns | Partial | Columns present; the manual has not been cross-checked |
| 20 | P7: correct the brief's distinctions (3+9 armies, cash vs power, gatherers, Particle Cannon, three progression tracks, no required sidebar, no flow fields) | Done | Rows of MECHANICS\_REFERENCE\_AUDIT.md |
| 21 | P7: classify features as B1 / B2 / later competitive / optional | Done | Phase column of the audit |
| 22 | P8: one spendable credit balance | Done | `battle.cash`; `spend()` |
| 23 | P8: finite, contestable deposits | Done | Pile stock (`AM: starts_fair`); the inspector shows stock |
| 24 | P8: active gatherers that travel and can be intercepted | Done | The CH-47 is a killable unit (`AM: supply_delivery`). No dedicated interception test |
| 25 | P8: optional faction-specific secondary income | Partial | Derricks and the Drop Zone exist but are shared by both nations |
| 26 | P8: neutral capturable economic sites | Done | `AM: derrick_capture`, `derrick_changes_owner` |
| 27 | P8: builder construction, production costs/times, power cap | Done | `building_defs.gd`; AB suite |
| 28 | P8: economy spec with units, formulas, rounding and fixed-step behaviour | Partial | `docs/ECONOMY_SPEC.md` v0.1 uses Zero Hour values that don't match the Godot game |
| 29 | P8: rules for raiding, denying, rebuilding and recapturing income sources | Partial | Derrick recapture and structure rebuild work. Derrick destruction and denial rules not documented |
| 30 | P8: each faction's economic advantage and counterplay | Not started | No USA/Iran economic difference yet |
| 31 | P8: mirrored starts with comparable travel to deposits | Done | `AM: starts_fair` (0.1 %) |
| 32 | P8: minimal B2 economy: gather, spend, lose and replace gatherers, contest a neutral, recover from a depleted node | Partial | Gather, spend, contest and replace work. Recovery from a depleted start node is not tested |
| 33 | P8: measure credit conservation, build orders, replacement time, income curve, snowball risk | Not started | No measurement table |
| 34 | P8: expand the other seven sides only after the two-side economy plays | Done | Followed; only two sides so far |
| 35 | P9: weapons, damage tags and armour classes in data | Done | `unit_defs.gd` weapons; `battle._armor_mult` |
| 36 | P9: projectile travel and splash | Done | Arcing artillery shells, `AB: artillery_range_rules` |
| 37 | P9: target priority, sight/fog, movement, pathfinding | Partial | Fog and pathfinding tested. Target priority rules not documented or tested |
| 38 | P9: unit veterancy | Done | `veterancy.gd`; `AB: veterancy_promotion` |
| 39 | P9: separate commander rank/ability tree | Not started | — |
| 40 | P9: upgrades researched at buildings | Done | `upgrades.gd`; `AB: research_starts` |
| 41 | P9: optional late-game constructed superweapons | Deferred | The brief marks them optional; not built |
| 42 | P9: explicit timing/range/cost/cooldown/damage rules with data validation, no hidden constants | Partial | Values live in defs, but there is no validator. Some constants sit in code (repair rate, difficulty) |
| 43 | P9: first roster shows infantry, vehicle and anti-air counterplay | Done | `AB: counter_matrix` |
| 44 | P9: garrison occupancy and combat rules | Not started | No garrison code (M9) |
| 45 | P9: capturable neutral structures | Done | Oil derricks (any infantry can capture) |
| 46 | P9: elevation, chokepoints, alternative routes | Done | Zagros Basin's three passes; `AM: routes_passable` |
| 47 | P9: destructible/repairable bridges only where pathing supports them | Deferred | The map has no bridges |
| 48 | P9: destructible cover, props and hazard zones | Not started | Props are static |
| 49 | P9: readable visual/audio cue for selection, impacts, veterancy changes, abilities | Partial | Chevrons, "promoted to" message, FX. No sound cues for rank-ups or abilities |
| 50 | P9: combat matrix doc, progression table, test scenarios (garrison, cover, elevation sight, cooldown, DoT) | Partial | Only the counter-matrix test exists; no documents |
| 51 | P9: mark unimplemented features as future tickets, not working buttons | Done | Locked states show reasons, e.g. "Requires Advanced Training" (`AB: battle_plans`) |
| 52 | P10: skirmish settings: maps, sides, teams, starting credits, difficulty, victory conditions, AI personalities | Partial | Map, nations, colours, starting cash, game speed, difficulty and the one victory rule are on the setup screen. Still 1v1, no alternative victory rules, no AI personalities |
| 53 | P10: design a challenge ladder | Not started | — |
| 54 | P10: prepare original campaigns (missions, briefings, triggers, cinematics) | Not started | — |
| 55 | P10: show which systems skirmish, challenges and campaigns share | Not started | — |
| 56 | P10: deterministic AI using the same economy and actions as players | Done | The AI acts only through `Battle.issue()` |
| 57 | P10: disclose scripted or difficulty modifiers | Done | The difficulty tooltip states the AI damage modifier (80 / 100 / 115 %) |
| 58 | P10: local LLM director only later, in single-player | Deferred | Not built |
| 59 | P10: multiplayer engineering (hashes, desync, lobbies, reconnect, observers, telemetry, anti-cheat) | Deferred | B5 |
| 60 | P10: build single-player B2 first | Done | Followed |

## 03: Master handoff (mechanics)

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Nine sides, any as player, ally or AI | Partial | Same as 01-#3 |
| 2 | Fictional tone; Europe as a coalition | Done | GAME\_DESIGN §4 (Europe as a modular coalition) |
| 3 | Core loop (CC, builders, logistics, power, queues, combined arms, fog, controls, tech, veterancy, powers, skirmish AI) | Done | Same as 01-#5…#13 |
| 4 | Saves, replays and multiplayer readiness | Not started | Same as 01-#14…#16 |
| 5 | Legal and content boundaries; independently author everything | Partial | Same as 01-#19 and #30 (manifest incomplete) |
| 6 | Don't pretend to run a Windows build | Done | Same as 01-#25 |
| 7 | Ten specialist roles | Partial | Same as 01-#71…#80 |
| 8 | Faction scale: nine country sides rather than generals | Done | `nations.gd` is built for nine; two exist |
| 9 | Dual constraint: one currency plus power capacity | Done | Same as 01-#21 |
| 10 | Logistics: physical gatherers plus separate secondary income | Done | Same as 01-#22 |
| 11 | Superweapons separate from rank powers and veterancy | Partial | Same as 01-#23 |
| 12 | UI layout modern and scalable, not a required right sidebar | Done | Minimap and Inspector bottom-left, production strip top-left, command card bottom-right |
| 13 | ECS, flow fields, snap grid and rollback are optional proposals | Done | Same as 01-#24 |
| 14 | Verify map objects (bridges, neutrals, garrisons, props) one by one | Partial | Derricks, piles and props verified (`AM: props_grounded`, `sites_grounded`); no bridges or garrisons exist |
| 15 | RECON, ARCHITECTURE, GAME\_DESIGN and MECHANICS\_REFERENCE\_AUDIT docs | Partial | All exist; ARCHITECTURE and GAME\_DESIGN are stale |
| 16 | B1 first playable content | Done | Same as 01-#51 |
| 17 | B2 standalone slice (USA & China, clean folder, save/load) | Partial | USA & Iran instead; no clean-folder audit; no save/load |
| 18 | B3–B5 | Partial | Same as 01-#60…#62 |
| 19 | Start now: recon, docs, B1.1 test procedure | Superseded | Zero Hour B1.1 test kit (`tests/b1/`) |

## 04: Gameplay, movement, UI and assets prompts

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Engine starting point is the SAGE fork | Superseded | ADR-0007 |
| 2 | Keep the Steam install and test copy intact; pin the commit | Done | Same as 01-#27; the pin is superseded |
| 3 | Inventory the U.S. asset packs actually present | Done | `docs/ASSET_REVIEW_US_PACKS.md`, `content/manifest/us_packs.json` |
| 4 | Treat 2D packs as concepts; prove the runtime pipeline before batches | Done | Pilot set first (`docs/PILOT3D_*.md`), then M1–M3 |
| 5 | AT4 shown shoulder-fired in art and animation | Done | scr:`m1_inf_at4_anims.png`; `docs/M1_INFANTRY.md` |
| 6 | P1: manifest with stable IDs, provenance, licence, edits, runtime path, status | Partial | Same as 01-#30 |
| 7 | P1: no fake UI; no claims without evidence | Partial | Same as 01-#70 |
| 8 | P1: match loop (pick faction and map → base → scout → upgrades/abilities → win) | Done | Skirmish menu and AB/AM suites |
| 9 | P2: trace startup, data, GUI, maps, audio, AI, save/replay, network | Superseded | Zero Hour RECON.md |
| 10 | P2: smallest validated pipeline for unit+icon, structure with construction states, map, sound/UI art | Done | Blender → GLB (`tools/art`), `build_reveal.gdshader`, `tools/map/gen_zagros_basin.py`, `tools/audio` |
| 11 | P2: manifests and missing-reference validation | Partial | Only `AB: all_models_load`. No Godot reference validator |
| 12 | P3: stable data for factions, starting forces, units, buildings, movement classes, orders | Done | `nations.gd`, `unit_defs.gd`, `building_defs.gd`, `grid_nav.gd` |
| 13 | P3: data for weapons, armour, queues, costs, prerequisites, rally, upgrades, powers, veterancy, maps, victory | Done | `unit_defs.gd`, `upgrades.gd`, `veterancy.gd`, `maps/zagros_basin/map.json` |
| 14 | P3: AI and humans share one command interface | Done | `Battle.issue()` |
| 15 | P3: consistent save and replay; nondeterminism kept off the frame path | Partial | Fixed tick and command log only; F7 |
| 16 | P3: schema examples and a reference validator | Partial | Same as #11 |
| 17 | P4: click-select, drag-select, add/remove modifiers | Done | `AT: box_select`, `select_all`; Shift adds |
| 18 | P4: right-click to move, attack, board a transport | Done | `AT: left_click_move` (classic scheme); `AB: board_transport` |
| 19 | P4: move, attack, attack-move, stop, guard orders | Done | `AT: guard_order`, `command_card_attack_move`; stop on S (untested) |
| 20 | P4: patrol order | Not started | No patrol code |
| 21 | P4: hold-fire order | Not started | — |
| 22 | P4: capture order | Partial | Capture by standing next to a derrick; no explicit order (F8) |
| 23 | P4: enter/exit transport | Done | `AB: board_transport`, `unload_transport` |
| 24 | P4: garrison | Not started | — |
| 25 | P4: deploy/undeploy where supported | Not started | No deployable units; correctly no generic Deploy button |
| 26 | P4: repair order | Done | `AB: repair_heals_and_costs` |
| 27 | P4: control groups, shift waypoints, rally points, selection feedback, tooltips | Done | `AT: control_group`, `waypoints`; `AB: rally_point` |
| 28 | P4: formations where practical | Not started | Only scatter (X) |
| 29 | P4: configurable hotkeys | Not started | Hard-coded in `commander.gd` |
| 30 | P4: clear feedback for invalid orders | Done | `hud.flash_message` |
| 31 | P4: orders respect terrain, obstacles, occupancy, line of sight, fog | Partial | Terrain, slope and fog respected; terrain does not block line of sight |
| 32 | P4: infantry animation states incl. reload, hit-react, suppressed, enter/exit | Partial | Idle, walk, run, aim, fire, crouch\_fire, die exist. No reload, hit-react, suppression or enter/exit |
| 33 | P4: vehicles: acceleration, turning, reverse, spacing, turret, damage states, repair | Partial | Turrets aim, wheels/tracks animate, repair works. No reverse; damage states unverified |
| 34 | P4: TOW, .50 and medical HMMWV variants with own icons/commands | Done | `hmmwv_tow`, `hmmwv_50cal`, `hmmwv_medical`; scr:`m2_hmmwv_*_sheet.png` |
| 35 | P4: medical HMMWV is a support unit | Done | Heals infantry |
| 36 | P4: define which units carry, deploy or garrison | Partial | Transports defined in data; garrison/deploy not defined |
| 37 | P4: regression tests for select, move, group, attack-move, stop, contextual orders | Partial | AT suite covers all except stop |
| 38 | P5: weapon data: range, damage, cooldown, projectile, targets, effects | Done | `unit_defs.gd` weapons |
| 39 | P5: fictional armour classes | Done | `UnitDefs.ARMOR_MULT` |
| 40 | P5: acquisition, LOS, range, aiming, cooldowns, projectiles, damage feedback, destruction | Done | `AT: f16_missile_strike`, `a10_cannon_fires`; `AB: artillery_range_rules` |
| 41 | P5: role/counter matrix | Partial | Same as 01-#43 |
| 42 | P5: fairness through cost, time, range, survivability, counters | Partial | Values provisional; no balance runs |
| 43 | P5: consistent fog visibility | Done | `AT: fog_of_war` |
| 44 | P5: validate an attack/damage/counter/destruction loop in a match | Done | `AB: counter_matrix`; `AT: match_end` |
| 45 | P6: cash shown separately from power | Done | HUD top centre; scr:`b12_b02_base_overview.png` |
| 46 | P6: active collection vs stored supply vs secondary income | Done | Trends, pile stock, next drop (`econ_panel.gd`) |
| 47 | P6: supply depot and vehicle loop | Done | `AB: depot_gives_hauler`, `supply_income` |
| 48 | P6: supply airdrop with cost, cooldown, quantity; not unbounded passive income | Partial | Drop Zone $2,500, $1,000 every 80 s. No cap while it stands |
| 49 | P6: costs, income, power changes and insufficient-resource states | Done | `econ_panel.gd` tooltips and disabled reasons |
| 50 | P6: Command Center provides the builder | Done | CC produces dozer |
| 51 | P6: footprint validation on valid terrain, no snap grid | Done | `AB: placement_rules`; `AM: steep_placement_rejected` |
| 52 | P6: placement preview, valid/invalid, blocked reason, rotate, cancel | Partial | No rotation; the rest works |
| 53 | P6: construction progress, scaffold, completion, interruption | Done | `build_reveal.gdshader`; `AB: dozer_constructs` |
| 54 | P6: construction queue, prerequisites, repair, sell/cancel with refunds | Done | `AB: sell_refund`, `cancel_refund` |
| 55 | P6: Corps of Engineers construction yard | Not started | — |
| 56 | P6: Barracks / War Factory / Airfield producers | Done | `building_defs.gd` produces lists |
| 57 | P6: queue order, progress, cost, time, cancel/refund, prerequisites, rally, alerts | Done | `AB: queue_units`, `rally_point`, `inspector_building_queue` |
| 58 | P6: reorder queues only if safe | Deferred by design | The brief allows this |
| 59 | P6: full structure list incl. Repair Bay, Field Hospital, Gatehouse, HESCO, defences | Partial | 10 kinds. No Repair Bay building (the War Factory repairs), Field Hospital or Gatehouse |
| 60 | P6: small base loop verified with save/load | Partial | Loop done (AB 18/18); F7 |
| 61 | P7: aircraft takeoff, travel, attack, return, land, rearm | Done | `AT: f16_takeoff`, `f16_return_to_pad`, `f16_rearm` |
| 62 | P7: helicopter vs jet flight profiles | Done | `AT: heli_return_lands_on_pad` |
| 63 | P7: aircraft move, attack-move, attack, return orders | Done | AT air tests |
| 64 | P7: aircraft patrol and looped routes | Not started | — |
| 65 | P7: edit and display waypoint routes | Partial | Waypoint lines shown; not editable; no loops |
| 66 | P7: ammunition/rearm with remaining capability shown | Done | Inspector ammunition line; `AT: f16_rearm` |
| 67 | P7: routes and aircraft state in saves and replays | Not started | F7 |
| 68 | P7: aircraft stay in playable space | Done | `AB: airfield_pads_on_map`, `aircraft_spawn_on_own_pads` |
| 69 | P7: distinct roles for the U.S. aircraft roster | Done | Airfield roster plus support powers; scr:`g11_air_*`, `b14_m3_*` |
| 70 | P7: MOAB strategic ability | Not started | — |
| 71 | P7: Patriot and THAAD air defences | Not started | — |
| 72 | P7: production, route, attack, return, landing/rearm, defensive response | Done | AT air tests; Defense Tower engages aircraft |
| 73 | P8: structures with cost, time, footprint, prerequisites, power, role, health | Done | `building_defs.gd` |
| 74 | P8: Construction Yard, Field Hospital, Patriot/THAAD, Gatehouse | Not started | — |
| 75 | P8: HESCO and barriers interact with pathing, placement, fire, sight | Partial | HESCO blocks movement; no cover or sight rules |
| 76 | P8: build preview and reliable placement feedback | Done | Same as #52 (except rotation) |
| 77 | P8: ownership, damage stages, selection bounds, attack/repair/sell, minimap visibility | Done | Status lights, radar rules |
| 78 | P8: Harbor Divide with elevation and sight-blocking checks | Superseded | Zagros Basin; sight-blocking not checked |
| 79 | P8: pathfinding validated per class | Partial | Infantry, wheeled, tracked tested (`AM: class_slope_rules`); aircraft fly free |
| 80 | P9: top HUD with cash, power, objectives, status, alerts, menu | Partial | No objectives display |
| 81 | P9: minimap overview, camera jump, indicators, pings | Partial | No pings |
| 82 | P9: selection panel with identity, portrait, health, count, status, commands | Done | `AB: inspector_unit`, `inspector_group` |
| 83 | P9: contextual command/build panel | Done | `econ_panel.gd`; scr:`b12_b09_production_card.png` |
| 84 | P9: placement ghost, rings, order markers, target cursor, routes, errors | Done | `hud.gd`, `commander.gd` |
| 85 | P9: scaling, contrast, colour-independent team ID, keyboard remap, tooltips | Partial | UI scale and tooltips only |
| 86 | P9: per-selection options only when valid | Partial | Patrol, hold-fire, deploy, capture, garrison missing |
| 87 | P9: support panel with cost/cooldown and targeting | Done | `AT: support_power_carpet` |
| 88 | P9: main menu shows only working items | Partial | All items work; the stale build label is now fixed (F2) |
| 89 | P9: match setup: faction, opponent, map, team/start, difficulty | Partial | No free team or start-position choice |
| 90 | P9: keyboard and mouse help | Done | Controls screen; F1 help |
| 91 | P9: UI tests at target resolutions, long names, full queues, low resources, power loss, with recording | Partial | Low power and full apron tested; 1080p/1440p/4K captures done (scr:\`b17/\`); no recording or long-name tests |
| 92 | P10: AI gathers, builds, mixes, scouts, defends, attacks, reacts, can win/lose | Partial | Same as 01-#64 |
| 93 | P10: difficulty changes decisions/timing; disclose modifiers | Partial | Timing varies; the damage modifier is now disclosed in the tooltip (F3) |
| 94 | P10: fog and detection the same for player and AI | Partial | Not verified that the AI respects fog |
| 95 | P10: tech, upgrades, veterancy and rank-earned powers | Partial | No rank-earned powers |
| 96 | P10: victory/defeat per mode | Done | `AB: victory_when_enemy_destroyed` |
| 97 | P10: early save/load and replay tests | Not started | F7 |
| 98 | P10: defer online multiplayer | Deferred by design | B5 |
| 99 | P11: verify source crops; no contact sheet used as one unit | Done | `docs/ASSET_REVIEW_US_PACKS.md` |
| 100 | P11: game-ready model, material, rig, animation, icon, effects, audio per asset | Done | M1/M2/M3 docs; `AB: roster_spawns_with_models` |
| 101 | P11: export to a supported format and inspect in-game | Done | GLB; scr:`b14_*`, `m1_*_rts.png` |
| 102 | P11: stable references and provenance in the manifest | Partial | Same as 01-#30 |
| 103 | P11: game data per asset | Done | `unit_defs.gd`, `building_defs.gd` |
| 104 | P11: UI entries, tooltips, hotkeys, AI use and tests per asset | Partial | No per-unit hotkeys; the AI uses part of the roster |
| 105 | P11: scale and readability from the game camera | Partial | Only CH-47 vs Depot scale tested |
| 106 | P11: expand only after USA and China finish a fair match | Superseded | Client prioritised Iran |
| 107 | P12 B1.1: pin the fork, product branch | Superseded | ADR-0007 |
| 108 | P12 B1.1: unit, icon, defs, test map; prove the loop | Done | Same as 01-#51 |
| 109 | P12 B1.2: CC/builder, supply, power, producer, combat unit, defence, UI, victory | Done | `docs/B1_2_BASE_LOOP.md`; AB 18/18 |
| 110 | P12 B2: original content only, clean install, every reference tested | Partial | Same as 01-#52 |
| 111 | P12 B2: Harbor Divide | Superseded | Zagros Basin |
| 112 | P12 B2: two factions, economy, construction, 3 roles, victory, AI, save/load | Partial | Save/load missing; Iran shares structure models |
| 113 | P12 B2: complete human-vs-AI match tested | Partial | Automated runs only; no recorded human match |
| 114 | P12: don't call it standalone before a clean-folder boot | Done | Never labelled standalone |
| 115 | P12 B3–B5 | Partial | Same as 01-#60…#62 |
| 116 | P12: distinguish concept / imported / visible / playable / standalone | Partial | Used in M-docs; no gate table |

## 05: B1.2 playtest QA report

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Keep the spinning helicopter rotors | Done | 3D rotors on CH-47/AH-64/UH-60; scr:`import_rotors.png`, `pilot3d_ch47_*` |
| 2 | Audit every asset as 3D, 2.5D, billboard or sprite | Partial | `docs/ASSET_AUDIT_3D.md` exists but is stale (F5) |
| 3 | Real 3D models for buildings, vehicles, aircraft, infantry, defences | Done | `AB: roster_spawns_with_models`, `all_models_load` (68) |
| 4 | Rotating/tilting the camera keeps assets consistent | Done | scr:`b13_p01_orbit_yaw*`, `b13_p02/p03_tilt_*`, `b14_m1_base_yaw*` |
| 5 | No floating cutouts at normal or close zoom | Done | scr:`b14_m1_close_*`, `b13_p04` |
| 6 | Keep the generated U.S. designs recognisable | Done | scr:`m1_*_vs_concept.png` |
| 7 | Structures seated on terrain; scaffolds share the ground reference | Done | `AM: structures_on_flattened_ground`; scr:`b14_m1_construction.png` |
| 8 | Vehicles follow terrain with ground contact and shadow | Done | `AM: vehicle_drives_on_terrain`, `units_grounded` (0.000 m) |
| 9 | Wheels turn with distance; tracks scroll | Done | `AB: dozer_wheels_and_tracks_animate`; others per `docs/M2_VEHICLES.md` (untested) |
| 10 | Infantry idle, walk/run, combat, fire and death states | Done | `AB: rifleman_animation_states`; scr:`m1_inf_*_anims.png` |
| 11 | Pivot, collision, ring and shadow share one ground anchor | Done | `AM: units_grounded`; `docs/SCALE_GUIDE.md` |
| 12 | Buildings on level and uneven ground while rotating/tilting | Done | `AM: flat_placement_grounded`; scr:`b15_zb_base_*` |
| 13 | Dozer, HMMWV, tank and infantry move without hover, slide, sink or snap | Partial | Dozer, Abrams, rifleman tested. No HMMWV test; slide/snap not measured |
| 14 | Document a world-scale reference | Done | `docs/SCALE_GUIDE.md` |
| 15 | Fix CH-47 scale against the Supply Depot | Done | `AB: scale_ch47_vs_depot` (18.1 m vs 22.0 m) |
| 16 | Collision, selection, shadow and rotor extent match the hull | Done | SCALE\_GUIDE |
| 17 | No camera-dependent scaling | Done | Fixed per-class factors (`UnitDefs.SCALE`) |
| 18 | Compare every unit against the scale guide | Partial | Only the CH-47 is checked automatically |
| 19 | GLB with Node3D/MeshInstance3D; no single flat plane | Done | `godot/assets/units3d/*/*.glb` |
| 20 | Moving parts: turret, wheels/tracks, rotors, skeletal infantry | Done | M1/M2/M3 docs |
| 21 | Building roots at the foundation; unit roots at ground contact | Done | ASSET\_AUDIT\_3D "Grounding" |
| 22 | Materials, lighting, shadows, contact shadows and LODs | Partial | No LODs |
| 23 | Flat images only for UI, minimap and decals | Done | ASSET\_AUDIT\_3D "Deliberate 2D" |
| 24 | Pilot set first, with front/side/rear/top captures | Done | scr:`pilot3d_*` |
| 25 | Four pads defined in Airfield space | Done | `AB: airfield_pads_on_map` |
| 26 | R returns aircraft to a free pad, lands and parks | Done | `AB: aircraft_return_land_on_pad`; `AT: f16_return_to_pad` |
| 27 | Full pads: wait or queue; no stacking; no flight to map edge | Done | `AB: full_apron_refuses_more` ("No free pad") |
| 28 | No stranded aircraft and no false "landed" | Done | 0.00 m LANDED in test output |
| 29 | Test F-16/A-10/AH-64 after combat, near edges, after camera rotation | Partial | Return tested for all three; no edge/rotation cases |
| 30 | Repair a damaged friendly building with cost tooltip; start/stop/resume | Done | `AB: repair_heals_and_costs`, `repair_stop` |
| 31 | Repair spends cash; pauses without cash; disabled at full health | Done | `AB: repair_pauses_without_cash`, `repair_completes_and_disables` |
| 32 | Destroyed building leaves rubble; rebuilt at normal cost and time | Done | `AB: rubble_left`, `rebuild_from_rubble`, `rebuild_completes` |
| 33 | Only friendly structures can be repaired or rebuilt | Done | `battle.rubble_at(gr, team)` |
| 34 | UI distinguishes repair from rebuild | Done | Separate actions; "Cannot rebuild …" |
| 35 | Core loop: preview, power, queues, orders, roles, readable UI | Done | AB/AT suites |
| 36 | Airfield sortie cycle with rearm/repair | Done | `AT: f16_rearm`; pad repair |
| 37 | Replace weak audio with licensed sounds | Partial | 14 Pixabay clips (`audio.json`). No infantry acknowledgements; only the Farsi shout as voice |
| 38 | Spatialised, balanced mix | Partial | Distance falloff (`sfx.gd`); an effects-volume slider is now in Options. No mixer buses |
| 39 | Rotor audio follows helicopter state | Partial | `heli_loop` attached; sync untested |
| 40 | Reproduce each issue, fix at the right level, report steps/files/tests | Partial | Fix list in `README_PLAYTEST.txt`; no reproduction doc |
| 41 | Prioritised plan, high-priority fixes first | Done | ASSET\_AUDIT\_3D "planned order"; P0/P1 done |

## 06: Modern UI, economy and mechanics

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Limited, threatenable supply; visible gatherers and deliveries | Done | Same as 02-#23/#24 |
| 2 | Low power slows production/construction/towers, radar off; UI says what is impaired | Done | `AB: low_power_state`, `low_power_slows_production` |
| 3 | Cash, income/spending trend, power, why tasks are blocked | Done | `econ_panel.gd` |
| 4 | Dozer builds and repairs damaged structures | Partial | Repair is a paid building action, not done by the Dozer; EOD engineers repair nearby |
| 5 | Producer buildings have clear roles | Done | `building_defs.gd` |
| 6 | Readable tech tree: locked items, exact requirement, cost | Done | "Requires …" (`econ_panel.gd`, `inspector.gd`) |
| 7 | Upgrades researched at specific buildings | Done | `upgrades.gd` "at" |
| 8 | Per-producer queues; global production strip | Done | Strip top-left; `AB: inspector_building_queue` |
| 9 | War Factory repairs vehicles; Barracks heals infantry; Airfield services 4 aircraft | Partial | `AB: war_factory_repairs_vehicle`; Airfield done. The Barracks does not heal |
| 10 | Full aircraft lifecycle with pad occupancy shown | Done | `AB: inspector_airfield_pads` |
| 11 | Transport capacity, compatibility, passengers, refusal reasons | Done | "has room for N" (`commander.gd`) |
| 12 | Don't turn the supply CH-47 into a troop transport | Done | UH-60 does air assault |
| 13 | Board, Unload one, Unload all; safe dismount | Partial | `AB: unload_transport`. No player-chosen dismount point |
| 14 | Transport controls only on transports | Done | Only defs with "transport" get controls |
| 15 | Orders discoverable with icons, labels, tooltips, hotkey hints | Done | `hud.gd` help; command card |
| 16 | Plain-language roles | Done | `role` field in the Inspector |
| 17 | Build menu from implemented data only | Done | `Nations.produces` |
| 18 | Data model ready for another faction | Done | Iran via `nations.gd` |
| 19 | Top bar: cash, trend, power, low-power state, alerts | Done | `hud.gd` |
| 20 | Map: rings, health bars, markers, rally, footprints, pad markers | Done | scr:`g11_air_01_pads_f16_selected.png`, `b12_b07` |
| 21 | Minimap: units, structures, camera rectangle, base, alerts | Partial | No alerts on the minimap |
| 22 | Selected-object panel updates immediately | Done | `AB: inspector_unit` |
| 23 | Building card: Overview, Production, Upgrades, Services | Done | `inspector.gd`; Production/Upgrades tabs in the command card (3196ef6) |
| 24 | Clicking a production-strip entry focuses the producer | Done | README\_PLAYTEST B1.4 (no automated test) |
| 25 | Tooltips: effect, cost, time, prerequisites, scope, hotkey | Partial | Hotkeys not shown on most tooltips |
| 26 | Responsive sizing at common resolutions | Done | HUD and menus scale 1.0 / 1.33 / 2.0; no overlap at 1080p, 1440p, 4K (scr:\`b17/ui\_\*\`, \`b17/skirmish\_\*\`) |
| 27 | Full building panel incl. queue, ETA, rally, disabled reason | Partial | All except queue reordering |
| 28 | Per-building contents | Done | `inspector.gd` |
| 29 | Real progress bars; cooldowns for powers | Done | Inspector ETA; `AB: research_starts` |
| 30 | Consistent queue states; no ETA while blocked | Partial | Only repair shows "Paused: reason" |
| 31 | One rule for cash deduction and refunds | Done | Charged on queue, full refund on cancel |
| 32 | Progress bars move only with real progress | Done | `AB: low_power_slows_production` |
| 33 | One authoritative economy for UI, AI and production | Done | `battle.cash`, `spend()` |
| 34 | Supply left at each source; gatherer routes | Done | Inspector supply stock |
| 35 | CH-47 states incl. Damaged, Blocked | Partial | Loading, Returning, Unloading only |
| 36 | Supply drops only when the structure exists | Done | `drop_zone` |
| 37 | Costs, times, refunds, prerequisites, power in data | Done | `building_defs.gd`, `upgrades.gd` |
| 38 | Dozer catalog shows cost, time, power, prerequisites, footprint, validity | Done | `econ_panel.gd` |
| 39 | Invalid placement explains why | Done | `AB: placement_rules` |
| 40 | Units exit to the rally point | Done | `AB: infantry_produced_to_rally` |
| 41 | Upgrades are real state changes | Done | `AB: composite_armor_effect` |
| 42 | Never list aircraft at the Barracks | Done | `building_defs.gd` |
| 43 | Repair by ordering a Dozer | Partial | Same as #4 |
| 44 | Repair must not resurrect a destroyed building | Done | Separate rubble/rebuild flow |
| 45 | War Factory repair bay one vehicle at a time | Partial | Heals all nearby at once; no occupancy |
| 46 | Airfield repairs, rearms and reserves pads | Done | `AB: aircraft_return_land_on_pad`, `full_apron_refuses_more` |
| 47 | Service cost, progress, blocked reason, funds | Partial | Building repair only; vehicle/aircraft service free with no progress UI |
| 48 | Transport definition incl. slot size, firing from inside | Partial | Capacity and accepted types only |
| 49 | Infantry board, or the transport picks up nearby units | Partial | Infantry → transport click only |
| 50 | Passenger list with occupied/total capacity | Done | Inspector passengers |
| 51 | Embark/disembark animation; documented passenger rules | Partial | Rules now in `docs/M4_TRANSPORT.md` (F4 fixed); no embark animation |
| 52 | Announce what happens to passengers when a transport dies | Done | All passengers die; rule in `M4_TRANSPORT.md` and an on-screen loss message |
| 53 | Configure HMMWV troop capacity | Done | HMMWV 5, MRAP 4 |
| 54 | No transport controls on other units | Done | Same as #14 |
| 55 | One source of truth; no duplicate managers | Done | `battle.gd` owns state |
| 56 | P1: implemented/partial/missing matrix with files | Partial | This tracker serves that role |
| 57 | P7: full-loop QA incl. destroyed producers | Partial | All except destroyed producers |
| 58 | Every building opens the correct panel | Partial | Barracks and Airfield tested; others captured in brief-10 screenshots |
| 59 | Airfield lists aircraft, real upgrades, four pad states | Done | `AB: inspector_airfield_pads` |
| 60 | Existing combat, selection, camera, hotkeys, AI still work | Done | AT 22/22, AB 35/35 + 18/18 (re-run pending after 3196ef6) |
| 61 | No fake controls, queues, upgrades or progress | Partial | Same as 01-#70 |

## 07: USA progression and Object Inspector (final consolidated handoff)

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Keep the B1.2 baseline incl. support power cards | Done | `nations.gd` usa powers; `AT: support_power_*` |
| 2 | Keep generated art out of menus until the unit exists | Done | Same as 06-#17 |
| 3 | Map C&C names to Steel Accord names | Done | `building_defs.gd` |
| 4 | Strategic Operations Center, or a CC module | Done | Module on the CC: Advanced Training and plans (`upgrades.gd`) |
| 5 | Don't relabel the Defense Tower as Patriot | Done | Still "Defense Tower" |
| 6 | Patriot battery once its systems exist | Not started | — |
| 7 | THAAD only if missiles can be intercepted | Deferred by design | No interception system |
| 8 | Field artillery emplacement (optional) | Deferred by design | Optional |
| 9 | MOAB via Carpet Bombing, gated by commander rank | Deferred by design | No rank system |
| 10 | Commander rank using the existing system | Not started | — |
| 11 | Costs and times in data; no "$?" | Done | `upgrades.gd` |
| 12 | Capture only for a designated Engineer | Partial | F8 |
| 13 | Medic as a Barracks unit with real healing | Done | `medic`, `ir_medic`; scr:`m1_inf_medic_anims.png` |
| 14 | Barracks as a treatment point (optional) | Not started | — |
| 15 | Flashbangs for Rangers | Not started | — |
| 16 | Exosuits → "Advanced Combat Armor" research | Partial | adv\_armor (−15 %); effect untested |
| 17 | Advanced Training gives more XP, no instant promotions | Partial | xp×1.5; XP effect untested |
| 18 | Composite Armor only for compatible armour | Done | `AB: composite_armor_effect` |
| 19 | HMMWV TOW as a separate variant | Done | `hmmwv_tow` |
| 20 | War Factory vehicle repair with availability, progress, cost | Partial | Same as 06-#45/#47 |
| 21 | No empty drone category | Done | None exists |
| 22 | Drones as real units | Deferred by design | Shahed exists only as a support power |
| 23 | Vehicle upgrades scoped by tags; UI names units affected | Done | `SCOPE_TEXT`; `AB: inspector_upgrade_states` |
| 24 | Rocket Pods on compatible aircraft | Not started | — |
| 25 | Guided Munitions for air-to-ground aircraft | Partial | Scope air\_ground; effect untested |
| 26 | Countermeasures only if missiles lock on | Deferred by design | No lock system |
| 27 | Hardened-Target Munitions | Not started | — |
| 28 | Airfield shows four pads and real aircraft states | Done | `AB: inspector_airfield_pads` |
| 29 | Research tab | Done | Research section; Upgrades tab in the command card |
| 30 | Battle Plans: one at a time, switch delay | Done | `AB: battle_plans` (15 s) |
| 31 | Intelligence tab connected to Recon Overflight | Not started | — |
| 32 | Active plan shown in HUD and unit inspectors | Done | `hud.gd` |
| 33 | Supply Line Efficiency +10 % without double counting | Partial | income×1.10; untested |
| 34 | Scout Armor | Deferred by design | Needs scout drones |
| 35 | Hazard Protection | Deferred by design | No hazard damage |
| 36 | Shared inspector header | Done | `AB: inspector_unit` |
| 37 | Building inspector fields | Done | `AB: inspector_building_queue`, `inspector_airfield_pads` |
| 38 | Unit inspector: role, order, weapons, veterancy, upgrades, ammo, passengers | Done | `AB: veterancy_promotion`, `inspector_upgrade_states` |
| 39 | Upgrade states Installed/Available/Researching/Locked | Done | `AB: inspector_upgrade_states` |
| 40 | Group inspector: counts, roster, no merged upgrades | Done | `AB: inspector_group` |
| 41 | Left-click opens; right-click unchanged; empty ground clears; no pause | Done | `AB: inspector_pin`; AT suite |
| 42 | Inspector readable at 1080p/1440p/4K without overlap | Done | Captured at 1080p, 1440p and 4K with no overlap (scr:\`b17/ui\_\*\`) |
| 43 | Veterancy separate from commander rank; data-driven | Done | `veterancy.gd` |
| 44 | Support units earn XP from support actions | Done | `unit.gd` healing/repair XP |
| 45 | Rank-up notification, badge, bonus, next threshold | Done | `battle.gd`, chevrons in `hud.gd` |
| 46 | Implementation order §6 steps 1–9 | Partial | Steps 1–4 done |
| 47 | Feature matrix doc | Not started | — |
| 48 | Fortifications: concrete wall and earth berm | Not started | M9 |
| 49 | Drag-placed wall lines | Not started | — |
| 50 | Wall collision, gates, pathfinding | Not started | — |
| 51 | Destructible, repairable walls | Not started | — |
| 52 | Infantry garrison a HESCO Fighting Position | Not started | — |
| 53 | HESCO capacity, occupants, firing ports, cover | Not started | — |
| 54 | Occupants ejected when HESCO destroyed | Not started | — |
| 55 | Fortification acceptance tests 1–6 | Not started | — |
| 56 | Builder visible with distinct silhouette and far-zoom icon | Partial | No far-zoom icon |
| 57 | Builder status control and Find Builder | Not started | M10 |
| 58 | Builder inspector: target, progress, blocked reason | Partial | Catalog only |
| 59 | Warning when the builder dies | Partial | CC can rebuild; no warning |
| 60 | Far-zoom readability: LODs, class icons | Not started | M10 |
| 61 | No enlarged distant meshes | Done | Fixed scale factors |
| 62 | Mid/close detail | Done | scr:`b14_m1_close_*`, `ir_*_sheet.png` |
| 63 | Contrast; colour-blind-safe team ID | Partial | Team paint and rim light; selectable team colours (3196ef6); no colour-blind option |
| 64 | Hover and selection highlights | Done | Rings |
| 65 | Free orbit around a selected object; recenter | Partial | Middle-drag rotate, tilt, Home resets; no focus orbit |
| 66 | Camera never clips terrain | Done | Camera follows terrain |
| 67 | Camera speed and inversion | Partial | Speed only |
| 68 | Readable map layout | Done | scr:`map_zagros_routes.png` |
| 69 | Coherent terrain materials | Done | Splat shader (ADR-0008) |
| 70 | Balanced lighting; fog distinct from haze | Partial | Haze reduced on terrain maps; no before/after review |
| 71 | Crisp detail without blur or halos | Partial | Not reviewed systematically |
| 72 | Visual quality settings | Not started | — |
| 73 | Faction data drives names, palette, roster, assets, doctrine, voices | Partial | Names, flags, roster, powers, structure/research/plan labels and battle cry per nation. Palette and structure models shared |
| 74 | Faction-specific building labels | Done | Iran labels via `Nations.label` / `battle.bname` (3196ef6) |
| 75 | Don't reuse U.S. models as another nation's | Partial | Iran uses U.S. structure models and placeholder Avenger/Paladin |
| 76 | Accessibility options global | Partial | Few options |
| 77 | Presentation acceptance tests 1–7 | Partial | #6 met; #7 (1080p–4K) in progress |
| 78 | Stale "Defense Tower 84 %" progress | Not started | — |
| 79 | Infantry readable at strategic zoom | Partial | 1.3× scale; no test |
| 80 | A-10 scale near the Airfield | Partial | 0.6×; no test |
| 81 | Bomber cinematic camera | Not started | — |
| 82 | Pale weapon trails and smoke | Not started | — |
| 83 | Small or clipped UI labels | Partial | Text buttons wrap (3196ef6); no measured fix |
| 84 | Volume controls | Done (code) | "Effects volume" slider drives `sfx_volume` |
| 85 | Subtitles | Not started | — |
| 86 | Distinct voice responses per unit | Not started | — |
| 87 | Clean capture | Partial | Game capture scripts; no promo recording |
| 88 | §10 items repeated from 05/06 | Done | Same as 05-#25…#36, 06-#11…#14 |

## 08: Zagros Basin (Iran) map prompt

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Inspect map, terrain, movement, placement, resources, renderer; report files and risks first | Done | `docs/MAP_ZAGROS_BASIN.md`, ADR-0008 |
| 2 | Fictional Zagros-foothills/basin sector | Done | `maps/zagros_basin`; scr:`b15_zb_overview.png` |
| 3 | Real public elevation for broad shape only | Partial | DEM download refused (403), so relief is synthetic; the generator accepts a DEM |
| 4 | Invent all bases, roads, towns, supplies, derricks | Done | `tools/map/gen_zagros_basin.py` |
| 5 | Playable area about 4–6 km | Partial | 1.2 × 1.2 km, scaled down deliberately for RTS pace |
| 6 | Evaluate Terrain3D 1.0.2 incl. Windows export | Done | ADR-0008: not adopted; built-in heightfield used |
| 7 | High-bit-depth heightmap | Done | R16 601×601 |
| 8 | Sand, rock, gravel, scrub, riverbed, road materials | Done | `terrain_map.gdshader` splat |
| 9 | Pads, balanced starts, supplies, derricks, roads, ridges, valleys, boundaries | Done | `AM: starts_from_map`, `starts_fair`, `sites_grounded` |
| 10 | Finite supplies delivered to a supply center | Done | `AM: supply_delivery` |
| 11 | Capturable derricks with recurring income | Done | `AM: derrick_capture`, `derrick_income` |
| 12 | Ground everything through a terrain query | Done | `AM: units_grounded`, `props_grounded` (0.000 m) |
| 13 | Reject placement on steep slopes | Done | `AM: steep_placement_rejected` |
| 14 | Per-class slope rules for navigation | Done | `AM: class_slope_rules`, `cliffs_block` |
| 15 | Resources, income, starts, terrain costs in data | Done | `maps/zagros_basin/map.json` |
| 16 | Map loads and runs | Done | `AM: map_loads` (Wine export too) |
| 17 | No floating or sinking buildings | Done | `AM: structures_on_flattened_ground` |
| 18 | Routes passable, cliffs block | Done | `AM: routes_passable`, `cliffs_block` |
| 19 | Comparable resource access for both starts | Done | `AM: starts_fair` |
| 20 | Derricks change owner | Done | `AM: derrick_changes_owner` |
| 21 | Supply delivery updates the economy | Done | `AM: supply_delivery` |
| 22 | RTS-camera screenshots and changed files | Done | scr:`b15_zb_*`; `docs/B1_5_ZAGROS_IRAN.md` |
| 23 | Preserve existing gameplay | Done | Proving Ground kept; QA, base, army suites passed (B1.5) |

## 09: Iran arsenal handoff

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Read the README and six sheets as concept art only | Done | `docs/reference/iran_pack/` |
| 2 | Don't break existing USA assets, mechanics, UI or scenes | Done | AB/AT regression suites |
| 3 | Data-driven faction with own unit and building definitions | Partial | Units in `nations.gd`; Iranian building labels exist but buildings share U.S. definitions and models |
| 4 | Never treat a contact sheet as one object | Done | Separate GLB per panel |
| 5 | Real 3D meshes with consistent scale and ground contact | Done | `AM: iran_roster_models`; scr:`ir_*_sheet.png` |
| 6 | Sheet 01: Karrar, T-72S, BMP-2, Boragh, engineer vehicle | Done | `docs/IRAN_VEHICLES_WAVE1.md` |
| 7 | Sheet 01: Zulfiqar, Chieftain, BTR-60, M113, Raad-1, M109, Fajr | Not started | Wave 2; Avenger/Paladin remain placeholders |
| 8 | Sheet 02: F-14, F-4, Su-24, AH-1J, CH-47C, C-130, Shahed-136 | Done | `docs/IRAN_AIRCRAFT_WAVE1.md`; `AM: iran_shahed_strike` |
| 9 | Sheet 02: F-5, F-7, MiG-29, Mirage F1, Su-22 | Not started | — |
| 10 | Sheet 03 missiles/air defence | Not started | — |
| 11 | Sheet 04 troop roles | Partial | 8 roles done (`docs/IRAN_INFANTRY.md`); Basij reserve, squad leader, officer, tank crew, pilot, AD operator missing |
| 12 | Medic with Red Crescent marking | Partial | Kept unmarked on purpose: protected emblems are not used in the game |
| 13 | Rank-insignia sheet not presented as official | Done | Not used |
| 14 | Sheet 06 installations | Not started | Iran uses U.S. structure models |
| 15 | Report asset mapping and 3D-vs-sprite decision first | Done | IRAN\_\*\_WAVE1.md, IRAN\_INFANTRY.md mapping tables |
| 16 | Small testable steps; report files and tests | Partial | Per-asset commits; no B1.6 report (F6) |
| 17 | Don't publish or release anything | Partial | Same as 01-#69 |

## 10: UI Inspector panels, Iran and Skirmish setup

The screenshots and CNCNZ page mentioned in this brief did not reach the project; items were judged from the brief's text. Full report: `docs/B1_7_UI_IRAN.md`.

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Report existing UI, faction data, selection, queues, upgrades and their files | Done | `docs/B1_7_UI_IRAN.md` §1 |
| 2 | Use CNCNZ only as an organisation pattern; copy no data | Done | No CNCNZ data in the source |
| 3 | Left-click opens or updates one inspector; right-click unchanged | Done | `AB: inspector_unit`, `inspector_pin`; AT 22/22 |
| 4 | Unit inspector: faction name, type, role, portrait/icon, owner | Done | scr:`b17/ui_1080_karrar.png` |
| 5 | Unit inspector: health, state/order, weapons/loadout | Done | Iranian weapon names ("125mm main gun") |
| 6 | Unit inspector: upgrade states and veterancy with bonuses | Done | `AB: inspector_upgrade_states`; scr Karrar (Veteran, XP 120/250) |
| 7 | Abilities, cooldowns, service, transport only when implemented | Done | Passengers, pads, ammo; no unit abilities exist, so none shown |
| 8 | Building inspector: name, purpose, health, state, power, prerequisites | Done | scr:`b17/ui_1080_warfactory.png` |
| 9 | Building inspector: production, queue, progress, blocked reason | Done | Same |
| 10 | Upgrades separate from production | Done | Inspector sections; command-card tabs |
| 11 | One authoritative state | Done | Single state line |
| 12 | War Factory panel | Done | Armour Works: Karrar 63% ETA, BMP-2 queued, Reactive Armour Kits 20% |
| 13 | Airfield panel: aircraft apart from research; four pads | Done | scr:`b17/ui_1080_airfield.png` (Pads 2/4 in use) |
| 14 | Barracks panel: infantry and upgrades; medical only if real | Done | scr:`b17/ui_1080_barracks.png`; no Barracks healing, so none shown |
| 15 | Command Center panel: builders, construction, command functions | Done | scr:`b17/ui_1080_cc.png` (Builders 1, 9 structure types, plans) |
| 16 | Other buildings by purpose | Done | Power, depot stock, drop timer, defence |
| 17 | Overview / Production / Upgrades / Services sections | Done | `inspector.gd` |
| 18 | Each item: icon, name, cost, prerequisite, progress or lock reason | Partial | Production cards have icons; research cards are text only |
| 19 | Consistent typography and spacing; panels don't overlap | Done | No overlap at 1080p/1440p/4K (scr:`b17/`) |
| 20 | Tooltips on icon-only controls | Done | `tooltip_text` throughout |
| 21 | Skirmish: player slots | Partial | Two-slot table; no more slots |
| 22 | Skirmish: faction/army | Done | scr:`b17/skirmish_1080.png` |
| 23 | Skirmish: colour | Done | Colour pickers drive HUD, minimap, rings |
| 24 | Skirmish: teams | Partial | Team column; no allied teams |
| 25 | Skirmish: map preview and selection | Done | Preview + map facts |
| 26 | Skirmish: starting resources | Done | $5k / $10k / $20k |
| 27 | Skirmish: game speed | Done | 75 / 100 / 125 % |
| 28 | Skirmish: match rules | Partial | The single implemented rule is shown |
| 29 | Skirmish: launch and back | Done | Start Match / Back |
| 30 | Skirmish screen scales cleanly | Done | Menu scaling added; scr:`b17/skirmish_4k.jpg` vs `before/skirmish_4k_unscaled.jpg`. Dropdown lists still unscaled |
| 31 | Iran's own terminology and roster | Done | Command Headquarters, Armour Works, Air Base, Reactive Armour Kits, Iranian weapon names |
| 32 | Inspector and layout shared across nations | Done | One `inspector.gd` |
| 33 | Test: Iranian soldier, Karrar, tactical vehicle, aircraft, Airfield, War Factory, Barracks, CC | Done | 9 captures per resolution (`b17/ui_*`); visual evidence, no automated assertions |
| 34 | Test: panels update live | Partial | Captures show progress, damage, XP and pad states; live updates asserted only on U.S. objects |
| 35 | Test: 1080p, 1440p and 4K | Done | `b17/ui_1080_*`, `ui_1440_*`, `ui_4k_*` |
| 36 | Test: inspection doesn't break selection, right-click, hotkeys, camera | Done | AT 22/22, QA 35/35 |
| 37 | Before/after screenshots, changed files, unsupported fields | Done | `docs/B1_7_UI_IRAN.md` §2–§4; `b17/before/` |

## Chat requests

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Spinning helicopter rotors | Done | Same as 05-#1 |
| 2 | Tanks visible against the terrain | Done | Team paint and rim light; scr:`b12_tank_team_paint.png`, `b15_zb_tanks_on_slope.png`. Far-zoom readability open (07-#60) |
| 3 | Add the supplied audio (A-10 etc.) | Done | `content/manifest/audio.json` (14 clips); `AT: a10_cannon_fires` |
| 4 | Real 3D models instead of flat cards | Done | Same as 05-#3 |
| 5 | Fix grounding and scale (Chinook too big) | Done | Same as 05-#8, #15 |
| 6 | Aircraft park on Airfield pads | Done | Same as 05-#26 |
| 7 | Repair and rebuild | Done | Same as 05-#30…#32 |
| 8 | AT4 animated like the rifleman | Done | scr:`m1_inf_at4_anims.png` |
| 9 | Buildings must not float or move with the cursor | Done | Same as 05-#7 |
| 10 | Flashing status lights on buildings | Done | `building.gd` status lights; scr:`b14_m1_close_*` |
| 11 | Supply Drop Zone | Done | `AB: supply_drop_zone_income` |
| 12 | Airfield redesigned with a runway | Done | scr:`m1_airfield_*`; `AT: f16_takeoff` |
| 13 | Full War Factory roster in 3D | Done | 12 vehicles; scr:`m2_*_sheet.png` |
| 14 | All aircraft in 3D | Done | `docs/M3_AIRCRAFT.md` |
| 15 | Vehicles repaired at the War Factory, aircraft at the Airfield | Done | `AB: war_factory_repairs_vehicle`; `AT: f16_rearm` |
| 16 | Paratroopers with parachutes | Done | `AB: paratroopers_land` |
| 17 | Air assault and troop transports | Done | `AB: air_assault_board`, `air_assault_unload` |
| 18 | Milestones delivered per push | Done | Builds B1.2…B1.6; per-milestone commits |
| 19 | Keep the U.S. star on U.S. aircraft | Done | `nations.gd`; B1.5 report |
| 20 | Iran faction with beard/moustache/shaven mix | Done | `AM: ai_nation_roster`; scr:`ir_faces.png` |
| 21 | Iranian flag | Done | `AM: nation_flag`; scr:`flags.png` |
| 22 | IRGC special unit | Done | `irgc_sf` |
| 23 | Farsi battle shout when Iranians attack | Done | `AM: iran_battle_cry` (14 s cooldown per side). Audio source/licence still to confirm before release |
| 24 | Iranian vehicles and aircraft from the arsenal pack | Partial | Wave 1 done; wave 2 and Iranian structures missing |

## 11: Zero Hour-style control bar (chat request, Oct 22)

Reference: the Zero Hour engine source (`ControlBar.cpp`: 14 command buttons in 2 rows of 7; right HUD portrait with veterancy overlay and up to 5 upgrade cameos lit when installed; up to 9 build-queue buttons) and the client's screenshots. Layout and behaviour follow that pattern; all art, icons and the frame are original (`content/manifest/ui_icons.json`). Report: B1.8 notes in `build/win/README_PLAYTEST.txt`; screens in `docs/screens/b18/`.

| # | Request | Status | Evidence / what is missing |
| --- | --- | --- | --- |
| 1 | Research the Zero Hour interface (command panel tiles, unit status panel) | Done | Engine source read; StrategyWiki controls page; CommandSet slot layout |
| 2 | Building selected: a panel of tiles listing everything it can build, research and do | Done | 2×7 grid: units (cost, queued count, progress sweep), research (amber, tick when installed), plans (teal), Repair/Sell fixed last; scr:`b18/ui_1080_warfactory.png`, `ui_1080_cc.png` |
| 3 | Same for every building | Done | Barracks, Armour Works, Air Base, Command HQ captured; grid is generic |
| 4 | Soldier selected: window of tiles with completed training and equipment status | Done | Selection panel: portrait + rank, health, state, XP, and up to 5 research tiles that apply to the unit (lit = installed, dim = not yet) plus the active plan; scr:`b18/ui_1080_soldier.png`, `ui_1080_karrar.png` |
| 5 | Specific Zero Hour upgrades (chemical suits, flashbangs) | Not started | Those upgrades do not exist in Steel Accord; the tiles show our real research only |
| 6 | Number troops, vehicles and tanks into groups | Done | Ctrl+0..9; a unit is in one group at a time; number shown next to its health bar and on the portrait; scr:`b18/ui_1080_group.png` |
| 7 | Ctrl+A select all | Done | Existing; also a Select All tile; plus Q / E / H / . / Space hotkeys |
| 8 | Name groups | Not started | Groups are numbered only; naming was not built (ask if wanted) |
| 9 | Tidy, consistently placed panels | Done | One framed bar: radar, side buttons, grid, selection panel; cash tab and power gauge on top; Details panel only on request |
| 10 | Double selection rings and floating health bars | Done | One ring per unit; bars anchored to each model's top |
| 11 | Units stacking in single file | Done | AI group orders spread into a grid; infantry spacing widened |
| 12 | 1080p / 1440p / 4K | Done | scr:`b18/ui_*`; bar shrinks to fit screens narrower than 1404 px |
| 13 | Windows build | Done | B1.8; Wine: map 24/24, QA 35/35 (not a real Windows PC) |
