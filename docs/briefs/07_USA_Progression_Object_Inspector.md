# Steel Accord — Final USA Progression, Object Inspector, and Visual Gameplay Handoff

## Purpose

This is the final combined Claude handoff for the requested USA progression, object inspector, construction/repair, fortifications, HESCO garrisoning, builder visibility, camera control, unit readability, map/rendering quality, and multi-faction architecture. It consolidates the relevant earlier UI/economy and playtest requirements into one implementation brief.

Use the current project source as the final authority. The B1.2 notes and gameplay footage document a playable baseline, but some generated assets and earlier design ideas are not yet implemented as game entities. Do not add a menu item, upgrade, button, building, or stat just because an image or design suggestion exists. First verify whether its underlying system is in the project.

The source project is the authority for what is currently implemented. The earlier QA files are useful evidence if Claude has them, but this handoff includes the required behavior and tests:

- SteelAccord_Modern_UI_Economy_Mechanics_Claude_Handoff.md
- SteelAccord_B1_2_Playtest_QA_Report_for_Claude.md
- Steel_Accord_Two_Clip_QA_Review_Claude_Handoff.md

The goal is to preserve the modern RTS direction, make progression understandable, give every selectable gameplay object a useful inspection panel, and make the battlefield readable and visually coherent at every camera distance. Implement USA first while keeping the architecture data-driven for every other nation/faction.

## 1. Steel Accord baseline to preserve

The B1.2 handoff documents the current baseline as:

- Command Center and a builder/Dozer for construction.
- Power Plant and cash/power economy.
- Supply Depot with Chinooks collecting cash from crate piles.
- Barracks producing Rifleman and AT4 Gunner.
- War Factory producing HMMWV .50, Vanguard tank, and Avenger AA.
- Airfield producing F-16, A-10, and AH-64, with four parking pads and a return-to-pad command.
- Defense Tower, Radar, Supply Drop Zone, HESCO Barrier, and other placeable structures.
- Existing support cards shown in footage: Carpet Bombing, Supersonic Strike, Stealth Precision Strike, Paratroopers, and Recon Overflight.
- Existing low-power effects documented in the prior mechanics handoff: slower construction and production, slower defense towers, and Radar disabled.

Confirm each item against the current source before implementation. Use the game's current building/unit names if they differ from these notes. Keep new generated aircraft, vehicles, infantry, and installation art out of live production menus until the corresponding entity, role, scale, animation, production rules, and tests exist.

## 2. Translate the C&C concepts into Steel Accord names

| Suggested C&C concept | Steel Accord treatment | Implementation decision |
|---|---|---|
| Supply Center | Supply Depot | Use the existing Supply Depot and its Chinook/crate-pile economy. Do not add a second Supply Center. |
| Cold Fusion Reactor | Power Plant | Use the existing Power Plant and current power rules. Add an advanced power upgrade only if the project has a clear late-game need. |
| Strategy Center plus R&D | Strategic Operations Center | Preferred name for one new mid/late-game technology building. It can host research and battle plans. If Command Center already owns these functions in source, add a research/operations module there instead of creating a duplicate headquarters. |
| Barracks | Barracks | Keep the existing producer. Add only implemented infantry, medical, and training features. |
| War Factory | War Factory | Keep it as the vehicle producer and, if implemented, the vehicle service/repair point. |
| Air Field | Airfield | Keep it as aircraft producer/service building and expose the four real pad slots. |
| Defense Tower | Existing Defense Tower | Retain its current identity unless its model/weapon truly corresponds to Patriot. Do not relabel a generic turret as Patriot merely to match a suggested name. |
| Patriot Missile System | Patriot Air Defense Battery | Add as a distinct structure only if the Patriot asset, air/vehicle targeting, power behavior, and damage logic are implemented. Otherwise keep the current Defense Tower and list Patriot as planned content. |
| THAAD | THAAD Missile Defense Site | A separate high-tier anti-missile/strategic-air-defense structure only if the game has interceptable missile/strike projectiles. Do not make THAAD a general anti-tank turret. If no missile interception system exists, defer it. |
| Firebase | Field Artillery Emplacement, optional | Do not duplicate an existing artillery unit or Defense Tower. Add only if Steel Accord needs a static long-range gun. Do not add garrison slots until garrison mechanics exist. |
| Fuel Air Bomb | Existing Carpet Bombing support ability | Connect a MOAB upgrade to the existing large bomber-strike card only if source confirms it is the same gameplay role. Do not create both cards for one function. |
| USA general | Commander progression, if present | Use the existing player-rank/general-promotion system if one exists. Do not introduce a second commander XP system just to gate one unlock. |

Costs, power use, build times, upgrade durations, prerequisites, and refund behavior must come from the game's existing economy data and be balanced in playtests. Do not leave "$?" values or invent prices from the old game's balance. Put values in the project's authoritative data definitions, not hard-coded separately in UI scripts.

## 3. Tailored upgrade and ability set

### Barracks and infantry

**Current producer:** Rifleman and AT4 Gunner are documented for B1.2. Generated Rangers, medics, engineers, and other infantry are not automatically live units.

