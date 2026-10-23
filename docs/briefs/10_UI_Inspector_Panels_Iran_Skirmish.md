Please review the attached Steel Accord UI screenshots and improve the in-game interface, with the Iran faction as the first test case.

I also provided a CNCNZ reference page for Command & Conquer: Generals – Zero Hour. It is a unit guide, not the game source code. Use its organization pattern—unit class, role, cost, prerequisites, abilities, upgrades, and research location—as inspiration. Do not copy its faction data or assume its mechanics exist in Steel Accord.

Before editing, inspect the project’s current UI, faction data, selection system, production queues, upgrades, and game state. Report what is already implemented and identify the files/components responsible. Treat the current source as authoritative. Do not add visual controls for mechanics that do not work.

### 1. Shared selected-object inspector

When the player left-clicks a selectable soldier, tank, tactical vehicle, aircraft, or building, open or update a consistent inspector panel. Keep right-click movement and attack commands intact.

For units, show the fields that actually exist:
- Faction-specific name, unit type, role, portrait or icon, and owner
- Health and a clear current state/order
- Weapon/loadout information
- Compatible installed, available, researching, and locked upgrades
- Promotion rank, progress to the next rank, and earned bonuses
- Unit abilities, cooldowns, and service or transport state only when implemented

For buildings, show the fields that apply:
- Name, purpose, health, operational state, power, and prerequisites
- Production choices, queue, progress, and blocked reason
- Upgrades grouped separately from production
- Repair, service, and other actions only if supported by the game

Do not present mutually exclusive states together. For example, an object should not be labeled both “idle” and “engaging.” Show one authoritative state and its current order.

### 2. Building-specific panels

Make the information useful for each producer and command building:

- **War Factory:** list available vehicles and tanks, their costs and prerequisites, the current queue and progress, and compatible upgrades.
- **Airfield:** list available aircraft separately from research; show all four pad states and aircraft status such as queued, parked, launching, returning, or servicing only if those states exist.
- **Barracks:** list available infantry and compatible upgrades. Show healing or medical services only if implemented.
- **Command Center:** show builder/Dozer availability, construction options, and command functions that exist in the current game.
- **Other buildings:** provide a panel based on their actual purpose, such as power, supply, defense, or research.

Use sections or tabs such as **Overview**, **Production**, **Upgrades**, and **Services** where they reduce clutter. Each item should show its icon, name, cost, prerequisite, and real progress or lock reason. Do not mix production cards and research cards into one unclear row.

### 3. Layout and visual design

Keep the battlefield as the main focus. Use consistent typography, spacing, icon sizes, contrast, button states, and panel placement. Keep the minimap, resource HUD, support abilities, selected-object inspector, and command buttons from obscuring one another. Make text readable at common resolutions and provide hover tooltips for icon-only controls.

Polish the Skirmish setup screen using the screenshot’s categories: player slots, faction/army, color, teams, map preview and selection, starting resources, game speed, match rules, and launch/back actions. Keep those settings easy to scan and resize cleanly.

### 4. Iran faction and other nations

Use faction data for names, unit roles, icons, upgrades, prerequisites, and visual identity. The Iran interface should use its own terminology and roster; do not label its units as American units or inherit USA upgrade names by default. Build the inspector and layout as shared systems so other nations can use them with their own traditions and settings.

### 5. Validation

Test by selecting an Iran soldier, Karrar tank, tactical vehicle, aircraft, Airfield, War Factory, Barracks, and Command Center. Verify that each panel shows the correct faction-specific data and updates when health, orders, queue progress, upgrade state, or pad occupancy changes.

Check 1080p, 1440p, and 4K layouts. Confirm that left-click inspection does not break selection, right-click commands, hotkeys, camera control, or existing gameplay. Provide before/after screenshots, list changed files, and report any requested fields that the source does not yet support.