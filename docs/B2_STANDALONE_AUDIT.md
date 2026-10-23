# B2 standalone and provenance audit (QA/build/release)

Date: 2026-10-23. Auditor: QA/build/release agent. Environment: Linux, Godot 4.5.1, **Wine 64-bit** (prefix `/root/.wine64b`). **No Windows PC test was run.** Every runtime result below comes from Wine.

Legend: **[O]** observed in this audit (command output or log on disk). **[A]** assumed or inferred, not directly verified.

## 1. Verdict

| Question | Answer |
|---|---|
| Does the exported build boot and pass the map test from a folder holding only `SteelAccord.exe`? | **Yes [O].** `RESULT 24/24`, reproduced in two runs. |
| Does the process read any game data outside its own folder? | **No [O].** Outside Wine/OS files, it opened only the exe and its own user-data log folder. |
| Did it touch any EA / Steam / Command & Conquer path? | **No [O].** No traced path matches the EA/Steam pattern. No such folder exists in the Wine prefix. |
| Is every shipped asset cleared for public release? | **No [O].** 24 of 503 shipped assets are `shippable`. 302 are `dev_only` and 177 are `unknown`. See section 6. |
| Does the process exit cleanly? | **No [O].** Under Wine, an unhandled page fault after `RESULT 24/24` gives exit code 5. Not tested on Windows. |

B2 standalone criterion ("needs nothing outside its own folder"): **met under Wine [O]**, Windows unverified.
B2 content criterion ("only our licensed/shipped content"): **not met**. The build still ships client-supplied AI concept art and derivatives marked DEV ONLY, plus assets with no manifest entry.

## 2. Build

```
mkdir -p /home/claude/pzh/build/clean_b2/SteelAccord_B2
cd /home/claude/pzh/godot && timeout 1500 /opt/godot/Godot_v4.5.1-stable_linux.x86_64 --headless \
    --export-release "Windows" /home/claude/pzh/build/clean_b2/SteelAccord_B2/SteelAccord.exe
```

- Result [O]: exit 0, 2 min 13 s, no `ERROR`/`WARNING` lines. Log: `build/clean_b2/export.log`.
- Preset [O] (`godot/export_presets.cfg`):
  - `export_filter=all_resources`
  - `include_filter="*.json,*.r16"`
  - `exclude_filter="scenes/art_preview.*"`
  - `embed_pck=true`
  - release template, x86_64
- Folder contents after export **and after both runs** [O]: exactly one file.

| File | Bytes | SHA-256 |
|---|---|---|
| `build/clean_b2/SteelAccord_B2/SteelAccord.exe` | 331,889,432 (317 MiB) | `5b190c181e8fbb8def573f3b1f8cc5c4cc70f144a0f970a32bcf152684849015` |

- No console wrapper is produced. The preset makes it for debug exports only.
- Pack contents [O]: the embedded pack stores 1,122 entries. These map to **578 project source files**: 503 assets, 54 code, 21 data JSON.
- The audit's own walk of the preset filters matches the export log **exactly**: 0 files walked but not in the log, 0 in the log but not walked. The cross-check is in `build/reports/asset_audit_b2.json` → `export_log_crosscheck`.
- Not exported [O]:
  - `_qa/` folders (`.gdignore`)
  - `scenes/art_preview.*`
  - `maps/zagros_basin/fairness_report.txt`
  - 89 generator copies of textures (`*_albedo.png` etc., `importer="skip"`; the same images are embedded in the GLBs)
  - `assets/ui/icons/_sheet.png`

## 3. Runtime test under Wine

```
cd /home/claude/pzh/build/clean_b2/SteelAccord_B2
WINEPREFIX=/root/.wine64b WINEDEBUG=-all strace -f -y -tt -e trace=%file,chdir,fchdir \
    -o /home/claude/pzh/build/clean_b2/strace_run_y.log \
    timeout 3000 /usr/lib/wine/wine64 SteelAccord.exe --headless --fixed-fps 30 -- maptest map=zagros_basin nation1=iran
```

| Run | Time (UTC) | strace | Result | Exit | Logs |
|---|---|---|---|---|---|
| 1 | 15:11–15:17 | `-f`, no fd decoding | `RESULT 24/24` | 5 | `build/clean_b2/wine_stdout.log`, `strace_run.log` |
| 2 (**authoritative**) | 15:23–15:30 | `-f -y` (exact paths for every fd and cwd) | `RESULT 24/24` | 5 | `build/clean_b2/wine_stdout_run2.log`, `strace_run_y.log` (90,492 lines) |

