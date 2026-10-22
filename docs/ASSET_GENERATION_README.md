# Steel Accord — Asset Generation Brief (README for image generation)

This is the brief to hand to an image generator, or to an artist, when producing art for **Steel Accord**. Steel Accord is an original, modern real-time strategy game built on Godot 4. Every section says what to make, the exact format, and how the game will use it. If you follow it, each delivery can be imported by our tools without manual cleanup.

> **The one rule that matters most:** everything must be **original and fictional**. Do not copy any existing game's art: no Command & Conquer units, logos, interface or maps. Do not depict real manufacturers' logos. Do not put text, watermarks or signatures in images.

---

## 0. How the game uses your images

| Image type | Engine use | Quality bar |
|---|---|---|
| **Top-down "game view"** (true overhead) | Used directly as an in-game **sprite**: the picture lies flat in the 3D world and casts a real shadow. Used for aircraft, ships and support-power planes. | Must be exactly overhead and complete (nothing cropped), on a clean transparent background, with no baked shadow or glow. |
| **Front three-quarter view** | **Portrait** in the selection panel, and the button icon. | Clean silhouette with the whole subject visible. |
| **Side / front / rear / top orthographic views** | **Reference** for building the 3D model in Blender. Tanks, vehicles, infantry and buildings are real 3D models, so the images guide the modelling. | Proportions must agree between views; it helps to include a scale bar. |
| **Construction-stage images** | Reference for each building's construction states (foundation → scaffolding → frame → complete), plus damaged and destroyed versions. | The same building from the same angle in every stage. |
| **Seamless textures** | Ground materials (grass, dirt, sand, snow, asphalt …). | Must tile seamlessly with no visible seams or repeating features. |
| **Map overview paintings** | Layout concept for a map. We rebuild the map in the engine from it. | Readable lanes, bases and resources, with a legend. |

The current build already uses the supplied U.S. aircraft this way: the overhead view is the in-game sprite, and the three-quarter view is the portrait.

---

## 1. Global art direction (applies to everything)

- **Style:** grounded, modern, semi-realistic military hardware with clean shapes that read well from a high RTS camera. Readability beats detail: strong silhouettes and clear parts such as turret, gun, rotors and wings.
- **Lighting:** neutral daylight from the **upper-left**, soft. No dramatic rim light, no lens flare, no motion blur, no depth-of-field blur.
- **Background:** **transparent (RGBA PNG)**. No ground, no cast shadow, and no dark halo or glow around the object (the engine adds real shadows).
- **Camera:** orthographic, or as close to it as possible, with no strong perspective distortion.
- **Paint:** standard per-faction camouflage (see §3). Leave **team-colour zones** in a neutral mid-grey on the main image. Also supply a **team mask** (§2.4).
- **Markings:** use our fictional **faction emblems** (§3), not real national roundels, flags or insignia. Numbers and stencils must be invented.
- **No text** anywhere in the image (no labels, captions or names).
- **Consistency:** each asset must look like the same object in every view (same loadout, colours and details). Generate all views of an asset in one session or one sheet so they match.

### Why fictional designs (please read)

The game treats every side as **fictional game factions**, not portrayals of real armed forces, and no side is the villain. Exact real equipment (for example the F-16, Apache or Abrams), with manufacturer names and real insignia, creates trademark and likeness problems for a commercial release. It also frames the game as a statement about real militaries. **Ask for "a fictional modern multirole fighter inspired by 4th-generation designs", not "an F-16".** Choose distinct, invented shapes. The U.S. aircraft pack already supplied stays in development builds, and is flagged for release review in `content/manifest/aircraft.json`.

---

## 2. File format and naming

### 2.1 Folder and file names
```
<faction>/<category>/<asset_id>/<asset_id>_<view>.png
e.g.  usa/air/usa_air_fighter_01/usa_air_fighter_01_top.png
```
- `faction`: `usa, china, europe, japan, taiwan, ukraine, iran, iraq, nkorea, neutral`
- `category`: `inf, veh, air, navy, bld, def, map, tex, ui, fx`
- `asset_id`: `<faction>_<category>_<role>_<nn>`, all lowercase with underscores.
- `view`: `top`, `front34`, `side`, `rear34`, `front`, `back`, `sheet`, `stage0`…`stage3`, `damaged`, `destroyed`, `mask`, `icon`

