# M1 infantry: U.S. roster in 3D (shared rig and animation kit)

**Status:** every asset was built and checked in Blender 5.2 (bpy) only. **Godot has not been run**, as the brief required. Nothing here has been seen in game.

The approved PILOT rifleman (`docs/PILOT3D_INFANTRY.md`) is now one variant of a shared kit. Every role uses:
- the same 17-bone `SkeletonProfileHumanoid` skeleton, with the identical rest pose and bone frames;
- the same body and uniform base, and the same pose solver and bake;
- the same conventions: metres, Blender +Y forward (Godot -Z), origin on the ground between the feet, feet on Z = 0 in `idle`;
- 30 fps, with one key per frame.

## Files

| What | Path |
|---|---|
| Shared kit: body, gear, rig, IK/pose solver, rifleman action set, bake, verification, export, previews | `tools/art/inf_kit.py` |
| Rifleman (now a thin wrapper; same CLI and output) | `tools/art/inf_rifleman_rigged.py` |
| Hand items: LMG, MMG, sniper rifle, carbine variants, pistol, mine detector | `tools/art/inf_weapons.py` |
| Camo palette sampler (run with `python3 -I`; concept PNGs are untrusted input) | `tools/art/inf_palette.py` |
| AT4 gunner | `tools/art/inf_at4_3d.py` |
| Paratrooper + personnel parachute | `tools/art/inf_paratrooper_3d.py` |
| Medic, SAW, M240, sniper, EOD, ranger, special forces, pilot | `tools/art/inf_roster_3d.py <role>` |
| Runtime assets | `godot/assets/units3d/<role>/<role>.glb`, plus `<role>_camo.png` (also embedded) and `<role>_report.json` |
| Parachute | `godot/assets/units3d/paratrooper/parachute_personnel.glb`, `parachute_gore.png`, `parachute_personnel_report.json` |
| Previews (Cycles CPU, 16 samples; anim strips 10 samples) | `docs/screens/m1_inf_<role>_{front,side,rts,anims}.png`, plus `m1_inf_paratrooper_chute.png` |

### Rebuild commands
Run from the repository root. The scripts are deterministic: each re-executes itself with `PYTHONHASHSEED=0`.
```
python3 tools/art/inf_at4_3d.py godot/assets/units3d/at4 --previews docs/screens
python3 tools/art/inf_paratrooper_3d.py godot/assets/units3d/paratrooper --previews docs/screens
python3 tools/art/inf_roster_3d.py medic godot/assets/units3d/medic --previews docs/screens   # any roster role
```
- Without `--previews`, a GLB builds in about 5–10 s.
- With previews, each role takes about 1–2 min on the shared 2 cores.

## Rifleman equivalence (regression check)
`godot/assets/units3d/rifleman/rifleman.glb` was **not rewritten**. The refactored kit rebuilds it equivalently:
- `rifleman_report.json` and `rifleman_camo.png` are byte-identical (md5 `fe625d67…` and `4d3f6abc…`).
- The GLB has identical glTF JSON: node, bone, action and material names, transforms, and accessors.
- Every vertex, normal, UV, skin and animation buffer is identical.

The only bytes that differ are the triangle *index order* inside quads. This was a correction to the PILOT doc: the **original** script already differed between two of its own runs, because Blender's exporter triangulates nondeterministically. The PILOT doc's "byte-identical" claim was therefore slightly too strong. I compared the triangles as sets; they are the same.

The check was re-run after every kit change. The rifleman keeps its own preview names (`pilot3d_rifleman_*`), and its previews were not re-rendered.

## Shared kit: what a role can vary
- **Palette.** The camo is generated with the same layered noise pattern. Colours come from `inf_palette.py --albedo <role>`:
  - It runs k-means (k = 6) on uniform pixels from the role's concept.
  - Each colour is calibrated by luminance rank against the approved rifleman albedo. This corrects for the shading baked into the concept images.
  - The resulting numbers are written into the role scripts, so builds never read the images. No concept pixels are on any model.
- **Body options:** pack (assault / small / none), radio, hydration hose, plate carrier or none, knee pads, eye-pro, beard, NVG, helmet material, armband, holster. There is also a material **remap** (special forces: `SA_CamoGear` → `SA_Green`), plus a per-role `body_extra` hook that adds geometry to the same skinned mesh.
- **Hand item.** Every item is built in the carbine's local frame, with its pistol grip at the rifle's grip, so the shared bind pose holds it. Recoil kick, lift and rise are set per weapon. Per-weapon "lay" parameters place the item on the ground in `die`.
- **Pose hooks** (none of these affect the rifleman):
  - Carry frames (`w_loc` / `w_q`) for one-handed carries.
  - Left-grip slide, roll and drop along the weapon.
  - A free left hand for arm swing or riser grip.
  - Extra ground-solved actions.
  - Bone-parented empties (`ChuteAttach`).
