# B1.7: Inspector panels, Iran terminology and Skirmish setup (brief 10)

Status: implemented and checked on Linux with Godot 4.5.1. The Windows export was run under Wine, not on a Windows PC.
The screenshots and CNCNZ page referenced in brief 10 did not reach the project; this work follows the brief's text only.

## 1. What already existed before this pass (files responsible)

| Area | Before B1.7 | File |
|---|---|---|
| Selection, right-click orders, hotkeys | Working; covered by the army suite | `commander.gd` |
| Selected-object inspector | Unit and building panels, group roster, pin/close | `inspector.gd` |
| Production queues | Per building, charged when queued, full refund on cancel | `battle.gd`, `building.gd` |
| Upgrades / battle plans | Research at buildings, scoped effects, one plan at a time | `upgrades.gd` |
| Veterancy | Four ranks, class bonuses, chevrons | `veterancy.gd`, `hud.gd` |
| Faction data | Rosters, unit swaps, powers, flags per nation | `nations.gd`, `unit_defs.gd` |
| Command card | Build menu and production buttons mixed with research buttons in one row | `econ_panel.gd` |
| Skirmish setup | Map, nation and difficulty only | `main_menu.gd` |
| UI scale | In-game HUD only | `hud.gd`, `ui_kit.gd` |

## 2. Changes

- **Iranian terminology** (`nations.gd` labels; `battle.lbl()` / `battle.bname()`): structures, research, battle plans, powers and weapon names. Mechanics are unchanged and shared.
- **Command card** (`econ_panel.gd`): Production and Upgrades tabs (Command Center: "Upgrades & Plans"); queue tiles show unit names instead of internal ids.
- **Inspector** (`inspector.gd`): Overview / Production / Services / Pads / Upgrades sections; one authoritative state line; Command Center lists builders (working / available); repair-bay text no longer names the U.S. building.
- **Skirmish setup** (`main_menu.gd`, `game.gd`, `unit_defs.gd`): player table (army, colour, team, AI difficulty with disclosed modifiers), starting cash, game speed, victory/start rules shown, map preview (`maps/<id>/preview.png`, made by `tools/map/make_previews.py`).
- **Team colours** (`unit_defs.gd` `team_color()`): chosen colours drive the HUD, minimap and selection rings.
- **Scaling**: the menu now scales with screen height like the HUD (1440p ×1.33, 4K ×2).
- **Options** (`ui_kit.gd`): effects-volume slider.
- **Test fix** (`autotest.gd`, `battle.gd`): the carpet-bombing check now targets a red structure and counts bomb damage (`battle.bomb_damage`). The old check aimed at units that chase blue forces out of the bomb line before the flight arrives.

## 3. Validation

| Check | Result | Evidence |
|---|---|---|
| Iranian soldier (IRGC), Karrar, Boragh, F-14, group, Armour Works, Air Base, Garrison Barracks, Command HQ | Iranian names, weapons, upgrades and veterancy shown | `docs/screens/b17/ui_1080_*.png` |
| Live updates (queue %, research %, pad states, damaged health, XP) | Shown in the captures; queue/pad updates also asserted in QA | `ui_*_warfactory*.png`, `ui_*_airfield.png`; `AB: inspector_building_queue`, `inspector_airfield_pads` |
| 1080p / 1440p / 4K | HUD scale 1.0 / 1.33 / 2.0, no overlap of minimap, inspector, command card, power cards | `ui_1080_*`, `ui_1440_*`, `ui_4k_*` |
| Skirmish setup at 1080p / 1440p / 4K | Scales cleanly (before: unscaled at 4K) | `skirmish_*`; `before/skirmish_4k_unscaled.jpg` |
| Selection, right-click, hotkeys, camera, gameplay | QA 35/35, base 18/18, army 22/22, map 24/24 (Linux) | test logs |
| Windows export under Wine | see section 5 | |

Before/after: `docs/screens/b17/before/ui_720_prefix_*.jpg` are the same scenes before the queue-name, weapon-name and repair-text fixes; those captures were 1280×720.

## 4. Requested fields the game does not support yet

- Unit abilities with cooldowns (no unit abilities exist; support powers have cooldowns on their cards).
- Barracks medical service (only medic units and ambulances heal).
- Iranian structure models (labels are Iranian; the 3D buildings are shared).
- Icons on research cards (text cards only).
- More than two player slots, allied teams, other victory rules.
- Scaling of dropdown lists (popup menus) at 4K.
- Automated assertions for the Iranian inspector panels; the captures are visual evidence only.

## 5. Build

`build/SteelAccord_B1_7_win64.zip`: `SteelAccord.exe` (export preset "Windows", Godot 4.5.1) + `README_PLAYTEST.txt`.
