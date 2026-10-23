# Steel Accord: Modern RTS UI, Economy, and C&C-Style Mechanics
## Claude implementation brief and staged prompts

### Master instruction

Claude, work as the senior RTS gameplay and UI engineer for Steel Accord. Use the current Godot project and B1.2 playtest build as the source of truth. Build a modern, polished RTS interface and connect it to real gameplay state. Draw on the economy, producer buildings, upgrades, command flow, transport, and air operations of Command & Conquer: Generals - Zero Hour, while keeping Steel Accord's original modern military setting, names, and generated assets.

This is an implementation brief, not a mockup request. Inspect the project first, map existing systems and controls, then implement in small working stages. Preserve working functionality. Do not add decorative buttons, fake progress bars, placeholder upgrade effects, or unavailable units in the production menu. If a feature is not implemented, omit it or show it as clearly locked with a truthful reason.

Use the previous B1.2 QA report as companion context. Continue to address its visual, grounding, scale, aircraft-parking, repair/rebuild, and audio findings. The UI must expose real gameplay and must not hide underlying bugs.

## 1. What to adapt from Zero Hour

Adapt these game design patterns to Steel Accord. Do not copy original C&C art, interface files, maps, faction writing, or exact balance values.

### Economy and power

- Cash is earned through battlefield supply logistics and other implemented sources, then spent on structures, units, and upgrades. Supply gathering should be a strategic choice: sources can be limited, routes can be threatened, and the player should be able to see gatherers and deliveries.
- The Zero Hour manual describes USA Chinooks collecting supplies for the Supply Center and Supply Drop Zones adding periodic income. It emphasizes developing and protecting the supply chain. [1]
- Power is a visible base-wide constraint. Players add or upgrade power generation, and the UI explains what is impaired when power is low. Preserve B1.2 rules unless the design is deliberately changed: low power slows production and construction, slows defense towers, and turns radar off.
- Show current cash, income and spending trends, power generated and used, and the reason a task is blocked or slowed. Avoid hidden deductions or unexplained pauses.

### Construction, technology, and production

- Dozers build structures and repair damaged structures. Structure placement is a tactical map action with a valid/invalid preview, footprint, blocked reason, and construction progress. A destroyed structure is rebuilt through construction; a repair order restores a structure that still exists.
- Producer buildings have clear roles. The USA Command Center provides base construction/support functions; Barracks train infantry; War Factories produce and repair vehicles; Airfields produce and service aircraft; power and supply buildings support the economy. [2]
- Prerequisites form a readable technology tree. Show what is locked, the exact unlock requirement, and the cost.
- Upgrades are researched at specific buildings and affect clearly identified units or systems. Zero Hour examples place aircraft countermeasures and weapons upgrades at the Airfield, infantry upgrades at the Barracks, and broader army upgrades at a technology structure. [1][2]
- Each production building has its own queue, cost, build time, progress, cancellation/refund behavior, and rally/deployment point. Multiple facilities must remain independently visible.
- A contemporary review notes that original Generals required repeated selection of Barracks, factories, and airstrips to produce units. Keep the useful contextual building panel, but improve it with a persistent global production strip that shows every active queue. [3]

### Service, aircraft, and transport

- The USA War Factory can repair vehicles; the Barracks can heal certain wounded infantry; each USA Airfield can build, arm, control, and repair up to four airplanes. Use these as role references for Steel Accord's facilities. [2]
- Aircraft need a complete lifecycle: production, parking, launch, orders, return, landing, repair/rearm, and readiness for another order. B1.2 already documents four Airfield pads, so show pad occupancy and enforce it consistently. [2]
- A transport-capable unit has explicit passenger capacity and compatibility rules. The UI shows passengers, free capacity, and why a unit can or cannot enter.
- The Zero Hour USA Humvee can carry up to five soldiers. The Chinook can carry up to eight infantry or a mixed load of two vehicles and two infantry. These are optional balance references; do not silently change the current supply CH-47 into a troop transport. [2]
- Provide Board/Enter, Unload one, and Unload all for configured transports. Choose a safe dismount location and prevent passengers from appearing inside walls, terrain, enemies, or each other.
- Only transport-capable units get transport controls. Do not make every vehicle enterable or treat HMMWV .50/TOW weapon upgrades as passenger capacity.

### Battlefield orders