### 2.2 Sizes
| Deliverable | Size | Notes |
|---|---|---|
| Single view (top / front34 / side / rear34) | **2048 × 2048** PNG RGBA | Subject centred, about 8% empty margin on every side, **never cropped** |
| Contact sheet (optional, for review) | 2048 × 2048, 2 × 2 grid | Same order every time: top-left = top, top-right = front34, bottom-left = side, bottom-right = rear34. Leave **at least 64 px of empty space between views** so they can be separated automatically. |
| Portrait icon | 512 × 320 PNG RGBA | Front three-quarter view, subject fills about 85% |
| Seamless texture | 2048 × 2048 PNG RGB | Tileable on both axes. State the real-world area covered, e.g. "covers 4 m × 4 m" |
| Map overview | 2048 × 2048 PNG RGB | Top-down painted plan with a legend |

### 2.3 Orientation rules for top-down views
- **Nose (front) pointing straight UP** in the image, every time. (Some of the U.S. pack pointed down or sideways and had to be corrected.)
- Exactly overhead (90°): wings and hull should show no visible side surfaces.
- **Aircraft:** wings fully visible; landing gear retracted for the flying version.
- **Helicopters:** supply the body **without rotor blades** in `_top.png`, plus the **main rotor alone** in `_rotor.png` (and `_tailrotor.png`). Each rotor image is centred on its hub, top-down, blades straight. The engine spins them.
- **Tanks and turreted vehicles:** supply `_hull_top.png` (no turret) and `_turret_top.png` (turret with gun, pivot centred in the image, gun pointing up) so the turret can rotate.
- **Ships:** bow pointing UP; also supply separate `_turret_top.png` images for rotating weapon mounts.

### 2.4 Team-colour mask
For every unit and building, supply `<asset_id>_mask.png`. It's the same image with the team-colour areas painted **pure magenta (#FF00FF)** and everything else pure black, at identical size and position. The engine tints the magenta areas with the player's colour (blue, red, and so on).

### 2.5 What to send with each batch
A short `batch.md` listing, for each file: asset id, the prompt used, the generator/model and date, any edits made, and known problems. We record this in the asset manifest.

---

## 3. The nine factions (fictional; none is a villain)

Each faction is a fictional game faction with its own emblem, colours and playstyle. Names of real countries are the client's chosen setting, but **equipment, emblems and markings are invented**. The table also sets each faction's camouflage and emblem direction.

| id | Faction (working name) | Playstyle identity | Camouflage | Emblem idea (original) |
|---|---|---|---|---|
| usa | United States (fictional forces) | Air power and precision strikes; expensive, high-tech units | Grey-green / tan two-tone | Stylised eagle-wing chevron |
| china | China (fictional forces) | Industrial mass production; strong armour and artillery in numbers | Green / brown / black three-tone | Five-point star inside a gear ring |
| europe | European Coalition | Combined arms, engineering and modular upgrades; strongest static defences | NATO-style green / brown / black | Ring of stars over a crossed-sword chevron |
| japan | Japan (fictional forces) | Advanced sensors, drones and naval and missile defence; small elite force | Blue-grey / dark green | Rising-disc in a hexagon |
| taiwan | Taiwan (fictional forces) | Defensive specialists: mobile anti-air and anti-ship missiles, fortifications | Jungle green / grey | Plum-blossom shield |
| ukraine | Ukraine (fictional forces) | Adaptive warfare: drone teams, field repair, fast mobile units | Pixel green / khaki | Abstract wheat-and-shield badge |
| iran | Iran (fictional forces) | Missiles and drones, fast attack boats, long-range rockets | Desert tan / brown | Stylised mountain-and-sun disc |
| iraq | Iraq (fictional forces) | Desert mobility, mechanised infantry, earthworks and engineering | Sand / light brown | Twin-river wave emblem |
| nkorea | North Korea (fictional forces) | Deep fortifications and tunnels, heavy artillery, rugged cheap vehicles | Dark green / olive | Mountain-ridge star badge |

