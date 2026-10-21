# Economy specification v0.1 (Prompt 8) — two-side slice, extensible to nine

All quantities are integers unless stated. Simulation runs at fixed 30 logic frames/s (`LOGICFRAMES_PER_SECOND`); every timer below is converted with `frames = ceil(ms × 30 / 1000)` once at load (engine INI parsers already do this), so all economy math is frame-exact and replay-deterministic. Money is integer credits; no fractional accumulation anywhere.

## 1. Quantities
| Symbol | Meaning | Unit |
|---|---|---|
| `V` | credit value of one cargo unit ("box") | credits/box (global, GameData `ValuePerSupplyBox`) |
| `C_h` | hauler capacity | boxes |
| `t_load` | load time per box at a deposit | ms/box |
| `t_unload` | unload time per trip at a depot | ms/trip |
| `d` | one-way path length deposit→depot | ft |
| `v_h` | hauler speed (locomotor) | ft/s |
| `B_0` | deposit starting boxes | boxes |
| `I_s` / `T_s` | secondary income amount / period | credits / ms |
| `P_prod`, `P_use` | power produced / consumed | power units |

## 2. Formulas
- Trip time: `T_trip = 2·d / v_h + C_h·t_load + t_unload` (plus ~1 s docking/turning, measured per hauler).
- Cargo value per trip: `Q = C_h · V`; income rate per hauler `R_h = Q / T_trip` (credits/s).
- Deposit life: `L = B_0 / C_h` trips; total value `B_0·V`; depletion when boxes = 0 → hauler auto-retargets within its scan radius or idles at depot (engine behaviour, verify).
- Secondary income: `R_s = I_s / T_s`, paid every `T_s` exactly; capture bonus `I_cap` once on first capture.
- Investment payback: `t_pay = cost / (R − R_alternative)`; design target: hauler payback 45–75 s, secondary site 120–180 s, so map control beats turtling.
- Power: `ratio = P_prod / P_use`; `ratio < 1` ⇒ brown-out (production rate × ratio-floor 0.5, powered defences off, radar off). Power is never spent.
- Build time: `frames = ceil(BuildTime_s × 30)`; multiple factories of the same type do **not** stack on one item (engine production queue per building).
- Rounding: credits integer; partial trips deliver nothing until unload completes (prevents fractional credit leaks; verify engine: unload is per-trip transaction).

## 3. Slice values (ours, provisional — balance agent owns)
| | USA (fictional) | China (fictional) |
|---|---|---|
| Hauler | "Mule" heavy-lift tiltrotor: `C_h=6`, `t_load=1100`, `t_unload=2500`, `v_h=110`, cost 1 400 | "Packhorse" truck: `C_h=3`, `t_load=900`, `t_unload=400`, `v_h=60`, cost 600 |
| Depot | Logistics Hub 1 800 | Logistics Yard 1 500 |
| Secondary | Uplink Contract building: 15 cr / 3 s, 2 max, killable | Field Market: +10 % on each delivery within 400 ft, stacks ×1 |
| Asymmetry intent | fewer, faster, fragile-to-AA haulers; pays for range | many cheap trucks; strong near home, weak to raids |
| Counterplay | AA/fighters on routes | fast raiders on truck lanes |
Global: `V = 80`, warehouse `B_0 = 360`, small pile `B_0 = 60` (deleted when empty), neutral derrick `I_s = 150 / 12 000 ms`, `I_cap = 750`.
Raid/deny/recapture: haulers killable; depots destroyable and rebuildable; derricks capturable by infantry, destroyable, **rebuildable only as a "derrick rig" by builders at the wreck** (B2 test).

## 4. B2 measurements to report (Prompt 8 acceptance)
Credit conservation (sum of deliveries + passive − spending = balance delta, per player, over a replay); trip times per hauler on Harbor Divide (measured, both sides); income curve 0–10 min human vs AI; replacement time of a lost hauler; recovery after starting deposit depletes; opening build orders; snowball check (lead at 5 min vs. win rate, AI-vs-AI 20 games).