Keep Steel Accord's current orders discoverable and working: select, move, attack, attack-move, guard, stop, waypoints, scatter, rally points, aircraft return-to-base, and control groups. Use clear icons, short labels, tooltips, and hotkey hints. Unit roles and counters should be visible in plain language: anti-infantry, anti-armor, anti-air, artillery, transport, support, logistics.


## 2. B1.2 features to preserve

The supplied B1.2 notes describe a Windows x64 Godot game with:

- Command Center, Dozer, placeable structures, scaffolds, construction progress, cash, and power.
- Supply Depot Chinooks that collect cash from crate piles.
- Barracks: Rifleman and AT4 Gunner.
- War Factory: HMMWV .50, Vanguard tank, and Avenger AA.
- Airfield: F-16, A-10, and AH-64.
- Command Center: Dozer production.
- Four Airfield pads and R to return aircraft to a pad.
- Existing commands including A attack-move, G guard, F force fire, W waypoints, S stop, X scatter, zoom, camera rotation, and control groups.
- Both sides use the U.S. roster in B1.2; China is planned for B2.

Build the live menu from implemented game data. The larger generated asset suite, including F-35, F-22, B-1, B-2, B-52, Black Hawk, Apache, Patriot, THAAD, and other assets, should appear only after each item has a defined role, balance, model/animation, production rule, and working gameplay. Keep future content hidden or truthfully marked as locked. Keep the data model ready for another faction without hard-coding every panel to the USA.

## 3. Modern in-game HUD and building panels

Keep most of the screen available for the battlefield, with clear persistent controls.

- Top bar: cash, income/spending trend, power generated/used, low-power state, and match alerts.
- Main map: selection rings, health bars, command markers, rally points, construction footprints, and Airfield pad markers.
- Minimap: units, structures, camera rectangle, base, and important alerts.
- Selected-object panel: updates immediately when a building or unit is clicked; shows name, health, status, role, and relevant actions.
- Building command card: Overview, Production, Upgrades, and Actions/Service sections or tabs. Keep the main actions visible and avoid burying the feature list in multiple menus.
- Persistent production strip: queues across all active producer buildings. Clicking an entry focuses the producer or camera on it.
- Tooltips: plain-language effects, cost, time, prerequisites, target scope, and hotkey.
- Responsive sizing: common desktop resolutions and UI scaling must not clip text, queues, or controls.

When a building is selected, show its implemented features and current state:

1. Name and role.
2. Health, damage, construction, operational and power state.
3. Production options, grouped by unit category.
4. Upgrades, including cost, research time, prerequisite, effect, and affected units.
5. Supported actions such as repair assignment, support power, radar, sale, or service.
6. Current queue, active item, progress, ETA, and cancel/reorder controls.
7. Rally/deployment point when relevant.
8. Truthful disabled reason: insufficient funds, missing prerequisite, no pad, offline/damaged building, no Dozer, full transport, or incompatible passenger.

| Selected building/component | Panel must show |
|---|---|
| Command Center | Dozer queue, implemented support powers/cooldowns, radar/intelligence status, emergency repair if implemented, prerequisites, and base alerts. |
| Dozer | Structure catalog, cost/time/prerequisites, placement preview, construction target/progress, and repair orders for damaged friendly buildings. |
| Supply Depot | Supply stock, active CH-47s, route/cargo/return state, income, crate-pile status, and CH-47 queue. |
| Power Plant | Output, base demand, surplus/deficit, damage, upgrades, and which systems are impaired. |
| Barracks | B1.2 Rifleman and AT4 Gunner, cost/time/role, queue/rally point, and only implemented infantry upgrades. |
| War Factory | B1.2 HMMWV .50, Vanguard tank, and Avenger AA; costs/times/roles, upgrades, queue/rally point, and vehicle repair status if implemented. |
| Airfield | B1.2 F-16, A-10, and AH-64; cost/time/role, real upgrades, aircraft health/ammunition/readiness, pad occupancy, parked/in-flight/returning/repairing state, and return-to-pad command. |
| Base defense | Weapon role, range, valid target types, power state, upgrade, and repair state. |
| Economy/support building | Income or power, next delivery/cooldown, resource use, prerequisites, and damage/disabled state. |

## 4. Real progress bars and queue feedback

Show a truthful progress bar for every active timed operation:

- Structure construction: world scaffold and selected-building panel, percentage and ETA.
- Unit production: unit button, producer queue, and global production strip.
- Upgrade/research: progress, cost, completion, and affected units/buildings.
- Repair/rearm: health/service progress and queue position.
- Support action: cooldown/ready state, not a build progress bar.

