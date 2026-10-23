# Claude Handoff Prompts — Modern RTS Gameplay, Movement, UI, and Assets

**Working title:** Modern RTS  
**Project:** An original standalone real-time strategy game inspired by the pace, base-building loop, and familiar controls of Command & Conquer: Generals — Zero Hour.  
**How to use this file:** Start with Prompt 1 in Claude. Give Claude the asset ZIPs and source checkout if those files are not already available in its project. Use the follow-up prompts one at a time as Claude reaches each phase. Do not paste every follow-up prompt into one request; the phase prompts depend on findings from earlier work.

## Existing project facts Claude must preserve

- The intended engine starting point is the SAGE-derived GeneralsGameCode fork: https://github.com/TheSuperHackers/GeneralsGameCode
- The fork has been built on the user's Windows PC and launched in an isolated copy of the licensed game; an original-game skirmish works. That proves the engine baseline only. The new Modern RTS does not yet have its own integrated content or standalone build.
- Known source checkout: C:/Users/moham/Downloads/PROJECT-ZERO-HOUR/engine
- Known Steam installation: C:/Program Files (x86)/Steam/steamapps/common/Command & Conquer Generals - Zero Hour
- Do not modify the Steam installation or destroy/overwrite the known-good isolated test copy. Work on a separate product branch and development copy. Pin and report the source commit.
- The first playable faction pair is provisionally USA and China. The first original test map is Harbor Divide. The longer-term faction roadmap is Iran, Iraq, North Korea, Taiwan, China, Japan, a Europe coalition, Ukraine, and USA.
- The prior project plan sets B1.1 as the first visible implementation: one original unit, an icon, and a small original map; the unit must be produced or spawned, selected, moved, ordered to attack, damaged, and destroyed.
- If the Windows checkout is not accessible from Claude's environment, Claude must say so plainly, prepare reviewable patches/assets where possible, and give the exact files or access needed. It must never claim it built or ran the user's Windows copy without evidence.

## Generated U.S. asset packs to inspect

Ask Claude to inventory the files actually present in the project or attached archives. The names below are references from our asset work; verify availability before claiming access.

- US_Aircraft_Game_Assets_Expanded.zip — B-1, B-2, B-52, F-16, F-18, F-22 Raptor, Chinook, Black Hawk, Apache, A-10, MOAB bomb, SR-71, THAAD, and Patriot missile-defense concepts.
- US_Ground_Forces_Game_Assets.zip — tanks, artillery/Paladin, HMMWVs, MRAPs, Strykers, Avenger and related ground-vehicle concepts. The HMMWV set includes a TOW-missile version, a turret-mounted .50-caliber version, and a medical version with a red-cross symbol.
- US_Armed_Forces_Personnel_Assets.zip — Army infantry, EOD engineers, sniper, 75th Rangers, medics, Special Forces, Air Force pilots with and without helmets, and support personnel. Weapon concepts include equipped riflemen, M249 SAW, M240B, and AT4.
- US_Installation_Game_Assets.zip — 14 structure concepts with four views each and individual transparent crops: command center, fortified defense tower, airfield, war factory, barracks, supply depot, supply airdrop zone, Corps of Engineers construction yard, HESCO defense position, radar/communications station, power generator, vehicle repair bay, field hospital, and perimeter gatehouse.

These generated images are static 2D references. They are not rigged models, animated sprite sequences, or automatically valid engine files. Use them as concept references and, where they are cleanly cropped, as portraits or button art. Inspect and prove the engine's supported runtime asset pipeline—expected to use W3D-compatible models and map formats—before producing batches of final models. The AT4 must be portrayed as shoulder-fired in the game art and animations.

## Prompt 1 — Master project handoff

You are Claude acting as senior game developer and technical lead for the Modern RTS project. Your goal is to help implement and validate a playable original RTS using the existing SAGE-derived GeneralsGameCode fork as the starting engine. Preserve the familiar fast RTS interaction loop while creating original game content, name, factions, maps, interface artwork, audio, and story.