- **Capture Structures:** implement as an ability for a designated Engineer only if neutral/capturable structures and ownership transfer already exist or are being implemented in this pass. Do not silently grant capture to every Rifleman. If the generated EOD Engineer is primarily a demolition/ordnance role, do not repurpose it as a general capture engineer without an explicit unit design.
- **Medical support:** add a Medic as a Barracks unit only when its asset and healing behavior are in-game. The Barracks may also act as a limited infantry treatment point, but define its radius, rate, cost, and eligibility. If there is no garrison system, do not imply that units can enter the building.
- **Flashbangs:** make this an Assault/Ranger loadout or upgrade only if that infantry type exists. The inspector should show the alternate fire mode and hotkey. Flashbangs should create a short, readable suppression/stun effect; keep damage and duration configurable for balance.
- **Exo suits:** this is not a currently documented Steel Accord unit or asset. First implement it as a research upgrade called **Advanced Combat Armor** using existing infantry models, unless a real exosuit model and animations are added. Do not promise an exosuit visual where none exists.
- **Advanced Training:** research at the Strategic Operations Center (or its existing equivalent) increases XP earned by eligible combat units. It must not instantly grant promotions or increase health without showing that effect.

### War Factory and ground units

**Current documented producer:** HMMWV .50, Vanguard tank, Avenger AA.

- **Composite Armor:** a global researched upgrade for compatible armored units. At minimum, define compatibility for the current Vanguard tank and Avenger only if source data supports those classes. Add future Abrams, Paladin, Stryker, MRAP, or other generated assets only after they are actual units.
- **TOW:** the generated tactical HMMWV with TOW is a different loadout from the current HMMWV .50. Prefer a separate HMMWV TOW production variant if both models/weapons are implemented. Do not replace a .50-caliber turret with a TOW stat upgrade if the model and combat behavior do not change accordingly.
- **Vehicle repair:** a damaged vehicle can return to the War Factory only if a service bay/repair mechanic is implemented. Show service availability, progress, cost, and a full/occupied state.
- **Drones:** small sentry/recon drones can be War Factory or Drone Bay products if the game includes drone movement, detection, targeting, and destruction. An MQ-9-class aircraft belongs in the Airfield/air-unit progression, not the ground-vehicle queue. If drones are not implemented, do not show an empty drone category.
- **Vehicle upgrades:** scope upgrades by unit tags such as armored, tactical, anti-air, or logistics. The UI must say which actual units benefit; never apply “armor upgrade” to every object indiscriminately.

### Airfield and aircraft

**Current documented roster:** F-16, A-10, AH-64. The F-18, F-22, F-35, B-1, B-2, B-52, C-130 variants, and other generated aircraft should remain future content until they are implemented and tested.

- **Rocket Pods:** attach to compatible aircraft such as the A-10 or AH-64 only if their weapons and model show the pod. Do not list it for every aircraft.
- **Guided Munitions:** apply to aircraft configured for air-to-ground weapons. Show eligible unit names. Do not apply a generic damage bonus to an aircraft that has no compatible weapon.
- **Countermeasures:** add flares/chaff only to aircraft that can actually be targeted by the game's missile system. Show a defensive cooldown/charge state if the mechanic uses charges. If the current game has no missile lock/interception behavior, defer this upgrade.
- **Bunker Busters:** rename to **Hardened-Target Munitions** if the game has destructible fortified structures. Use a building-damage modifier with visible feedback. The old suggestion's garrison-kill, Tunnel Network evacuation, and vehicle-launch effects rely on systems not documented in Steel Accord; do not implement those effects unless garrison, tunnel, and launch physics exist.
- **Aircraft service:** Airfield selection must show all four pad states and each aircraft's parked, queued, launching, airborne, returning, landing, repairing, and rearming status only when those states exist in code. Preserve the prior QA requirement that R returns an aircraft to a valid Airfield pad.

### Strategic Operations Center: one research and battle-plan hub

If no existing building provides advanced research, add one building named **Strategic Operations Center**. It replaces the separate Strategy Center/R&D concept with a single understandable building. A reasonable prerequisite is Command Center plus either a War Factory or Airfield, subject to the existing tech tree. If the Command Center already has an operations module, use that instead.

Its tabs can be:

1. **Research:** compatible armor, advanced training, supply efficiency, and other real upgrades.
2. **Battle Plan:** choose one global doctrine at a time.
3. **Intelligence:** connect to the existing Recon Overflight ability rather than adding a duplicate map-reveal button.

Suggested battle-plan identities:

- **Assault:** a configurable combat bonus for eligible ground units.
- **Recon:** improves detection, vision, or range only if those stats exist in the game.
- **Fortify:** a configurable defensive bonus for eligible ground units.

Show the active plan in the HUD and in affected unit inspectors. Only one plan may be active. Make switching rules explicit and balanceable; a short switching delay can prevent rapid-toggle exploits. Do not add a cannon, stealth detector, sandbags, or other visual feature to the building unless it has a real model/action and a gameplay effect.

### Economy and support upgrades

