# PILOT 3D infantry: rigged U.S. Army rifleman

Status: **asset built and checked in Blender only.** It has not been imported or run in Godot. The brief said not to run Godot, so nothing here says it has been.

| Item | Path |
|---|---|
| Generator (deterministic) | `tools/art/inf_rifleman_rigged.py` |
| Runtime asset | `godot/assets/units3d/rifleman/rifleman.glb` (712 KB, camo texture embedded) |
| Camo texture (also inside the GLB) | `godot/assets/units3d/rifleman/rifleman_camo.png` (512x512, tiling) |
| Build report (numbers below come from here) | `godot/assets/units3d/rifleman/rifleman_report.json` |
| Previews | `docs/screens/pilot3d_rifleman_{front,side,back,top,rts}.png`, `docs/screens/pilot3d_rifleman_anims.png` |

To rebuild, run from the repository root: `python3 tools/art/inf_rifleman_rigged.py godot/assets/units3d/rifleman --previews docs/screens`. You can leave out `--previews`. The GLB and report then build in about 5 s. With previews, Cycles CPU rendering takes about 1 minute. Two builds produce byte-identical files. The glTF exporter iterates hash-ordered sets, so the script re-executes itself once with `PYTHONHASHSEED=0` to keep the output stable.

## Design and provenance
- The design is original and fully procedural: Blender primitives, lofts and tubes. No external meshes, photos or downloads were used.
- The concept art (`godot/assets/us/infantry/rifleman/*.png`) was used for proportions, gear layout and colour only. I ran k-means on its sleeve, trouser and helmet pixels to get the palette. The camo is generated from that palette as layered periodic noise (base tan, khaki, olive, brown, dark branch veins, cream highlights). No pixels from the reference are on the model.
- Gear modelled:
  - Multicam-style uniform with cargo and thigh pockets
  - Plate carrier with front/back plate bags, cummerbund and shoulder straps
  - Triple magazine pouch with coyote flaps, admin pouch with ID patch, radio pouch with whip antenna, IFAK
  - Battle belt with hip pouches and dump roll; drop-leg holster
  - Helmet with camo cover, NVG shroud, side rails, headset cups, counterweight pouch and IR patch
  - Eye protection, chin strap, coyote gloves, knee pads and boots
  - Assault pack with compression straps and a team ID panel on the lid
  - Generic carbine: collapsible stock, flat-top receiver, coyote polymer magazine, free-float rail, vertical grip, weapon light, prism optic, muzzle device. There is no sling; it read as a rigid stick.
- Units are metres. Blender +Y is forward (Godot -Z), +Z is up, and the character's right is +X. The scene origin is on the ground between the feet.

## Mesh and materials
| Object | Triangles | Notes |
|---|---|---|
| `Rifleman_Body` | 3,470 | One skinned mesh, 17 joints |
| `Rifle` | 360 | Rigid; child of the `RightHand` joint |
| **Total** | **3,830** | Target was 2.5k–6k |

All materials are Principled BSDF and export to glTF PBR:

| Material | Base colour | Used for |
|---|---|---|
| `SA_Camo` | `rifleman_camo.png` texture | Uniform, helmet cover, pack |
| `SA_CamoGear` | Same texture × factor (0.86, 0.84, 0.80) | Plate carrier and pouches, slightly darker than the uniform |
| `SA_Canvas` | Coyote (0.40, 0.32, 0.22) | Boots, knee pads, gloves, belt, magazine, mag flaps |
| `SA_Skin` | Plain colour | Face and neck |
| `SA_Metal` | Plain colour | Rifle and NVG metal |
| `SA_Rubber` | Plain colour | Holster, straps, headset |
| `SA_Glass` | Plain colour | Lenses |
| `SA_Team` | Neutral 0.75 grey | Armband, chest ID patch, pack lid panel, helmet IR patch. Meant to be tinted in game. The previews tint it blue. |

UVs are box-projected in world metres at 0.55 m per texture repeat, so the camo has the same scale on every part.

## Skeleton
Bone names follow Godot's `SkeletonProfileHumanoid`. `Hips` is the root. The rest pose is the low-ready rifle hold (not a T-pose), so the animations need little deformation.

```
Hips (0, 0, 0.97)
├─ Spine (0, 0, 1.07)
│  └─ Chest (0, 0.012, 1.25)
│     ├─ Neck (0, 0.03, 1.50)
│     │  └─ Head (0, 0.04, 1.585)          head top 1.80, helmet crown ~1.80
│     ├─ LeftUpperArm (-0.195, 0.025, 1.44) ─ LeftLowerArm ─ LeftHand
│     └─ RightUpperArm (0.195, 0.025, 1.44) ─ RightLowerArm ─ RightHand
│                                                              └─ Rifle (mesh) ─ Muzzle (empty, barrel end)
├─ LeftUpperLeg (-0.095, 0, 0.93) ─ LeftLowerLeg (knee z 0.515) ─ LeftFoot (ankle z 0.095)
└─ RightUpperLeg (0.095, 0, 0.93) ─ RightLowerLeg ─ RightFoot
```

- Upper arm is 0.30 m and forearm 0.27 m. Thigh is 0.415 m and shin 0.42 m.
- The `Muzzle` empty sits at rifle-local (0, 0.905, 0.008), with its +Y along the bore. Godot is expected to import the `Rifle` and `Muzzle` nodes under a `BoneAttachment3D` on `RightHand`. I have not verified this.
- Skinning uses explicit weights, not Blender's automatic weights:
  - Rigid gear (helmet, carrier, pouches, pack, boots, gloves, knee pads) is weighted 100% to one bone each.
  - Cloth tubes (torso, sleeves, trousers, neck) blend between neighbouring bones within 3–8 cm of each joint.