Start by checking which repository, files, archives, and build environment you can actually access. Read any project handoff and design brief supplied with the source. Compare the actual branch and commit with the known baseline above. Do not silently assume that a brief describes current code. Label findings as observed, inferred, or unverified.

### Product and content boundaries

- Use the existing engine path unless inspection demonstrates a blocking technical reason. Before any major engine change, write a short decision record with measured evidence, alternatives, and consequences. Do not rewrite the engine, pathfinding, renderer, or networking just because a new architecture sounds cleaner.
- Make an original standalone game inspired by Zero Hour. Reuse interaction patterns, not EA names, logos, maps, voice lines, music, textures, menu art, or campaign story.
- Keep all faction equipment and capabilities as fictional game design and balance values, not factual claims about real armed forces. No nationality is inherently evil.
- Keep an asset manifest with stable IDs, source/archive, creator or generation provenance, license, edit history, runtime destination, and integration status. Do not ship any source-game assets or Steam archives as Modern RTS content.
- The GeneralsGameCode / EA source carries license and notice requirements. Preserve notices, mark source modifications, and review distribution obligations before any public release.
- Do not make paid API calls or incur charges. Do not push publicly, tag a release, upload or distribute builds, or publish content without explicit user approval.
- Do not add fake or nonfunctional UI controls. A concept mockup is not evidence of a working feature.
- Do not claim a feature, asset import, Windows build, or test is complete without logs, runtime evidence, or a clear explanation of the test limitation.

### Expected design direction

The match loop is: choose a faction and map; establish a command center, builder, income, power and production; scout and contest supply; construct a base; produce a combined force; use upgrades and support abilities; then win by the mode's stated objective.

Plan for nine playable sides: Iran, Iraq, North Korea, Taiwan, China, Japan, Europe coalition, Ukraine, and USA. The initial vertical slice should focus on USA and China, subject to the existing project brief. “Europe” is a coalition. All sides may be players, allies, or AI opponents. Make faction differences strategically meaningful and reasonably balanced.

The required systems include command centers and builders; cash/resources and logistics; power as a separate capacity constraint; construction and building damage; production queues; infantry, ground vehicles, aircraft, and counterplay; scouting and fog of war; selection and orders; control groups; camera and minimap; tech, upgrades, veterancy, support powers; skirmish AI; save/load and replays; and later multiplayer.

### Work method

1. Recon the actual repository, branch, build, runtime data dependencies, UI, maps, model pipeline, game logic, AI, saves/replays, and networking.
2. Record architecture decisions and define a content/asset validation workflow that fits the existing engine.
3. Implement a visible, testable increment immediately after the essential recon. Do not stop after writing a design document.
4. Integrate the art, game data, and code. A folder of disconnected concepts is not a completed game feature.
5. Report exact changed paths, build commands, tests, runtime evidence, defects, and next work. If you cannot run the Windows build, state that and provide the precise next step for the user.

Begin now with a concise access/repository report, then proceed into recon and B1.1.

## Prompt 2 — Recon, engine, and asset-pipeline audit

Inspect the actual source and current project environment. Trace startup and data loading, player/faction definitions, object and weapon definitions, commands, GUI/shell, map loading, model/texture import, audio, AI, save/replay, and networking. Identify which old-game archives the existing test copy loads and which content references must be replaced for a standalone build.

Confirm the exact model, texture, icon, animation, and map formats supported by this fork, and find a repeatable example of each from the repository or tools. Do not assume PNG contact sheets can be loaded as animated units. Propose the smallest validated pipeline for:
- a simple original unit and icon;
- a structure with footprint and construction states;
- an original test map;
- sound and UI artwork;
- manifests and missing-reference validation.

Create or update concise project docs for observed findings and architecture decisions. Preserve the current successful test copy. Then move directly to B1.1. If the art pipeline cannot be fully exercised in your environment, prepare a minimal asset and exact import/test instructions rather than claiming it works.

## Prompt 3 — RTS simulation, commands, and data model