- **Report.** Each role's report adds, beyond the rifleman's fields:
  - the role name;
  - weapon and empty positions;
  - the palette and the material list;
  - `ik_worst_frame`;
  - notes.

**Stride (all roles; the gait is shared).** `walk` covers 1.40 m per 1.0 s cycle (1.4 m/s). `run` covers 3.15 m per 0.7 s cycle (4.5 m/s). These are at model scale 1.0. At the 1.3x infantry scale, multiply by 1.3. Set the playback rate to `speed / stride` exactly as for the rifleman. For example, the AT4 at 4.2 m/s plays `run` at 4.2 / 4.095 ≈ 1.03x.

**Loop flags.** The action names carry no `-loop` suffix, so set `loop_mode = LINEAR` in Godot for every clip that the tables mark as looping. That is everything except `die` and `para_land`.

**Materials.** New plain materials are `SA_Olive`, `SA_Marking`, `SA_Webbing`, `SA_Ghillie`, `SA_Ghillie2`, `SA_Green`, `SA_Vest`, `SA_Helmet`, plus `SA_Canopy` and `SA_Lines` on the parachute. These, like `SA_Camo` and `SA_CamoGear` (PILOT doc, shortcoming 4), are **not** in `UnitArt`'s palette. The integrator must keep the imported materials or extend the palette.

`SA_Team` stays the neutral 0.75 grey patch for team tint. The previews tint it blue.

## Roles

### 1. AT4 gunner (`at4`)
- **Launcher** (object `Launcher` on `RightHand`). A generic disposable tube (original design), 1.03 m long:
  - olive tube with black shock-absorber ends and a flared venturi;
  - fold-up rear sight, front sight post and sight rail on the **left** side;
  - pistol grip, firing block with cocking lever, foregrip, shoulder pad, sling swivels;
  - one yellow ammunition band (`SA_Marking`).
- **Empties.** `Muzzle` is at the front end, with +Y along the bore. `Backblast` is at the rear end, rotated 180° about Z so its +Y points out of the venturi.
- **Gear.** Rifleman base with a slimmer patrol pack. The gunner's own carbine is slung diagonally across the pack (rigid to Chest) with a sling strap, plus a hip pouch.
- **Carry (idle, walk, run).** One-handed side carry, as in the concept: tube along the right side, rear end behind the hip, front angled down and forward. The left arm swings free (walk) or pumps (run).
- **`aim`.** Tube on the right shoulder, level, left hand on the foregrip, head beside the left-side sight.
- **`fire` / `crouch_fire`.** A 0.6 s launch: 55 mm kick and 5° rise in 0.07 s, a short hold while the backblast clears, then the torso rocks back and recovers to the aim pose. Start and end frames are identical, so the clip can loop or play once per shot.
- **Tube-clearance check.** I counted body vertices inside the tube's cylinder on every second frame of the re-imported GLB. The grip hands are excluded, since they intentionally wrap the grip.
  - `idle`, `walk`, `aim`, `fire`: 0 mm.
  - `crouch_fire`: 1.2 mm.
  - `run`: 4.4 mm (forearm, 2 vertices).
  - `die`: one transient pass of about 3 cm through the chest at the impact frame (about frame 24).

### 2. Medic (`medic`)
- **Carbine:** the rifleman's.
- **Gear:**
  - large aid bag on the back with an `SA_Team` panel;
  - hip aid pouch with an `SA_Team` patch;
  - a wide `SA_Team` armband on the right arm.
- **Emblem.** No red cross or any medical emblem is modelled. **The client must supply an approved emblem before release.**
- **Extra action `heal`** (2.0 s loop): kneeling, torso bent over, two pressing cycles with the left hand. The carbine stays in the right hand, muzzle down along the right thigh.

### 3. SAW gunner (`saw_gunner`)
- **Weapon** (object `LMG`): light machine gun with skeleton stock, tall receiver with feed cover, small optic, soft 200-round pouch, carry handle, heat shield and folded bipod.
- **`fire` / `crouch_fire`:** a 3-round burst cycle in 0.3 s.

