# B1 runtime test - Kestrel scout + Field Depot (Harbor Divide or PZ Test Range)

Private prototype. Runs on the fork executable with your licensed Zero Hour data;
the Kestrel, its icon/glyphs, weapon, FX, wreck, terrain textures and the map are project-original.

## Install (once)
1. Unzip `PZ_B1_1_testkit.zip` anywhere.
2. PowerShell in that folder:
   `powershell -ExecutionPolicy Bypass -File .\install_b1.ps1 -TestCopy "<your isolated test copy>"`
3. Launch the command it prints, e.g.
   `& "<TestCopy>\generalszh.exe" -win -mod "<TestCopy>\PZ\PZDev_B1.big"`

## Test script (record result for each step; screenshot = PrintScreen / Win+Shift+S)
| # | Action | Expected | Shot |
|---|--------|----------|------|
| 1 | Skirmish -> Unofficial Maps | "PZ_TestRange.map (2)" listed with preview | S1 |
| 2 | You: **USA** (or **China**, not a sub-general). AI: any, Easy. Start | Map loads: concrete pads, gravel basin, ramps, supply docks beside each base; no crash | S2 |
| 3 | **Left-click your Command Center** so its build panel opens | Slot 11 (bottom row of the CC panel) shows the Kestrel button (vehicle icon); tooltip "Kestrel Scout (DEV)" | S3 |
| 4 | Click it twice | $450 deducted each; ~5 s build bar; Kestrel rolls out, tinted in your team colour | S4 |
| 5 | Left-click / box-select the Kestrels | Selection ring + health bar; portrait = Kestrel icon; panel shows Attack Move / Guard / Stop glyphs | S5 |
| 6 | Right-click ground across the map | Drives there (wheels don't spin - expected), climbs the ramps | - |
| 7 | **Ctrl + right-click** one Kestrel with the other selected (force-fire) | Yellow tracers + muzzle light; target health bar drops (~8 dmg/shot after 60% small-arms armour) | S6 |
| 8 | Keep firing until it dies | Flash + light camera shake; burnt wreck stays ~12 s then disappears | S7 |
| 9 | Drive Kestrels to the enemy base / let AI units arrive | Auto-acquires and fights enemies; can be destroyed by them | S8 |
| 10 | Select your **builder (dozer)** | New "Field Depot" button (USA slot 12 / China slot 13) with the depot icon | S9 |
| 11 | Place the depot on open ground | $800 deducted; structure rises from the ground over ~12 s; power usage +1 | S10 |
| 12 | Select the depot | Panel: Kestrel (slot 1), Rally Point, Sell; produce a Kestrel from it | S11 |
| 13 | Force-fire the depot with Kestrels (Ctrl+right-click) until destroyed | Burnt look when heavily damaged, flash + shake, rubble remains ~20 s | S12 |
| 14 | Exit | No crash on exit | - |

## Report back
- Screenshots S1-S8 (or a short video).
- If anything fails: the exact step, the on-screen text, and if the game crashed the
  `ReleaseCrashInfo.txt` / `*.dmp` from the user data folder
  (`Documents\Command and Conquer Generals Zero Hour Data\`).
- If your fork build is a debug/logging config, also attach `DebugLogFile*.txt` from the game folder.

## Known B1.1 limitations (not defects of this ticket)
- No sounds (audio is B3). No shadow (disabled: flat-shaded mesh, no shadow volume yet).
- Wheels are part of the static mesh (no wheel spin/steer bones yet).
- Still boots through the EA shell/menus and the stock USA/China command center. Original menu,
  building and standalone data are B1.2+ / B2 work.