Emblem deliverable per faction: `<faction>/ui/<faction>_emblem.png`, 1024 × 1024 transparent, flat 2–3 colours, readable at 32 px. Also a one-colour white version (`_emblem_mono.png`) for decals.

---

## 4. What every faction needs (the roster template)

Generate a full set for **each** faction. Any faction can be the player, an ally or the AI enemy, so "enemy" units are simply the other eight factions' rosters. Give each faction **its own original design language** (shapes, details, camouflage); faction rosters must not look alike.

### 4.1 Infantry (3D models; images are reference)
Deliver per soldier type: **character turnaround** — `front`, `side`, `back`, `front34` — in a relaxed **A-pose** (arms 30° from body), full body head-to-boot, same scale, plus a **portrait icon** (head-and-shoulders, front34).

| Role id | Description |
|---|---|
| inf_rifle | Rifle infantry: basic soldier with a carbine, helmet and plate carrier |
| inf_at | Anti-tank soldier with a shoulder-fired launcher (unloaded and loaded poses) |
| inf_aa | Anti-air soldier with a portable SAM launcher |
| inf_engineer | Engineer / builder: tool belt, demolition kit, repair tools (no weapon or a sidearm) |
| inf_special | Faction special soldier (e.g. drone operator for Ukraine, sniper for Taiwan, commando for USA) |
| inf_hero | One hero / commander unit with a distinctive look |

### 4.2 Ground vehicles (3D models; images are reference)
Per vehicle: `top` (split into hull and turret for turreted vehicles), `front34`, `side`, `rear34`, `front`, `back`, `mask`, `icon`, plus `damaged` (scorched, missing parts) and `destroyed` (burnt-out wreck) as `front34` views.

| Role id | Description |
|---|---|
| veh_builder | **Construction vehicle**: dozer or engineering vehicle that builds the base. It must look like it deploys scaffolding and cranes. |
| veh_supply | Supply truck / hauler: collects supplies from depots and brings them to the base |
| veh_scout | Light scout car or buggy with a machine gun |
| veh_apc | Wheeled APC / IFV carrying infantry |
| veh_mbt | Main battle tank (with any faction variant, e.g. heavy or light) |
| veh_arty | Self-propelled artillery or rocket launcher |
| veh_aa | Mobile anti-air (gun and/or missiles) |
| veh_special | Faction special vehicle (e.g. mobile missile launcher for Iran, drone-carrier truck for Ukraine) |

### 4.3 Aircraft (sprites; overhead image used directly)
Per aircraft: `top` (helicopters split into body and rotors, §2.3), `front34`, `side`, `rear34`, `mask`, `icon`, plus `top_damaged` (smoking, holes). Flying configuration; weapons visible on pylons.

| Role id | Description |
|---|---|
| air_fighter | Air-superiority / multirole fighter |
| air_attack | Ground-attack jet or strike fighter |
| air_heli_attack | Attack helicopter |
| air_heli_transport | Transport helicopter |
| air_drone | Combat drone (large UAV) |
| air_bomber | Bomber for a support power (fly-over only) |
| air_recon | Reconnaissance aircraft for a support power |

### 4.4 Naval (sprites; overhead image used directly)
Bow pointing up. Per ship: `top`, `turret_top` for each rotating mount, `front34`, `side`, `mask`, `icon`, `top_damaged`. Also a short **wake strip** `_wake_top.png` (white foam V behind the stern, transparent).

| Role id | Description |
|---|---|
| navy_patrol | Fast patrol / attack boat |
| navy_frigate | Frigate or destroyer with a gun and missile cells |
| navy_sub | Submarine (surfaced and periscope-depth views) |
| navy_landing | Landing craft that carries vehicles |
| navy_carrier | Large ship used as a support-power platform (optional, top view only) |

### 4.5 Buildings and base construction (3D models; images are reference)
The base is built by the construction vehicle (§4.2). **Every building needs construction stages**, all from the **same front three-quarter camera angle**:

