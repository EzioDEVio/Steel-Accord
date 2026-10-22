"""Steel Accord M2 - HMMWV family 3D (bpy 5.x): hmmwv, hmmwv_50cal, hmmwv_tow, hmmwv_medical.
Pipeline: tools/art/vehkit.py (M88 method: silhouette-fitted geometry + projected concept art).

Run:  python3 tools/art/veh_hmmwv_3d.py <id> [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/<id>/<id>.glb (+ <id>_albedo.png inspectable copy)

Body = exact boolean intersection of the concept side silhouette (auto-traced, wheel discs removed, roof
equipment clipped off) and a hand-measured plan outline from the top view. Pixel coordinates below are in the
side image AFTER the nose-left flip (vehkit.load_refs flips side views whose manifest says faces=right).
"""
import math

import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
from vehkit import Part, PI  # noqa: E402


def body_and_wheels(ctx, V):
    """Common chassis: Hull (body + bumpers + lights + mirrors) and 4 wheels (left authored)."""
    S, T, mat, o = ctx.S, ctx.T, ctx.mat, ctx.objs
    fw, rw = V["front_wheel"], V["rear_wheel"]
    r_px = V["wheel_r_px"]
    wheels = V.get("wheels", [("FL", fw), ("RL", rw)])
    discs = [(p[0], p[1], r_px + V.get("arch_pad", 5)) for _, p in wheels]
    poly = vk.silhouette_poly(ctx.refs["side"], V["body_clip"], discs=discs, open_px=V.get("open_px", 3),
                              tol=1.2, extra_remove=V.get("remove", ()))
    side_yz = [S(px, py) for px, py in poly]
    plan = [T(px, py) for px, py in V["plan"]]
    body = vk.vhull("Hull", side_yz, plan, (-0.1, 4.0), (-2.0, 2.0), mat=None, bevel=0.012)
    H = Part("HullDetail")
    hw = V["half_w"]
    # bumpers
    fb = V["front_bumper"]           # (px0, px1, py0, py1)
    H.box((0, (S.y(fb[0]) + S.y(fb[1])) / 2, (S.z(fb[2]) + S.z(fb[3])) / 2),
          (2 * hw * 0.97, abs(S.y(fb[0]) - S.y(fb[1])), abs(S.z(fb[2]) - S.z(fb[3]))))
    rb = V["rear_bumper"]
    H.box((0, (S.y(rb[0]) + S.y(rb[1])) / 2, (S.z(rb[2]) + S.z(rb[3])) / 2),
          (2 * hw * 0.95, abs(S.y(rb[0]) - S.y(rb[1])), abs(S.z(rb[2]) - S.z(rb[3]))))
    # headlights / tail lights
    yf = S.y(V["nose_px"]); yr = S.y(V["tail_px"])
    for s in (-1, 1):
        H.cyl((s * (hw - 0.25), yf + 0.01, S.z(V["headlight_py"])), 0.08, 0.06, (PI / 2, 0, 0), seg=12)
        H.box((s * (hw - 0.12), yr - 0.02, S.z(V["taillight_py"])), (0.12, 0.05, 0.14))
    # mirrors on arms at the A-pillars
    if V.get("mirror"):
        mpx, mpy = V["mirror"]
        for s in (-1, 1):
            H.box((s * (hw + 0.17), S.y(mpx), S.z(mpy)), (0.05, 0.08, 0.24))
            H.beam((s * (hw - 0.02), S.y(mpx) + 0.03, S.z(mpy) - 0.08), (s * (hw + 0.15), S.y(mpx), S.z(mpy) - 0.08),
                   0.03, 0.03)
    # chassis underside between the axles (frame rails, axles, diffs) so it is not see-through from low angles
    fy, ry_ = S.y(fw[0]), S.y(rw[0])
    wz = S.z(fw[1])
    H.box((0, (fy + ry_) / 2, wz + 0.15), (1.3, fy - ry_ + 0.6, 0.24))
    for y in [S.y(p[0]) for _, p in wheels]:
        H.cyl((0, y, wz), 0.07, 2 * V["wheel_x"] - 0.2, (0, PI / 2, 0), seg=8)
        H.box((0, y, wz), (0.4, 0.35, 0.3))
    # common HMMWV details: grille slats, brush-guard tubes, rocker steps, tow shackles, hood vents
    for k in range(7 if V.get("hmmwv_details", True) else 0):
        H.box(((k - 3) * 0.13, yf + 0.03, S.z(V["headlight_py"]) - 0.02), (0.05, 0.04, 0.3))
    for s in ((-1, 1) if V.get("hmmwv_details", True) else ()):
        H.rod((s * 0.55, yf + 0.12, S.z(fb[3]) + 0.02), (s * 0.55, yf + 0.12, S.z(V["headlight_py"]) + 0.2), 0.025)
        H.cyl((s * 0.62, yf + 0.06, S.z(fb[3]) + 0.06), 0.045, 0.06, (0, PI / 2, 0), seg=10)
        H.box((s * (hw + 0.03), (fy + ry_) / 2, S.z(V.get("rocker_py", fw[1] - 5))), (0.08, fy - ry_ - 1.2, 0.05))
        H.cyl((s * (hw - 0.3), yr - 0.04, S.z(rb[3]) + 0.07), 0.04, 0.06, (PI / 2, 0, 0), seg=8)
    if V.get("hmmwv_details", True):
        H.rod((-0.95, yf + 0.12, S.z(V["headlight_py"]) + 0.2), (0.95, yf + 0.12, S.z(V["headlight_py"]) + 0.2), 0.025)
    for fn in V.get("hull_extra", []):
        fn(H, S, T)
    det = H.build(mat, bevel=0.0)
    vk.join_objs(body, [det])
    body.data.materials.clear(); body.data.materials.append(mat)
    o["Hull"] = body
    # wheels (left authored; right are UV-sharing mirrors made after unwrapping)
    r = r_px * S.s * V.get("wheel_scale", 1.04)        # concept tyres read ~4% larger than the arch fit
    for suf, (px, py) in wheels:
        P = vk.tyre_part(f"Wheel{suf}", r, V["tyre_w"], r * V.get("rim_frac", 0.55), seg=V.get("tyre_seg", 34))
        o[f"Wheel{suf}"] = P.build(mat, bevel=0.0, smooth=50, location=(-V["wheel_x"], S.y(px), r))
    return [f"Wheel{suf}" for suf, _ in wheels], r


