# ADR-0007: Move Steel Accord to Godot 4 (supersedes the Zero Hour engine path)

Status: Accepted by client (Mohammed), 2026-10-21.

## Context
- The Zero Hour engine's renderer is DirectX 8 fixed-function (2003). The client judged the B1 result (Kestrel) unacceptable visually and set a 2026-quality presentation as a requirement.
- Good art on that renderer still reads as a 2003 title; modernising it means replacing the renderer.

## Decision
- Engine: **Godot 4.5.1** (MIT licence, no royalties), Forward+ renderer.
- Chosen over Unreal 5 and Unity 6 because it can be built, run and screenshot-tested in Claude's Linux workspace (software Vulkan), and exported to Windows and Web.
- Gameplay: **reimplement** the mechanics documented in GAME_DESIGN / ECONOMY_SPEC / MECHANICS_REFERENCE_AUDIT in our own code. Do not translate EA's GPL source; it may be consulted for behavioural reference only.
- Art: authored by Claude as code: Blender (bpy 5.2) modelling scripts in tools/art, baked AO, Godot shaders (camouflage, grime, team colour), procedural terrain. No paid generation services. Provenance of each asset is its generating script.

## Consequences
- Zero Hour fork work (B1, clean boot) is archived as reference; design docs and map specs carry over.
- Visual ceiling is a clean, stylised-realistic modern look, not photoreal AAA.
- Evidence: docs/screens/godot_vanguard_*.png rendered in-engine (Godot 4.5.1, llvmpipe software Vulkan).
