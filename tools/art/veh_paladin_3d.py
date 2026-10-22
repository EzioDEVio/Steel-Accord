"""Steel Accord M2 - Paladin-style self-propelled howitzer, 3D (bpy 5.x). Pipeline: tools/art/vehkit.py.

Run:  python3 tools/art/veh_paladin_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Measurements: paladin_side.png flipped to nose-left (hull px 150..862 = 6.8 m; ground py 477) and
paladin_top.png (hull py 224..809, centre px 244; Y rectified: the top view's turret front is ~1 m further
forward than in the side view). The side view shows the howitzer elevated ~15 deg; the model's gun rests level
and is textured from the top view only (where the barrel is drawn straight).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
from vehkit import Part, PI  # noqa: E402

S = vk.SideFrame(6.8 / 712.0, 506.0, 477.0)
T = vk.TopFrame(6.8 / 585.0, 244.0, 516.5, sx=1.0, ymap=[(224, S.y(150)), (400, S.y(470)), (809, S.y(862))])
TRACK = vk.TrackSpec(track_x=1.5, width=0.52, thick=0.1, wheel_r=0.33,
                     wheel_ys=[S.y(px) for px in (273, 350, 427, 509, 591, 668, 750)],
                     sprocket=(S.y(191), 0.72, 0.27), idler=(S.y(823), 0.68, 0.26),
                     rollers=[(1.9, 0.86, 0.08), (0.4, 0.86, 0.08), (-1.2, 0.86, 0.08)],
                     pitch=0.155, links_per_tile=6, wheel_w=0.15, wheel_gap=0.1, sprocket_teeth=10)
TURRET_O = (0.0, -1.2, S.z(302))
TRUNNION = (0.0, S.y(530), S.z(262))
GUN_LEN = math.hypot(530 - 15, 262 - 140) * S.s
MUZZLE_Y = TRUNNION[1] + GUN_LEN


def build(ctx):
    mat, o, refs = ctx.mat, ctx.objs, ctx.refs
    hull_side = vk.silhouette_poly(refs["side"], (0, 306, 875, 412), discs=[(191, 400, 31), (823, 405, 31)],
                                   open_px=3, tol=1.2)
    plan = [T(px, py) for px, py in [(100, 224), (388, 224), (395, 240), (395, 800), (380, 809), (110, 809),
                                     (95, 800), (95, 240)]]
    hull = vk.vhull("Hull", [S(*p) for p in hull_side], plan, (-0.1, 4), (-2.5, 2.5), bevel=0.015)
    H = Part("HullDetail")
    H.side([S(170, 405), S(850, 405), S(840, 425), S(240, 428)], -1.2, 1.2)               # belly between tracks
    for s in (-1, 1):
        for (y, z, r) in TRACK.rollers:
            H.cyl((s * TRACK.track_x, y, z), r, 0.26, (0, PI / 2, 0), seg=10)
        H.box((s * 1.35, S.y(160) + 0.05, S.z(352)), (0.2, 0.12, 0.14))                    # headlight guards
        H.cyl((s * 1.35, S.y(160) + 0.1, S.z(352)), 0.05, 0.04, (PI / 2, 0, 0), seg=10)
        H.box((s * 1.45, S.y(862) - 0.03, S.z(330)), (0.16, 0.06, 0.12))                   # tail lights
    H.box((0, S.y(862) - 0.04, S.z(370)), (1.6, 0.08, 0.5))                                 # rear door frame
    det = H.build(mat, bevel=0.0)
    vk.join_objs(hull, [det]); hull.data.materials.clear(); hull.data.materials.append(mat)
    o["Hull"] = hull

    # ------------------------------------------------------------ turret (large, full width, bustle rack)
    tur_side = vk.silhouette_poly(refs["side"], (472, 196, 875, 304), open_px=4, tol=1.2,
                                  extra_remove=((430, 190, 474, 304), (472, 196, 500, 240)))
    tur_plan = [T(px, py) for px, py in [(110, 400), (380, 400), (395, 430), (395, 800), (380, 809), (110, 809),
                                         (95, 800), (95, 430)]]
    tur = vk.vhull("Turret", [S(*p) for p in tur_side], tur_plan, (1.4, 3.2), (-2.2, 2.2), bevel=0.015)
    TD = Part("TurretDetail")
    TD.box((0, TURRET_O[1] + 0.3, TURRET_O[2] + 0.04), (2.6, 2.6, 0.1))                    # ring / base plate
    # commander's cupola + RWS (side px 473..655, py 132..200)
    cx, cy = T.x(255), (S.y(564) + S.y(655)) / 2
    ztop = S.z(205)
    TD.cyl((cx, cy, ztop + 0.06), 0.42, 0.12, seg=18)
    TD.box((cx, cy, (ztop + S.z(160)) / 2 + 0.05), (0.45, 0.6, S.z(160) - ztop))
    TD.box((cx + 0.3, cy + 0.1, S.z(165)), (0.2, 0.35, 0.25))
    TD.box((cx - 0.05, cy + 0.2, S.z(150)), (0.16, 0.5, 0.14))
    TD.cyl((cx - 0.05, (cy + 0.45 + S.y(480)) / 2, S.z(150)), 0.025, S.y(480) - cy - 0.45, (PI / 2, 0, 0), seg=6)
    # sight box + hatches on the roof
    TD.box((-0.8, S.y(560), ztop + 0.1), (0.4, 0.4, 0.2))
    TD.cyl((-0.6, S.y(700), ztop + 0.03), 0.35, 0.06, seg=16)
    # antennas
    for x, px, top in ((1.2, 723, 50), (-1.2, 764, 70), (-1.3, 777, 40)):
        TD.cyl((x, S.y(px), (ztop + S.z(top)) / 2), 0.012, S.z(top) - ztop, seg=5)
    td = TD.build(mat, bevel=0.0)
    vk.join_objs(tur, [td]); tur.data.materials.clear(); tur.data.materials.append(mat)
    vk.set_origin(tur, TURRET_O)
    o["Turret"] = tur

    # ------------------------------------------------------------ 155 mm howitzer (level at rest)
    G = Part("Gun")
    ty, tz = TRUNNION[1], TRUNNION[2]
    G.box((0, ty + 0.35, tz), (0.75, 0.75, 0.62))                                  # mantlet / cradle
    L = GUN_LEN
    prof = [(0.7, 0.2), (0.7, 0.13), (L * 0.42, 0.115), (L * 0.42, 0.17), (L * 0.55, 0.17), (L * 0.55, 0.11),
            (L - 0.45, 0.105), (L - 0.45, 0.18), (L, 0.18), (L, 0.08)]
    vk.lathe(G, (0, ty, tz), prof, seg=16, axis="y")
    for s in (-1, 1):                                                               # muzzle brake ports
        G.box((s * 0.19, ty + L - 0.22, tz), (0.04, 0.3, 0.22))
        G.cyl((s * 0.25, ty + 0.45, tz - 0.18), 0.06, 0.6, (PI / 2, 0, 0), seg=8)   # recuperators
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, TRUNNION); vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (0, MUZZLE_Y + 0.01, tz), parent=gun)

    gear = vk.build_running_gear(TRACK, mat)
    o.update(gear)
    left = list(gear)
    tm = Part("TeamTurret")
    for s in (-1, 1):
        tm.box((s * (T.x(395) + 0.012), S.y(620), S.z(225)), (0.02, 1.2, 0.12))
    ctx.team.append(("Turret", tm))
    th = Part("TeamHull")
    for s in (-1, 1):
        th.box((s * (T.x(395) + 0.012), S.y(300), S.z(330)), (0.02, 0.8, 0.1))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(vk.mirror_gear(objs, left))
    hubs = {n: (gear[n].location.y, gear[n].location.z, (TRACK.wheel_r - 0.05) if n.startswith("Wheel") else None)
            for n in left}
    return dict(uv=["Hull", "Turret", "Gun"] + left, post_uv=post_uv, tracks=TRACK, track_rect=(273, 468, 750, 477),
                roots=["Hull", "Turret", "TrackL", "TrackR"] + [f"Wheel{s}{i}" for s in "LR" for i in range(7)]
                + ["IdlerL", "IdlerR", "SprocketL", "SprocketR"],
                cams={"front34": 40.0, "rear34": -140.0},
                cfg=dict(mud_h=0.9, hubs=hubs, top_only=["Gun"]),
                preview=dict(length=9.0, width=3.7, height=3.4, rts_dist=19, close_dist=15, close_az=-40),
                extra=[f"turret pivot {tuple(round(v, 3) for v in TURRET_O)}, trunnion "
                       f"{tuple(round(v, 3) for v in TRUNNION)}, barrel {GUN_LEN:.2f} m, muzzle y {MUZZLE_Y:.3f}",
                       f"road wheel r {TRACK.wheel_r}, sprocket (front) r {TRACK.sprocket[2]}, idler (rear) r {TRACK.idler[2]}"])


if __name__ == "__main__":
    vk.run_vehicle("paladin", S, T, build, "Steel Accord M2 - Paladin-style SP howitzer - Cycles CPU preview")