def post_uv_wheels(objs, left=("WheelFL", "WheelRL"), steer=("FL", "FR")):
    for n in left:
        rn = n[:-1] + "R"
        objs[rn] = vk.mirror_copy_x(objs[n], rn)
    for suf in steer:
        for side in "LR":
            w = objs[f"Wheel{suf}{side}"]
            e = vk.empty(f"Steer{suf}{side}", w.location)
            vk.parent_to(w, e)
            objs[f"Steer{suf}{side}"] = e


# ======================================================================== hmmwv_50cal
def turret_50cal(ctx, V):
    S, T, mat, o = ctx.S, ctx.T, ctx.mat, ctx.objs
    ring = V["ring"]                                  # (x, y, z) yaw axis on the roof
    Tp = Part("Turret")
    rx, ry, rz = ring
    Tp.cyl((rx, ry, rz + 0.06), 0.66, 0.12, seg=24)                 # gun ring
    Tp.cyl((rx, ry, rz + 0.13), 0.56, 0.04, seg=24)
    # ballistic shields arranged around the ring (front taller), open at the rear
    z0 = rz + 0.12
    zf, zm, zr = V.get("shield_z", (S.z(25), S.z(42), S.z(50)))
    k = V.get("shield_r", 1.0)
    for ang, w, ztop, rad in ((0, 0.62, zf, 0.68), (40, 0.62, zm, 0.76), (-40, 0.62, zm, 0.76),
                              (90, 0.5, zm, 0.72), (-90, 0.5, zm, 0.72),
                              (138, 0.6, zr, 0.76), (-138, 0.6, zr, 0.76)):
        w, rad = w * k, rad * k
        a = math.radians(ang)
        c = (rx + rad * math.sin(a), ry + rad * math.cos(a), (z0 + ztop) / 2)
        Tp.box(c, (w, 0.05, ztop - z0), (0, 0, -a))
        Tp.box((c[0] + 0.03 * math.sin(a), c[1] + 0.03 * math.cos(a), ztop - 0.25), (w * 0.5, 0.03, 0.14), (0, 0, -a))
    # pintle post + cradle
    gy, gz = V["trunnion"]
    Tp.cyl((rx, gy - 0.05, (z0 + gz) / 2 - 0.05), 0.05, gz - z0 - 0.1, seg=10)
    Tp.box((rx, gy, gz - 0.12), (0.22, 0.2, 0.1))
    tur = Tp.build(mat, bevel=0.0)
    vk.set_origin(tur, ring)
    o["Turret"] = tur
    G = Part("Gun")
    G.box((0, gy + 0.08, gz), (0.16, 0.46, 0.17))                   # receiver
    G.box((0, gy - 0.2, gz - 0.02), (0.18, 0.12, 0.12))             # back plate / spade grips
    G.box((-0.16, gy + 0.05, gz - 0.06), (0.14, 0.26, 0.17))        # ammo can (left)
    my = V["muzzle_y"]
    G.cyl((0, (gy + 0.31 + gy + 0.6) / 2, gz), 0.045, 0.29, (PI / 2, 0, 0), seg=10)   # barrel jacket
    G.cyl((0, (gy + 0.6 + my) / 2, gz), 0.028, my - gy - 0.6, (PI / 2, 0, 0), seg=8)
    G.cyl((0, my - 0.05, gz), 0.04, 0.1, (PI / 2, 0, 0), seg=8)
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, (0, gy, gz))
    vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (0, my + 0.01, gz), parent=gun)
    tm = Part("TeamTurret")
    tm.box((rx, ry + 0.68 * k + 0.03, zf - 0.07), (0.6 * k, 0.02, 0.1))
    ctx.team.append(("Turret", tm))
    return ["Turret", "Gun"]