- **Supply Line Efficiency:** adapt the 10% supply-income idea to the actual Steel Accord sources: Chinook crate-pile deliveries and Supply Drop Zone income if the latter is functional. Include neutral oil derricks only on maps that actually contain capturable/owned derricks. Prevent double counting.
- **Scout Armor:** defer until a scout/sentry drone unit is actually implemented.
- **Chemical Protection:** defer until the game has toxin, radiation, or another hazard damage type. If it does, call the upgrade **Hazard Protection** and show the damage types reduced.
- **Intelligence:** improve the current Recon Overflight's duration, cooldown, or reveal scope rather than adding a second overlapping ability.
- **MOAB:** use the generated MOAB payload with the existing B-52 asset and the existing large-bombing support slot if that is the correct source-code mapping. Gate it through the current commander rank system at a suitable late-game rank. The suggested B-3 transport aircraft is not part of the documented Steel Accord roster; do not invent or display it. If the rank system or B-52 support sequence does not exist yet, defer the unlock until both are real.

### Base defenses

- Keep the current Defense Tower behavior and name unless it is replaced by a correctly implemented Patriot unit.
- Patriot should have clear target classes and power requirements based on the current power system. Any coordinated-lock feature is optional; first make one battery acquire and fire correctly.
- THAAD is for compatible high-altitude/missile threats, not infantry or tanks. Add it only when the game supports such targets and intercepts.
- If an artillery emplacement is added, make its firing arc, range, reload, power, and vulnerability clear. Do not add garrison controls unless infantry boarding/garrison rules exist.

## 4. Universal click-to-inspect window

Every **selectable gameplay object** should open the same consistent contextual inspector when clicked. Use a slide-out/pinnable side panel or a compact pop-out card that does not pause the game or cover the selected object. Keep the panel open while the object remains selected; selecting another object updates it. Include close/pin controls. Clicking decorative terrain or non-interactive scenery should not open a fake information panel.

### Shared header for every selectable object

Show:

- Name and object class.
- Owner/team and current role.
- Health bar and damage state.
- Current operational state: idle, moving, attacking, building, repairing, returning, rearming, disabled, or the applicable real state.
- A clear selected outline/marker on the battlefield.
- Only actions that object can actually perform.

### Building inspector

For Command Center, builder, Supply Depot, Power Plant, Barracks, War Factory, Airfield, Defense Tower/Patriot, Radar, Supply Drop Zone, and future structures, show the fields that apply:

- Health, damage, construction/repair progress, operational/low-power state.
- Building purpose and build prerequisites.
- Production queue, selected item, progress/ETA, rally point, and cancel controls where supported.
- Upgrades grouped as **Available**, **Researching**, **Installed/Active**, or **Locked** with the exact reason and prerequisite.
- Effects and compatible units for each completed or pending upgrade.
- Power produced/used and current power effect where applicable.
- Service actions such as infantry healing, vehicle repair, aircraft repair/rearm, Radar, or support powers only if implemented.
- For Airfield, four pad slots and aircraft states.
- For resource buildings, real stock/income/delivery state.
- Repair and Sell/Rebuild actions with costs and clear confirmation when needed.

### Unit inspector: infantry, vehicles, aircraft, drones

For every combat-capable selected unit, show:

- Name, class/role, health, current order, weapon/loadout, and valid abilities.
- **Veterancy/Promotion:** rank name, XP progress to the next rank, and actual bonuses already earned. Use one consistent promotion scheme across infantry, vehicles, aircraft, and implemented combat drones, but make bonuses class-appropriate.
- **Upgrade compatibility:** list only registered upgrades that can affect this unit. Show whether each is installed/active, researchable, researching, or locked; state the prerequisite and actual effect. If a global upgrade applies to the unit, show it as active without requiring a second purchase.
- Armor/weapon/vision/range values only where those values exist in the simulation.
- Ammunition, fuel, passengers, flares, cooldowns, or service state only if that resource/system exists.
- For transports, passenger list, occupied/total capacity, and load/unload controls.
- For aircraft, pad/airborne/return state, health, and available service actions.
- For infantry, medic/healing, capture, grenade mode, or squad status only if applicable to that unit.

Do not show “missing upgrade” as a blank or red warning. Use plain states:

- **Installed** — the unit currently receives the upgrade.
- **Available** — the upgrade can be researched now.
- **Researching** — show the real queue and progress.
- **Locked** — show the missing prerequisite, funds, power, commander rank, or building.
- **Not compatible** — omit by default, or explain only when a player explicitly opens the full upgrade catalog.
- **Not implemented** — never show this in the player-facing game UI. Keep it in developer notes/roadmap, not as a dead button.

### Group selection

When multiple units are selected, show a group inspector with unit counts by type, a shared health/command area, and a roster that opens each individual inspector on click. Do not combine unrelated upgrade lists into a misleading single panel. Commands should operate on the eligible selected units and clearly report when some units cannot perform an action.

### Interaction and accessibility