| File | Content |
|---|---|
| `_stage0.png` | Cleared, levelled plot with a concrete foundation outline, stakes and a parked material pallet |
| `_stage1.png` | **Scaffolding** erected around a partial frame; a crane or boom; workers optional |
| `_stage2.png` | Walls and roof mostly built, scaffolding still on parts, open sections |
| `_front34.png` | Completed building (also the "stage 3" view) |
| `_damaged.png` | Completed building, damaged: holes, fire scorch, broken antennas |
| `_destroyed.png` | Rubble and burnt frame |
| `_top.png` | Exactly overhead view of the completed building, for the footprint check and the minimap |
| `_mask.png`, `_icon.png` | Team mask and build-menu icon |

State the **footprint in metres** (e.g. "16 × 16 m footprint, 10 m tall") in the prompt and in `batch.md`.

| Role id | Description | Footprint |
|---|---|---|
| bld_hq | Command HQ, where the builder is produced | 18 × 18 m |
| bld_power | Power plant (faction style: generators, solar, reactor …) | 12 × 12 m |
| bld_barracks | Barracks (infantry) | 14 × 12 m |
| bld_factory | Vehicle factory with a large door | 20 × 16 m |
| bld_airfield | Airfield / helipad complex, with pads for 4 aircraft | 30 × 24 m |
| bld_supply | Supply centre, where haulers deliver | 14 × 14 m |
| bld_depot | Neutral supply depot or stockpile (map resource, faction-neutral) | 12 × 12 m |
| bld_radar | Radar / intelligence centre (unlocks the minimap and upgrades) | 10 × 10 m |
| bld_tech | Tech centre (unlocks advanced units) | 16 × 16 m |
| bld_super | Faction super-structure (original concept, e.g. orbital uplink or long-range missile silo) | 24 × 24 m |
| def_mg | Machine-gun bunker | 6 × 6 m |
| def_at | Anti-tank emplacement | 6 × 6 m |
| def_aa | Anti-air site | 8 × 8 m |
| def_wall | Wall segment and gate (straight, corner, gate) | 4 m segments |

### 4.6 Neutral and civilian props (one set, shared)
Oil derrick (capturable), supply crates stack, civilian buildings (house, apartment block, warehouse, shop, factory, petrol station), bridges (straight segment), trees (4 kinds per biome), rocks, fences, road signs (no real text), wrecked civilian cars, a harbour crane and shipping containers. `front34` plus `top` for each.

---

## 5. Maps

The game needs five starting maps. For each, deliver:
1. **Overview painting** (`<map>_overview.png`): exactly top-down plan with clear lanes, bases, cliffs, water, bridges and resources. Mark start positions with **numbered circles** and supply depots with **yellow squares**. Put the legend in `batch.md`, not in the image.
2. **Mood shot** (`<map>_mood.png`): a front three-quarter view at RTS-camera height, showing the look (time of day, weather).
3. **Seamless textures** for the biome (§5.1).

| Map id | Concept | Players | Size |
|---|---|---|---|
| map_harbor_divide | Coastal industrial crossing: a harbour split by water, three bridges/causeways, a container yard in the centre, neutral supplies near each bridge | 2 | 600 × 600 m |
| map_city | Dense city: blocks, a central plaza, a river with bridges, parks, high-rise chokepoints | 2–4 | 700 × 700 m |
| map_mountain_pass | Mountain pass: two valleys joined by a winding pass, high ground with ramps, a dam | 2 | 600 × 800 m |
| map_island_coast | Island coast: two islands, a shallow-water ford, beaches for landings, a naval lane | 2 | 800 × 800 m |
| map_open_steppe | Open terrain: rolling grassland, scattered villages, a few ridgelines, wide flanks | 2–4 | 800 × 800 m |

**Fairness rules** for every map: starting areas mirrored or rotated so no side has an advantage; the same number and distance of supply depots per player; at least two routes between bases; one contested resource in the middle.

