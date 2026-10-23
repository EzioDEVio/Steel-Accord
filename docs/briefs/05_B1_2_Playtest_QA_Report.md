# Steel Accord B1.2 — Playtest QA Report and Claude Handoff

## Purpose

Claude, please treat this as a prioritized QA and implementation brief based on my playtesting of Steel Accord B1.2 and the attached screenshots. Review the relevant project scenes, scripts, art pipeline, and gameplay systems; reproduce each issue; then fix and verify it. Keep the modern U.S. aircraft, ground-force, troop, and installation assets we generated. The goal is a polished modern RTS with the readable base-building, production, command, and combat flow of Command & Conquer: Generals — Zero Hour.

Do not treat the notes below as a request to replace the game's identity or remove working features. Preserve the existing modern asset direction and improve how the game presents and uses it.

## Build and evidence

- Build reviewed: SteelAccord B1.2, Windows x64.
- Screenshots supplied with the playtest:
  - two different aircraft landing.png
  - the air cargo shinook size bigger than the supply depot and it is 2nd not 3d.png
  - the building vehicle floating of the map no wheel moving.png
- The build notes say buildings do not rotate with the camera, vehicles switch between three views plus mirroring, turrets do not rotate, and infantry use a two-pose walk cycle. These are documented limitations, but they do not meet the visual target below.
- The helicopter rotor spinning is an improvement. Keep that behavior and use it as the baseline for other visible unit animations.

## Executive summary

The main problems are visual credibility and world interaction: assets often read as flat 2D images instead of objects occupying the game world; buildings and vehicles appear insufficiently grounded; the Chinook is oversized relative to nearby structures; and aircraft can end up idle outside the airfield’s intended landing area. Ground-unit movement also needs a visible animation and grounding review. In addition, the player currently lacks a clear way to repair damaged structures or rebuild destroyed ones.

The game should retain its modern military assets while adopting a cohesive C&C-style RTS loop: build a base, manage supplies and power, produce and deploy units, command them in combat, and repair or rebuild the base.

## Priority 0 — Make the world and assets look coherent

### Finding: Units and structures read as flat 2D art

Across the game, objects look like flat images rather than 3D game objects. Buildings also do not turn with the camera, while unit art changes between a small number of views. The current presentation makes vehicles, troops, aircraft, and structures feel like separate pictures placed on top of the map rather than parts of one coherent world.

### Required direction

1. Audit every playable asset and record whether it is a 3D model, a 2.5D asset, a billboard, or a fixed-view sprite. Include buildings, vehicles, aircraft, infantry, defenses, construction scaffolds, shadows, and selection indicators.
2. The target is a consistent 3D-like RTS presentation. Prefer real 3D models with correctly assigned materials, pivots, collision, and animations for assets that must rotate, move, or be viewed from multiple camera angles.
3. If any asset must remain sprite-based, make it a deliberate 2.5D solution with enough directional views, consistent perspective, correct camera-facing behavior, lighting, and contact shadows. A single flat image stretched or rotated to imitate a model is not sufficient.
4. Ensure the camera and asset presentation agree. Rotating or tilting the camera must not make objects appear detached, incorrectly oriented, or visibly flat.
5. Keep the generated modern U.S. asset designs recognizable. Do not replace them with unrelated placeholder art.

### Acceptance checks

- Rotate and tilt the camera around a base, moving vehicles, aircraft, and infantry. Assets must remain visually consistent with the world.
- Inspect each asset at the normal gameplay zoom and at close zoom; no object should look like a floating cutout or an incorrectly scaled billboard.
- Provide an asset audit that identifies which objects are now true 3D models and which deliberately remain 2.5D, with the reason for each exception.

## Priority 0 — Fix grounding, terrain contact, and movement presentation

### Finding: Buildings and mobile units appear to float

Buildings appear to hover or become visually detached from the map as the camera moves. The Dozer/M88 in the supplied screenshot appears elevated above the ground, and its wheels or tracks are not visibly moving in the still image. Please reproduce this while the unit is moving; the screenshot alone cannot confirm whether its movement animation is absent.

### Required behavior

- Structures must remain fixed to their placement position and sit on the terrain surface. Construction scaffolds and build-progress effects must use the same ground reference.
- Vehicles must follow terrain height, keep their wheels or tracks visually in contact with the ground, and cast a contact shadow that matches their footprint.
- Wheels should rotate according to distance traveled; tracks should animate or scroll believably. The body should not slide without matching wheel or track motion.
- Infantry should have distinct idle, walk/run, combat, firing, and death states appropriate to their current actions.
- Object pivots, collision shapes, visual meshes/sprites, selection circles, and shadows must share a consistent ground anchor. Camera movement must not change their world attachment.