- Left-click selects and opens/updates the inspector.
- Right-click remains the contextual move/attack command; it must not open the inspector.
- Clicking empty ground clears selection and closes/unpins the panel according to the current UI convention.
- Preserve keyboard shortcuts, selection groups, camera controls, and RTS flow.
- At 1080p, 1440p, and 4K, text and controls must remain readable and not cover the minimap or command panel.
- Tooltips explain cost, time, prerequisite, target scope, effect, and hotkey.
- Do not pause combat just because a panel opened.

## 5. Promotion/veterancy rules

Keep individual unit promotion distinct from the player's Commander Rank:

- **Unit veterancy** is earned by an individual unit through combat or its intended support role. It appears on that unit's inspector and persists while the unit survives.
- **Commander Rank** is a player-wide progression value used only for global support unlocks such as MOAB, if the game already has or intentionally adds that system.
- A new unit starts at the base rank. XP thresholds and bonuses are data-driven. A veteran bonus must be visible in the inspector and reflected in combat.
- Use class-appropriate bonuses. For example, infantry may gain survivability/accuracy, a vehicle may gain handling/armor, and aircraft may gain rearm/readiness or weapon efficiency. Do not apply the same raw damage/health multiplier to every class.
- Support units gain XP only for meaningful support actions if that is part of the design. Non-combat scenery and buildings do not receive unit promotions.
- Promotions must be testable: show XP earned, rank-up notification, rank badge, bonus, and next threshold. Avoid hidden random promotion resets.

## 6. Recommended implementation order

1. **Audit the source and reconcile names.** Compare live code/data to the B1.2 roster and existing handoffs. Mark each feature implemented, partial, planned, or absent. Do not change balance yet.
2. **Build the universal inspector.** Make all existing buildings and units inspectable first. Show real status and current upgrade/queue data. This gives the player visibility before adding more systems.
3. **Fix core service and progression.** Add building repair/rebuild, vehicle service, Airfield pad state, per-unit veterancy, and accurate queue feedback where missing.
4. **Add one tech building/module and a small upgrade set.** Start with Advanced Training, Composite Armor for existing compatible units, Supply Line Efficiency, and the three battle plans. Test balance and low-power behavior.
5. **Add aircraft upgrades and MOAB only after compatibility and strike cinematics work.** Use existing F-16/A-10/AH-64 and B-52 assets only when they are game-ready. Keep non-implemented aircraft hidden.
6. **Add Patriot/THAAD, capture, general building garrisons, drones, hazard protection, or firebase only when their underlying combat mechanics are available.** These are optional systems, not blockers for the core UI.
7. **Add perimeter fortifications and HESCO garrisoning as a distinct feature phase.** First validate wall collision, line of sight, terrain placement, and pathfinding; then add player-directed infantry occupancy for garrisonable HESCO positions.
8. **Make the existing builder/Dozer easy to find and command.** Preserve it as a visible, selectable world unit and provide clear build/repair status and find/select controls.
9. **Polish camera, terrain, lighting, shading, detail, and multi-faction presentation.** Maintain readable unit silhouettes at strategic zoom and a free orbit/pan/tilt camera at close zoom before expanding the roster.

## 7. Claude-ready implementation prompt

Please implement this as the final consolidated handoff, alongside the existing Steel Accord UI/economy and B1.2 QA briefs. Inspect the current Godot project and confirm live names, roster, prerequisites, economy, power rules, support abilities, camera behavior, rendering settings, and object-selection architecture before coding.

First create a feature matrix with columns: present in source, visible in B1.2, planned only, and required new mechanic. Then implement the universal click-to-inspect panel for every selectable gameplay building and unit using real game state. Include unit veterancy, compatible upgrade status, building production/research/service state, costs/prerequisites, power, health, and blocked reasons as appropriate. Do not expose fields for systems the game does not have.

Map the supplied suggestions to existing Steel Accord names: Supply Center to Supply Depot; Cold Fusion Reactor to Power Plant; Strategy Center/R&D to one Strategic Operations Center or a module on the existing Command Center; Intelligence to the current Recon Overflight; Fuel Air Bomb to the correct existing large-bombing support slot; and the current Defense Tower to Patriot only if its actual model and behavior match. Do not add the proposed B-3, Tunnel Network, garrison-kill effects, drone upgrades, chemical protection, or THAAD interception until the corresponding asset and gameplay system exist.

Use live project economy values rather than inventing prices or power values. Do not show fake buttons, placeholder progress, or upgrades that have no effect. Keep current units and controls working. Make the builder/Dozer conspicuous and commandable, keep friendly/enemy tactical vehicles and tanks readable at far zoom, provide free camera orbit/pan/tilt at close zoom, and apply the same readability and visual-quality standards to every faction. Test every existing producer and object type, at least one unit with and without an applicable upgrade, locked prerequisites, current low-power behavior, click/selection changes, group selection, builder construction/repair, wall and HESCO behavior, close and strategic camera views, and 1080p/4K UI scaling. Report the files changed, actual behavior implemented, tests/results, and remaining features intentionally deferred.

## 8. Perimeter walls, berms, and HESCO garrisoning