Run 1 is kept for reference only. Without `-y`, relative paths (Wine registry, font scan) cannot be resolved reliably.

- Tests passed [O] (24):
  - map_loads, starts_from_map, units_grounded, structures_on_flattened_ground, props_grounded, sites_grounded
  - routes_passable, cliffs_block, class_slope_rules, starts_fair, steep_placement_rejected, flat_placement_grounded
  - derrick_capture, derrick_income, derrick_changes_owner, supply_delivery, vehicle_drives_on_terrain
  - ai_builds_on_terrain, ai_captures_derrick, ai_nation_roster, iran_battle_cry, iran_shahed_strike, iran_roster_models, nation_flag
- Defects seen in both runs [O]:
  1. **Crash at shutdown.** `wine: Unhandled page fault on read access to 0000000000000000 at address 000000014423E4D9 (thread 0024)`, printed after `RESULT 24/24`; exit code 5. Whether this also happens on Windows is **unknown [A]**.
  2. **`ERROR: Could not create directory: '/tmp'`** (`core/io/dir_access.cpp:178`). Test and screenshot scripts hard-code `/tmp/...` output paths: `autotest.gd`, `evidence.gd`, `baseshots.gd`, `mapshots.gd`, `m1shots.gd`, `pilotshots.gd`, `vischeck.gd`, `main_menu.gd:55`. These harness scripts ship in the release build. In this run the call failed before reaching the file system: no matching syscall in the trace [O]. On Windows, a path like this could resolve to `<drive>:\tmp`, outside the game folder [A]. They should write to `user://` or be excluded from release exports.
  3. Two `Unicode parsing error ... Unexpected NUL character` lines at startup. Not investigated.

## 4. Files actually opened (filtered)

The classifier is `tools/qa/filter_strace.py`. Full output: `build/reports/b2_wine_file_access.json` (+ `.txt`).

