# Decision log

| Date | Decision | Why | Ref |
|---|---|---|---|
| 2026-10-21 | Pin engine at `8154df9028e8` (upstream 2026-10-20) | reproducible base | ADR-0001 |
| 2026-10-21 | B1.1 is data-only, loaded with `-mod <abs>\PZDev_B1.big`; no engine edits | lowest-risk first visible change; engine loads per-folder INI and mod BIGs with override priority | RECON §3 |
| 2026-10-21 | Hook the Kestrel into stock USA/China CC slot 11 via map.ini, scoped to PZ Test Range only | engine copy-on-override for CommandSets; avoids touching global EA data; slot 11 verified empty | map.ini |
| 2026-10-21 | Write runtime formats with own Python tools verified against engine source + reference files | no Windows/DCC tools here; keeps assets reproducible from scripts | ADR-0006 |
| 2026-10-21 | Kestrel shadows off; static wheels | flat-shaded mesh unsuitable for stencil shadows; wheel bones need W3DTruckDraw — later ticket | TEST_B1_1.md |
| 2026-10-21 | Vertical slice stays USA vs China | no evidence against; both have stock CC hooks for B1 | GAME_DESIGN §3 |
| 2026-10-21 | Roles run sequentially this session (no subagents) | single environment, shared files, no runtime to parallelize; parallel agents planned for independent design/art in B1.2+ | TASKBOARD |