def V_50cal():
    S = vk.SideFrame(4.6 / 784.0, 404.0, 437.0)
    T = vk.TopFrame(4.6 / 717.0, 216.5, 370.5, sx=1.0)
    ring = (0.0, -0.15, S.z(126))
    V = dict(
        S=S, T=T, front_wheel=(119, 360), rear_wheel=(642, 360), wheel_r_px=76, arch_pad=6,
        body_clip=(0, 118, 814, 452), remove=((744, 80, 766, 168), (744, 324, 766, 420)),  # rear antenna rod above / below the body
        plan=[(60, 14), (372, 14), (397, 60), (397, 170), (388, 200), (388, 700), (380, 729), (53, 729),
              (45, 700), (45, 200), (36, 170), (36, 60)],
        half_w=T.x(388), wheel_x=1.05, tyre_w=0.33, nose_px=12, tail_px=797, headlight_py=255, taillight_py=230,
        front_bumper=(8, 40, 292, 322), rear_bumper=(770, 800, 300, 322), mirror=(212, 190),
        ring=ring, trunnion=(S.y(395), S.z(30)), muzzle_y=S.y(146),
        hull_extra=[lambda H, S, T: H.cyl((-0.95, S.y(754), (S.z(375) + S.z(100)) / 2), 0.015,
                                          S.z(100) - S.z(375), seg=6)],
        cams={"front34": 40.0, "rear34": -140.0},
        top_patch=[((300, 388, 400, 416), -30)],
        hull_extra2=True,      # concept top view: M2 drawn traversed right across the roof
        team_strips=[(S.y(700), S.y(790), S.z(195))],
        preview=dict(length=4.9, width=2.5, height=2.6, rts_dist=12, close_dist=9, close_az=-40),
        turret=turret_50cal,
    )
    return V