### Acceptance checks

- Place several buildings on level and uneven ground; rotate and tilt the camera. They must remain seated on the terrain.
- Move the Dozer, HMMWV, tank, and infantry over the map and confirm the ground contact and movement animations.
- Confirm movement direction, turning, stopping, and terrain transitions do not produce hovering, sliding, sinking, or sudden snapping.

## Priority 1 — Standardize asset scale

### Finding: Chinook is oversized

The CH-47 Chinook appears larger than the nearby Supply Depot in the supplied screenshot and dominates the scene. Its current size makes the relative scale of aircraft, structures, and ground units feel inconsistent.

### Required behavior

- Establish and document a world-scale reference for structures and units, then calibrate all assets against it.
- Correct the CH-47's world scale and visual footprint. Compare it with the Supply Depot, Airfield, roads, infantry, and other aircraft at the default camera angle.
- Keep collision bounds, selection bounds, shadow size, rotor extent, and displayed hull scale aligned.
- Avoid one-off camera-dependent scaling that causes the aircraft to change size relative to the world.

### Acceptance checks

- Compare a CH-47 beside the Supply Depot at default zoom and at a closer zoom. It should read as a large aircraft without visually dwarfing the base structure.
- Compare all aircraft and ground units against the same scale guide and check that their footprints and selection indicators match their visible size.

## Priority 0 — Put world objects on real 3D geometry

### Important distinction

An object can be positioned in a 3D scene and still be only a flat image. A Sprite3D or billboard is a plane facing the camera; it does not become a 3D model because it has an X, Y, and Z position. The current art often has that flat, cutout appearance.

### Required 3D asset approach

- Convert the actual playable buildings, vehicles, aircraft, and infantry into 3D geometry. Use properly modeled and textured meshes imported as GLB/glTF, with a Node3D root and MeshInstance3D parts in Godot. Do not represent an entire unit or building as one flat plane.
- Use the generated concept images as modeling references and, where appropriate, as UV-mapped textures, decals, or surface details. A single front-view image cannot provide a complete 3D model by itself; create the missing side, rear, top, and underside geometry instead of stretching or rotating the image.
- Give moving objects articulated parts: chassis and turret for tanks, wheels or animated tracks for vehicles, rotors for helicopters, and appropriate skeletal rigs for infantry. Aircraft and buildings also need usable depth and silhouettes from multiple camera angles.
- Set consistent origins and pivots. Place building roots at the foundation and mobile-unit roots at their ground-contact point. In Godot's 3D world, movement should use the ground plane's X/Z coordinates and terrain height on Y; visuals, collision, selection bounds, and shadows must agree on that anchor.
- Add suitable materials, lighting, cast shadows, and contact shadows. Keep the RTS camera style and performance budget in mind, using level-of-detail meshes where needed.
- Keep flat images for appropriate uses such as UI icons, minimap symbols, decals, and texture artwork. Do not use those as substitutes for the full world model.

### Recommended migration

First build a small, representative 3D pilot set: one building, the Dozer/M88, one aircraft such as the CH-47, and one infantry unit. Establish the model scale, import settings, pivot convention, material style, collision setup, and animation workflow with those assets. Then apply the same pipeline to the remaining roster. If the full conversion needs multiple stages, keep the current build playable and report which assets are complete, which remain sprite-based, and the planned order for converting them.

### Acceptance checks

- Orbit the camera around each pilot asset. Its side, rear, and top geometry must be visible; it must not collapse into a thin card or turn to face the camera as a billboard.
- Check the Dozer's wheels/tracks, aircraft rotor, infantry rig, and building foundation from more than one angle.
- Move the Dozer and infantry across terrain while rotating the camera. Their model, collider, selection marker, and shadow must stay aligned and grounded.
- Capture front, side, rear, top, and normal gameplay-camera views for each pilot asset before expanding the conversion to the full roster.

## Priority 1 — Correct aircraft return and parking

### Finding: Aircraft idle outside the Airfield landing area

Aircraft produced from the Airfield have been observed sitting idle near the lower edge of the map rather than inside the Airfield landing zone. The B1.2 playtest notes state that Airfield aircraft should park on four pads and that R returns aircraft to a pad.

### Required behavior

- Make the four Airfield pads explicit parking targets in the Airfield's local space, then convert them correctly into world coordinates for spawning, return flight, and landing.
- Aircraft production, takeoff, attack, return, and parking must use valid routes and destinations within the map.
- R must return the selected aircraft to an available pad, land it there, and leave it in a clear parked/idle state.
- If all pads are occupied, aircraft must wait, queue, or use another defined safe behavior. They must not stack on one pad or travel to a map boundary.
- Aircraft must not become stranded, hover indefinitely, or report that they have landed while visually outside the Airfield.