These are requested additions, not confirmed B1.2 mechanics. The current handoff documents HESCO as a placeable structure, but does not establish wall linking, infantry occupancy, cover, or firing ports. Inspect the source first. If absent, implement this as a new, data-driven fortification system rather than pretending the mechanics already work.

### Player-built concrete walls and berms

- Add a **Fortifications** build category for the existing builder/Dozer. Offer a concrete wall and an earth berm as separate, understandable options.
- Let the player drag a line or connect two valid endpoints. Provide a placement preview with segment count, total cost/time, terrain fit, and clear invalid-placement reasons. Segments may snap to compatible defense-tower anchors, but must not auto-connect every tower or fill the base without the player choosing to build them.
- Use concrete wall segments for strong, destructible ground cover that blocks ground passage and direct line of fire. Use berm segments for lower-profile, lower-cost cover that slows ground movement and gives eligible infantry directional protection; define its sight and projectile behavior explicitly.
- Provide a gate or deliberate gaps for player/AI traffic where a continuous wall would trap units. Wall and berm endpoints must not overlap building footprints, tower firing arcs, Airfield routes, or map boundaries.
- Ground each segment to the terrain height and slope. Use the same world-scale, collision, shadow, health, ownership, and repair conventions as other structures.
- Treat walls as destructible and repairable by the normal builder/Dozer repair system. Show segment health and connection state in the object inspector. Do not make them invulnerable or allow bullets to pass through without clear rules.
- Preserve pathfinding around walls and gates for infantry, vehicles, and AI. Aircraft should not collide with ground walls unless the project's flight/collision rules intentionally require it.

### Player-controlled HESCO garrisoning

- Let the player order eligible infantry into a friendly, garrisonable HESCO position. Support both selecting infantry and right-clicking the position, and selecting the HESCO and choosing a **Garrison** action. This is an explicit player order; do not automatically hide or move a squad into cover.
- Treat garrison capacity as data on the HESCO prefab. Do not invent a capacity or assume every long barrier segment is occupiable. If the current HESCO mesh is only a continuous barrier, add a clearly identified **HESCO Fighting Position** variant with an entry point and firing ports; keep plain barrier segments as cover.
- The inspector shows occupant count/capacity, occupant roster and health, **Unload/Exit**, and the position's health and repair state. Full capacity, incompatible unit types, enemy ownership, and unreachable entry points must have clear feedback.
- Reserve a physical slot/entry point for each occupant, remove garrisoned infantry from ordinary pathing/collision, and prevent multiple soldiers from occupying the same slot. When units exit, place them at a safe nearby location and restore selection, health, veterancy, and orders according to a documented rule.
- Show occupancy visually: use correctly aligned soldier/weapon silhouettes at firing ports or another clear indicator. Keep health/status feedback visible. Do not simply make soldiers disappear with no indication that they are inside.
- Garrisoned soldiers receive configurable cover against eligible direct-fire attacks. Explosives and attacks that can damage the HESCO should remain effective. Firing is limited to supported ports/arcs; soldiers must not shoot through solid sections or gain unlimited range.
- Define what happens when the position is destroyed: safely eject surviving occupants to nearby valid ground and apply the configured damage rule. Never leave units trapped, invisible, invulnerable, or stuck in collision.
- Keep the mechanic scoped to HESCO positions first. Do not imply support for tunnels, every building, or every wall type unless those systems are separately implemented.

### Acceptance checks for fortifications

1. Place a concrete wall and berm between two defense towers, including on uneven terrain. Verify endpoints, segment alignment, collision, shadows, footprints, and tower firing arcs.
2. Test ground pathfinding with infantry, HMMWV, Vanguard tank, and AI units. Units must route around, use a gate, or report a blocked order; they must not become stuck or cross solid sections.
3. Test direct fire, vision, and explosive damage against concrete and berm using documented rules. Confirm both can be damaged/repaired and a breach becomes traversable only when intended.
4. Garrison an eligible infantry unit in HESCO, fill capacity, attempt one incompatible unit, then unload/exit. Verify correct counts, visible occupancy, cover, firing ports, and safe placement.
5. Destroy an occupied HESCO position. Confirm surviving soldiers exit safely, receive the configured damage, and can immediately be selected and commanded.
6. Repeat at 1080p and 4K; the inspector and placement preview must remain readable and must not obscure the map.

## 9. Builder visibility, unit readability, camera freedom, map, and faction-wide visual quality

These requirements apply to every faction. The visual theme, unit names, markings, traditions, and doctrine can differ by nation; camera behavior, gameplay readability, selection feedback, terrain anchoring, and UI quality must remain consistent.

### Builder/Dozer visibility and commandability