## Actions
All actions are sampled at 30 fps with one key per frame. Looping clips have an identical first and last key, which was checked as a 0.0 m seam on the re-imported GLB.

| Action | Loop | Length | Frames | Content |
|---|---|---|---|---|
| `idle` | yes | 3.0 s | 91 | Low-ready breathing (chest ±1.2°), small weight shift, head glance, rifle sway |
| `walk` | yes | 1.0 s | 31 | Patrol walk with low-ready rifle; pelvis yaw and sway with chest counter-rotation; heel strike and toe-off |
| `run` | yes | 0.7 s | 22 | Forward lean (about 20° total), rifle at port; flight phase where both feet are off the ground (up to 67 mm clearance) |
| `aim` | yes | 2.0 s | 61 | Standing, rifle shouldered and level (+Y), cheek weld on the stock, bladed stance, slight breathing sway |
| `fire` | yes | 0.3 s | 10 | `aim` plus one recoil cycle: 35 mm push back and 4° muzzle rise, peaking at 0.036 s, then recovery |
| `crouch_fire` | yes | 0.3 s | 10 | Kneeling: right knee pad on the ground, toes tucked, left foot planted. Same recoil cycle. |
| `die` | **no** | 1.5 s | 46 | Hit reaction, knees buckle, drops to the knees, falls face down with the head turned. The rifle ends flat on the ground in the right hand. Still from about 1.25 s. |

**Stride (root-motion-free).** The hips stay over the origin and the stance foot slides backward at the locomotion speed. To avoid foot sliding, set the playback rate to `speed / stride`.

| Clip | Stride per cycle | Matching speed |
|---|---|---|
| `walk` | 1.40 m | 1.4 m/s |
| `run` | 3.15 m | 4.5 m/s |

- These figures are at model scale 1.0. At the game's 1.3x infantry scale, multiply them by 1.3: walk stride 1.82 m at 1.82 m/s, run stride 4.10 m at 5.85 m/s.
- For example, a unit moving at `unit_defs` speed 4.5 m/s while drawn at 1.3x should play `run` at 4.5 / 4.095 ≈ 1.10x.
- I measured this on the re-imported GLB: flat-stance foot speed was 1.34–1.40 m/s for walk and 4.41–4.50 m/s for run. The lower values are frames at the edge of stance where the leg reach clamps by about 2 mm.

## Verification (all in Blender; source: `rifleman_report.json` plus re-import scripts)
- **Ground contact.** I took the lowest point of the deformed mesh on every frame:

  | Action | Body | Rifle |
  |---|---|---|
  | `idle`, `aim`, `fire` | exactly 0 mm (feet planted flat) | above ground |
  | `walk` | -1.4 to 0 mm | above ground |
  | `run` | -1.8 to +67 mm | above ground |
  | `crouch_fire` | -2.9 mm (knee pad and toe on the ground) | above ground |
  | `die` | -4.5 mm worst, -1.3 mm on the final frame | -4.7 mm worst |

  The `die` clip is kept on the ground by a solver that lifts the hips and raises the muzzle frame by frame.
- **IK reach error** (target the limb could not reach):

  | Limb | Worst | Where |
  |---|---|---|
  | Right hand | 0 mm | All actions; it is driven by the rifle |
  | Left hand on the handguard | 9.5 mm | `run` (6.2 mm in `walk`, 1.7 mm in `idle`) |
  | Legs | 2.2 mm | `walk` |
  | Legs | 98 mm | `die` final pose; the legs simply lie fully extended |

- **GLB structure** (parsed directly):
  - One skin with 17 joints and seven animations with the exact names above.
  - Channels are translation and rotation (plus constant scale).
  - Materials and the embedded image are as listed.
- **Round-trip.** The GLB was re-imported into Blender and the close-up frames were re-rendered from it (aim cheek weld, kneel, die transition, hands at rest and in the run).

## Known shortcomings
1. **Style and detail.** The body is built from primitives: blocky boxes and lofts, a boxy deltoid and shoulder line, no sculpted anatomy, and a simple face with no facial rig. It reads well at RTS zoom but is clearly low-poly in close-up.
2. **Hands.** Hands are rigid glove blocks with no finger bones. At the wrist, the arm twist and the rifle-driven hand rotation can disagree, which shows as a small seam at the cuff.
3. **Loop flags.** These must be set in Godot. The names are exactly as specified, so Godot's `-loop` / `_loop` name heuristic does not apply. Set `loop_mode = LINEAR` for every clip except `die` (import settings or code).
4. **Material override.** `godot/scripts/unit_art.gd` `UnitArt.apply()` replaces every surface material from a palette keyed by material name. `SA_Camo` and `SA_CamoGear` are not in that palette, so they would fall back to `SA_Paint` and the camo texture would be lost. The integrator must keep the imported materials or extend the shader path. I did not touch scripts, per the boundaries.
5. **UV seams.** The camo UVs are box-projected, so the pattern breaks where the projection axis changes. It is not visible at game zoom.
6. **Lighting in previews.** Previews are Blender Cycles renders, not Godot's renderer or unit shader. There is no baked AO.
7. **Left hand slip.** The left hand can sit up to about 1 cm off the handguard at peak run bounce. In `die`, it lets go of the rifle by design.
8. **Single death.** `die` is one fall direction (forward). There are no prone, crawl, reload or hit-react clips.
9. **No root bone.** There is no separate ground "root" bone; `Hips` is the root, as specified. All clips are in place.
