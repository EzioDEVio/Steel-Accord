"""Steel Accord M2 - Bradley-style infantry fighting vehicle, 3D (bpy 5.x). Pipeline: tools/art/vehkit.py.

Run:  python3 tools/art/veh_bradley_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Measurements: bradley_side.png (nose left; hull px 12..775 = 6.6 m; ground py 455) and bradley_top.png
(hull py 40..694, centre px 182.5; Y rectified: the top view's turret sits ~0.4 m further forward).
Hull and turret bodies are side-silhouette (auto-traced) x plan-outline intersections.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
from vehkit import Part, PI  # noqa: E402

S = vk.SideFrame(6.6 / 763.0, 393.5, 455.0)
T = vk.TopFrame(6.6 / 654.0, 182.5, 367.0, sx=1.0,
                ymap=[(40, S.y(12)), (262, S.y(320)), (472, S.y(664)), (694, S.y(775))])
TRACK = vk.TrackSpec(track_x=1.42, width=0.53, thick=0.11, wheel_r=0.30,
                     wheel_ys=[S.y(px) for px in (164, 252, 340, 428, 516, 604)],
                     sprocket=(S.y(44), 0.78, 0.25), idler=(S.y(736), 0.80, 0.25),
                     rollers=[(1.6, 0.76, 0.08), (0.0, 0.76, 0.08), (-1.5, 0.76, 0.08)],
                     pitch=0.155, links_per_tile=6, wheel_w=0.15, wheel_gap=0.1, sprocket_teeth=10)
TURRET_O = (0.0, S.y(480), S.z(214))
TRUNNION = (0.0, S.y(335), S.z(160))
MUZZLE_Y = S.y(96)


def build(ctx):
    mat, o, refs = ctx.mat, ctx.objs, ctx.refs
    vk.patch_copy(refs["top"], (168, 13, 200, 262), dx=30)           # barrel drawn over the front deck
    hull_side = vk.silhouette_poly(refs["side"], (0, 214, 790, 377), discs=[(44, 364, 32), (736, 360, 32)],
                                   open_px=3, tol=1.2)
    plan = [T(px, py) for px, py in [(30, 40), (335, 40), (350, 80), (351, 640), (346, 694), (21, 694), (14, 640),
                                     (18, 80)]]
    hull = vk.vhull("Hull", [S(*p) for p in hull_side], plan, (-0.1, 4), (-2.5, 2.5), bevel=0.015)
    H = Part("HullDetail")
    # lower hull between the tracks (below the side-armour line)
    H.side([S(30, 372), S(760, 372), S(750, 400), S(150, 410), S(60, 395)], -1.15, 1.15)
    for s in (-1, 1):
        for (y, z, r) in TRACK.rollers:
            H.cyl((s * TRACK.track_x, y, z), r, 0.26, (0, PI / 2, 0), seg=10)
        H.cyl((s * 1.3, S.y(14) - 0.02, S.z(300)), 0.07, 0.06, (PI / 2, 0, 0), seg=10)   # headlights
        H.box((s * 1.25, S.y(775) + 0.03, S.z(240)), (0.18, 0.06, 0.12))                 # tail lights
        H.box((s * 1.6, S.y(30), S.z(330)), (0.16, 0.12, 0.18))                          # tow eyes
    H.box((0, S.y(775) + 0.05, S.z(300)), (1.7, 0.08, S.z(240) - S.z(370)))            # rear ramp plate
    det = H.build(mat, bevel=0.0)
    vk.join_objs(hull, [det]); hull.data.materials.clear(); hull.data.materials.append(mat)
    o["Hull"] = hull

    # ------------------------------------------------------------ turret
    tur_side = vk.silhouette_poly(refs["side"], (318, 112, 700, 214), open_px=4, tol=1.2,
                                  extra_remove=((300, 140, 340, 182),))
    tur_plan = [T(px, py) for px, py in [(120, 262), (250, 262), (312, 300), (315, 450), (300, 472), (70, 472),
                                         (55, 450), (58, 300)]]
    tur = vk.vhull("Turret", [S(*p) for p in tur_side], tur_plan, (1.5, 3.4), (-2, 2), bevel=0.015)
    TD = Part("TurretDetail")
    TD.cyl((0, TURRET_O[1], TURRET_O[2] + 0.04), 1.0, 0.12, seg=26)                         # ring
    # commander's sight head (side px 412..528, py 68..116)
    sy0, sy1 = S.y(412), S.y(528)
    TD.box((0.45, (sy0 + sy1) / 2, (S.z(116) + S.z(68)) / 2), (0.55, sy0 - sy1, S.z(68) - S.z(116)))
    TD.cyl((0.45, (sy0 + sy1) / 2, S.z(116) - 0.03), 0.3, 0.08, seg=14)
    # TOW launcher box on the left of the turret
    ty0, ty1 = S.y(520), S.y(664)
    TD.box((-1.32, (ty0 + ty1) / 2, (S.z(188) + S.z(122)) / 2), (0.36, ty0 - ty1, S.z(122) - S.z(188)))
    for i in (-1, 1):
        TD.cyl((-1.32 + i * 0.09, ty0 + 0.01, (S.z(188) + S.z(122)) / 2), 0.08, 0.04, (PI / 2, 0, 0), seg=12)
    # smoke dischargers on both front cheeks
    for s in (-1, 1):
        for k in range(4):
            TD.cyl((s * 1.15, S.y(455) - k * 0.1, S.z(170) + (k % 2) * 0.1), 0.045, 0.18, (0, PI / 2, s * 0.4), seg=8)
    # antennas
    for px in (548, 648):
        TD.cyl((0.95 if px == 548 else -0.95, S.y(px), (S.z(124) + S.z(15)) / 2), 0.012, S.z(15) - S.z(124), seg=5)
    td = TD.build(mat, bevel=0.0)
    vk.join_objs(tur, [td]); tur.data.materials.clear(); tur.data.materials.append(mat)
    vk.set_origin(tur, TURRET_O)
    o["Turret"] = tur

    # ------------------------------------------------------------ 25 mm gun + coax
    G = Part("Gun")
    ty, tz = TRUNNION[1], TRUNNION[2]
    G.box((0, ty + 0.05, tz), (0.5, 0.4, 0.34))                                  # mantlet
    vk.lathe(G, (0, ty, tz), [(0.2, 0.09), (0.2, 0.07), (0.9, 0.06), (0.9, 0.045), (MUZZLE_Y - ty - 0.2, 0.045),
                              (MUZZLE_Y - ty - 0.2, 0.06), (MUZZLE_Y - ty, 0.06), (MUZZLE_Y - ty, 0.03)], seg=12, axis="y")
    G.cyl((0.18, ty + 0.45, tz - 0.05), 0.022, 0.5, (PI / 2, 0, 0), seg=6)        # coaxial MG
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, TRUNNION); vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (0, MUZZLE_Y + 0.01, tz), parent=gun)

    gear = vk.build_running_gear(TRACK, mat)
    o.update(gear)
    left = list(gear)
    tm = Part("TeamTurret")
    tm.box((-1.51, (ty0 + ty1) / 2, S.z(140)), (0.02, (ty0 - ty1) * 0.7, 0.1))
    tm.box((T.x(315) + 0.012, S.y(560), S.z(150)), (0.02, 0.7, 0.1))
    ctx.team.append(("Turret", tm))
    th = Part("TeamHull")
    for s in (-1, 1):
        th.box((s * (T.x(351) + 0.012), S.y(700), S.z(250)), (0.02, 0.6, 0.1))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(vk.mirror_gear(objs, left))
    hubs = {n: (gear[n].location.y, gear[n].location.z, (TRACK.wheel_r - 0.05) if n.startswith("Wheel") else None)
            for n in left}
    return dict(uv=["Hull", "Turret", "Gun"] + left, post_uv=post_uv, tracks=TRACK, track_rect=(164, 446, 604, 455),
                roots=["Hull", "Turret", "TrackL", "TrackR"] + [f"Wheel{s}{i}" for s in "LR" for i in range(6)]
                + ["IdlerL", "IdlerR", "SprocketL", "SprocketR"],
                cams={"front34": -40.0, "rear34": -140.0},
                cfg=dict(mud_h=0.9, hubs=hubs, side_only=["Gun"]),
                preview=dict(length=7.0, width=3.6, height=3.4, rts_dist=17, close_dist=13, close_az=-40),
                extra=[f"turret pivot {tuple(round(v, 3) for v in TURRET_O)}, trunnion "
                       f"{tuple(round(v, 3) for v in TRUNNION)}, muzzle y {MUZZLE_Y:.3f}",
                       f"road wheel r {TRACK.wheel_r}, sprocket (front) r {TRACK.sprocket[2]}, idler (rear) r {TRACK.idler[2]}"])


if __name__ == "__main__":
    vk.run_vehicle("bradley", S, T, build, "Steel Accord M2 - Bradley-style IFV - Cycles CPU preview")