- The current builder/Dozer must remain a visible world unit that the player can select, locate, and command. Do not make construction happen invisibly or leave the builder hidden under the structure preview.
- Give the builder a distinctive but restrained silhouette, faction accent/marking, selection outline/ring, health/status display, and a far-zoom role icon. Keep its world scale and collision correct.
- Add a persistent builder count/status control showing available, constructing, repairing, blocked, and selected builders. Clicking it selects or cycles to a builder and recenters the camera; include a clear **Find Builder** action or equivalent.
- The selected builder inspector must expose the real structure catalog, placement/repair actions, current assigned target, progress, blocked reason, and return-to-idle state. After a build/repair order, show the builder traveling to the target and performing the job.
- If the builder is destroyed, show a clear loss/state warning and a real recovery or replacement path through the appropriate producer. Do not leave the player with no visible way to continue construction.
- Preserve selection after placing a building when useful, and provide clear feedback if another builder is required or the current one is busy.

### Readability at strategic zoom and detail at close zoom

- At far zoom, tanks and tactical vehicles must not blend into terrain or become indistinguishable colored specks. Use progressive LODs, readable silhouettes, consistent faction/team accents, class symbols, and unobtrusive health/selection markers.
- Show persistent icons only at zoom levels where the 3D model cannot be identified; avoid covering the map with icons. Use distinct silhouettes and colors for infantry, builders, tanks, tactical vehicles, artillery, air defense, logistics, and aircraft.
- Keep each unit's real world scale, collision, and movement intact. Do not make distant meshes physically huge to improve screen visibility. Any screen-space size bias must be subtle, consistent, and tested against selection and collision.
- At mid zoom, show clear weapon mounts, turrets, wheels/tracks, faction markings, team color, and motion. At close zoom, expose fine model details: sharp geometry edges, legible surface materials/decals, normal/detail maps where supported, and clean anti-aliasing.
- Preserve contrast between units and terrain in sun, shade, fog, desert, green terrain, and built-up areas. Selection rings are supplemental; unit identification must not depend on a ring alone.
- Provide hover and selection highlights that do not wash out the asset. Keep friendly/enemy identification readable for color-blind players using shape, icons, labels, and patterns in addition to color.

### Free camera when inspecting objects

- Keep the RTS strategic camera responsive at all times. At close zoom, allow the player to orbit around, pan across, and tilt above/below the selected object using configurable controls.
- Camera focus on a selected object is a convenience, not a lock. The player must be able to move the camera away, inspect another angle, and return to the strategic overview with a clear reset/recenter action.
- Prevent the camera from clipping through terrain or buildings. Do not let camera orbit change unit movement, object orientation, selection, or simulation.
- Preserve current pan/zoom/rotation hotkeys and add tooltips/settings for any new camera controls. Include adjustable camera speed and inversion if supported by the input system.
- Test free orbit and detail views on a building, builder, tank, tactical vehicle, aircraft, and infantry. Close-up inspection must not break the strategic camera or command flow.

### Map layout, light, shade, contrast, and sharpness

- Treat map composition and rendering as core gameplay readability, not decorative polish. Build maps with visible routes, buildable areas, elevation, cover, supply areas, defensive positions, and landmarks that help players understand where to move and fight.
- Give each terrain type a coherent material palette and readable surface detail. Avoid large repetitive fields where roads, build areas, and supply points disappear into the same texture.
- Balance key lighting, ambient fill, shadows, contact shadows, and fog so the player base and active battle remain legible. Keep fog-of-war distinct from global haze; do not apply a grey wash across the whole playable area.
- Ensure buildings, walls, HESCO, vehicles, aircraft, and infantry have grounded contact shadows and consistent material response. Review shadow direction, softness, and contrast across the full map.
- Make asset details crisp at close zoom with appropriate texture resolution/filtering, clean mip transitions, readable decals, and restrained sharpening. Avoid blur, muddy surfaces, oversharpening halos, noisy textures, and excessive post-processing.
- Use level-of-detail transitions that preserve silhouettes and team identity rather than abruptly changing size or color. Maintain a stable frame rate by reducing fine detail gracefully at distance.
- Provide visual settings for quality, shadows, effects, and any sharpening/post-process options if the project supports settings. The default preset should remain clear and balanced on the target hardware.

### Nation/faction data and style

- Build shared gameplay/UI systems around faction data, not USA-specific assumptions. A faction definition should hold its display name, faction accent/palette, unit/building names, roster, asset references, upgrade compatibility, tech prerequisites, doctrine/battle plans, voice set, and any distinct rules.
- The same inspector, construction system, queues, camera, pathfinding, selection, health, veterancy, and accessibility behavior should work for every faction. Faction differences come from validated data and assets rather than duplicated UI/gameplay code.
- Preserve each nation's chosen military naming conventions, visual traditions, symbols, colors, and doctrine. Do not force every faction into USA labels such as War Factory or Airfield if its design uses different names; the data may localize the same gameplay role under a faction-specific label.
- Keep new factions hidden or marked as future content until their units, buildings, upgrades, voices, and balance are implemented. Do not reuse USA models or voice lines as if they represented another nation.
- Apply the same minimum readability, lighting, detail, and camera standards across all factions. Tune faction camouflage so it fits the environment without making units invisible to the player.
- Keep shared accessibility options global: UI scale, contrast/selection strength, camera speed, color-blind indicators, and readability settings must not reset when the player changes faction.

### Acceptance checks for presentation and factions

