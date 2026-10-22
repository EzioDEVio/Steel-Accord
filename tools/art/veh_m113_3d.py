"""Steel Accord M2 - M113-style armoured personnel carrier, 3D (bpy 5.x). Pipeline: tools/art/vehkit.py.

Run:  python3 tools/art/veh_m113_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Measurements: m113_side.png (nose left; hull px 12..735 = 4.9 m; ground py 415), m113_top.png (hull py 15..680,
centre px 189). Turret = commander's cupola ring with shielded MG (yaw); Gun = MG (pitch).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
from vehkit import Part, PI  # noqa: E402

S = vk.SideFrame(4.9 / 723.0, 373.5, 415.0)
T = vk.TopFrame(4.9 / 665.0, 189.0, 347.5)
TRACK = vk.TrackSpec(track_x=1.12, width=0.38, thick=0.1, wheel_r=0.285,
                     wheel_ys=[S.y(px) for px in (167, 267, 362, 471, 575)],
                     sprocket=(S.y(62), 0.55, 0.22), idler=(S.y(683), 0.58, 0.21),
                     rollers=[(1.0, 0.74, 0.07), (-0.7, 0.74, 0.07)],
                     pitch=0.15, links_per_tile=6, wheel_w=0.11, wheel_gap=0.075, sprocket_teeth=10)
CUP = (T.x(210), T.y(310), S.z(118))
TRUNNION = (S.y(325), S.z(35))
MUZZLE_Y = S.y(150)


def build(ctx):
    mat, o, refs = ctx.mat, ctx.objs, ctx.refs
    hull_side = vk.silhouette_poly(refs["side"], (0, 120, 764, 283), discs=[(62, 333, 36), (683, 329, 34)],
                                   open_px=3, tol=1.2)
    plan = [T(px, py) for px, py in [(30, 15), (350, 15), (365, 35), (366, 660), (355, 680), (25, 680), (13, 660),
                                     (13, 35)]]
    hull = vk.vhull("Hull", [S(*p) for p in hull_side], plan, (-0.1, 4), (-2.5, 2.5), bevel=0.015)
    H = Part("HullDetail")
    H.side([S(30, 280), S(725, 280), S(715, 330), S(660, 352), S(110, 352), S(45, 320)], -0.92, 0.92)    # belly between tracks
    for s in (-1, 1):
        for (y, z, r) in TRACK.rollers:
            H.cyl((s * TRACK.track_x, y, z), r, 0.2, (0, PI / 2, 0), seg=10)
        H.box((s * 1.05, S.y(40), S.z(175)), (0.22, 0.14, 0.2))                         # headlight clusters
        H.cyl((s * 1.05, S.y(40) + 0.07, S.z(175)), 0.06, 0.04, (PI / 2, 0, 0), seg=10)
        H.box((s * 1.1, S.y(735) - 0.02, S.z(160)), (0.14, 0.05, 0.14))                    # tail lights
        H.box((s * 0.95, S.y(20), S.z(260)), (0.12, 0.12, 0.16))                           # tow eyes
    H.box((0, S.y(735) - 0.03, S.z(200)), (1.5, 0.06, S.z(130) - S.z(280)))               # rear ramp
    H.cyl((-0.8, S.y(175), (S.z(122) + S.z(108)) / 2 + 0.02), 0.03, 0.2, seg=6)           # periscope stub
    for s in (-1, 1):                                                                       # trim vane hinge
        H.box((s * 0.6, S.y(30), S.z(210)), (0.5, 0.06, 0.06))
    det = H.build(mat, bevel=0.0)
    vk.join_objs(hull, [det]); hull.data.materials.clear(); hull.data.materials.append(mat)
    o["Hull"] = hull

    # cupola ring + gun shield (Turret), MG (Gun)
    cx, cy, cz = CUP
    gy, gz = TRUNNION
    Tp = Part("Turret")
    Tp.cyl((cx, cy, cz + 0.06), 0.52, 0.14, seg=24)
    Tp.cyl((cx, cy, cz + 0.15), 0.44, 0.05, seg=24)
    gx = T.x(198) - cx                                                   # MG slightly left of the ring centre
    Tp.box((cx + gx, gy + 0.18, (cz + 0.15 + S.z(20)) / 2), (0.75, 0.05, S.z(20) - cz - 0.15))   # front shield
    for s in (-1, 1):
        Tp.box((cx + gx + s * 0.42, gy + 0.02, (cz + 0.15 + S.z(40)) / 2), (0.05, 0.35, S.z(40) - cz - 0.15),
               (0, 0, s * 0.3))
    Tp.cyl((cx + gx, gy - 0.05, (cz + gz) / 2), 0.045, gz - cz - 0.05, seg=8)                    # pintle
    tur = Tp.build(mat, bevel=0.0)
    vk.set_origin(tur, CUP)
    o["Turret"] = tur
    G = Part("Gun")
    G.box((cx + gx, gy - 0.08, gz), (0.15, 0.46, 0.16))
    G.box((cx + gx - 0.15, gy - 0.1, gz - 0.05), (0.14, 0.26, 0.16))
    G.cyl((cx + gx, (gy + 0.15 + gy + 0.45) / 2, gz), 0.045, 0.3, (PI / 2, 0, 0), seg=10)
    G.cyl((cx + gx, (gy + 0.45 + MUZZLE_Y) / 2, gz), 0.027, MUZZLE_Y - gy - 0.45, (PI / 2, 0, 0), seg=8)
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, (cx + gx, gy, gz)); vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (cx + gx, MUZZLE_Y + 0.01, gz), parent=gun)

    gear = vk.build_running_gear(TRACK, mat)
    o.update(gear)
    left = list(gear)
    th = Part("TeamHull")
    for s in (-1, 1):
        th.box((s * (T.x(366) + 0.012), S.y(600), S.z(140)), (0.02, 0.9, 0.1))
    th.box((0, S.y(735) - 0.07, S.z(140)), (0.8, 0.02, 0.1))
    ctx.team.append(("Hull", th))
    tm = Part("TeamTurret")
    tm.box((cx + gx, gy + 0.21, S.z(30)), (0.5, 0.02, 0.08))
    ctx.team.append(("Turret", tm))

    def post_uv(objs):
        objs.update(vk.mirror_gear(objs, left))
    hubs = {n: (gear[n].location.y, gear[n].location.z, (TRACK.wheel_r - 0.04) if n.startswith("Wheel") else None)
            for n in left}
    return dict(uv=["Hull", "Turret", "Gun"] + left, post_uv=post_uv, tracks=TRACK, track_rect=(167, 405, 575, 415),
                roots=["Hull", "Turret", "TrackL", "TrackR"] + [f"Wheel{s}{i}" for s in "LR" for i in range(5)]
                + ["IdlerL", "IdlerR", "SprocketL", "SprocketR"],
                cams={"front34": -40.0, "rear34": -140.0},
                cfg=dict(mud_h=0.8, hubs=hubs),
                preview=dict(length=5.0, width=2.7, height=2.7, rts_dist=13, close_dist=10, close_az=-40),
                extra=[f"cupola (Turret) pivot {tuple(round(v, 3) for v in CUP)}, MG trunnion y {gy:.3f} z {gz:.3f}, "
                       f"muzzle y {MUZZLE_Y:.3f}",
                       f"road wheel r {TRACK.wheel_r}, sprocket (front) r {TRACK.sprocket[2]}, idler (rear) r {TRACK.idler[2]}"])


if __name__ == "__main__":
    vk.run_vehicle("m113", S, T, build, "Steel Accord M2 - M113-style APC - Cycles CPU preview")