Every queue item shows icon, short name, quantity, progress, ETA, affordability, and state. Use consistent states such as Queued, Working, Paused, Blocked, Complete, and Ready. Explain why an operation is paused. Define one rule for when cash is deducted/reserved and how cancellation refunds work; use it consistently. Do not show an ETA while a task is blocked.

A progress bar must be driven by the real game operation. It must never advance when production, construction, upgrade, or repair is not actually advancing.


## 5. Economy and core gameplay requirements

### Cash, supplies, and power

- Use one authoritative game economy shared by UI, AI, production, and support abilities.
- Display current cash plus income and spending. Track remaining supplies at each map source and active gatherer routes/deliveries.
- Keep the current CH-47 supply loop and show Loading, Returning, Unloading, Idle, Damaged, or Blocked.
- Use Supply Drops or passive income only when the required structure and rules are implemented.
- Preserve B1.2 low-power effects and identify them in the UI.
- Keep costs, times, refunds, prerequisites, power use/output, and upgrade effects in game data, not duplicated across UI scripts.

### Construction and production

- The Dozer opens a structure catalog. Each entry shows cost, build time, power use/output, prerequisites, footprint, and placement validity.
- Invalid placement explains why. Construction starts only after an accepted order.
- Each producer has an independent queue. Add/cancel and reorder only if supported and tested.
- Units exit from valid locations, then move to the rally point without intersecting buildings or leaving the map.
- Upgrades are real state changes. Define cost, research time, prerequisites, target scope, effect, and whether an upgrade is one-time or repeatable.
- Show clear prerequisites; never list aircraft at the Barracks or infantry at the Airfield.

### Repair, rebuild, and service

- A damaged structure can be repaired by ordering an eligible Dozer. The selected building panel may offer a Repair action that assigns an idle Dozer.
- A destroyed structure is rebuilt through the construction menu at the normal cost and prerequisites. Repair must not resurrect a destroyed object.
- If implemented, the War Factory repair bay services vehicles one at a time. The Airfield repairs/rearms aircraft and reserves pad slots correctly.
- Show repair/service cost, progress, blocked reasons, and insufficient-funds state.

## 6. Transport: Board, mount, dismount, unload

Implement only for data-configured transports.

- Each transport definition lists capacity, compatible passenger types, passenger slot size, and whether passengers can fire while aboard.
- Let infantry board a compatible nearby transport, or let the player select a transport and choose eligible nearby units.
- Show passenger portraits/names and occupied/total capacity.
- Provide Unload one and Unload all. The player can choose a safe dismount point.
- Play embark/disembark animation. Preserve health, ownership, veterancy, and orders according to a documented rule.
- Define passenger outcome if a transport is destroyed and communicate it.
- If HMMWV is a troop carrier, configure its capacity; five infantry is a Zero Hour Humvee reference, not a forced value.
- Keep the current CH-47 dedicated to supplies unless a separate troop-transport mode/upgrade is explicitly designed.
- Do not expose transport controls for non-transports.

## 7. Technical requirements

Inspect current Godot scenes, scripts, input map, definitions, queues, signals, and state managers before changing code. Reuse sound systems. Do not make duplicate economy managers, duplicate production timers, or one-off hard-coded UI tables.

Use one source of truth for buildings, units, upgrades, production jobs, transports, economy/power, and Airfield pad assignments. The UI renders from that data and subscribes to authoritative state changes. Suggested data concepts:

- Building: role, cost/time, prerequisites, power, production categories, upgrades, actions, service features.
- Unit: role, cost/time, producer, prerequisites, weapons, health/ammo, transport compatibility/capacity, upgrades.
- Upgrade: producer, cost/research time, prerequisites, target units/buildings, effect, repeatability.
- Production job: owner, producer, item, quantity, progress, state, blocked reason, refund rule.
- Economy: cash, income, spending, supply stock/routes, power output/demand.
- Transport: passengers, capacity, compatibility, load/unload state, safe exits.
- Airfield: pad reservations, aircraft readiness, return/repair/rearm state.

Use the existing architecture's equivalent if it is better. These are behavioral requirements, not a mandate to add classes with these names.

## 8. Staged prompts for Claude

Apply the master instructions above to every stage. Work sequentially and keep each stage playable.