# ======================================================================== avenger (HMMWV with pedestal SAM turret)
def turret_avenger(ctx, V):
    S, T, mat, o = ctx.S, ctx.T, ctx.mat, ctx.objs
    ring = V["ring"]
    rx, ry, rz = ring
    Tp = Part("Turret")
    Tp.cyl((rx, ry, rz + 0.04), 0.62, 0.08, seg=24)                         # slew ring on the cargo bed
    Tp.cyl((rx, ry, (rz + S.z(182)) / 2), 0.42, S.z(182) - rz, seg=20)      # pedestal
    # gunner's cab between the pods (side px 380..490, py 50..182)
    y0, y1 = S.y(380), S.y(490)
    Tp.box((rx, (y0 + y1) / 2, (S.z(182) + S.z(52)) / 2), (0.9, y0 - y1, S.z(52) - S.z(182)))
    Tp.box((rx, y0 + 0.02, S.z(110)), (0.7, 0.04, 0.32))                    # front window frame
    Tp.box((rx + 0.1, (y0 + y1) / 2, S.z(52) + 0.05), (0.5, 0.5, 0.1))      # roof sight
    # .50 cal on the right side of the cab
    Tp.box((0.62, y0 - 0.1, S.z(170)), (0.16, 0.5, 0.14))
    Tp.cyl((0.62, y0 + 0.5, S.z(170)), 0.025, 0.7, (PI / 2, 0, 0), seg=6)
    tur = Tp.build(mat, bevel=0.0)
    vk.set_origin(tur, ring)
    o["Turret"] = tur
    # missile pods (elevate together = Gun), trunnion through the cab
    tz = S.z(102)
    ty = ry
    G = Part("Gun")
    py0, py1 = S.y(312), S.y(620)
    zb, zt = S.z(140), S.z(65)
    for s in (-1, 1):
        xc = s * 0.95
        G.box((xc, (py0 + py1) / 2, (zb + zt) / 2), (0.68, py0 - py1, zt - zb))
        G.box((xc, py0 + 0.03, (zb + zt) / 2), (0.72, 0.06, zt - zb + 0.04))     # front frame
        G.box((xc, py1 - 0.03, (zb + zt) / 2), (0.72, 0.06, zt - zb + 0.04))     # rear frame
        for k in range(4):
            G.box((xc, py0 - 0.35 - k * 0.45, zt + 0.015), (0.6, 0.06, 0.03))      # top straps
        for i in (-1, 1):
            for j in (-1, 1):
                G.cyl((xc + i * 0.15, py0 + 0.05, (zb + zt) / 2 + j * 0.11), 0.095, 0.06, (PI / 2, 0, 0), seg=16)
                G.cyl((xc + i * 0.15, py0 + 0.08, (zb + zt) / 2 + j * 0.11), 0.06, 0.02, (PI / 2, 0, 0), seg=12)
        G.box((s * 0.56, ty, tz), (0.16, 0.4, 0.4))                          # trunnion arms
    gun = G.build(mat, bevel=0.0)
    vk.set_origin(gun, (0, ty, tz))
    vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (-0.95, py0 + 0.1, (zb + zt) / 2), parent=gun)
    tm = Part("TeamTurret")
    for s in (-1, 1):
        tm.box((s * 1.30, (py0 + py1) / 2, zt - 0.08), (0.02, (py0 - py1) * 0.6, 0.1))
    ctx.team.append(("Gun", tm))
    return ["Turret", "Gun"]