| Category | Unique paths | With a successful call | Written | Meaning |
|---|---|---|---|---|
| clean_folder | 305 | **2** | **0** | The folder itself and `SteelAccord.exe` |
| user_data | 11 | 10 | 3 | `C:\users\root\AppData\Roaming\Godot\app_userdata\Steel Accord\logs\` |
| wine_prefix | 177 | 93 | 6 | Registry hives, `system32`, `winsxs`, `com1` |
| wine_runtime | 174 | 167 | 4 | `/usr/lib/wine`, `/usr/share/wine`, wineserver socket dir `/tmp/wine-*` |
| system | 826 | 627 | 36 | `/usr/share` fonts, fontconfig, `/lib`, `/etc`, `/proc/<pid>/task/*/comm`, `/dev/null` |
| ancestor_dir | 7 | 7 | 0 | `/`, `/home`, `/home/claude`, `/home/claude/pzh`, `/home/claude/pzh/build`, `/home/claude/pzh/build/clean_b2`, `/root` |
| OTHER | 8 | 5 | 0 | See below |

The ancestor directories were only stat'ed or `readlink`ed while Wine resolved the exe path; none of them was read as a file.

**Game files read with success [O]:**
- `build/clean_b2/SteelAccord_B2/SteelAccord.exe` (contains the embedded pack)

**User data [O]:**
- Under `AppData/Roaming/Godot/app_userdata/Steel Accord/`, the game wrote `logs/godot.log` and `logs/godot2026-10-23T11.24.11.log`. It also rotated (deleted) `logs/godot2026-10-22T23.19.42.log`.
- It looked for `settings.json` there and did not find it.

**Lookups that failed (files absent), inside the clean folder [O]:**
- 303 paths, all optional, nothing was missing for the run:
  - Godot's on-disk fallbacks for `res://` paths: `*.remap` 136, `.godot/**` 68, `*.import` 30, `*.gd` 24
  - Windows DLL search order: 37 `*.dll`
  - `override.cfg`, `icudt_godot.dat`, `default_bus_layout.tres`
- Release note [A]: Godot loads an `override.cfg` placed next to the exe. That is standard Godot behaviour, worth knowing for support and anti-tamper.

**OTHER [O]** is not game data. It holds:
- `//` and `//home`: the root and `/home` spelt with a double slash, which normpath keeps. Directory stat only.
- `/dev`, `/proc`, `/sys`: directory stat.
- `/.flatpak-info`, `//.windows-label`, `//.windows-serial`: Wine probing drive `Z:` (mapped to `/`); not found.

**EA / Steam / C&C [O]:**
- No traced path matches `steam|command & conquer|c&c|cnc|generals|zero hour|electronic arts|ea games|*.big`.
- `find` over the prefix's `drive_c` (depth 4) found no Steam, C&C or Electronic Arts folder.
- The binary has no `Zero Hour`/`Command & Conquer`/`Electronic Arts`/`.big`/`steamapps` strings.
- In the sources, the only such text is the menu disclaimer `main_menu.gd:228` ("Not affiliated with or endorsed by Electronic Arts. No Command & Conquer assets are used.") and a code comment in `battle.gd:1289`.

**Caveat [A]:** the prefix maps `Z:` to `/`, so the game *could* reach any host path. The trace shows it did not. This holds for the `maptest` path only; the menu, skirmish and save flows were not traced.

## 5. Asset audit method

The script is `tools/qa/asset_audit.py` (read-only):

```
python3 -I tools/qa/asset_audit.py --export-log build/clean_b2/export.log
```

It writes `build/reports/asset_audit_b2.json`. That file gives path, size, SHA-256, manifest source, licence, status, match rule and review flags for each of the 578 files, plus summary counts and the export-log cross-check.

Matching order:
1. Exact path in `content/manifest/{audio,ui_icons,aircraft,us_packs}.json`. `content/MANIFEST.json` was also read, but it lists only the Zero Hour-era `content/` and `maps/` trees, with no Godot paths.
2. Folder-level entries: `assets/us/**` → `us_packs.json`; `assets/aircraft/**` → `aircraft.json`.
3. Textures Godot extracted from a GLB (`<glbstem>_<image>`) inherit that GLB's record.
4. GLBs, which have **no manifest entry at all**, get an audit-derived record from their generator script in `tools/art/`:
   - The pipeline kit the script imports is read at run time.
   - `vehkit`/`airkit`, and the M88 and CH-47 pilot scripts, **project client AI concept art into the albedo**. These are `dev_only` derivatives.
   - `vehkit_ir`, `airkit_ir`, `bldkit`, `bldkit_b`, `inf_kit`, `prop_zb_common` and the G1 scripts are procedural. They count as `unknown` until a manifest entry exists, because ARCHITECTURE.md requires a manifest entry before ship status.
5. Iran icons, menu background and map files are matched by explicit audit rules. No manifest entry exists for them.

Status rules:
- `shippable` only when a manifest says so.
- `dev_only` when a manifest says DEV ONLY / dev_only / dev_ok-pending, or when the asset derives from such material.
- Otherwise `unknown`.
- Code and data JSON are counted separately and not licence-audited.

## 6. Results

### 6.1 Counts [O]

| Status | Assets | Bytes |
|---|---|---|
| shippable | 24 | 0.23 MB |
| dev_only | 302 | 205.5 MB |
| unknown | 177 | 144.2 MB |
| **total assets** | **503** | 349.9 MB (before import compression) |

- 243 assets have no manifest entry.
- 139 assets carry a review flag:
  - they depict a real-world equipment design or name (trademark/design review), **or**
  - they carry a national flag or insignia texture.

### 6.2 Licence table [O]

| Licence recorded | Files | Status |
|---|---|---|
| AI-generated concept art supplied by client (ChatGPT; generator terms; not cleared) — `us_packs.json` | 199 | dev_only |
| Project-original, code-generated — **no licence recorded in any manifest** (audit-derived) | 156 | unknown |
| Derivative of client AI concept art (texture projected by `vehkit`/`airkit`/M88/CH-47) | 66 | dev_only |
| Original work, project-owned — `ui_icons.json` | 24 | shippable |
| Client-supplied AI art, "confirm before release" — `aircraft.json` | 23 | dev_only |
| Unknown, no record (Iran icons, menu background) | 21 | unknown |
| Pixabay Content License — `audio.json` | 13 | dev_only (per-item page URL and uploader not recorded) |
| Not stated — `iran_shout.ogg` | 1 | dev_only |

### 6.3 Every `dev_only` asset (302) [O]

| Group | Files | Why |
|---|---|---|
| `assets/us/buildings`, `infantry`, `vehicles`, `rotors` | 42 + 84 + 65 + 8 | Client AI concept packs. `us_packs.json` marks them DEV ONLY: real designs, names and insignia. |
| `assets/aircraft/*` (sprites and icons for a10, ah64, b1, b2, b52, c130, ch47, f16, f22, fa18, sr71, uh60) | 23 | `aircraft.json`: "DEV ONLY - release review required". `c130_top.png` is covered only by the folder rule. |
| US aircraft GLBs + extracted textures: a10, ac130, ah64, b1, b2, b52, c130, c17, ch47, f16, f22, f35, fa18, sr71, uh60 | 36 | `airkit` / `air_ch47_3d.py` projects the client concept views into the albedo. |
| US vehicle GLBs + extracted textures: abrams, bradley, hmmwv, hmmwv_50cal, hmmwv_medical, hmmwv_tow, avenger (all from `veh_hmmwv_3d.py`), m113, m777, m88, mrap, paladin, stryker | 30 | `vehkit` / `veh_m88_3d.py` projects the client concept views. |
| `assets/audio/*.ogg` | 14 | 13 Pixabay clips (status "dev_ok; release needs per-item page URL"), plus `iran_shout.ogg`. |

On `iran_shout.ogg`: the client's Farsi clip, source file `Iranian_soldiers_shouting.mp3`. Provenance, licence and spoken content are not confirmed, so release is **blocked**.

**Correction to the brief:** `audio.json` lists **13** Pixabay clips plus the client shout (14 files in total), not 14 Pixabay clips. The 13 Pixabay clips are:

| | | | | |
|---|---|---|---|---|
| a10_cannon | rifle_burst | mg_burst | explosion_big | rocket_launch |
| sam_launch | bomb_fall | jet_flyby | jet_takeoff | heli_loop |
| tank_loop | construction_loop | radar_ping | | |

All 13 cite the Pixabay Content License, with client confirmation dated 2026-10-22. None records its item page URL or uploader.

These dev-only assets are **in active use**, not leftovers:
- `unit_defs.gd` loads the aircraft sprites and icons.
- `building_defs.gd` and the US art path use `us_packs.json` art.
- The US 3D units use the projected GLBs.

They therefore have to be replaced; excluding them alone would remove the US faction's art.

### 6.4 Every `unknown` asset (177) [O]

| Group | Files | Evidence | To move to shippable |
|---|---|---|---|
| Iran vehicles and aircraft GLBs + textures: ir_bmp2, ir_boragh, ir_engineer_dozer, ir_karrar, ir_t72s, ir_ah1j, ir_c130, ir_ch47, ir_f14, ir_f4, ir_su24, ir_shahed, ir_shahed_rail | 34 | `vehkit_ir`/`airkit_ir`: procedural paint, concept panels used for reference only | Manifest entries; trademark/design review (real designations) |
| Infantry GLBs + textures. US: rifleman, at4, paratrooper (+ parachute), medic, saw_gunner, m240_gunner, sniper, ranger, special_forces, pilot, eod_engineer. Iran: ir_rifleman, ir_rpg, ir_mg, ir_sniper, ir_medic, ir_engineer, ir_paratrooper, irgc_sf | 58 | `inf_kit`: procedural. Camo palette colours were k-means-sampled from client AI concept art (colour values only) [O, from source]. Iran roles carry a flag patch. | Manifest entries; insignia decision |
| Structures: airfield, barracks, command_center, defense_tower, drop_zone, hesco, power_plant, radar, supply_depot, war_factory, command_post | 27 | `bldkit`/`bldkit_b`: procedural tileable textures, colours sampled from concept sheets | Manifest entries |
| Map props: date_palm, oil_derrick, pylon, rock_cluster, ruin, scrub, supply_crate_chute, village_house, `props/props.glb`; flags `flag_iran`, `flag_usa` | 22 | `prop_*` / `env_props.py`: procedural; national flags | Manifest entries; flag decision |
| G1 originals: `units/vanguard.glb` (+ 4 AO maps), `units/kite.glb` (+ AO), `units/rifleman.glb` | 8 | `mbt_vanguard.py`, `heli_kite.py`, `inf_rifleman.py`: procedural originals | Manifest entries |
| `assets/iran/icons/*_icon.png` | 20 | **No generator script and no record.** Visual inspection of 2 icons: they look like renders of our own Iran GLBs [A]. | Find or record the generator; manifest entries |
| `assets/ui/menu_bg.png` | 1 | **No generator script and no record.** Visual inspection: looks like a render of the original Vanguard tank [A]. | Same as above |
| Maps: `maps/zagros_basin/{map.json, fairness_report.json, height.r16, splat.png, height_preview.png, preview.png}` and `maps/proving_ground/preview.png` | 7 | `tools/map/gen_zagros_basin.py`, `make_previews.py`: synthetic terrain, no DEM (`docs/MAP_ZAGROS_BASIN.md`) | Manifest entries |

Total: 34 + 58 + 27 + 22 + 8 + 20 + 1 + 7 = 177.

### 6.5 Shippable (24) [O]

`assets/ui/icons/*.png` (`ui_icons.json`): procedural Pillow vector icons, "original work, project-owned".

### 6.6 Fonts

- [O] The project has no font files and no `FontFile`/`SystemFont` use in scripts or scenes. Scripts and scenes contain no non-Latin text.
- [A] The UI therefore uses Godot's **built-in default font**, compiled into the engine. Per the Godot 4 source, that is **Open Sans SemiBold, SIL OFL 1.1**. The audit did not extract it from this binary.
- [O] Under Wine, fontconfig and Wine's own system fonts were scanned. These belong to the Wine/OS layer; the game does not ship them.
- Release task: credit Open Sans (OFL) in Godot's licence notices.

### 6.7 Shipped data and code (not licence-audited)

- 21 JSON files ship only because of the `*.json` include filter:
  - 20 per-model `*_report.json` QA reports under `assets/units3d/`
  - `assets/us/us_packs.json`

  No script reads the 20 reports [O, grep]. They are harmless but unnecessary.
- 54 code files: `.gd` (stored compiled as `.gdc`), shaders, scenes, `project.godot`.
- This includes the test and screenshot harnesses `autotest*.gd`, `*shots.gd`, `evidence*.gd`, `vischeck.gd`, `airdiag.gd`, and `scenes/showcase.*`.

## 7. Blockers before any public release

1. **Replace the US faction art.** That means 199 `us_packs` sprites, 23 aircraft sprites and icons, and 66 GLB and texture files whose albedo is projected from the same client AI concept art. These are DEV ONLY by the project's own manifests, they depict real designs, names and insignia, and they are in active use.
2. **Write manifest entries for the 156 procedural assets** (GLBs, extracted textures, maps). Each entry needs generator script, commit or hash, licence and ship status. Until then they are `unknown` by the project's rule.
3. **Trace and record the 20 Iran icons and `menu_bg.png`.** No generator and no record exist.
4. **Iran Farsi shout `iran_shout.ogg`.** Confirm source, licence and spoken content, or replace it.
5. **Pixabay clips (13).** Record each item's page URL, uploader and download date. Keep a copy of the Pixabay Content License terms that apply.
6. **Real-world designs and insignia review** (139 flagged assets). This covers:
   - Iran designations (T-72S, F-14, Su-24, Shahed, Karrar, Boragh, AH-1J, BMP-2) and US designations still used in names
   - the national flags `flag_iran.glb` and `flag_usa.glb`, and the Iranian flag patches on infantry

   This needs a decision against the client's "fictional setting, no real insignia" art direction (GAME_DESIGN.md). It is separate from licence clearance.
7. **Crash at shutdown under Wine** (exit 5, null read). Reproduce on a real Windows PC. Fix or confirm it is a Wine-only problem.
8. **Remove dev harnesses from release exports**, or redirect them to `user://`. That covers autotest, screenshot and evidence scripts with hard-coded `/tmp/...` paths. Also exclude `*_report.json` from the include filter.
9. **Engine notices.** Ship Godot's MIT licence and third-party notices, including the Open Sans OFL, with the build.
10. **Windows PC test.** None has been done. The standalone result is Wine-only. On a clean Windows machine, repeat it with Process Monitor filtered to `SteelAccord.exe`, covering both the menu/skirmish flow and the `maptest` flow.

## 8. Artefacts

| Path | Contents |
|---|---|
| `build/clean_b2/SteelAccord_B2/SteelAccord.exe` | Audited build |
| `build/clean_b2/export.log` | Export log; the cross-check source |
| `build/clean_b2/strace_run_y.log` | Raw trace, run 2 (authoritative) |
| `build/clean_b2/strace_run.log` | Raw trace, run 1 (no fd decoding) |
| `build/clean_b2/wine_stdout_run2.log`, `wine_stdout.log` | Game output, runs 2 and 1 |
| `build/clean_b2/run_start.txt`, `run2_times.txt` | Run start and end times (UTC) |
| `build/clean_b2/prefix_ea_scan.txt` | Prefix scan for EA/Steam folders (empty = none found) |
| `build/reports/asset_audit_b2.json` | Per-file provenance audit |
| `build/reports/b2_wine_file_access.json`, `.txt` | Classified file access |
| `tools/qa/asset_audit.py`, `tools/qa/filter_strace.py` | Audit tools (read-only) |
