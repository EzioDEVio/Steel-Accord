# RECON — Steel Accord

Date: 2026-10-21 · Author: Claude (technical lead) · Status: B1.1 recon complete

Legend: **[O]** observed in source/files this session · **[R]** reported by client · **[A]** assumption, needs confirmation

## 1. What this environment can and cannot reach

| Item | Access | Notes |
|---|---|---|
| `C:\Users\moham\Downloads\PROJECT-ZERO-HOUR\engine` (your fork checkout + build) | **No** | No device bridge/shell to your PC in this session. |
| Steam install `...\Command & Conquer Generals - Zero Hour` | **No** | Not touched, by design and by access. |
| Your isolated test copy | **No** | Path not given; needed for the runtime test. |
| Public fork `TheSuperHackers/GeneralsGameCode` | **Yes** [O] | Cloned, pinned `8154df9028e8737439226b10ea56c4ccb5adb4c0` (2026-10-20, "chore: Add static asserts…"). |
| `TheSuperHackers/GeneralsGamePatch` | **Yes** [O] | Cloned `6c7f40d6af6a` as a **format reference only** (reference INI schema, 55 community test maps, 80 W3D samples used to validate our parsers). Nothing from it is shipped. |
| Windows build / game run | **No** | Linux container; no Windows, no Wine, no game data. **No Windows build or game run was executed by me.** |
| "Prompts 7–10" mechanics brief + addendum | **Missing** | Not in this conversation's files. Design uses the main brief only; audit pending. |

Your B0 facts (fork built with CMake + VS C++ + Ninja; skirmish runs in an isolated copy; FPS/clock are fork features) are **[R]**; I could not re-verify them.

## 2. Source layout & toolchain [O]

- `GeneralsMD/` = Zero Hour; `Generals/` = base game; `Core/` = shared engine (GameEngine, GameEngineDevice/W3D, WWVegas libs, tools).
- CMake presets: `vc6*`, `win32*`, `win32-vcpkg*`, `default`, `unix`, `mingw-w64-i686*`. Executable target `z_generals` → `generalszh.exe` (`GeneralsMD/Code/Main/CMakeLists.txt`).
- Tools in-tree: WorldBuilder, W3DView, MapCacheBuilder, ImagePacker, GUIEdit, ParticleEditor, max2w3d, wdump, textureCompress.
- Tests: `TESTING.md` — GoogleTest (`RTS_BUILD_OPTION_TESTS`), and **headless replay checking** (`generalszh.exe -jobs 4 -headless -replay <glob>`). This is our future automated regression harness (§8).

## 3. Startup & data loading (traced)

