# Task board — 2026-10-21

How this session ran: the ten specialist roles were executed **in sequence by me in one session** (shared files, one environment, no Windows runtime to parallelize against). No separate agent outputs exist yet; nothing below is a simulated hand-off.

| ID | Role | Ticket | Files | Acceptance | Status |
|---|---|---|---|---|---|
| R-1 | Engine/platform | Recon: clone/pin fork, trace load paths, formats | docs/RECON.md | evidence + paths | ✅ done |
| A-1 | Engine/platform | Architecture + ADRs 0001–0006 | docs/ARCHITECTURE.md, docs/adr/* | reviewed by client | ✅ draft |
| T-1 | QA/build | DataChunk/RefPack, W3D, BIG, TGA codecs | tools/pzlib/* | round-trip on 55 maps / 79 W3D | ✅ done |
| T-2 | QA/build | Content validator + negative tests | tools/validate_content.py, tests/test_validator_negative.sh | 11/11 mutations caught | ✅ done |
| B1.1-a | Visual + Tech art | Kestrel model, atlas, wreck, icon, glyphs | tools/gen_kestrel.py → content/dev/Art/* | structure valid; preview from exported W3D | ✅ built, **not render-tested in game** |
| B1.1-b | Gameplay | Object/weapon/armor/locomotor/FX/OCL/buttons/sets | content/dev/Data/INI/* | validator PASS | ✅ built, **not run** |
| B1.1-c | Map/world | PZ Test Range map + terrain | tools/gen_testrange_map.py → maps/PZ_TestRange/* | decodes, 2 starts, slopes ≤ 10.6° | ✅ built, **not loaded in game** |
| B1.1-d | QA/build | Test kit + install script + test script | tools/build_b1.py, tests/b1/* | checksums, refuses Steam path | ✅ built |
| B1.1-e | Client | **Run TEST_B1_1.md on Windows, return S1–S8** | — | all steps pass | ⏳ blocked on your PC |
| B1.2 | UI/UX + Engine | Original title/menu screen; product name + "modified version" marking | engine `pzh/main`, shell art | in-game screenshot | next |
| B1.3 | Gameplay + Tech art | Original building "Field Depot" (builds Kestrel), dozer hook | content/dev | produce from it in game | next |
| D-1 | Faction/balance | USA + China slice sheets, cost/time/counter matrix | docs/factions/* | review | queued |
| D-2 | Map/world | Harbor Divide blockout (generator) + fairness metrics | tools/gen_harbor_divide.py | path/resource symmetry report | queued |
| D-3 | Audio | Original UI/weapon SFX set v0 + provenance | content/dev/Audio | in-game playback | queued (B3 priority, small v0 in B2) |
| D-4 | AI | Deterministic build order for the slice | content/…/Scripts | AI wins/loses vs. AI | queued (B2) |
| Q-1 | QA/build | Base-data inventory for clean boot (file-access log flag) | engine patch | list of every file opened | queued (B2) |