### Acceptance checks

- Produce one aircraft and return it with R. Confirm it lands fully inside a pad.
- Produce enough aircraft to occupy multiple pads, then return them in different orders. Confirm correct pad assignment and no overlap.
- Repeat near map edges and after camera rotation; landing targets must remain tied to the Airfield, not screen-space coordinates.
- Test F-16, A-10, and AH-64, including aircraft currently selected and aircraft returning after combat.

## Priority 1 — Add C&C-style building repair and rebuilding

### Finding: The player cannot restore damaged or destroyed structures

There is no clear player action to repair a damaged building or rebuild a structure after it has been destroyed. This removes an important base-management mechanic from the intended C&C-style game loop.

### Required behavior

- When a friendly structure is selected and damaged, show a Repair action in its command panel. It should show a tooltip with the cost or repair rate, provide clear feedback, and allow the player to start, stop, or resume repairs.
- Repairs should consume in-game funds at a predictable rate. If funds run out, pause repair and tell the player why. Fully repaired buildings should disable or hide the action.
- Treat a destroyed building separately from a damaged building: repair restores an existing structure while it is alive; a destroyed structure should be rebuildable through the normal construction/build menu at the normal cost and build time, subject to placement and prerequisite rules. Show rubble or another clear destroyed state if appropriate.
- Make ownership rules clear: the player can repair or rebuild eligible friendly structures, not enemy structures.

### Acceptance checks

- Damage a friendly building, select it, start repair, stop it, and resume it. Confirm health and funds update correctly.
- Test repair with insufficient funds and at full health.
- Destroy a building and confirm it can be rebuilt through the expected construction flow, with the correct cost, prerequisites, and build time.
- Confirm the UI distinguishes repair from rebuilding and communicates disabled or unavailable states.

## Priority 2 — Strengthen the C&C-style RTS loop while retaining the modern assets

Use the modern assets we generated as the game's visual identity, and implement the familiar RTS mechanics around them. The player should be able to understand and control the base and army through a clear command interface.

Core loop requirements:

- Base construction through the Dozer/engineer, with placement previews, valid/invalid placement feedback, visible construction progress, and clear build completion.
- Resource and power management with readable income, spending, power use, and low-power effects.
- Production queues for structures and units with cost, build time, progress, rally points, cancel/refund behavior, and clear deployment locations.
- Direct unit commands such as move, attack, attack-move, guard, stop, and return-to-base for aircraft, with visible command feedback.
- Useful unit roles and counters across infantry, vehicles, aircraft, and base defenses, with readable health and status.
- Airfield aircraft should follow a clear sortie cycle: park, launch, fly/attack, return, land, and become available for the next order. Add rearming or repair at the Airfield if supported by the design.
- A consistent player UI for build, production, deployment, repair, rally points, unit status, and support actions. Keep labels, costs, progress, and disabled states easy to read.

Please first make the existing systems reliable and understandable, then expand mechanics. Keep the modern U.S. art roster and avoid copying original C&C art or interface files.

## Priority 2 — Replace weak or placeholder audio

I previously reported that the generated game sounds were not close to the intended quality and were effectively unusable. Please review the sounds included in this build rather than assuming the earlier audio pack is acceptable.

- Replace generic or unconvincing effects with carefully selected, properly licensed, or custom-designed sounds that fit each event: A-10 cannon, aircraft pass and takeoff, helicopter rotor, tanks and vehicles, infantry acknowledgements and combat, weapons, explosions, construction, and base defenses.
- Keep sounds distinct, correctly timed, and spatialized where appropriate. Balance them so important events are audible without overwhelming orders or music.
- Retain working rotor animation and synchronize rotor audio with the helicopter's state.

## Test and delivery expectations

Before calling this complete:

1. Reproduce each reported issue in the B1.2 project or a current development build and note the steps.
2. Fix issues at the correct level: asset/model setup, world transforms, terrain sampling, path/landing targets, animation, or gameplay logic. Do not hide them with arbitrary scale changes or screen-space offsets.
3. Test at the normal gameplay camera and while rotating/tilting/zooming.
4. Run the aircraft, grounding, scale, repair/rebuild, construction, production, and movement acceptance checks above.
5. Report the specific scenes/scripts/assets changed, the tests performed and their results, and any remaining known limits.
6. Keep the rotor improvement and existing working features intact.

The attached screenshots should be reviewed alongside this report. Please return a prioritized implementation plan and then address the high-priority issues before adding optional features.