def V_avenger():
    S = vk.SideFrame(4.95 / 745.0, 387.5, 479.0)
    # concept top view is compressed in length and disagrees with the side view; rectify through
    # nose, windshield, pod front, pod rear, hull rear (turret placement follows the side view)
    T = vk.TopFrame(4.95 / 475.0, 206.0, 252.5, sx=0.70,
                    ymap=[(15, S.y(15)), (207, S.y(255)), (310, S.y(312)), (490, S.y(620)), (521, S.y(760))])
    ring = (0.0, (S.y(312) + S.y(620)) / 2, S.z(292))
    return dict(
        S=S, T=T, front_wheel=(115, 404), rear_wheel=(628, 404), wheel_r_px=75, arch_pad=6,
        body_clip=(0, 184, 789, 491),
        plan=[(60, 15), (352, 15), (359, 60), (359, 500), (352, 521), (60, 521), (53, 500), (53, 60)],
        half_w=T.x(359), wheel_x=1.02, tyre_w=0.34, nose_px=15, tail_px=762, headlight_py=312,
        taillight_py=300, front_bumper=(12, 48, 362, 392), rear_bumper=(735, 766, 352, 378), mirror=(255, 268),
        ring=ring, cams={"front34": -40.0, "rear34": -140.0},
        team_strips=[(S.y(560), S.y(740), S.z(300))],
        preview=dict(length=5.2, width=2.6, height=3.2, rts_dist=13, close_dist=10, close_az=-40),
        turret=turret_avenger,
        notes=["Avenger: concept top view is ~25% short and pods sit further aft than in the side view -> "
               "top projection rectified piecewise in Y (side view wins for geometry); width squeezed (sx 0.70) "
               "to 2.23 m."],
    )


# ======================================================================== hmmwv_tow
def turret_tow(ctx, V):
    S, T, mat, o = ctx.S, ctx.T, ctx.mat, ctx.objs
    rx, ry, rz = V["ring"]
    Tp = Part("Turret")
    Tp.cyl((rx, ry, rz + 0.05), 0.6, 0.1, seg=24)                               # roof ring
    Tp.cyl((rx, ry, (rz + S.z(118)) / 2), 0.09, S.z(118) - rz, seg=10)          # pedestal (side px 420..520)
    Tp.box((rx, ry, S.z(118)), (0.3, 0.34, 0.12))                               # traversing head
    for s in (-1, 1):                                                           # low gunner shields
        Tp.box((rx + s * 0.55, ry + 0.25, rz + 0.3), (0.04, 0.6, 0.45), (0, 0, s * 0.35))
    Tp.box((rx, ry + 0.62, rz + 0.3), (0.7, 0.04, 0.45))
    tur = Tp.build(mat, bevel=0.0)
    vk.set_origin(tur, (rx, ry, rz))
    o["Turret"] = tur
    gy, gz = V["trunnion"]
    y0, y1 = V["tube_y"]
    G = Part("Gun")
    vk.lathe(G, (rx, 0, gz + 0.06), [(y1, 0.15), (y1 + 0.12, 0.17), (y0 - 0.15, 0.17), (y0 - 0.1, 0.15),
                                     (y0, 0.15)], seg=16, axis="y")            # launch tube
    G.box((rx, gy + 0.3, gz - 0.16), (0.36, 0.5, 0.26))                        # sight / guidance box
    G.cyl((rx + 0.12, gy + 0.56, gz - 0.12), 0.07, 0.04, (PI / 2, 0, 0), seg=12)
    G.box((rx, gy - 0.25, gz - 0.2), (0.3, 0.3, 0.2))                          # traverse unit / grips
    G.box((rx, gy, gz - 0.05), (0.14, 0.2, 0.2))
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, (rx, gy, gz)); vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (rx, y0 + 0.02, gz + 0.06), parent=gun)
    tm = Part("TeamTurret")
    tm.box((rx, ry + 0.645, rz + 0.45), (0.5, 0.02, 0.1))
    ctx.team.append(("Turret", tm))
    return ["Turret", "Gun"]


