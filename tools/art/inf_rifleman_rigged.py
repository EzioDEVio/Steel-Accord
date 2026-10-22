"""Steel Accord - PILOT 3D infantry: rigged + animated U.S. Army rifleman (procedural, Blender bpy 5.x).

Run:  python3 inf_rifleman_rigged.py <out_dir> [--previews <screens_dir>]
Out:  <out_dir>/rifleman.glb  (one skinned body mesh + Armature + bone-parented rifle with a Muzzle empty, 7 actions)
      <out_dir>/rifleman_camo.png (the procedural tiling camouflage texture, also embedded in the GLB)
      with --previews: pilot3d_rifleman_{front,side,back,top,rts,anims}.png in <screens_dir>

Since M1 the body, gear, rig, pose solver, actions and exporter live in inf_kit.py (shared by every infantry role);
this file is the rifleman variant: the kit defaults ARE the approved rifleman, so the output is unchanged
(identical glTF JSON, vertex and animation data; see docs/M1_INFANTRY.md for the regression check).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inf_kit as K          # pins PYTHONHASHSEED (re-exec) before bpy is imported

OUT, PREV, ONLY_ANIMS = K.parse_args()
role = K.Role("rifleman", prev_prefix="pilot3d_rifleman", prev_views=("front", "side", "back", "top", "rts"))
report = K.build(role, OUT)
if PREV:
    K.previews(role, PREV, K.rifleman_actions(), only_anims=ONLY_ANIMS, legacy=True)
print("RIFLEMAN_RIGGED OK", report["triangles"])