### 4. M240 gunner (`m240_gunner`)
- **Weapon** (object `MMG`): heavier and longer, 1.17 m to the `Muzzle`. It has a belt pouch with the belt running into the feed tray, a barrel carry handle, a gas tube and a folded bipod.
- **Gear:** a spare-barrel bag strapped diagonally on the pack.
- **`fire` / `crouch_fire`:** a 3-round burst in 0.35 s, with heavier chest recoil.

### 5. Sniper (`sniper`)
- **Weapon** (object `SniperRifle`): long precision rifle with cheek rest, large scope, heavy barrel and suppressor (`Muzzle` at 1.225 m), and a folded bipod.
- **Ghillie:** 380 strand cards (single quads) rooted, area-weighted, on the uniform, gear and helmet faces. Each card copies its root vertex's skin weights. Materials are `SA_Ghillie`, `SA_Ghillie2` and the camo.
- **`fire` / `crouch_fire`:** one heavy shot in 0.8 s (kick then settle). `crouch_fire` is kneeling.

### 6. EOD engineer (`eod_engineer`)
- **Bomb-suit look:**
  - armoured torso, chest plate and groin plate;
  - high collar;
  - padded sleeves and legs;
  - large helmet with a visor and lamp;
  - cooling unit / tool kit on the back.
- **Hand item:** a **mine detector** (object `Detector`): arm cuff, grip, electronics box, telescopic shaft, and a search coil that lies flat when the shaft is pitched 45°. **`Muzzle` is the coil centre** (the sweep or effect point), not a gun bore.
- **Actions:**
  - `aim`: slow search sweep (2 s).
  - `fire`: fast sweep (1 s).
  - `crouch_fire`: kneeling sweep (1.5 s).
  - Extra **`work`** (2 s loop): kneeling, coil grounded at the right, left hand working in front.

### 7. Ranger (`ranger`)
Rifleman actions. The changes from the rifleman are:
- bare coyote helmet with a strobe;
- slim pack, a second antenna and chest-rig magazines;
- carbine with an illuminator box and a magnifier.

### 8. Special forces (`special_forces`)
Rifleman actions. The changes from the rifleman are:
- solid ranger-green carrier and pouches (`SA_Green`);
- no pack, but a back panel with a team patch;
- boom mic and a second antenna;
- short suppressed carbine (coyote furniture, `Muzzle` at 0.75 m).

### 9. Pilot (`pilot`)
- **Clothing:** a flight suit using the same camo pipeline with a nearly flat sage palette, a G-suit over the thighs, a survival vest with pockets and a radio, and a flight helmet with visor, visor housing and a team stripe. No plate carrier and no knee pads.
- **Hand item:** pistol (object `Pistol`).
  - `idle`, `walk`, `run`: pistol held one-handed at the side, left arm free (swinging or pumping).
  - `aim`, `fire`, `crouch_fire`: two-handed, arms extended, support hand under the firing hand. `fire` has a 9° muzzle rise.

### 10. Paratrooper (`paratrooper`) and parachute
- **Paratrooper.** Rifleman with:
  - a jump harness: main lift webs, canopy releases, chest strap, leg-strap bands;
  - a reserve on the belly;
  - a main container on the back with a team panel.
- **`ChuteAttach` empty.** A child of the `Chest` bone at the riser connection point. Its rest position is (0, 0, 1.49). During `para_descend` it sits at about (0, 0, 1.525).
- **`para_descend`** (2 s loop): hanging with legs together, slightly bent, toes pointed down, a gentle pendulum sway, head looking down. The left hand is up on the left riser; the right hand keeps the rifle tucked. The hang height is calibrated so the toes just reach Z = 0.
- **`para_land`** (2.4 s, **one-shot**): touchdown with feet and knees together, roll onto the right side and back, roll up onto one knee, stand. **Its last frame equals `idle` frame 0.**
- **Parachute GLB.** `parachute_personnel.glb` holds two objects:
  - `Canopy`: a round 24-gore dome with apex vent and scalloped billow, 6.4 m skirt diameter, skirt about 5.3 m and apex 7.3 m above the origin. Its texture is `parachute_gore.png` (generated seams and bands).
  - `Rigging`: 4 risers and 24 suspension lines.
  - The origin is the harness attachment point; the risers end at x = ±0.12.
  - Action `canopy_idle` is a 2 s breathing loop on the canopy's scale. All materials export as double-sided.