def V_tow():
    S = vk.SideFrame(4.6 / 772.0, 399.0, 450.0)
    T = vk.TopFrame(4.6 / 663.0, 231.5, 344.5, sx=0.83)

    def extra(H, S, T):
        H.cyl((0, S.y(770), S.z(260)), 0.4, 0.26, (PI / 2, 0, 0), seg=24)           # spare tyre on the tailgate
        H.cyl((0, S.y(770) - 0.14, S.z(260)), 0.2, 0.04, (PI / 2, 0, 0), seg=14)
    return dict(
        S=S, T=T, front_wheel=(117, 373), rear_wheel=(620, 373), wheel_r_px=77, arch_pad=6,
        body_clip=(0, 141, 803, 464), open_px=3,
        plan=[(100, 13), (360, 13), (421, 50), (423, 590), (378, 640), (340, 676), (160, 676), (96, 640), (40, 590),
              (41, 50)],
        half_w=T.x(423), wheel_x=1.0, tyre_w=0.32, nose_px=14, tail_px=788, headlight_py=272, taillight_py=292,
        front_bumper=(12, 40, 318, 346), rear_bumper=(750, 785, 325, 347), mirror=(225, 205),
        ring=(0.0, S.y(470), S.z(141)), trunnion=(S.y(470), S.z(70)), tube_y=(S.y(310), S.y(615)),
        hull_extra=[extra],
        cams={"front34": -40.0, "rear34": -140.0},
        team_strips=[(S.y(640), S.y(740), S.z(200))],
        preview=dict(length=4.9, width=2.5, height=2.8, rts_dist=12, close_dist=9, close_az=-40),
        turret=turret_tow,
        notes=["HMMWV TOW: Gun = launch tube + sight (pitch); Muzzle at the tube mouth. Width squeezed sx 0.83 "
               "(concept top view 2.66 m)."],
    )


# ======================================================================== hmmwv (base troop carrier, soft top)
def base_extra(H, S, T):
    hw = T.x(266)
    for px in (300, 420, 540, 660, 780):                       # canvas bows / tie-down straps over the soft top
        H.box((0, S.y(px), S.z(16) + 0.01), (2 * hw * 0.98, 0.05, 0.03))
        for s in (-1, 1):
            H.box((s * (hw + 0.005), S.y(px), S.z(60)), (0.02, 0.05, S.z(16) - S.z(105)))
    H.cyl((-0.85, S.y(248), (S.z(18) + S.z(170)) / 2), 0.04, S.z(18) - S.z(170), seg=8)   # snorkel/antenna mast
    for s in (-1, 1):
        H.box((s * 0.6, S.y(858) - 0.04, S.z(205)), (0.5, 0.06, 0.1))   # tailgate hinges / latches
def V_base():
    S = vk.SideFrame(4.6 / 845.0, 435.0, 365.0)
    T = vk.TopFrame(4.6 / 493.0, 152.0, 259.5)
    return dict(
        S=S, T=T, front_wheel=(117, 281), rear_wheel=(715, 281), wheel_r_px=84, arch_pad=6,
        body_clip=(0, 0, 873, 379), open_px=3,
        plan=[(45, 13), (262, 13), (274, 60), (274, 180), (266, 200), (266, 500), (258, 506), (46, 506), (38, 500),
              (38, 200), (31, 180), (31, 60)],
        half_w=T.x(266), wheel_x=0.98, tyre_w=0.32, nose_px=14, tail_px=858, headlight_py=170, taillight_py=180,
        front_bumper=(13, 40, 222, 250), rear_bumper=(838, 862, 222, 250), mirror=(245, 110),
        cams={"front34": -40.0, "rear34": -140.0},
        team_strips=[(S.y(740), S.y(840), S.z(150))],
        preview=dict(length=4.9, width=2.4, height=2.3, rts_dist=11, close_dist=8.5, close_az=-40),
        turret=None, tyre_seg=40, hull_extra=[base_extra],
        notes=["HMMWV base: soft-top troop carrier, no weapon -> no Turret/Gun/Muzzle nodes."],
    )


