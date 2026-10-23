"""Steel Accord - Iran wave 1: Shahed-136-style delta-wing loitering munition + its launch rail (bpy 5.x).

Run:  python3 -I tools/art/air_ir_shahed_3d.py [out_dir_root] [--no-previews] [--quick]
Out:  godot/assets/units3d/ir_shahed/ir_shahed.glb (+ ir_shahed_albedo.png, ir_shahed_prop.png)
      godot/assets/units3d/ir_shahed_rail/ir_shahed_rail.glb (+ ir_shahed_rail_albedo.png)
      docs/screens/ir_shahed_sheet.png, docs/screens/ir_shahed_rail_sheet.png (rail shown with the drone mounted)

Reference: iran_pack/02_aircraft_and_uav_catalog.png panel 12 (perspective concept: light-grey cropped delta with
tip fins on an inclined steel launch frame, olive box beside it). Authored at real-world size: drone 3.5 m
long, 2.5 m span; rail ~4.6 m inclined 20 deg.
Drone nodes: Body (fuselage, wing, tip fins, SA_Team fin caps), Prop0 (2-blade pusher, origin = hub, shaft = local
Z in Godot). Origin = lowest point (lower tip fins) under the midpoint, as for the other aircraft.
Rail nodes: Body (frame, base, crate, SA_Team crate stripe), Mount (empty: place the drone's origin here with this
node's rotation; it is pitched nose-up 20 deg about local X so the drone sits on the rails pointing up-range +Y).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402

K, L = A.K, A.L
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

ID = "ir_shahed"
RID = "ir_shahed_rail"
ZC = 0.25                      # fuselage axis / wing plane height above the drone origin
Y_NOSE, Y_TAIL = 1.75, -1.48
X_TIP = 1.25
PROP_Y = -1.62
PITCH = math.radians(20)


def build_drone(mat):
    objs = {}
    F = K.Part("Airframe")
    K.body_rev(F, (0, Y_TAIL, ZC), (0, 1.35, ZC), [(0, 0.10), (0.06, 0.15), (0.2, 0.18), (0.8, 0.18), (1, 0.17)], seg=20,
               squash=0.85)
    # cropped delta wing, blended into the body
    secs = [((0.12, 1.25, ZC), (0.12, -1.38, ZC), 0.045, (0, 0, 1)),
            ((0.55, 0.30, ZC), (0.55, -1.36, ZC), 0.05, (0, 0, 1)),
            ((X_TIP, -0.98, ZC), (X_TIP, -1.34, ZC), 0.06, (0, 0, 1))]
    K.surface(F, K.mirror_sections(secs[1:]) + secs)
    # tip fins (up and down)
    for sg in (-1, 1):
        A.fin(F, (-0.96, ZC - 0.22), (-1.36, ZC - 0.22), (-1.14, ZC + 0.28), (-1.40, ZC + 0.28), t_root=0.06, t_tip=0.06,
              x=sg * (X_TIP + 0.005))
    # engine cowl + exhaust stub
    K.body_rev(F, (0, PROP_Y + 0.08, ZC), (0, Y_TAIL + 0.05, ZC), [(0, 0.07), (0.5, 0.10), (1, 0.10)], seg=14)
    F.rod((0.08, -1.2, ZC + 0.12), (0.08, -1.5, ZC + 0.1), 0.025, seg=6)
    objs["air"] = F.build(mat, smooth=45)
    N = K.Part("Nose")
    K.body_rev(N, (0, 1.34, ZC), (0, Y_NOSE, ZC), [(0, 0.17), (0.35, 0.16), (0.7, 0.12), (0.9, 0.07), (1, 0.01)], seg=20,
               squash=0.85)
    objs["nose"] = N.build(mat, smooth=60)
    Tm = K.Part("Team")
    for sg in (-1, 1):
        A.fin(Tm, (-1.135, ZC + 0.255), (-1.40, ZC + 0.255), (-1.15, ZC + 0.30), (-1.405, ZC + 0.30), t_root=0.075,
              t_tip=0.075, x=sg * (X_TIP + 0.005))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    return objs


def drone_painter():
    zones = [(lambda P, N: (np.abs(P[:, 0]) < 0.2) & (P[:, 1] < -1.25) & (P[:, 1] > -1.6), (0.26, 0.27, 0.27), ("air",))]
    return dict(scheme="light", camo_scale=1.5, flat={"nose": (0.88, 0.88, 0.86)}, zones=zones,
                panel=dict(dy=0.7, keys=("air",), k=0.9, w=0.008), seed=7, grime=0.05)


def rail_frame():
    """Rail geometry in world space. Returns (rail start, unit direction, mount point)."""
    p0 = Vector((0, -2.10, 0.55))
    d = Vector((0, math.cos(PITCH), math.sin(PITCH)))
    return p0, d


def build_rail(mat):
    objs = {}
    p0, d = rail_frame()
    up = Vector((0, -math.sin(PITCH), math.cos(PITCH)))
    Ln = 4.6
    F = K.Part("Frame")
    for sg in (-1, 1):
        a = p0 + Vector((sg * 0.25, 0, 0)); b = a + d * Ln
        F.beam(a, b, 0.08, 0.12)                                                    # rails
        F.beam(a + up * 0.08 + Vector((sg * 0.03, 0, 0)), b + up * 0.08 + Vector((sg * 0.03, 0, 0)), 0.02, 0.05)  # guide lip
        F.beam((sg * 0.9, -2.45, 0.06), (sg * 0.9, 2.45, 0.06), 0.12, 0.12)        # ground base beams
    for t in np.linspace(0.05, 0.95, 6):                                            # rail cross members
        c = p0 + d * (Ln * t) - up * 0.04
        F.beam(c + Vector((-0.29, 0, 0)), c + Vector((0.29, 0, 0)), 0.06, 0.06)
    for yb in (-2.35, 0.0, 2.35):
        F.beam((-0.96, yb, 0.06), (0.96, yb, 0.06), 0.1, 0.1)                       # base cross beams
    legs = []
    for t, spread in ((0.05, 0.9), (0.47, 0.9), (0.9, 0.9)):
        c = p0 + d * (Ln * t) - up * 0.06
        for sg in (-1, 1):
            top = c + Vector((sg * 0.25, 0, 0))
            foot = Vector((sg * spread, c.y, 0.12))
            F.beam(foot, top, 0.07, 0.07, up=(0, 1, 0))
            legs.append((foot, top))
    # diagonal braces between consecutive legs on each side, and an X between the front legs
    for sg in (-1, 1):
        side_legs = [lg for lg in legs if (lg[0].x > 0) == (sg > 0)]
        for (f0, t0), (f1, t1) in zip(side_legs[:-1], side_legs[1:]):
            F.beam(f0, t1 - (t1 - f1) * 0.15, 0.045, 0.045, up=(1, 0, 0))
    fl = [lg for lg in legs if abs(lg[0].y - legs[-1][0].y) < 1e-6]
    F.beam(fl[0][0], fl[1][1], 0.04, 0.04, up=(0, 1, 0)); F.beam(fl[1][0], fl[0][1], 0.04, 0.04, up=(0, 1, 0))
    # launch cradle (saddle the drone belly rests on), front stop pins
    mount_t = 0.55
    mc = p0 + d * (Ln * mount_t) + up * 0.08
    F.beam(mc - d * 0.5, mc + d * 0.5, 0.36, 0.06, up=tuple(up))
    objs["frame"] = F.build(mat, smooth=30)
    C = K.Part("Crate")
    C.box((-1.32, -1.95, 0.30), (0.56, 1.0, 0.48))
    C.box((-1.32, -1.95, 0.56), (0.60, 1.04, 0.05))                                 # lid
    for yy in (-2.3, -1.6):
        C.box((-1.32, yy, 0.30), (0.60, 0.05, 0.50))                                # stiffeners
    C.box((-1.32, -1.95, 0.04), (0.6, 1.04, 0.08))                                  # skid
    objs["crate"] = C.build(mat, smooth=30)
    Tm = K.Part("Team")
    Tm.box((-1.32, -1.95, 0.588), (0.62, 0.22, 0.012))
    objs["team"] = Tm.build(K.team_material(), smooth=30)
    # drone origin: belly (ZC - 0.18*0.85 below axis) on the cradle top
    belly = ZC - 0.18 * 0.85
    mount = mc + up * (0.03 - belly)
    return objs, {"Mount": {"loc": tuple(mount), "rot": (PITCH, 0, 0)}}


def rail_painter():
    steel = ((0.34, 0.35, 0.33), (0.30, 0.31, 0.29), (0.30, 0.31, 0.29), 0.3, 0.0)
    return dict(scheme=steel, camo_scale=1.0, flat={"crate": (0.30, 0.32, 0.20)}, seed=8, grime=0.25)


def main():
    o = A.parse_args(ID)
    root = os.path.dirname(o["out"]) if o["out"] != os.path.join(A.OUT3D, ID) else A.OUT3D
    o["out"] = os.path.join(root, ID); os.makedirs(o["out"], exist_ok=True)
    sheet_dir = os.path.dirname(o["sheet"])
    # ---------------- drone
    L.reset_scene()
    mat = L.image_material("SA_IR_SHAHED", None, rough=0.55)
    pmat = L.image_material("SA_IR_SHAHED_Prop", None, rough=0.6)
    objs = build_drone(mat)
    prop = K.rotor("Prop0", (0, PROP_Y, ZC), 2, 0.38, 0.075, pmat, root_r=0.06, axis="y", hub_r=0.05, coning=0,
                   twist=(28, 12), thick=0.018, paddle=True, phase=math.radians(15))
    ppng = os.path.join(o["out"], f"{ID}_prop.png")
    K.flat_texture((0.10, 0.10, 0.10), ppng)
    A.finish_ir(ID, o, mat, objs, {}, drone_painter(), ((-1.4, -1.9, -0.1), (1.4, 1.9, 0.7)), (3.5, 2.5, 0.6),
                "Steel Accord Iran wave 1 - Shahed-style loitering munition - Cycles CPU preview",
                extra_export=[prop], blade=(pmat, ppng, f"{ID}_prop"), cell=0.006, atlas=1024, ao_dist=0.25,
                prev_kw=dict(close_k=1.5))
    drone_glb = os.path.join(o["out"], f"{ID}.glb")
    # ---------------- rail
    L.reset_scene()
    ro = dict(o); ro["out"] = os.path.join(root, RID); os.makedirs(ro["out"], exist_ok=True)
    ro["sheet"] = os.path.join(sheet_dir, f"{RID}_sheet.png"); ro["prev"] = False
    rmat = L.image_material("SA_IR_SHAHED_RAIL", None, rough=0.7, metal=0.0)
    robjs, rem = build_rail(rmat)
    body, export = A.finish_ir(RID, ro, rmat, robjs, rem, rail_painter(), ((-1.8, -2.6, -0.1), (1.8, 2.6, 2.6)),
                               (5.0, 3.2, 2.6), "", cell=0.01, atlas=1024, ao_dist=0.3)
    if o["prev"]:
        mount = [e for e in export if e.name == "Mount"][0]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=drone_glb)
        for ob in set(bpy.data.objects) - before:
            if ob.parent is None:
                ob.matrix_world = mount.matrix_world @ ob.matrix_world
        A.preview_sheet(RID, "Steel Accord Iran wave 1 - Shahed launch rail (drone placed at Mount) - Cycles CPU preview",
                        5.0, 3.2, 2.6, ro["sheet"] if not o["quick"] else os.path.join(sheet_dir, f"{RID}_q.png"),
                        quick=o["quick"], close_k=1.5)
        print("IR_SHAHED_RAIL sheet", ro["sheet"])


if __name__ == "__main__":
    main()