1. At the default and farthest strategic zoom, locate the builder, a tank, a tactical vehicle, infantry, and an aircraft on multiple terrain palettes without confusing them with the ground.
2. Select the builder from both the map and builder status control; issue a build and repair order; verify visible travel, work, progress, completion, and blocked-state feedback.
3. At close zoom, freely orbit, pan, and tilt around a building, builder, vehicle, aircraft, and infantry; return to the strategic camera without clipping or disrupting orders.
4. Inspect the same assets in sunlight, shadow, and fog-of-war. Confirm material detail, color separation, contact shadows, and sharpness without a global washed-out look or harsh sharpening.
5. Compare map routes, cover, supply points, build zones, and defensive positions at the default camera. Confirm terrain detail supports navigation rather than obscuring units.
6. Load a second faction through data/configuration without copying the USA UI or gameplay systems. Confirm its names, roster, markings, doctrine, and voices differ while controls, readability, and inspector behavior remain consistent.
7. Repeat readability and UI checks at 1080p, 1440p, and 4K with accessibility options enabled.

## 10. Core world, RTS, audio, and recorded-playtest requirements

This section folds the earlier playtest report and UI/economy brief into this final handoff. The two submitted recordings total about 9 minutes 43 seconds. Times below are local to each clip.

### Evidence from the two clips

| Clip time | What is visible | What Claude should verify |
|---|---|---|
| Part 1 around 3:20 and 4:20 | “Defense Tower building 84%” appears unchanged while the Airfield changes from construction to complete. | Determine whether the tower job is actually stalled or only its notification is stale. Show its real progress or a specific blocked reason. |
| Part 1 near the end | Selected infantry are difficult to identify at the strategic view; rings/markers are more prominent than the soldiers. | Test infantry visibility at the default and far zoom; improve silhouettes, LOD, scale, and selection feedback. |
| Part 2 around 0:14 | Airfield roster panel and 0/4 pad count are visible. | Exercise all four pad slots through production, takeoff, return, landing, and parking. |
| Part 2 around 2:02 (HUD about 6:12) | Selected A-10 passes near the base and appears large beside the Airfield. | Review world scale and framing. This is a scale concern to test, not proof of a bad model scale. |
| Part 2 around 2:10–2:14 (HUD about 6:20–6:24) | Strike/recon notifications and a target marker appear, but no clear B-1/B-2/B-52 cinematic pass is framed. | Improve bomber identity and optional camera focus without interrupting RTS control. |

Across both clips, the scene looks washed out and hazy, the map is broad and repetitive, some bright pads/scaffolds weaken ground contact, UI labels/costs are small or clipped, and pale weapon trails/smoke are hard to read. The buildings have visible volume in the footage; audit each asset before deciding whether it needs real 3D geometry, a deliberate 2.5D treatment, or only camera/material/lighting corrections. The recordings also contain desktop/editor capture artifacts; these are presentation/capture cleanup, not gameplay defects.

### Asset representation, scale, grounding, and animation

- Audit every playable building, vehicle, aircraft, infantry unit, defense, construction scaffold, shadow, and selection marker as a true 3D model, deliberate 2.5D asset, billboard, or fixed-view sprite. Do not assume all objects share the same representation.
- An object positioned in a 3D world is not automatically a 3D model. If a unit must rotate or be inspected from multiple angles, use geometry with depth or a deliberate directional 2.5D solution. Use generated images as modeling/material references; a single front view is not a complete 3D model.
- Keep pivots, terrain anchors, visuals, colliders, selection bounds, and shadows aligned. Building roots sit on their footprint; mobile roots sit at the ground-contact point. Camera motion must not make objects detach from terrain.
- Vehicle wheels/tracks must match movement; chassis and turrets rotate as intended. Infantry need recognizable idle, walk/run, firing, combat, and death states. Keep the working helicopter rotor animation and synchronize other moving parts with their state.
- Establish one world-scale reference for infantry, builder, HMMWV, tank, Airfield, Supply Depot, runway, and aircraft. Recheck the Chinook-to-Supply Depot and A-10-to-Airfield proportions. Do not fix perceived scale with inconsistent camera-space model resizing.
- Use a small representative asset set to validate model scale, material response, pivots, collision, animation, LOD, and lighting before converting the full roster.

### Core economy, construction, production, and command flow

- Keep one authoritative economy/power system shared by UI, AI, construction, production, and support abilities. Show current cash, income/spending, power generated/used, supply sources, and the reason an action is blocked or slowed.
- Preserve the documented B1.2 low-power effects unless source review proves they have changed: construction and production slow, Defense Towers slow, Radar turns off. Show the affected systems to the player.
- The builder/Dozer places structures with valid/invalid footprint previews, cost/time/prerequisites, construction progress, and clear placement errors. The same unit can be ordered to repair a damaged friendly structure. Rebuilding a destroyed structure goes through construction; it is not the same as repair.
- Keep a distinct queue per producer and a global production strip. Every real queue shows item, cost, progress, ETA when working, and a truthful queued/working/paused/blocked/complete state. Explain insufficient funds, power, blocked site, full pads, or missing prerequisites. Never show fake progress.
- Producer panels must use real definitions: B1.2 Barracks Rifleman/AT4; War Factory HMMWV .50/Vanguard tank/Avenger AA; Airfield F-16/A-10/AH-64; builder/Dozer structures; Supply Depot/Chinook logistics. Add future generated assets only after their complete game role exists.
- Preserve working commands such as move, attack, attack-move, guard, stop, force-fire, waypoints, scatter, rally point, control groups, and aircraft return-to-pad. Show accepted/blocked command feedback.
- Keep costs, build/research times, prerequisites, refunds, and power values in authoritative data/configuration. Do not hard-code them separately in UI code or copy original C&C balance numbers.