- **Game fit.** `unit.gd` puts the canopy at `vis` y = 2.0 and does not use `ChuteAttach`. At the 1.3x infantry scale, the harness during `para_descend` sits at 1.525 × 1.3 ≈ 1.98 m, so it lines up if the canopy itself is not scaled. This is not verified in Godot.
- **Preview.** `m1_inf_paratrooper_chute.png` shows the two GLBs assembled in Blender.

## Per-role numbers (from `<role>_report.json`)
- **Worst IK slip** is the largest distance a hand or foot target was beyond reach, over the whole clip. The leg value in `die` (about 98 mm) is the extended-legs final pose and is the same as the approved rifleman's.
- **Min Z** is the lowest point of the deformed body or hand item over all frames (negative means below the ground).

**at4** - triangles: `AT4_Body` 3,850, `Launcher` 480, **total 4,330**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0 / 0.0 mm | 0.0 mm | 691.5 mm |
| `walk` | yes | 1.00 s | 31 | 0.0 / 2.2 mm | -1.4 mm | 591.9 mm |
| `run` | yes | 0.70 s | 22 | 0.0 / 0.0 mm | -1.8 mm | 610.5 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1350.7 mm |
| `fire` | yes | 0.60 s | 19 | 0.0 / 0.0 mm | 0.0 mm | 1353.0 mm |
| `crouch_fire` | yes | 0.60 s | 19 | 0.0 / 0.0 mm | -2.9 mm | 934.6 mm |
| `die` | **no** | 1.50 s | 46 | 26.8 / 98.5 mm | -4.5 mm | 2.0 mm |

**medic** - triangles: `Medic_Body` 3,498, `Rifle` 360, **total 3,858**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 780.9 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 678.1 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 520.0 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1153.8 mm |
| `fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | 0.0 mm | 1159.2 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0 / 0.0 mm | -2.9 mm | 735.4 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 98.5 mm | -4.5 mm | 1.5 mm |
| `heal` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | -2.9 mm | 0.8 mm |

**saw_gunner** - triangles: `SAW_Body` 3,470, `LMG` 288, **total 3,758**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 735.8 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 630.8 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 464.1 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1283.7 mm |
| `fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | 0.0 mm | 1289.1 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | -2.9 mm | 865.2 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 98.5 mm | -4.5 mm | -0.1 mm |

**m240_gunner** - triangles: `M240_Body` 3,498, `MMG` 284, **total 3,782**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 644.5 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 532.6 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 337.0 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1263.6 mm |
| `fire` | yes | 0.33 s | 11 | 0.0 / 0.0 mm | 0.0 mm | 1269.1 mm |
| `crouch_fire` | yes | 0.33 s | 11 | 0.0 / 0.0 mm | -2.9 mm | 845.2 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 98.5 mm | -4.5 mm | 5.0 mm |

**sniper** - triangles: `Sniper_Body` 4,138, `SniperRifle` 408, **total 4,546**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 610.0 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 495.1 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 288.4 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1311.6 mm |
| `fire` | yes | 0.80 s | 25 | 0.0 / 0.0 mm | 0.0 mm | 1315.8 mm |
| `crouch_fire` | yes | 0.80 s | 25 | 0.0 / 0.0 mm | -22.6 mm | 935.2 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 98.7 mm | -4.5 mm | 1.5 mm |

**eod_engineer** - triangles: `EOD_Body` 3,258, `Detector` 152, **total 3,410**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0 / 0.0 mm | 0.0 mm | 151.5 mm |
| `walk` | yes | 1.00 s | 31 | 0.0 / 2.2 mm | -1.4 mm | 44.9 mm |
| `run` | yes | 0.70 s | 22 | 0.0 / 0.0 mm | -1.8 mm | 70.7 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 51.2 mm |
| `fire` | yes | 1.00 s | 31 | 0.0 / 0.0 mm | 0.0 mm | 0.1 mm |
| `crouch_fire` | yes | 1.50 s | 46 | 0.0 / 0.0 mm | -2.9 mm | -0.1 mm |
| `die` | **no** | 1.50 s | 46 | 13.4 / 99.5 mm | -4.5 mm | 0.5 mm |
| `work` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | -2.9 mm | 18.2 mm |

**ranger** - triangles: `Ranger_Body` 3,506, `Rifle` 412, **total 3,918**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 780.9 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 678.1 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 520.0 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1153.8 mm |
| `fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | 0.0 mm | 1159.2 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0 / 0.0 mm | -2.9 mm | 735.4 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 100.0 mm | -4.5 mm | -0.1 mm |

**special_forces** - triangles: `SF_Body` 3,426, `Rifle` 268, **total 3,694**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 783.2 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 700.6 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 621.2 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1153.8 mm |
| `fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | 0.0 mm | 1159.2 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0 / 0.0 mm | -2.9 mm | 735.4 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 98.5 mm | -4.5 mm | 4.7 mm |

