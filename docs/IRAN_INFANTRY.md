# Iranian infantry roster in 3D (same skeleton, animation set and conventions as the U.S. roster)

**Status:** every asset was built and checked in Blender 5.2 (bpy) only. **Godot was not run in this session.** Nothing here has been seen in game. (Godot `.import` files and `<role>_<role>_*.png` extracted textures appeared in the role folders during the session from an editor import outside this work. I left them in place, matching the U.S. folders.)

This is fictional game content. The equipment shapes are generic procedural silhouettes, not copies of any product design, and no nation is portrayed as villainous.

## Same as the U.S. roster (client: "for troops keep same movement and mechanics")
- **Skeleton:** the same 17-bone `SkeletonProfileHumanoid` with the identical rest pose. The raw-GLB audit found the joint list identical to `rifleman.glb` in all 8 files.
- **Shared kit:** the same body base, IK/pose solver, gait (walk 1.40 m per 1.0 s, run 3.15 m per 0.7 s at scale 1.0), aim, kneel and `die` solvers.
- **Timing and units:** 30 fps with one key per frame; metres.
- **Orientation and origin:** Blender +Y forward (Godot -Z), origin on the ground between the feet, feet on Z = 0 in `idle`.
- **Hand item:** rigid on `RightHand`, with a `Muzzle` empty (+Y along the bore).
- **Team tint:** `SA_Team` patches are neutral 0.75 grey. The previews tint them blue.
- **Action names:** `idle walk run aim fire crouch_fire die`, plus the role extras listed below. Every clip loops except `die` and `para_land`.
- **`inf_kit.py` was not modified.** The Iranian script only uses the kit's public hooks: `Role`, `body_extra`, `extra_objects`, `after_bake`, `POSE_EXTRA`, `AIM_EXTRA`, `DIE_HOOK`, `GROUND_SOLVE` and `WEAPON_SOLVE_ITERS`. It replaces `K.make_camo` in its own process only.
- **U.S. regression check (re-run at the end).** `inf_rifleman_rigged.py` was regenerated into scratch and compared with the committed `rifleman.glb`:
  - identical glTF JSON (21 nodes, 17 joints, the same 7 actions, the same accessor counts);
  - `rifleman_report.json` and `rifleman_camo.png` md5-identical;
  - the only binary differences are 4 triangle-index buffers whose triangle sets are equal. This is the known exporter ordering noise described in M1_INFANTRY.md.

## Files
| What | Path |
|---|---|
| Iranian roster script (role argument) | `tools/art/inf_iran_3d.py` |
| Flag props + procedural flag artwork (also used for the sleeve patch) | `tools/art/prop_flag_3d.py` |
| Role GLBs | `godot/assets/units3d/<role>/<role>.glb`, plus `<role>_report.json`, `<role>_camo.png`, `<role>_flagpatch.png`, `<role>_hair.png` (and `<role>_shemagh.png` for the sniper and IRGC). All textures are also embedded in the GLB. |
| Flag props | `godot/assets/units3d/props/flag_iran.glb`, `flag_usa.glb` (texture embedded) |
| Previews (Cycles CPU, 16 samples; strips 10; faces 24) | `docs/screens/ir_<role>_{front,rts,anims}.png` (the IRGC prefix is `ir_irgc_sf_`), `docs/screens/ir_faces.png`, `docs/screens/flags.png` |

The roles are `ir_rifleman`, `ir_rpg`, `ir_mg`, `ir_sniper`, `ir_engineer`, `ir_medic`, `irgc_sf` and `ir_paratrooper`.

### Rebuild (from the repository root; deterministic, PYTHONHASHSEED pinned)
```
python3 tools/art/inf_iran_3d.py ir_rifleman godot/assets/units3d/ir_rifleman            # GLB only, ~4 s
python3 tools/art/inf_iran_3d.py ir_rpg godot/assets/units3d/ir_rpg --previews docs/screens --faces <tiles>   # ~40 s
python3 tools/art/inf_iran_3d.py faces_sheet <tiles> docs/screens/ir_faces.png
python3 tools/art/prop_flag_3d.py godot/assets/units3d/props --previews docs/screens     # both flags, ~10 s
```
`--faces <tiles>` renders three head close-ups per role into a scratch folder. `faces_sheet` combines them.