Design the implementation around the actual engine's existing fixed-step simulation and command systems. Keep game-changing decisions in simulation logic; input and UI should issue commands. Do not assume a custom ECS, grid snap, flow-field pathfinder, or networking rewrite is needed.

Define stable, validated data for:
- factions and starting forces;
- units and buildings;
- movement classes and unit orders;
- weapons, armor classes, and damage effects;
- production queues, build costs, prerequisites, and rally points;
- upgrades, support powers, and veterancy;
- maps, supply locations, and victory conditions.

The model should express each unit's gameplay role without hardwiring faction rules into the UI. Keep AI and human players on the same allowed command interface. Ensure game state can be saved and replayed consistently, and keep nondeterministic model or network calls off the simulation frame path.

Deliver an architecture note, schema examples that match the codebase, and a reference validator. Then integrate the schema with B1.1 instead of building a parallel prototype that cannot load in the game.

## Prompt 4 — Ground movement, troop control, and deployment

Implement familiar RTS unit control using the existing engine's input, pathfinding, and object systems.

### Player controls and orders
- Click-select one unit; drag-select groups; add/remove selection with the established modifier behavior.
- Right-click ground to move; right-click an enemy to attack; right-click an interactable friendly, neutral object, or transport for its valid context action.
- Support move, attack, attack-move, stop, guard, patrol, hold-fire, capture, enter/exit transport or garrison, deploy/undeploy where the unit supports it, and repair where applicable.
- Support numbered control groups, shift-queued waypoints, formations where practical, rally points, selection feedback, and readable command tooltips.
- Provide configurable hotkeys and clear feedback when an order is invalid.
- Orders must respect terrain, obstacles, occupancy, line of sight, and fog-of-war rules. Use and validate the existing pathfinder before proposing replacements.

### Infantry movement and animation
Support the game states required by implementation: idle, turn, walk/run, aim, fire, reload, hit/react, suppressed or pinned if used by the design, death, enter/exit, and deploy where relevant. Coordinate animation state with actual movement and weapon cooldowns. Add pose and facing variants through an authored rigged asset or a validated sprite pipeline. Static generated poses are references, not a complete animation.

### Vehicles
Support acceleration/deceleration, turning, reverse movement where appropriate, path following, collision/spacing, turret traverse independent of hull direction, weapon aiming, damage, disabled/destroyed states, and repairs if the game design supports them. The TOW HMMWV, .50-caliber HMMWV, and medical HMMWV must be distinct gameplay variants with distinct commands and icons. The medical version is a support unit, not an attack variant unless balancing explicitly gives it a weapon.

### Deployment and garrison
Define which units can deploy, unpack, garrison, or carry passengers. Show an explicit contextual command and the resulting unit state. Do not make “Deploy” a generic button on every unit.

Deliver evidence for selecting, moving, grouping, attack-moving, stopping, and using each implemented contextual order. Add focused tests for regressions in command handling and pathfinding.

## Prompt 5 — Combat, weapons, damage, and counters

Implement combat as readable game rules in data, using the engine's existing attack, projectile, damage, and targeting systems where possible.

Each weapon definition should provide game-balance values for range, damage, cooldown, projectile or hit behavior, target categories, effects, and sound/VFX references. Unit defenses should use clear fictional armor classes and damage responses. Implement target acquisition, valid attack orders, attack-move behavior, line of sight, range checks, facing/aiming, cooldowns, projectile travel or hit resolution, damage feedback, destruction, and counterplay.

Create a role/counter matrix for infantry, anti-armor infantry, vehicles, artillery, air units, and air defense. Keep each side fair through cost, build time, range, survivability, and counter availability. Apply fog-of-war visibility consistently.

Use these generated personnel equipment concepts as visual references: equipped riflemen, M249 SAW, M240B, and AT4. The AT4 is a shoulder-fired weapon: depict it braced at the soldier's shoulder in firing poses. Its game animation should clearly show a shoulder-fired attack. Do not mount it on a vehicle or portray it as an underarm, hip-fired, or crew-served weapon. Keep the representation at the level of game animation and balance data.

