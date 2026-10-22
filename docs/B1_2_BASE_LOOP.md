# B1.2 - Base loop (Godot build)

Status: implemented and tested headless. Rendered evidence is in `docs/screens/b12_*`. All gameplay numbers are PROVISIONAL.

## What the player can do
- **Start.** A skirmish starts with a Command Center, one Dozer (M88 art), $10,000 and five neutral supply piles: two near each base and a larger one in the centre.
- **Build.** Select the Dozer. The build panel lists eight structures with icons, costs and tooltips.
  - Pick one; a green or red ghost of its art follows the cursor on a 2 m snap. Click to place it.
  - The cost is paid at placement. The Dozer drives to the site and builds it.
  - The card shows a scaffold lattice and a rising build line; a construction sound loops while the Dozer works.
  - Placement is refused when the cash is short, a requirement is missing, the footprint is blocked (rocks, structures, units) or the site is more than 140 m from your structures.
- **Power.** Power plants generate power and other structures consume it.
  - The HUD shows *use / generated*.
  - Under-powered: production and construction run at half speed, towers fire slowly, and the radar goes dark.
- **Economy.** The Supply Depot comes with a CH-47.
  - It flies to the nearest pile, loads $300 in 3 s, flies back and unloads in 2 s, then repeats.
  - Idle haulers resume on their own after 4 s.
  - More CH-47s can be bought at the depot.
- **Production.** Select a structure to see its production buttons and queue (up to 9).
  - Click a queue tile to cancel the last item; the refund is the full cost.
  - Click the map to set the rally point.
  - Aircraft appear on one of the Airfield's four pads and rearm there.
- **Sell.** Selling returns 50 % of the cost, scaled by remaining health.
- **Cancel construction.** Cancelling refunds the full cost.
- **Counters.** Combat uses armour classes:

  | Weapon type | Infantry | Light | Heavy | Air | Structure |
  |---|---|---|---|---|---|
  | Bullets | 1.0 | 0.5 | 0.1 | 0.5 | 0.15 |
  | Shells | 0.5 | 1.0 | 1.0 | 1.0 | 0.8 |
  | Rockets / missiles | 0.35 | 1.0 | 1.0 | 1.0 | 0.8 |

  The A-10 cannon overrides these values.
- **Victory and defeat.** Destroy every enemy structure and unit. Structures you have scouted stay visible in the fog at their last known state.
- **Minimap.** Enemy units show on the minimap only while you have a powered Radar.

## Structures (U.S. development side)

| Structure | Cost | Time | Power | Requires | Produces |
|---|---|---|---|---|---|
| Command Center | - (start) | - | 0 | - | Dozer |
| Power Plant | 800 | 12 s | +10 | - | - |
| Barracks | 500 | 15 s | -1 | Power Plant | Rifleman, AT4 Gunner |
| Supply Depot | 1500 | 18 s | -1 | Power Plant | CH-47 (one free) |
| War Factory | 2000 | 25 s | -2 | Supply Depot | HMMWV .50, Vanguard MBT, Avenger AA |
| Airfield | 1200 | 25 s | -2 | War Factory | F-16, A-10, AH-64 |
| Defense Tower | 1000 | 15 s | -2 | Barracks | (missiles vs ground and air) |
| HESCO Barrier | 100 | 4 s | 0 | - | - |
| Radar | 500 | 15 s | -2 | Power Plant | (enemy units on minimap) |

## Units added

| Unit | Cost | Time | Role |
|---|---|---|---|
| Dozer (M88) | 1000 | 10 s | Builder, unarmed |
| Rifleman | 200 | 5 s | Anti-infantry |
| AT4 Gunner | 300 | 7 s | Shoulder-fired anti-armour rocket |
| HMMWV .50 cal | 700 | 9 s | Fast; machine gun vs infantry and helicopters |
| Avenger | 800 | 10 s | Anti-air only |
| CH-47 | 1200 | 14 s | Supply hauler |

## Computer opponent (`scripts/base_ai.gd`)
- **Determinism.** It acts only through `Battle.issue()`, so its orders are logged with tick numbers like the player's.
- **Build order.** It follows a fixed build order around its Command Center: power, barracks, depot, power, factory, towers, airfield.
- **Upkeep.** It replaces a lost Dozer and adds a second hauler.
- **Production.** It trains a mix of rifles, AT4s, tanks, HMMWVs and Avengers.
- **Defence.** It answers enemies within 90 m of any of its structures.
- **Attacks.** It attacks the nearest enemy structure once enough units are idle, then pushes on.
- **Difficulty:**

  | Difficulty | Thinks every | Attack size | First attack after |
  |---|---|---|---|
  | Easy | 3 s | 10 | 300 s |
  | Normal | 1.5 s | 8 | 200 s |
  | Hard | 1 s | 6 | 120 s |

## Engine changes
- **Pathfinding.** Ground pathfinding moved from the baked navigation mesh to a deterministic 2 m grid (`AStarGrid2D`, `scripts/grid_nav.gd`). Structures update it instantly when placed or destroyed. Paths are string-pulled with a grid line-of-sight test.
- **Fog visibility.** Enemy visibility now reads the fog grid (O(units)) instead of an all-pairs distance test.
- **Structure visuals.** Structures use the imported building art on a camera-facing card (`shaders/structure.gdshader`), standing on the footprint edge nearest the camera. A team-coloured footprint outline marks the owner.
- **Vehicles and infantry from the art packs.** Vehicles pick the front 3/4, side or rear 3/4 view from the heading relative to the camera, and mirror it as needed. Infantry choose a pose from what they are doing: walk/run alternation, aim when firing.
- **Team marker.** Every card unit has a team-coloured ground marker.

## Known limitations (honest list)
- **Same roster on both sides.** Both sides use the U.S. roster until the China art and data arrive (B2).
- **Building art.** It does not rotate with the camera and has no damage states; the art's shadows are painted in.
- **Vehicle art.** Views switch in 3 steps (plus mirroring) instead of turning smoothly. Turrets are part of the art and do not turn.
- **Infantry art.** The walk cycle is a two-pose alternation.
- **Unused imported art.** Construction Yard, Airdrop Zone, Repair Bay, Field Hospital and Gatehouse were imported but are not used yet.
- **No save/load yet.** It is the next B2 item.
