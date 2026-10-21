# GAME DESIGN — Steel Accord · draft v0.1

Fictional, skirmish-first modern RTS. Factions are playable armies with invented equipment and doctrine; nothing here describes or judges real forces or governments. No faction is the villain; any side can be player, ally or AI. No campaign story in scope.

## 1. Pillars
1. **Fast and readable** — 30 Hz lockstep sim, instant command response, silhouettes and team colour readable at default zoom.
2. **Counters over stats** — every unit has a job, a hard counter and a soft counter.
3. **Asymmetric but fair** — factions differ in *how* they win (economy shape, mobility, defence, support powers), validated by matchup tests, not intuition.

## 2. Core economy (audited against the brief's corrections)
- **Cash** is the only spendable resource.
- **Power** is a *capacity* (supply vs. demand). Underpowered: radar off, production −50 %, powered defences offline. Never spent.
- **Active income**: gatherers haul from finite supply sites to a depot (travel + load time = harassable).
- **Secondary income**: slower, uncapturable-by-gathering sources (e.g. faction-specific derricks/markets), each a target.
- **Rank powers** (earned by combat experience points, cooldown-based) are separate from **constructed superweapons** (building, long timer, visible countdown, killable).

## 3. Vertical slice (B2): USA vs China — 3 combat roles each
| Role | USA (fictional) | China (fictional) |
|---|---|---|
| Line infantry / anti-infantry | Rifle Team | Rifle Squad (larger, cheaper) |
| Anti-vehicle | Javelin-style AT Team | Rocket Team |
| Main battle vehicle | Medium Tank (fast, precise) | Heavy Tank (slow, armoured) |
| Scout (B1.1 test unit) | **Kestrel Scout** — shared dev unit, faction-neutral art | same |
Counter rule of thumb: infantry ⟶ beaten by scouts/tanks; scouts ⟶ beaten by AT and tanks; tanks ⟶ beaten by AT and air (B4).

## 4. Nine sides — identity sheets (mechanical, not political)
| Side | Doctrine hook | Strengths | Weaknesses |
|---|---|---|---|
| USA | Precision & air superiority; drones as detection | strong air, long-range sensors | expensive units, small armies |
| China | Massed formations; horde bonus; strong artillery | numbers, durable tanks | slow, weak early air |
| Japan | Advanced tech, robotics & naval-coastal defence | highest-tech units, shields | low unit count, high power demand |
| Taiwan | Island-fortress doctrine; mobile coastal missiles | best static/mobile AA & AT defence | weak late offence |
| Europe (coalition) | Modular coalition: pick 1 of 3 national "detachments" per match | flexible, best logistics | each detachment shallow |
| Ukraine | Adaptive warfare; cheap drones, field repair, salvage | resilient, cost-efficient | fragile units, low armour |
| Iran | Missile & fast-attack doctrine; strong mobile rockets | burst damage, raids | weak sustained fights |
| Iraq | Combined-arms rebuild; strong engineers & fortified convoys | durable logistics, repair | slow tech curve |
| North Korea | Deep defence; tunnels and hardened artillery | static durability, artillery | poor mobility and air |
Each gets a full sheet (tech tree, roster, cost/time, counter matrix row) before entering B4 implementation; batches of two sides.

## 5. Maps
Five fictional biomes: coastal industrial crossing, dense city, mountain pass, island coast, open terrain.
**Harbor Divide (B1 map, built 2026-10-21)** — 2 players, 3 000 × 3 000 ft playable (300 × 300 cells), point-symmetric. A north–south tidal channel (engine water polygon, surface 34 ft) splits the map; ground units cross on a wide centre causeway (contested) and narrow north/south causeways. Raised quays hold the starts (P1 west, P2 east). Per base: 2 safe supply docks (600 / 720 ft from start); per bank: 1 forward supply warehouse (1 230 ft); 2 contested oil derricks beside the north/south crossings. Measured by `tools/gen_harbor_divide.py` BFS on 10 ft cells: start-to-start 3 480 ft both ways; each crossing usable alone (3 480 / 4 140 / 4 160 ft); all resources reachable; report `build/reports/harbordivide_fairness.txt`. Bridges as destructible objects: B2 (needs our own bridge object + pathfinding layer test). Engine path check in-game still required.
**PZ Test Range (B1.1, built)** — 1 280 ft square, mirrored, raised start pads, central basin with berm and three crossings. See `build/previews/testrange_blockout.png`.

## 6. UI flow (target)
Title → Skirmish setup (side, colour, team, AI difficulty, map preview) → Loading (map art + tips) → In-game HUD: minimap (left), selection/portrait (centre), command grid 4×3 + production queue (right), power & cash readout top, rank-power bar top-left → Pause/options (keybind remap, UI scale, colour-blind team palettes).

## 7. Art / audio briefs (short)
Art: grounded near-future military industrial; clean shapes, 3-tone palettes per side, team colour on dedicated panels (engine HOUSECOLOR meshes); no real insignia or emblems — every side gets invented emblems. Audio: original UI clicks, mechanical/engine foley, weapon layers by calibre; music direction: percussive hybrid orchestral/electronic, no imitation of existing scores; voice via licensed actors or licensed TTS, no cloning.

## 8. Acceptance criteria (gates)
B1.1: Kestrel can be built from the CC on PZ Test Range, selected, moved, attacks, damages, is destroyed and leaves a wreck (screenshots S1–S8). B2: clean-folder boot; full match USA vs China AI to victory/defeat; save/load round-trip. Balance gate per batch: AI-vs-AI 50 matches per pairing, no side >60 % win rate.