Do not invent real-world capability claims. Show hit and damage feedback clearly without obscuring the player's view. Validate at least one attack, damage, counter, and destruction loop in a running match.

## Prompt 6 — Economy, construction, and production

Implement the base-building loop with distinct, clear rules.

### Economy and power
- Show spendable cash separately from power capacity and current power use.
- Make active supply collection, stored supply, and any secondary income distinguishable.
- Define the supply depot and supply vehicle/collection loop, including limits and player feedback.
- Treat a supply airdrop as a support ability or defined supply event with a cost, cooldown, quantity, and landing feedback. Do not accidentally turn it into unbounded passive income.
- Display costs, income, power changes, and insufficient-resource states in the HUD.

### Builders and construction
- The command center unlocks or provides the faction's builder, such as a construction vehicle or engineer team.
- Builders place structures on valid terrain. Use the engine's real footprint and placement validation; do not assume a new grid snap.
- Show a placement preview, valid/invalid state, footprint, rotate/cancel controls if supported, and blocked-placement reason.
- After placement, show construction progress with scaffold or staged visuals, health, completion effects, and interruption/destruction behavior.
- Support construction queues, prerequisites, repair, and sell/cancel rules with clear refund behavior.
- The Corps of Engineers construction yard is a production/support structure or construction theme according to the final faction design. Do not confuse the player-facing building with the builder unit that actually performs construction.

### Production
- Barracks produce infantry; War Factory produces ground vehicles; Airfield produces aircraft; specialized structures unlock defenses, upgrades, and support powers.
- Show queue order, progress, cost, time, cancel/refund, prerequisites, rally point, and alerts.
- Let players cancel or reorder queues only if the engine supports it safely.
- Add distinct structure roles: Command Center, Barracks, Supply Depot/Airdrop Zone, War Factory, Airfield, Radar/Communications, Power Generator, Repair Bay, Field Hospital, Gatehouse, HESCO position, and defensive structures.

Deliver a playable small base loop: gather supply, build power and production, produce units, set rally points, and destroy or capture a stated objective. Verify costs, power, queue behavior, and save/load.

## Prompt 7 — Aircraft, routes, sorties, and air defense

Implement aircraft using the engine's existing aircraft and targeting behavior. Add explicit state transitions appropriate to the aircraft type: takeoff or spawn, climb, travel, loiter, attack, return, land, and rearm. Give helicopters and fixed-wing craft different movement profiles. Keep exact realism out of scope; tune the behavior for clear, enjoyable RTS play.

### Player aircraft orders
- Launch or produce aircraft through the Airfield.
- Select an aircraft or group and issue move, patrol, attack-move, attack target, and return/rearm orders as supported.
- Let players set and edit a route using map waypoints, display the route clearly, and support queued waypoints or a looped patrol.
- Provide attack approach/target orders as a game command. Keep the order readable and interruptible.
- Provide configurable ammunition, sortie, cooldown, or rearm rules and display remaining capability. Balance these as game rules, not real operational guidance.
- Save routes and aircraft state in saves/replays.
- Route aircraft around map boundaries and obstacles using the engine's tested system, and prevent units from becoming stuck outside playable space.

### Aircraft roles and defenses
Use the generated B-1, B-2, B-52, F-16, F-18, F-22, Chinook, Black Hawk, Apache, A-10, SR-71, and other concepts as art references. Assign fictional roles based on balance. The SR-71 concept can serve a reconnaissance role if desired; bombers, fighters, helicopters, and transports need distinct gameplay profiles. Treat the MOAB as a strategic support ability or scenario asset with an explicit cooldown and warning, if included.
Make Patriot and THAAD concepts fit the game's anti-air defense category through fictional target classes and balance rules. Add attack feedback, effects, and counters.
Prove aircraft production, route movement, attack, return, landing/rearm, and a defensive response in a running match before adding the rest of the aircraft roster.

