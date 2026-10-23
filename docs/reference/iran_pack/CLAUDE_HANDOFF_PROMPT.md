# Claude handoff prompt — Iran-inspired RTS faction assets

I’m attaching `Iran_Arsenal_Claude_Pack.zip`. Review `README_for_Claude.md` and the six numbered reference sheets first. They are generated concept art, not authoritative inventories, final sprites, or 3D models.

Integrate the visual direction into the existing Godot 4.5.1 RTS project without removing or breaking existing USA assets, mechanics, UI, saves, or scenes. First inspect the current project structure and existing asset/import conventions. Keep the faction data-driven and use separate faction/unit/building definitions so future factions can be added cleanly.

Use the panel index in the README to identify each concept. Do not treat a whole contact sheet as one game object. If using panels temporarily as UI portraits, crop each panel cleanly and keep the source sheet intact. For gameplay assets, create separate assets with consistent scale and ground contact; for 3D gameplay use real meshes or properly licensed models, and for 2D/isometric gameplay create separate sprites with consistent camera angle and required directional/action states. Do not claim the generated rank board is an official Iranian rank chart; replace it with verified references if exact official insignia are required.

Before changing files, report the proposed asset mapping and any needed 3D-versus-sprite decision. Then implement in small, testable steps, preserve current behavior, and report the files changed and tests run. Do not publish or release anything.
