# Steel Accord

An original, standalone modern real-time strategy game: nine fictional playable sides (Iran, Iraq, North Korea, Taiwan, China, Japan, a European coalition, Ukraine, USA), skirmish against AI, and competitive multiplayer as the long-term goal.

EA has not endorsed and does not support this product.

Original modern RTS content and tooling built on a modified version of the GPL-3.0 *Generals Zero Hour* engine source (TheSuperHackers/GeneralsGameCode fork). This repository contains only project-original content, tools and docs. It contains no EA game assets. "Command & Conquer" is an EA trademark; this project is not affiliated with EA.

- Status / plan: `docs/TASKBOARD.md`, `docs/ARCHITECTURE.md`, `docs/RECON.md`
- Build B1.1 kit: `python3 tools/build_b1.py --engine <GeneralsGameCode checkout>`
- Windows runtime test: `tests/b1/TEST_B1_1.md`

Licence for project-original content: not yet chosen (all rights reserved until decided). Engine code remains under GPL-3.0 with EA's additional terms.

## Status (2026-10-21)
- B1 prototype (private, runs on a licensed Zero Hour install): original Kestrel scout unit, PZ Test Range and Harbor Divide maps — tested in-game by the client.
- B2 standalone (no EA files) in progress: engine cross-built, clean-folder boot harness (`tools/run_clean.sh`).
- Internal content IDs still use the `PZDev` / `PZ_` prefix from the working title; they will be renamed when B2 content replaces the dev tree.

## Repository layout
`content/` original game data (+ `MANIFEST.json` provenance) · `maps/` map folders · `tools/` generators, packers, validator, test harness · `tests/` runtime test kits · `docs/` recon, architecture, ADRs, design, economy, mechanics audit, task board.
The engine (GPL-3.0 fork of TheSuperHackers/GeneralsGameCode, branch `pzh/main`) lives in a separate repository.