## Face variants (all roles)
- **Shared base head (clean-shaven):** the body mesh carries a shaven face with small dark eyes, upper lids, brows and a lip line. The U.S. roster's eye protection is off, so the face reads.
- **Two extra objects in every GLB**, separate skinned meshes on the same skin, 100 % weighted to `Head`:
  - `Beard`: 324 triangles. It is a shell ray-cast onto the head and jaw ellipsoids, offset along the surface normal, with edges tapered into the skin and a slight chin drop. The material is `SA_Beard`, a procedural dark-brown strand texture.
  - `Moustache`: 64 triangles.
- **The game picks the look per unit by hiding nodes:**

  | Look | Beard | Moustache |
  |---|---|---|
  | bearded | shown | shown |
  | moustache only | hidden | shown |
  | clean-shaven | hidden | hidden |

- **Suggested mix:** spawn a deterministic per-unit pick, for example `unit_id % 5` gives 0–2 bearded, 3 moustache, 4 shaven.
- **Beard style per role** (baked into each GLB's `Beard`):
  - `full` (short full beard): rifleman, mg, sniper, irgc_sf;
  - `trim` (trimmed beard): rpg, engineer, medic, paratrooper.
- Each report records this under `face_variants`.

## Flags
- **Sleeve patch.** A 56 × 32 mm patch on the **left** upper sleeve, just below the team armband.
  - Material `SA_FlagIR`, using its own texture (`<role>_flagpatch.png`, 140 × 80 px) with its own planar UVs.
  - The artwork comes from `prop_flag_3d.flag_image`.
  - It is visible in close views (see `ir_rpg` aim); it is too small to read at RTS zoom.
- **Props.** `flag_iran.glb` and `flag_usa.glb` each contain:
  - `Pole`: an 8 m tapered mast with a truck, ball finial, concrete plinth and an `SA_Team` collar for team tint.
  - `Flag`: a 28 × 12-quad cloth with a double-sided material. Iran is 2.45 × 1.40 m (7:4); the U.S. is 2.47 × 1.30 m (19:10).
  - `Armature`: a 7-bone chain, `Flag0`–`Flag6`, along the fly.
  - Action **`wave`**: a 2.0 s loop (61 frames, first = last) combining a travelling wave about the vertical axis, a slight droop and a ripple twist.
  - Each prop has about 950 triangles.
  - The origin is the foot of the pole. The flag flies toward +X; rotate the prop about Y for wind direction.
- **Iranian artwork is simplified and geometric, with no text drawn:**
  - green-white-red tricolour;
  - a red central emblem built from two pairs of crescents, a central blade and a small diamond;
  - the band edging is 11 + 11 white comb motifs instead of the calligraphy of the real flag.
- **U.S. artwork:** 13 stripes, a canton over 7 stripes, and 50 stars drawn as white dots in the 9-row staggered layout.

## Camouflage (generated from colours only, no photos)
- **Regular army (`camo_woodland`):** a disruptive woodland/desert pattern with large, hard-edged, slightly horizontal blotches. The palette is sand base, light sand, olive green, brown, and small near-black branches.
- **Regular-army kit materials:**
  - gear is solid olive-drab canvas (`SA_Rig`; the kit's `SA_CamoGear` is remapped to it);
  - boots, gloves and belt are dark-brown leather (an `SA_Canvas` override).
- **IRGC (`camo_digital`):** a two-scale pixel pattern (about 0.9 cm cells) in khaki-olive, green, brown and dark tones. IRGC gear is solid coyote (`SA_Coyote`).

## Roles
1. **`ir_rifleman`**
   - Rifleman actions.
   - AK-family rifle (`Rifle`, wood furniture, curved magazine, slanted front sight; `Muzzle` at 0.89 m).
   - Older-style helmet with a cloth cover and elastic band, no rails or NVG mount, team patch on top.
   - Olive chest rig with 4 magazine pouches and an X harness; small pack and a bedroll under it.
2. **`ir_rpg`** (AT4 conventions)
   - `idle`/`walk`/`run`: one-handed side carry with the left arm swinging or pumping.
   - `aim`: shouldered, with the left hand on the tube ahead of the grip.
   - `fire` and `crouch_fire`: a 0.6 s launch (50 mm kick and 5° rise, then recovery); both start and end in the aim pose.
   - `die`.
   - **`Launcher`:** a reusable tube with a wooden heat guard, flared venturi, pistol grip and an optic on the left. The rocket is loaded with an olive ogive warhead, a marking band and a nose probe.
   - **Empties:** `Muzzle` at the warhead tip (0.86 m); `Backblast` at the venturi (-0.58 m), rotated 180° so its +Y points out of the rear.
   - **Gear:** a rocket carrier on the back holding two spare rockets with warheads up, which gives a strong RTS silhouette.
   - **Tube clearance** (re-imported GLB, every 2nd frame; hands excluded): 0 mm in every action except a 29 mm transient in `die`. The approved AT4 has about 3 cm.
3. **`ir_mg`**
   - PKM-family GPMG (`MMG`): skeleton stock, ammo box under the receiver, long barrel with carry handle, folded bipod; `Muzzle` at 1.175 m.
   - Brass ammunition belt worn across the chest; spare ammo box on the hip.
   - `fire` and `crouch_fire`: 3-round burst in 0.35 s.
4. **`ir_sniper`**
   - SVD-family DMR (`SniperRifle`): thumbhole stock with cheek rest, slender barrel, slotted flash hider, optic on the **left** side mount; `Muzzle` at 1.245 m.
   - Boonie hat with a team patch on the crown, and a shemagh with a soft check texture. No helmet; lighter chest rig.
   - `fire` and `crouch_fire`: one heavy shot in 0.8 s.
5. **`ir_engineer`**
   - G3-family rifle (`Rifle`): straight stock, cocking tube over the barrel, straight magazine, drum sight; `Muzzle` at 0.985 m.
   - **Tool kit:**
     - a tool pack carrying an entrenching shovel (handle with a T-grip above the pack lid) and a large wrench;
     - a hip tool pouch with a hammer and pliers;
     - a wire/det box on the hip.
   - Extra **`work`** (2 s loop): kneeling while the left hand hammers and turns; the rifle is held muzzle-down in the right hand.
6. **`ir_medic`**
   - AK with an under-folding stock.
   - Aid bag with `SA_Team` panels on the back and lid, a hip aid pouch with an `SA_Team` patch, and a wide `SA_Team` armband on the right arm.
   - **No red crescent or red cross is modelled.** The client must supply an approved emblem before release.
   - Extra **`heal`** (2 s kneeling treatment loop).
7. **`irgc_sf`**
   - Rifleman actions.
   - **Distinct from the regular army:**
     - digital camo;
     - coyote plate carrier with magazine pouches;
     - modern coyote helmet with rails and headset, plus a boom mic;
     - radio and second antenna, knee pads, holster, back panel with a team patch;
     - shemagh around the neck;
     - full beard.
   - **Weapon:** a modernised AK-family rifle with adjustable polymer stock, rail handguard, magnified optic, suppressor and laser box; `Muzzle` at 0.855 m.
   - I chose the helmet variant, not a balaclava, so the beard stays visible.
8. **`ir_paratrooper`**
   - The same harness, actions and calibration as the U.S. paratrooper.
   - **Gear:** main container with a team panel, reserve on the belly, lift webs with canopy releases, leg straps and chest strap, over the olive chest rig.
   - **`ChuteAttach` empty:** on `Chest` at (0, 0, 1.49).
   - **Para actions:** `para_descend` (2 s loop) and `para_land` (2.4 s one-shot; its last frame equals `idle` frame 0).
   - **Parachute:** reuses the existing `godot/assets/units3d/paratrooper/parachute_personnel.glb`. No new parachute was made.
   - **Weapon:** AK with a folding stock.

## Per-role numbers (from `<role>_report.json`)
- **Triangles:** totals include `Beard` (324) and `Moustache` (64). The shaven look draws 388 fewer. Every role is inside the 2.5k–6k budget.
- **IK slip and leg values:** "worst IK slip" and the ~98–101 mm leg value in `die` (the extended-legs final pose) behave exactly as on the U.S. roster.
- **Body min Z** is the lowest deformed body point over the clip. **Hand item min Z** is the lowest point of the hand item.

**ir_rifleman** - triangles: `IR_Rifleman_Body` 3,106, `Rifle` 320, `Beard` 324, `Moustache` 64, **total 3,814** (beard style: full)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 781.3 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 679.3 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 524.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1194.0 mm |
| `fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1199.9 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 732.0 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 98.0/23.1 mm | -4.5 mm | 0.1 mm |

**ir_rpg** - triangles: `IR_RPG_Body` 3,238, `Launcher` 564, `Beard` 324, `Moustache` 64, **total 4,190** (beard style: trim)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 590.9 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/0.0, 2.2/2.2 mm | -1.4 mm | 483.6 mm |
| `run` | yes | 0.70 s | 22 | 0.0/0.0, 0.0/0.0 mm | -1.8 mm | 508.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1352.3 mm |
| `fire` | yes | 0.60 s | 19 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1354.6 mm |
| `crouch_fire` | yes | 0.60 s | 19 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 892.1 mm |
| `die` | **no** | 1.50 s | 46 | 29.0/0.0, 98.0/22.9 mm | -4.5 mm | -0.5 mm |

**ir_mg** - triangles: `IR_MG_Body` 3,058, `MMG` 292, `Beard` 324, `Moustache` 64, **total 3,738** (beard style: full)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 640.0 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 526.8 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 326.1 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1288.5 mm |
| `fire` | yes | 0.33 s | 11 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1294.1 mm |
| `crouch_fire` | yes | 0.33 s | 11 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 826.1 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 98.0/22.8 mm | -4.5 mm | 7.2 mm |

**ir_sniper** - triangles: `IR_Sniper_Body` 3,056, `SniperRifle` 352, `Beard` 324, `Moustache` 64, **total 3,796** (beard style: full)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 609.7 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 493.7 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 282.4 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1306.5 mm |
| `fire` | yes | 0.80 s | 25 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1310.7 mm |
| `crouch_fire` | yes | 0.80 s | 25 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 842.8 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 98.1/22.8 mm | -4.5 mm | 5.5 mm |

**ir_engineer** - triangles: `IR_Engineer_Body` 3,110, `Rifle` 248, `Beard` 324, `Moustache` 64, **total 3,746** (beard style: trim)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 734.5 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 628.8 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 458.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1281.1 mm |
| `fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1286.4 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 818.5 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 98.0/22.9 mm | -4.5 mm | 2.3 mm |
| `work` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 13.5 mm |

**ir_medic** - triangles: `IR_Medic_Body` 3,002, `Rifle` 308, `Beard` 324, `Moustache` 64, **total 3,698** (beard style: trim)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 781.3 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 679.3 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 524.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1194.0 mm |
| `fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1199.9 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 732.0 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 98.1/22.8 mm | -4.5 mm | -0.0 mm |
| `heal` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | -0.3 mm |

**irgc_sf** - triangles: `IRGC_SF_Body` 3,654, `Rifle` 380, `Beard` 324, `Moustache` 64, **total 4,422** (beard style: full)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 792.7 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 692.8 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 544.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1194.0 mm |
| `fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1199.9 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0/0.0, 0.0/0.0 mm | -2.9 mm | 776.1 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 100.0/26.7 mm | -4.5 mm | 4.3 mm |

**ir_paratrooper** - triangles: `IR_Paratrooper_Body` 3,202, `Rifle` 308, `Beard` 324, `Moustache` 64, **total 3,898** (beard style: trim)

| Action | Loop | Length | Frames | Worst IK slip (arm R/L, leg R/L) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0/1.7, 0.0/0.0 mm | 0.0 mm | 781.3 mm |
| `walk` | yes | 1.00 s | 31 | 0.0/6.2, 2.2/2.2 mm | -1.4 mm | 679.3 mm |
| `run` | yes | 0.70 s | 22 | 0.0/9.5, 0.0/0.0 mm | -1.8 mm | 524.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1194.0 mm |
| `fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | 0.0 mm | 1199.9 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0.0/0.0, 0.0/0.0 mm | -2.9 mm | 732.0 mm |
| `die` | **no** | 1.50 s | 46 | 0.0/0.0, 101.0/28.2 mm | -4.5 mm | 0.9 mm |
| `para_descend` | yes | 2.00 s | 61 | 0.0/0.0, 0.0/0.0 mm | -1.0 mm | 676.2 mm |
| `para_land` | **no** | 2.40 s | 73 | 0.0/0.0, 0.0/0.0 mm | -4.6 mm | 107.1 mm |

## Known shortcomings
1. **Not seen in Godot.** All checks were done in Blender:
   - parsing the GLBs: joints identical to the U.S. rifleman, one shared skin for body, `Beard` and `Moustache`, every action name present, `Muzzle`/`Backblast`/`ChuteAttach` parented correctly, the flag materials `doubleSided`;
   - re-importing the GLBs and rendering the RPG aim and the flags from the re-imported files;
   - checking RPG tube clearance.

   Hiding `Beard` and `Moustache` per unit has **not** been exercised in Godot. `unit.gd` and `unit_defs.gd` do not yet reference these roles; integration is a separate task.
2. **Shared kit style limits** (as for the U.S. roster): primitive-built bodies, rigid glove hands, box-projected camo seams, one forward `die`.
3. **Faces:**
   - The base head is low-poly. Beards are solid shells with tapered edges, with no alpha or stubble fade.
   - At close zoom the full beard reads as a dense, dark short beard. It is not comical, but it is blocky (see `ir_faces.png`).
   - The `trim` style is only moderately different from `full`: it is thinner, has a lower cheek line and covers less under the chin.
   - The moustache is a simple bar with dropped corners.
   - All units share one face shape; only the hair objects vary.
4. **Materials not in the game palette.** The new materials are `SA_Rig`, `SA_Wood`, `SA_Olive`, `SA_Lip`, `SA_Eye`, `SA_Coyote`, `SA_Brass`, `SA_Webbing`, `SA_Marking`, `SA_FlagIR`, `SA_Beard` and `SA_Shemagh`, plus `SA_FlagUS`, `SA_Pole`, `SA_Finial` and `SA_Concrete` on the props. Like the U.S. roster's materials, they are **not** in `UnitArt`'s palette, so the importer must keep the imported materials.
5. **RPG:**
   - The left hand joins only for `aim` and `fire`; the carry is one-handed.
   - The warhead stays on the launcher after firing. There is no reload clip and no "empty tube" state, so the game should hide or show the warhead mesh if needed. The warhead is part of the `Launcher` mesh, not a separate node.
   - `die` has a 29 mm transient tube/body overlap.
6. **Sniper:**
   - No ghillie (unlike the U.S. sniper); the boonie hat and shemagh give the silhouette instead.
   - In `die` the rifle lies 5.5 mm above the ground; this is fine.
   - `crouch_fire` is kneeling, not prone.
7. **Engineer and medic:**
   - The hand item cannot be put down. `work` and `heal` keep the rifle in the right hand, muzzle down.
   - There is no hand-held tool or patient prop; the tools are on the pack and hip.
8. **IRGC:** the combat-helmet chin-strap boxes sit near the sideburns and may touch the beard at close zoom.
9. **Flag sleeve patch:** too small to read at the RTS camera distance. It only shows up close.
10. **Flags:**
    - The bone-chain wave keeps the cloth rigid along each vertical line, with no vertical ripples beyond the twist.
    - The U.S. stars are dots.
    - The Iranian emblem and edging are deliberate geometric simplifications. If an exact official flag is wanted, the client must approve that artwork separately.