# ======================================================================== hmmwv_medical (ambulance; red crosses removed)
def med_extra(H, S, T):
    H.box((0.0, S.y(640), S.z(24) + 0.1), (0.9, 0.6, 0.24))          # roof air-conditioning unit (rear)
    H.box((0.0, S.y(640), S.z(24) + 0.23), (0.7, 0.45, 0.04))
    for s in (-1, 1):
        H.box((s * 0.75, S.y(762) - 0.05, S.z(20) - 0.05), (0.3, 0.1, 0.1))     # rear marker / flood lights
        H.box((s * 0.55, S.y(762) - 0.02, S.z(150)), (0.03, 0.04, 1.0))         # rear door hinges
        H.box((s * (T.x(313) + 0.02), S.y(300), S.z(40)), (0.04, 0.12, 0.1))   # side marker lights
    H.box((0, S.y(770), S.z(300)), (1.2, 0.3, 0.05))                  # rear step
def neutralise_red_emblems(ref, min_px=1000):
    """Replace large saturated-red regions (protected red-cross emblem in the concept) with the surrounding
    white panel colour. Returns the bounding boxes that were neutralised."""
    from scipy import ndimage
    rgb = ref["rgb"]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = (r > 0.3) & (r > 1.7 * g) & (r > 1.7 * b) & ref["a_full"]
    m = ndimage.binary_closing(m, iterations=2)
    lab, n = ndimage.label(m)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        reg = lab[sl] == i + 1
        if reg.sum() < min_px:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        pad = 6
        Y0, Y1, X0, X1 = max(y0 - pad, 0), y1 + pad, max(x0 - pad, 0), x1 + pad
        box = rgb[Y0:Y1, X0:X1]
        mm = ndimage.binary_dilation(lab[Y0:Y1, X0:X1] == i + 1, iterations=3)
        lum = box.mean(-1)
        white = box[(~mm) & (lum > np.percentile(lum[~mm], 60))]
        col = np.median(white, 0) if len(white) else np.array([0.85, 0.85, 0.82])
        box[mm] = col
        boxes.append((x0, y0, x1, y1))
    return boxes


def V_medical():
    S = vk.SideFrame(5.1 / 757.0, 391.5, 383.0)
    T = vk.TopFrame(5.1 / 575.0, 179.5, 299.5, sx=0.92)

    def team(th, S, T):
        # plain team-colour squares where the concept had red crosses (sides, roof, rear doors)
        cy, cz = S.y(582), S.z(145)
        for s in (-1, 1):
            th.box((s * (T.x(313) + 0.012), cy, cz), (0.02, 0.42, 0.42))
        rx, ry = T(178, 381)
        th.box((rx, ry, S.z(21) + 0.012), (0.55, 0.55, 0.02))
        th.box((0, S.y(762) - 0.012, S.z(150)), (0.4, 0.02, 0.4))

    return dict(
        S=S, T=T, front_wheel=(117, 306), rear_wheel=(602, 306), wheel_r_px=76, arch_pad=6,
        body_clip=(0, 0, 781, 395), open_px=3,
        plan=[(52, 12), (306, 12), (321, 40), (321, 160), (313, 200), (313, 580), (305, 587), (54, 587), (46, 580),
              (46, 200), (38, 160), (38, 40)],
        half_w=T.x(313), wheel_x=1.0, tyre_w=0.33, nose_px=13, tail_px=765, headlight_py=215, taillight_py=235,
        front_bumper=(12, 38, 250, 278), rear_bumper=(745, 772, 262, 285), mirror=(215, 125),
        cams={"front34": -40.0, "rear34": -140.0},
        team_strips=[], team_extra=[team], emblem_fix=True,
        preview=dict(length=5.4, width=2.5, height=2.9, rts_dist=12, close_dist=9.5, close_az=-40),
        turret=None, tyre_seg=40, hull_extra=[med_extra],
        notes=["HMMWV ambulance: the concept's red-cross emblems (protected emblem) were removed from all four "
               "projection sources (replaced by the surrounding white panel colour) and replaced by plain SA_Team "
               "squares on both sides, the roof and the rear doors. No weapon -> no Turret/Gun/Muzzle."],
    )


