# ADR-0001 Engine: product branch of the TheSuperHackers fork
Status: Accepted (2026-10-21) · Client direction: "same engine"
**Decision.** Develop on branch `pzh/main` of TheSuperHackers/GeneralsGameCode, based on pinned commit `8154df9028e8737439226b10ea56c4ccb5adb4c0`. Rebase onto upstream only deliberately (ticketed), re-running all validators and replay checks.
**Rules.** Preserve all copyright/licence notices; tag every modified function `// PZH modified YYYY-MM-DD: <why>`; product binary must be renamed and visibly marked as a modified version (EA §7); no EA trademarks in name, UI or marketing; ship corresponding source with any binary.
**Evidence.** B1.1 needed zero engine changes (data-driven via `-mod`, directory INI loading, map.ini overrides) — see RECON §3.
**Revisit if** a requirement is measured impractical on this engine (write a superseding ADR with numbers; client approval required).