**pilot** - triangles: `Pilot_Body` 2,718, `Pistol` 60, **total 2,778**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 0.0 / 0.0 mm | 0.0 mm | 780.0 mm |
| `walk` | yes | 1.00 s | 31 | 0.0 / 2.2 mm | -1.4 mm | 694.8 mm |
| `run` | yes | 0.70 s | 22 | 0.0 / 0.0 mm | -1.8 mm | 647.3 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1243.5 mm |
| `fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | 0.0 mm | 1250.4 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 4.7 / 0.0 mm | -2.9 mm | 820.6 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 98.3 mm | -4.5 mm | 1.0 mm |

**paratrooper** - triangles: `Paratrooper_Body` 3,666, `Rifle` 360, **total 4,026**

| Action | Loop | Length | Frames | Worst IK slip (arm / leg) | Body min Z | Hand item min Z |
|---|---|---|---|---|---|---|
| `idle` | yes | 3.00 s | 91 | 1.7 / 0.0 mm | 0.0 mm | 780.9 mm |
| `walk` | yes | 1.00 s | 31 | 6.2 / 2.2 mm | -1.4 mm | 678.1 mm |
| `run` | yes | 0.70 s | 22 | 9.5 / 0.0 mm | -1.8 mm | 520.0 mm |
| `aim` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | 0.0 mm | 1153.8 mm |
| `fire` | yes | 0.30 s | 10 | 0.0 / 0.0 mm | 0.0 mm | 1159.2 mm |
| `crouch_fire` | yes | 0.30 s | 10 | 0 / 0.0 mm | -2.9 mm | 735.4 mm |
| `die` | **no** | 1.50 s | 46 | 0.0 / 101.0 mm | -4.5 mm | -4.2 mm |
| `para_descend` | yes | 2.00 s | 61 | 0.0 / 0.0 mm | -1.0 mm | 672.0 mm |
| `para_land` | **no** | 2.40 s | 73 | 0.0 / 0.0 mm | -4.6 mm | 98.1 mm |

## Known shortcomings (honest)
1. **Not seen in Godot.** No in-engine import, material or animation check was done. The checks are Blender-only:
   - parsing the GLBs: 17 joints and all action names present in every file, `Muzzle` present under every hand item, `Backblast` and `ChuteAttach` present;
   - re-importing the GLBs and checking ground contact and the AT4 tube clearance.
2. **The PILOT style limits apply to every role:** primitive-built bodies, rigid glove hands with no finger bones, box-projected camo seams, and one forward `die`.
3. **AT4:**
   - It runs with a 1-handed side carry. The left hand joins only for `aim` and `fire`.
   - In `die`, the tube briefly clips the chest at the impact frame.
   - It has no separate "spent tube" or reload clip. The launcher stays in the hand after firing, as in the brief's "carries a tube" design.
4. **Medic `heal` / EOD `work`:**
   - The hand item cannot be put down because it is rigid to `RightHand`. The carbine is held muzzle-down, and the detector coil rests on the ground.
   - Both use the left hand only. No patient or device prop is included.
5. **Sniper:**
   - The strands are single quads and need double-sided rendering. glTF exports `doubleSided: true`; keep cull disabled in Godot.
   - In kneeling `crouch_fire`, a few strands under the knee go up to 23 mm below ground.
   - The strands are rigid to their root bone. They do not flutter.
   - `crouch_fire` is kneeling, not prone.
6. **EOD.** The tool kit is the back unit, not the hand-held case shown in the concept, because the left hand must stay free for `work`. The bomb suit is a padding shell over the standard body and does not change proportions in the joints.
7. **Pilot.** The pistol is in the hand at all times. There is no holster draw.
8. **Paratrooper:**
   - `para_land` uses the ground solver. The worst body point is -4.6 mm in the roll.
   - `canopy_idle` is the only canopy animation. There is no collapse or deflation clip, so `unit.gd` simply frees the canopy on landing.
   - The rifle stays in the right hand during the descent; no weapon case is modelled.
9. **Ranger vs special forces.** They are mostly distinguished by helmet colour, carrier colour, pack and weapon. Their silhouettes are close to the rifleman's by design ("variants of the rifleman").