### Transport and service behavior

- Add Board/Enter and Unload controls only to actual data-configured transports. Define capacity, compatible passenger types, safe entry/exit, passenger display, destruction behavior, and whether passengers can fire while aboard.
- Do not turn every HMMWV into a troop carrier. HMMWV .50 and HMMWV TOW are distinct combat loadouts; configure passenger capacity only for a designed transport variant.
- Keep the current Chinook dedicated to Supply Depot crate collection unless a separate troop-transport mode is deliberately implemented. Do not silently change its economy role.
- Test unit service at War Factory and aircraft service at Airfield only if those repair/rearm mechanics are present. Show costs, progress, occupancy, and blocked reasons.

### Airfield lifecycle and bomber camera

- Reserve each of the four Airfield pads explicitly in Airfield-local coordinates and convert correctly to world positions. Aircraft should produce clear of buildings, launch, follow a valid route, return with the existing command, land on a reserved pad, and become available again.
- Full Airfields need a visible queue/wait state; aircraft must not overlap, idle outside the LZ, or fly to a map edge. Test F-16, A-10, AH-64 and any later aircraft at different map positions.
- The B-1, B-2, and B-52 are generated assets but are not documented in the B1.2 production roster. Keep them out of live menus until implemented as support aircraft with routes, payload, balance, and effects.
- When a bomber strike is implemented, identify the aircraft and mission on its card. Add a brief, optional, skippable camera focus of approach, release, and impact; blend back to the strategic camera and preserve player control. A close shot should improve visibility without changing world scale.
- Reuse current strike cards where their actual roles match; do not duplicate Recon Overflight, Carpet Bombing, or other existing support functions.

### Audio quality and capture readiness

- The earlier generated game audio was reported as unusable. Reassess or replace it with properly licensed or custom-designed sound that matches the event: aircraft flyby/takeoff, helicopter rotor, A-10 cannon, tank/vehicle movement, infantry commands, distinct weapons, impacts, construction, and base defense.
- Use unique readable signatures, correct timing, spatialization where helpful, and a mix that keeps commands audible. Add player volume controls and subtitles for spoken acknowledgements. Do not use generic voice lines as a substitute for distinct unit responses.
- Keep promotional/test capture clean: one resolution, game-only framing, no editor/startup dialogs, Windows taskbar/window chrome, or OBS display recursion. Treat these as recording fixes, not game bugs.

## 11. Acceptance checklist

- Every selectable existing building and unit opens the correct inspector on left-click.
- Right-click movement/attack behavior and existing hotkeys still work.
- Building panels list actual production, progress, prerequisites, power, upgrades, and service actions.
- Unit panels show role, status, promotion rank/XP, actual rank bonuses, and applicable upgrade states.
- The panel never lists unavailable aircraft or unimplemented mechanics as clickable content.
- Locked and blocked states explain what the player needs.
- Group selection remains useful and does not mix incompatible upgrades.
- Existing Support cards and names are reused where their roles match; no duplicate ability cards.
- Repair, aircraft pads, veterancy, and upgrades update from authoritative game state.
- Wall/berm placement, collision, line of fire, gate routing, damage, and repair follow their stated rules.
- Garrisonable HESCO positions support capacity, visible occupants, firing ports, safe exit, and destruction handling.
- The builder/Dozer remains visible, selectable, locatable, and commandable for construction and repair.
- Tanks and tactical vehicles remain identifiable against terrain at far zoom and show detailed models at close zoom.
- Close camera orbit, pan, tilt, and strategic recenter work without affecting simulation or clipping through the world.
- Map layout, lighting, shading, contrast, contact shadows, and fine object detail meet the same readability standard across factions.
- Faction names, assets, doctrine, and traditions are data-driven and distinct without duplicating shared systems.
- Current money, power, and queue rules remain consistent with B1.2 unless a deliberate, documented balance change is made.
- UI is readable at 1080p, 1440p, and 4K.
- Playable assets have a documented 3D/2.5D audit, consistent scale, grounded pivots/colliders/shadows, and visible movement animations.
- Construction, production, repair/rebuild, supply flow, power effects, and Airfield service are tested as a complete RTS loop.
- Transport controls appear only for implemented transports, with safe boarding/unloading and correct passenger state.
- Bomber strikes identify the right aircraft, show their route/release/impact clearly, and let the player skip back to the RTS view.
- Audio is reviewed and replaced or corrected where it does not match the event; commands remain audible.