## Prompt 8 — Buildings, base defense, and map interactions

Integrate the generated installation concepts as distinct functional structures, not decorative copies of the same building. Define their cost, build time, footprint, prerequisites, power use/output, production/support role, health, and interactions.

Potential roles:
- Command Center: starting anchor, builder access, core interface, faction abilities.
- Barracks: infantry production and infantry upgrades.
- War Factory: vehicle production and rally point.
- Airfield: aircraft production, routes, landing, and rearm.
- Supply Depot and Airdrop Zone: economy and supply events.
- Construction Yard: faction construction support or production role.
- Power Generator: separate power output and vulnerability tradeoff.
- Radar/Communications: scouting, minimap or information upgrades.
- Repair Bay and Field Hospital: support and recovery.
- Fortified Tower, Patriot/THAAD defenses: target selection and area defense.
- HESCOs, gatehouse, and barriers: terrain or base layout interaction; test pathing, placement, and firing/sight interactions.

Implement a build preview and reliable placement feedback. Structures should have readable team ownership, health/damage stages, selection bounds, attack/repair/sell commands, and minimap visibility rules. HESCOs should behave as clearly defined cover or obstacles if the design uses those rules.

Create one original test map, Harbor Divide, with two fair start zones, a contested center, alternate routes, supply locations, elevation and sight-blocking checks, and sufficient base-building space. Do not copy a Zero Hour map. Validate pathfinding for infantry, vehicles, and aircraft separately.

## Prompt 9 — Player UI, menus, and commands

Design a modern, scalable, original RTS interface that retains familiar RTS interaction patterns. Implement it in the actual game UI; do not stop at a mockup.

### In-match layout
- Main viewport for the map and orders.
- Top HUD for cash, power output/use, objectives, match status, alerts, and pause/menu access.
- Minimap for overview, camera jump, unit/building indicators, and later map pings.
- Selection panel for unit/building identity, portrait, health, selected count, status, and available commands.
- Contextual command/build panel that changes based on selection.
- Production queue with progress, cost, time, cancel, prerequisite, and rally-point feedback.
- Clear placement ghost, selection rings, order markers, target cursor, waypoint route, and error messages.
- Scale cleanly to supported modern resolutions; support contrast, readable text, color-independent team identification, keyboard remapping, and concise tooltips.

### Contextual options
- Builder selected: Build Structures, place/rotate/cancel, queue status.
- Barracks selected: Train Infantry.
- War Factory selected: Produce Vehicles.
- Airfield selected: Produce Aircraft, set routes, return/rearm.
- Combat unit selected: Move, Attack, Attack-Move, Stop, Guard, Patrol, Hold Fire, Deploy, Capture, Garrison, Enter/Exit, or Repair only when valid.
- Support panel: available abilities, cost or cooldown, target selection, range/eligibility feedback.
- Add repair/sell, upgrades, veterancy, rally points, control groups, and minimap commands where implemented.

### Main menu and player options
Plan an original main menu with Skirmish, Campaign, Multiplayer, Replays/Load, Options, Credits, and Exit as appropriate to the release. Only present features that are functional in that build; do not create nonfunctional buttons. B1 should expose only what can be used, such as a working test/skirmish path and Options.
Include match setup: faction, opponent, map, team/start position, difficulty, and valid gameplay settings. Keep game rules and accessibility options separate and understandable. Add keyboard and mouse help.

Test the UI at target resolutions and with long faction/unit names, full production queues, low resources, lost power, alerts, multiple selection, and map edges. Provide a short recording or screenshots of actual in-game behavior.

## Prompt 10 — AI, tech, fog, victory, saves, and replays

Implement basic skirmish AI through the same command and economy rules available to players. It should gather supply, build a base, produce a mixed force, scout, defend, attack, respond to losses, and be able to win or lose. Difficulty should adjust decision quality or response timing; disclose any mode modifiers and avoid hidden resource cheats by default.

