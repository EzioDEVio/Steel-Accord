# ARCHITECTURE — Steel Accord

Status: draft v1 (B1.1). Decisions are recorded in `docs/adr/`. Engine change requires client approval.

## 1. Repositories and separation

```
PROJECT-ZERO-HOUR\
  engine\        TheSuperHackers fork, product branch  pzh/main  (pinned base 8154df9028e8)
                 GPL-3.0 + EA §7 terms. Code only. No new game assets in this tree.
  pzh\           THIS repo: product content + tooling + docs (project-original)
    content\dev\     B1 development content tree (packed to PZDev_B1.big)
    content\MANIFEST.json   provenance/licence/hash for every content file (validator-enforced)
    maps\            map folders (map, map.ini, map.str, preview)
    tools\           generators, packers, validator (pure Python 3 + numpy + Pillow)
    tests\           runtime test scripts, negative tests
    docs\            recon, architecture, ADRs, design, task board, decisions
  testcopy\      your isolated runnable copy (never committed). Steam install is read-only.
```
B1.1 required **no engine code change** — everything is data, loaded via `-mod`. Engine edits start in B1.2 (title screen / product marking) on `pzh/main`, each marked `// PZH modified <date>` per EA §7.

## 2. Content pipeline

`generator/hand-authored source → content/<tree> → MANIFEST.json → validate_content.py → .big → test kit`

- Runtime formats are the engine's own: W3D (models), TGA (textures/UI/terrain), INI (definitions), DataChunk `.map`, `.str` strings. We write them with our own tools (`tools/pzlib`), verified against the pinned engine source.
- **Validator gates** (run in `build_b1.py`; negative tests in `tests/test_validator_negative.sh`): INI fields/modules/enums exist in the engine; every reference resolves; W3D/TGA/map structure; manifest hash + licence fields; BIG == tree; base-game references enumerated. Build refuses to stage on failure.
- AI image/model generation (if used later) produces *sources*: the manifest records tool, model, prompt; a human/agent edit and an in-game render check are required before `ship_status=shippable`.

## 3. Product data layers (target)

| Layer | B1 (now) | B2 (standalone slice) |
|---|---|---|
| Base runtime data (shell `.wnd`, fonts, cursors, control bar, CSF strings, default INI, AI scripts, terrain/water, shaders) | licensed EA archives in test copy | **`PZBase.big`** — project-authored replacements, inventory-driven |
| Product content (factions, units, maps) | `PZDev_B1.big` + map folders | `PZContent.big` |
| Boot | `generalszh.exe -mod PZDev_B1.big` inside test copy | clean folder: `pzh.exe` (renamed, marked build) + our `.big` only; **no EA archive present** |

**Clean-boot gate (B2):** folder with only our binaries + archives; launcher logs every file opened (instrument `LocalFileSystem/ArchiveFileSystem::openFile` behind a `-logfileaccess` flag); test passes when the log lists zero EA-derived files and a skirmish completes.

## 4. Simulation, AI, saves, replays, multiplayer

- Keep the engine's fixed-rate lockstep logic (`LOGICFRAMES_PER_SECOND`) and deterministic RNG. No ECS rewrite, no rollback (ADR-0004).
- AI: deterministic skirmish AI first (engine AI + our own build-order scripts per faction). Optional local-LLM "director" later: single-player only, proposes high-level goals at ≤1 Hz from a side thread, applied as ordinary player commands through the message stream; never in the frame path; disabled in MP/replays unless the commands are recorded (ADR-0004).
- Saves/replays: engine `GameState` + `Recorder`; content hash (manifest SHA set) embedded in our build ID so replays/saves refuse mismatched content.
- Regression harness: `-headless -replay` (engine feature) on recorded test replays per milestone; replays become CI fixtures once a Windows runner exists.
- Multiplayer (B5): engine lockstep + CRC mismatch detection; two real clients, matching content hashes, desync logs. A local skirmish never counts as MP proof.

## 5. Renderer / UI plan (B3, evidence first)

Texture upscaling alone will not modernize the look. Candidate path, to be measured before committing: (1) higher-res authored textures + normal-mapped materials only where the W3D FX-shader path supports it; (2) post-processing (tonemap, AO, bloom) via a renderer-side pass; (3) UI scaling for 1440p/4K via resolution-independent layouts. If the DX8 path blocks (2), an ADR with frame-time/feature evidence will propose a renderer backend change (e.g. DXVK-style translation or a new backend) for your approval.

## 6. Milestone gates & dependency graph

```
B0 fork runs (done, client) ──► B1.1 original unit+map (this) ──► B1.2 original title/menu screen + product marking
          │                                                   └► B1.3 original building (Field Depot) producing Kestrel
          ▼
B2 standalone slice: PZBase.big inventory+replacement ─► 2 factions × 3 roles + economy + construction
                     ─► Harbor Divide map ─► deterministic AI ─► save/load ─► clean-folder boot test
          ▼
B3 visuals/audio (renderer ADR) ─► B4 remaining 7 factions + 4 maps (batches) ─► B5 MP, replay/spectator, packaging, licence audit
```
Each gate needs: files changed, build command, environment, logs, in-game screenshots/video, defects, next ticket.

## 7. Repeatable local build (content)

```
python3 -m pip install numpy pillow          # only deps
git clone https://github.com/TheSuperHackers/GeneralsGameCode engine && git -C engine checkout 8154df9028e8737439226b10ea56c4ccb5adb4c0
python3 tools/build_b1.py --engine ./engine   # regenerate → manifest → BIG → validate → build/stage_b1 + zip
sh tests/test_validator_negative.sh ./engine  # validator self-test
```
Engine binary build on Windows (your B0 path): `cmake --preset win32` then `cmake --build --preset win32` from the fork (VS 2022 toolchain + Ninja). Record the exact preset you used in `docs/DECISIONS.md`.
