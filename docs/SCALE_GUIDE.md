# World scale guide (Steel Accord)

- **Units:** 1 world unit = 1 metre.
- **Authored size:** art and models are authored at real size. The game draws each class at a fixed factor, so that structures stay dominant and units stay readable, as in classic RTS games.
- **Code:** the factors live in `UnitDefs.SCALE` and are applied by `Unit._apply_scale_guide()`, which scales the "Vis" visual root.
- **Collision:** hit and selection radius are scaled with the drawn size (infantry keep their real radius).

| Class | Factor | Example (real -> drawn) |
|---|---|---|
| Structures | 1.0 (footprint as defined in BuildingDefs) | Supply Depot 22 x 18 m; Airfield 34 x 26 m with a 2 x 2 apron of 16 m pads |
| Ground vehicles | 0.8 | M88 8.3 m -> 6.6 m; Vanguard; HMMWV 4.6 m -> 3.7 m |
| Aircraft | 0.6 | CH-47 30.1 m (with rotors) -> 18.1 m; F-16 15.1 m -> 9.1 m; AH-64 17.7 m -> 10.6 m |
| Infantry | 1.3 | 1.8 m -> 2.3 m |

**Checks (in automated tests):**
- `scale_ch47_vs_depot`: the drawn CH-47 must be smaller than the Supply Depot width and larger than 60 % of it.

**Not scaled:**
- Flight altitudes and weapon ranges are gameplay values.
- Old test-scenario pads (army scenario only) keep 28 m.