### 5.1 Seamless ground textures (per biome)
Each texture comes as a set: `_albedo.png` (colour, no lighting or shadow baked in), plus optionally `_normal.png` and `_rough.png`. 2048², tileable, with the covered area stated.
- Temperate: grass (lush), grass (dry), dirt path, mud, gravel, rock cliff
- Urban: asphalt (with cracks, no lane text), concrete slabs, pavement, rubble
- Coastal: wet sand, dry sand, harbour concrete, shallow water bed
- Mountain: scree, rock, snow, alpine grass
- Desert: sand dunes, hardpan, rocky desert

---

## 6. Interface art

- **Faction emblems** (§3).
- **Command icons** (one style for all factions, 256 × 256, white line icon on transparent): attack-move, guard, stop, scatter, force fire, waypoints, return to base, sell, repair, rally point, build, cancel, upgrade.
- **Support-power icons** per faction power (256 × 256, illustrated).
- **Main menu backgrounds** (1920 × 1080, one per faction): atmospheric battlefield key art with no text and no logos. The game title is drawn by the engine.
- **Loading screens** per map (1920 × 1080), no text.

---

## 7. Prompt templates (copy, then fill the brackets)

**Vehicle / aircraft view sheet**
> Original fictional [modern main battle tank | multirole fighter jet | attack helicopter …] for the [faction] faction of a modern real-time strategy game. Distinct, invented design inspired by [general real-world class, no specific model], [faction camouflage from §3], neutral grey team-colour panels, small invented stencil numbers, no real insignia, no text. Exactly top-down orthographic view, [nose pointing straight up], centred, complete object with wide empty margins, transparent background, no shadow, no glow, soft neutral daylight from upper left, clean hard-surface detail, high resolution.

(Repeat with "front three-quarter view", "side profile view", "rear three-quarter view". Keep **all other words identical** so the design stays the same.)

**Helicopter rotor**
> The main rotor of the same helicopter only: hub and [4] straight blades, exactly top-down, centred on the hub, transparent background, no body, no shadow.

**Building construction stage**
> Original fictional [vehicle factory] for the [faction] faction of a modern RTS game, [16 × 20 m footprint], [faction style]. Stage: [levelled concrete foundation with stakes | steel frame surrounded by scaffolding and a small crane | mostly built with scaffolding on one side | complete | damaged with scorch marks and holes | destroyed rubble]. Front three-quarter view from a high angle (about 45° down), same camera and framing as the other stages, transparent background, no text, no logos.

**Infantry turnaround**
> Original fictional [anti-tank soldier] of the [faction] faction, modern equipment, [faction camouflage], invented patches only, carrying [launcher]. Full-body character turnaround on one sheet: front, side, back and three-quarter, relaxed A-pose, same scale, plain transparent background, no text.

**Seamless texture**
> Seamless tileable top-down photo texture of [dry grass with small dirt patches], covering 4 m × 4 m, flat even lighting with no shadows, no objects, no repeating features, no seams.

**Map overview**
> Top-down painted tactical map for a modern RTS: [coastal industrial harbour split by water with three causeway bridges, container yard in the centre]. Two mirrored starting areas (bottom-left and top-right) marked with numbered circles, supply depots marked with yellow squares, clear routes and chokepoints, readable at small size, no text, no labels.

---

## 8. Quality checklist before sending

- [ ] Transparent background where required; no dark halo or glow around the subject
- [ ] Nothing cropped at the image edges; margins about 8%
- [ ] Top views exactly overhead, **nose or bow pointing up**, rotating parts supplied separately
- [ ] All views of an asset show the same design (colours, loadout, details)
- [ ] No text, logos, real insignia, watermarks or signatures
- [ ] Team mask matches the main image pixel-for-pixel
- [ ] Files named per §2.1; `batch.md` lists prompts and generator per file
- [ ] Each PNG opens without errors (the last U.S. pack had three corrupted files: the A-10, B-2 and F-22 front three-quarter views in the expanded zip)

---

## 9. Suggested generation order

1. Faction emblems for all nine factions (fast, and they fix the identities).
2. **USA and China full rosters** (§4.1–4.5): these are the first two playable sides.
3. Harbor Divide map (overview, mood shot, coastal textures).
4. Base construction stages for the USA and China buildings.
5. Remaining seven factions, two at a time.
6. Naval units, then the remaining maps.