Implement fog-of-war visibility, scouting, detection, and minimap information consistently for player and AI. Add the agreed tech progression, upgrades, veterancy, and rank-earned support powers. Keep constructed superweapons distinct from abilities earned through rank or match progress.

Define clear victory/defeat conditions per mode. Add save/load and replay support early enough to test state serialization, production queues, current orders, aircraft routes, construction, and AI. Keep deterministic simulation and content versions in saves/replays. Defer online multiplayer until matching content hashes and repeatable two-client desync tests are available.

## Prompt 11 — Asset integration and faction expansion

After the first vertical slice is proven, inventory and integrate the provided U.S. asset packs in batches.

For each asset:
1. Verify the original source image and crop; do not treat a multi-view contact sheet as one runtime unit.
2. Create or commission a game-ready model, material/texture, rig, animation, icon, effects, and audio as needed.
3. Export to a format actually supported by the current engine and inspect it in-game.
4. Add stable references and provenance to the asset manifest.
5. Add game data: faction, role, production building, cost, time, health, movement class, orders, weapon/ability references, upgrades, counters, icon, and audio/effects.
6. Add UI entries, tooltips, hotkeys, AI build/use behavior, and tests.
7. Verify scale and readability from the actual game camera, selection, movement, combat, damage, death, destruction, and minimap.

The personnel image packs include multiple concepts and poses but do not prove a continuous animation set. The vehicle and aircraft views do not prove a rig or turning/flight animation. Plan model, rig, and animation authoring separately. Preserve the AT4 shoulder-fired correction in all final art and animation.

Expand the rest of the seven factions only after USA and China can each complete a fair match. Use shared rules and a unit/counter matrix. Treat faction-specific real-world names and equipment as fictionalized game content; no factual claims about current capability.

## Prompt 12 — Milestone implementation and acceptance report

Implement and validate in these gates. Do useful work in the accessible environment; report access blockers precisely.

### B1.1 — First original object
- Pin the fork commit and create a separate product branch/work tree.
- Add one original unit, icon, definitions, and small original test map in a separate development content tree.
- Prove production or spawn, selection, movement, attack, damage, and destruction.
- Validate asset and command references.
- Provide changed file paths, exact build/run steps, test logs, and a runtime screenshot/video if available.

### B1.2 — First base loop
- Add command center/builder, supply, power, one production building, a combat unit, a defense, and working UI.
- Prove gathering, building placement/construction, production queue, movement, combat, power, and victory/defeat in a small match.

### B2 — Standalone USA/China vertical slice
- Use only independently sourced or original shipped content in a clean install with no EA/Steam archives.
- Include Harbor Divide, two playable factions, economy, construction, three combat roles per faction, victory/defeat, a competent skirmish AI, and save/load.
- Test every asset reference, factions, map pathing, and complete human-versus-AI match.
- Do not label it standalone until it boots in a clean folder without old game archives.

### B3–B5 — Presentation, expansion, and multiplayer
- B3: original scalable UI, models, effects, and audio at target resolutions.
- B4: add remaining seven factions and maps in tested batches.
- B5: only then add multiplayer/replays/spectator and release packaging. Require two-client tests, identical content hashes, deterministic replay/desync evidence, license notices, and user approval before any public release.

At every gate, report: requirement, exact files changed, build/test environment, command and result, screenshot or log evidence, known defects, and the next concrete ticket. Distinguish “concept art,” “imported,” “visible in-game,” “playable,” and “standalone verified.” Do not claim all generated assets are implemented because the archives exist.

## Recommended execution order

1. Paste Prompt 1.
2. Have Claude perform Prompt 2 and report what it can access.
3. Apply Prompts 3–6 to build the core simulation and first base loop.
4. Apply Prompts 7–9 for aircraft, installations, and player UI.
5. Apply Prompts 10–12 for AI, asset expansion, and acceptance gates.

Claude should work from the actual repository state and the files available in its project. If an asset ZIP or Windows checkout is missing, it must identify that exact missing input rather than assuming it can see files from another chat or computer.