### Prompt 1: audit and plan

Inspect the Godot source project, not only the Windows executable. Map current UI scenes, input actions, game-state managers, economy/power logic, building/unit definitions, queues, upgrades, repair, transport, Airfield pads, and controls. Compare them with this brief and the previous B1.2 QA report.

Return a concise matrix of implemented, partial, missing, and broken behavior; identify exact files; give a staged plan and meaningful test cases. Then proceed to Prompt 2. Do not stop with a mockup.

### Prompt 2: implement the HUD

Implement the actual in-game HUD, selected-object panel, contextual command card, minimap integration, resource/power header, and global production strip. Connect selection, hover, tooltips, actions, and status to real state. Keep the battlefield large and preserve B1.2 controls.

### Prompt 3: building panels and production queues

Implement data-driven building panels for Command Center, Dozer, Supply Depot, Power Plant, Barracks, War Factory, Airfield, and defenses. Include only implemented features. Add real per-producer queues, progress bars, costs, times, prerequisites, affordability, cancel/refund, rally points, and global queue navigation.

### Prompt 4: economy, upgrades, and power feedback

Connect the HUD to the authoritative cash, supply, and power systems. Show gatherer routes, supply stock, income/spending, power demand/output, low-power effects, and blocked reasons. Implement truthful upgrade progress and effects. Verify cash cannot be charged twice and UI values match game state.

### Prompt 5: transport and mount/dismount

Implement Board/Enter and Unload controls for configured transports with capacity, passenger list, compatibility, safe dismount, animation, and persistent passenger state. Decide and document whether a particular HMMWV or CH-47 variant is a transport. Do not change the supply CH-47's role accidentally.

### Prompt 6: repair, rebuild, and Airfield service

Implement Dozer repair for damaged structures and construction-based rebuilding for destroyed structures. Add War Factory vehicle service and Airfield repair/rearm if supported. Expose actual Airfield roster, upgrades, readiness, and four pad reservations. Test multiple aircraft and R returns.

### Prompt 7: integration QA and handoff

Run the full loop: supply gathering, cash/power changes, building placement/construction, unit production, upgrades, transport load/unload, combat orders, repair/rebuild, aircraft takeoff/return/landing, repair/rearm, and AI production. Test low funds, low power, blocked placement, full transport, full Airfield, canceled queues, and destroyed producers.

Report changed paths, implemented behavior, tests and results, screenshots or a recording, and remaining limits. Do not mark a button complete unless it works in the running game.

## 9. Acceptance checklist

- Clicking every building opens the correct panel with actual features.
- The B1.2 Airfield lists F-16, A-10, and AH-64, shows real upgrades, and reports four pad states.
- Barracks, War Factory, Supply Depot, Command Center, Power Plant, and defenses show correct actions/status.
- Every active construction, unit, upgrade, and repair job has an accurate bar and state.
- Cash, supply, and power values match game state; low-power rules match B1.2.
- Global queue shows work across buildings without hiding the selected producer queue.
- Rally points and unit exits work; no unit spawns inside a building or outside the map.
- Transport-capable units load and unload safely; other vehicles do not expose those actions.
- Damaged buildings repair through Dozers; destroyed buildings rebuild through construction.
- Aircraft produce, launch, return with R, land on an available pad, repair/rearm, and become usable.
- Existing combat, selection, camera, hotkeys, and AI still work.
- No fake controls, queues, upgrades, or progress.


## 10. Sources

[1] Command & Conquer: Generals - Zero Hour manual, PDF mirror. USA upgrades, supply strategy, Airfield, and economy descriptions: https://static.wikia.nocookie.net/cnc_gamepedia_en/images/b/b1/CNC_Generals_Zero_Hour_Manual_2015.pdf/revision/latest?cb=20180801163919&format=original

[2] Command & Conquer: Generals PC manual, PDF mirror. USA Dozer, Humvee, Chinook, production buildings, repairs, and aircraft descriptions: https://static.wikia.nocookie.net/cnc_gamepedia_en/images/2/2b/CCDECpcMAN.pdf/revision/latest

[3] GameSpot, Command & Conquer: Generals Zero Hour review (2003). Describes the contextual producer-selection workflow and its usability tradeoff: https://www.gamespot.com/reviews/command-and-conquer-generals-zero-hour-review/1900-6075810/

Use the manuals as mechanics references and the Steel Accord source project as the authority for what is implemented.