1. **Archives** — `BIGFileSystem` loads `*.big` from the game dir, then `loadMods()`: `-mod <file.big>` (absolute path, or relative to user data dir) is inserted with **overwrite priority**; `-mod <dir>` loads every `*.big` in it (`Core/GameEngine/Source/Common/System/BIGFileSystem.cpp`, `CommandLine.cpp:parseMod`). Header format verified (BIGF, LE size, BE count/offsets).
2. **INI** — `GameEngine::init` (`GeneralsMD/.../Common/GameEngine.cpp:448–623`) calls `initSubsystem(…, "Data\\INI\\Default\\X", "Data\\INI\\X")`; `INI::loadFileDirectory` loads `X.ini` **and every `*.ini` in folder `X\`**. Same for `CommandButton`, `CommandSet` (`ControlBar.cpp:1069–1072`), `MappedImages\HandCreated` (`Image.cpp:271`). ⇒ new content can live in separate files without editing EA files.
3. **Duplicates** — redefining an existing Object/CommandSet in normal load is a crash/throw (`ThingFactory.cpp:396`, `ControlBar.cpp:2027`). In `INI_LOAD_CREATE_OVERRIDES` mode the engine **copies** the original and applies only the listed fields/slots (`newCommandSetOverride`).
4. **Per-map overrides** — on map load, `<mapdir>\map.ini` and `solo.ini` are loaded as overrides and `map.str` as a string table (`GameLogic.cpp:2492–2515`).
5. **Skirmish sides** — a map with no player scripts gets `data\Scripts\SkirmishScripts.scb` from base data (`SidesList::prepareForMP_or_Skirmish`).
6. **Map list** — `MapCache::addMap` needs `Player_N_Start` waypoints (≥2 ⇒ multiplayer) and uses WorldInfo `mapName` + `map.str` for the display name (`MapUtil.cpp`).
7. **User data dir** — `Documents\` + registry `UserDataLeafName` or default `Command and Conquer Generals Zero Hour Data` (`GlobalData.cpp:1370`).
8. **Art lookup** — `Art/W3D/`, `Art/Textures/`, `Art/Terrain/` (`FileSystem.h:76–78`); terrain textures resolved via `Terrain` INI → `Art/Terrain/<file>` and must be uncompressed 24/32-bit TGA, multiple of 64 px, ≤10×10 tiles (`WorldHeightMap::countTiles`).

## 4. Formats verified with our own tools (round-trip / structure)

| Format | Engine reference | Our tool | Verification |
|---|---|---|---|
| `.map` (DataChunk, optional RefPack "EAR\0") | `DataChunk.cpp`, `WHeightMapEdit.cpp`, `SidesList.cpp`, `PolygonTrigger.cpp`, `WorldHeightMap.cpp` | `tools/pzlib/datachunk.py`, `mapformat.py` | Decoded **55/55** reference maps; decode→encode→decode structurally identical for all. Tile-index formula confirmed on a full map (0 mismatches). |
| `.w3d` | `w3d_file.h`, `meshmdlio.cpp`, `htree.cpp` | `tools/pzlib/w3d.py` | Struct sizes asserted against header; chunk walker parses **79/80** reference files (1 reference file is itself truncated); winding convention measured on 31,370 reference triangles (stored normal = (v1−v0)×(v2−v0), 0 exceptions); loader flips V (`meshmdlio.cpp:1512`). |
| `.big` | `BIGFileSystem.cpp` | `tools/pzlib/big.py` | Pack→read round trip; size and directory-end fields checked. |
| TGA | `WorldHeightMap.cpp`, texture loader | `tools/pzlib/tga.py` | Type 2, bottom-left origin. |

These are **structural** verifications. Rendering/loading in the real engine is unproven until the Windows test.

## 5. Subsystems (where they live) [O]

Shell/UI: `GameClient/GUI` (+ `.wnd` layouts in base data) · Control bar: `Core/.../ControlBar*.cpp` · Renderer: `Core/GameEngineDevice/Source/W3DDevice` on WWVegas/WW3D2 (DirectX 8 era) · Maps: `GameLogic/Map`, `W3DDevice/GameClient/WorldHeightMap.cpp` · Models: WW3D2 asset manager (`W3DAssetManager.cpp`; meshes named `HOUSECOLOR*` get team tint) · AI: `GameLogic/AI` + skirmish `.scb` scripts · Save/replay: `Common/System/SaveGame`, `Common/Recorder.cpp` (`-loadsave`, `-loadreplay` CLI added by the fork) · Simulation rate: `LOGICFRAMES_PER_SECOND = WWSyncPerSecond` (`GameCommon.h:67`) · Network: `Core/GameEngine/Source/GameNetwork` (lockstep command relay, LAN API, GameSpy remnants).

## 6. Base-game data the B1.1 test still depends on

**Expected from source** [A — confirm with `dir *.big` in your test copy]: every `*.big` in the test copy (INI, W3D, textures, terrain, audio, English strings/CSF, window layouts, shaders, maps, music/speech).
**Specific symbols B1.1 references** (reported automatically by `tools/validate_content.py`):
- `AmericaCommandCenterCommandSet`, `ChinaCommandCenterCommandSet` — map.ini adds our button to their empty slot 11 (slots verified empty in the reference ZH 1.04 data).
- Faction template `FactionCivilian`; `Side = America` on the Kestrel.
- Implicitly: shell menus, control-bar art, fonts, cursors, USA/China command center and dozer, SkirmishScripts.scb AI.

## 7. Licensing findings

- Engine code: GPL-3.0-or-later + EA §7 terms: **no EA trademark rights**, modified versions **must be marked as modified**, must carry the notice, may not misrepresent origin (`LICENSE.md`). Corresponding source required when conveying binaries.
- **Flag for review:** the community data repo's EA terms (`GeneralsGamePatch/TERMS.txt`) for derivatives of EA *game content* include "not for commercial profit" and a required "EA has not endorsed and does not support this product." statement. These govern mods using EA data (our B1 prototype), not our independently authored assets — but if the product is ever commercial, a lawyer must confirm that a standalone build of the GPL engine with 100% original data is outside those terms. **I am not a lawyer; this is an open release-rights risk.**

## 8. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | No runtime access: B1.1 is validated structurally only | High | Single Windows test run with the kit (TEST_B1_1.md). |
| R2 | Flat-shaded mesh may produce bad stencil shadows | Low | Shadows disabled in B1.1; build smoothed shadow proxy later. |
| R3 | Renderer is DX8-era fixed function; "modern visuals" can't come from textures alone | High (B3) | ADR-0005: renderer plan with measured evidence before deciding. |
| R4 | Standalone boot needs replacements for *all* base data (shell `.wnd`, fonts, CSF, cursors, AI scripts, terrain, water…) | High (B2) | Data-inventory + "clean-folder boot" gate in ADR-0002. |
| R5 | Commercial-release terms uncertain | Medium | Legal review before any public release (§7). |
| R6 | Mechanics brief (Prompts 7–10) missing | Low now | Request; design stays provisional. |

## 9. Missing inputs (blocking only the runtime test)

1. **Run the B1.1 kit on your PC** (exact steps in `tests/b1/TEST_B1_1.md`) and return screenshots — or link this chat to your PC through the Claude desktop app so I can run it myself next time.
2. Path of your isolated test copy (for exact commands) and the output of `dir *.big` there.
3. Prompts 7–10 brief/addendum.