VARIANTS = {"hmmwv_50cal": V_50cal, "avenger": V_avenger, "hmmwv_tow": V_tow, "hmmwv": V_base,
            "hmmwv_medical": V_medical}
TITLES = {"avenger": "Avenger air-defence (HMMWV)", "hmmwv_50cal": "HMMWV with .50 cal gun ring", "hmmwv": "HMMWV troop carrier",
          "hmmwv_tow": "HMMWV TOW launcher", "hmmwv_medical": "HMMWV ambulance (neutral markings)"}


def main(vid=None, V=None, title=None):
    if vid is None:
        vid = next(a for a in sys.argv[1:] if not a.startswith("--") and a in VARIANTS)
    argv = [a for a in sys.argv[1:] if a != vid]
    V = V or VARIANTS[vid]()
    title = title or TITLES[vid]

    def build(ctx):
        if V.get("emblem_fix"):
            for k in ("side", "top", "front34", "rear34"):
                bx = neutralise_red_emblems(ctx.refs[k])
                print(f"  emblem neutralised in {k}: {bx}")
        for rect, dy in V.get("top_patch", []):
            vk.patch_copy(ctx.refs["top"], rect, dy=dy)
        for rect, dy in V.get("side_patch", []):
            vk.patch_copy(ctx.refs["side"], rect, dy=dy)
        wheels, r = body_and_wheels(ctx, V)
        tnames = V["turret"](ctx, V) if V.get("turret") else []
        th = Part("TeamHull")
        for y0, y1, z in V.get("team_strips", []):
            for s in (-1, 1):
                th.box((s * (V["half_w"] + 0.012), (y0 + y1) / 2, z), (0.02, abs(y0 - y1), 0.1))
        for fn in V.get("team_extra", []):
            fn(th, ctx.S, ctx.T)
        ctx.team.append(("Hull", th))
        hubs = {n: (ctx.objs[n].location.y, ctx.objs[n].location.z, r - 0.06) for n in wheels}
        gun_names = [n for n in ("Gun",) if n in ctx.objs] + V.get("side_only", [])
        steer = V.get("steer", ("F",))
        roots = ["Hull"] + [n for n in ("Turret",) if n in tnames]
        for wn in wheels:
            suf = wn[5:-1]
            roots += [f"Steer{suf}L", f"Steer{suf}R"] if suf in steer else [f"Wheel{suf}L", f"Wheel{suf}R"]
        roots += V.get("extra_roots", [])
        return dict(uv=["Hull"] + tnames + V.get("extra_uv", []) + wheels,
                    post_uv=lambda objs: post_uv_wheels(objs, wheels, steer), tracks=None,
                    roots=roots, cams=V["cams"],
                    cfg=dict(mud_h=0.8, hubs=hubs, hub_period=36.0, side_only=gun_names),
                    preview=V["preview"],
                    extra=[f"wheel radius {r:.3f} m, tyre width {V['tyre_w']} m, wheel track x +-{V['wheel_x']}"]
                    + V.get("notes", []))

    vk.run_vehicle(vid, V["S"], V["T"], build, f"Steel Accord M2 - {title} - Cycles CPU preview", argv=argv)


if __name__ == "__main__":
    main()
