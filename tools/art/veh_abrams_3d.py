"""Steel Accord M2 - Abrams-style main battle tank, 3D (bpy 5.x). Pipeline: tools/art/vehkit.py.

Run:  python3 tools/art/veh_abrams_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/abrams/abrams.glb (+ abrams_albedo.png, abrams_track.png inspectable copies)
Measurements: pixels on godot/assets/us/vehicles/abrams/abrams_{side,top}.png (side: nose left; hull nose
px 98 .. rear px 778 = 7.9 m; ground py 389. Top: hull py 145..723, centre px 174.5, rectified in Y).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
from vehkit import Part, PI  # noqa: E402

S = vk.SideFrame(7.9 / 680.0, 438.0, 389.0)
# top view: the concept turret sits ~0.5 m further forward and its bustle rack ~0.4 m shorter than in the side
# view -> piecewise Y rectification through hull nose, turret front, turret rear, rack end, hull rear
T = vk.TopFrame(7.9 / 578.0, 174.5, 434.0, sx=0.9,
                ymap=[(145, 3.95), (262, 1.85), (600, S.y(605)), (650, S.y(730)), (723, -3.95)])


def SP(pts):
    return [S(px, py) for px, py in pts]


def TP(pts):
    return [T(px, py) for px, py in pts]


TRACK = vk.TrackSpec(track_x=1.62, width=0.62, thick=0.14, wheel_r=0.35,
                     wheel_ys=[S.y(px) for px in (228, 306, 382, 457, 530, 600, 670)],
                     idler=(S.y(123), 0.85, 0.29), sprocket=(S.y(730), 0.93, 0.30),
                     rollers=[(2.0, 1.0, 0.1), (0.2, 1.02, 0.1), (-1.7, 1.04, 0.1)],
                     pitch=0.16, links_per_tile=6, wheel_w=0.17, wheel_gap=0.12)
TURRET_O = (0.0, -0.05, 1.74)
TRUNNION = (0.0, S.y(300), S.z(183.5))
MUZZLE_Y = S.y(11)


def build(ctx):
    mat = ctx.mat
    o = ctx.objs
    H = Part("Hull")
    # lower hull between the tracks
    H.side(SP([(98, 282), (772, 262), (774, 330), (745, 343), (172, 343)]), -1.30, 1.30)
    # upper hull / sponsons over the tracks (glacis + deck rising slightly to the rear)
    H.side(SP([(96, 281), (126, 251), (450, 239), (772, 225), (778, 232), (778, 286), (120, 286)]), -1.88, 1.88)
    # side skirts (armour) - outer faces carry the concept side view
    sk = SP([(84, 284), (108, 254), (772, 252), (772, 282), (735, 282), (703, 322), (130, 322), (98, 300)])
    for s in (-1, 1):
        H.side(sk, min(s * 1.885, s * 1.975), max(s * 1.885, s * 1.975))
    # rear plate details: tail lights, grille frame, tow pintle
    yr = S.y(778)
    for s in (-1, 1):
        H.cyl((s * 1.72, yr - 0.03, S.z(232)), 0.085, 0.12, (PI / 2, 0, 0), seg=12)
        H.box((s * 0.62, yr - 0.04, 1.35), (1.0, 0.08, 0.62))
        H.box((s * 1.25, 3.55, 1.68), (0.26, 0.16, 0.13))            # headlight guards on the front deck
        H.cyl((s * 1.25, 3.64, 1.68), 0.05, 0.04, (PI / 2, 0, 0), seg=10)
        H.box((s * 1.6, S.y(110), 1.28), (0.16, 0.12, 0.2))           # front tow eyes
    H.box((0, yr - 0.06, 0.95), (0.2, 0.14, 0.2))
    # engine deck louvres (low raised panel), driver's hatch hump
    H.box((0, -3.35, S.z(228) + 0.03), (2.6, 0.95, 0.07))
    H.cyl((0, 2.55, S.z(247)), 0.36, 0.08, seg=16)
    for s in (-1, 1):                                                  # return rollers (static, behind skirts)
        for (y, z, r) in TRACK.rollers:
            H.cyl((s * TRACK.track_x, y, z), r, 0.3, (0, PI / 2, 0), seg=10)
    o["Hull"] = H.build(mat, bevel=0.02, angle=35)

    # ------------------------------------------------------------ turret (origin on the yaw axis)
    tur_side = SP([(292, 164), (300, 159), (605, 150), (605, 220), (345, 236), (311, 225), (283, 204)])
    tur_plan = TP([(140, 262), (209, 262), (298, 322), (300, 470), (292, 560), (282, 600), (67, 600), (57, 560),
                   (49, 470), (51, 322)])
    tur = vk.vhull("Turret", tur_side, tur_plan, (1.6, 3.2), (-2.2, 2.2), mat=None, bevel=0.025)
    TP_ = Part("TurretDetail")
    TP_.cyl((0, TURRET_O[1], TURRET_O[2] + 0.1), 1.15, 0.24, seg=28)                    # turret ring skirt
    # bustle rack (basket) behind the turret
    y0, y1 = S.y(605), S.y(730)
    TP_.box((0, (y0 + y1) / 2, (S.z(200) + S.z(154)) / 2), (2.9, y0 - y1, S.z(154) - S.z(200)))
    # turret side stowage boxes
    for s, (a, b) in ((-1, (45, 100)), (1, (295, 335))):
        xa, xb = T.x(a), T.x(b)
        ya, yb = T.y(460), T.y(560)
        TP_.box(((xa + xb) / 2, (ya + yb) / 2, 2.38), (abs(xb - xa), abs(ya - yb), 0.5))
    # smoke grenade dischargers (2 rows x 3) on both cheeks
    for s in (-1, 1):
        for r in range(2):
            for c in range(3):
                TP_.cyl((s * 1.56, S.y(436) - c * 0.12, 2.36 + r * 0.14), 0.05, 0.2, (0, PI / 2, s * 0.35), seg=8)
    # commander's independent viewer, loader's hatch + MG pintle
    TP_.box((-0.75, S.y(415), (S.z(148) + S.z(116)) / 2 + 0.02), (0.36, 0.38, S.z(116) - S.z(148)))
    TP_.cyl((-0.75, S.y(415), S.z(148) - 0.02), 0.22, 0.1, seg=14)
    lx, ly = -0.45, T.y(470)
    TP_.cyl((lx, ly, 2.79), 0.36, 0.07, seg=18)
    TP_.box((lx, ly + 0.25, 2.93), (0.12, 0.6, 0.12))
    TP_.cyl((lx, ly + 0.8, 2.94), 0.025, 0.6, (PI / 2, 0, 0), seg=6)
    # commander's remote weapon station (CROWS-like): base, sensor box, MG
    rx, ry = 0.75, (S.y(474) + S.y(555)) / 2
    TP_.cyl((rx, ry, 2.82), 0.42, 0.1, seg=18)
    TP_.box((rx, ry, (S.z(100) + 2.8) / 2), (0.55, 0.9, S.z(100) - 2.8))
    TP_.box((rx + 0.36, ry + 0.15, S.z(100)), (0.22, 0.4, 0.3))
    TP_.box((rx - 0.05, ry + 0.05, S.z(93)), (0.2, 0.75, 0.16))
    TP_.cyl((rx - 0.05, (ry + 0.4 + S.y(396)) / 2, S.z(91)), 0.03, S.y(396) - ry - 0.4, (PI / 2, 0, 0), seg=6)
    # antennas on the rack corners (thin)
    for s, px in ((-1, 645), (1, 695)):
        TP_.cyl((s * 1.25, S.y(px) + 0.3, (2.75 + S.z(30)) / 2), 0.013, S.z(30) - 2.75, seg=5)
        TP_.cyl((s * 1.25, S.y(px) + 0.3, 2.78), 0.06, 0.08, seg=8)
    td = TP_.build(mat, bevel=0.0)
    vk.join_objs(tur, [td])
    tur.data.materials.clear(); tur.data.materials.append(mat)
    vk.set_origin(tur, TURRET_O)
    o["Turret"] = tur

    # ------------------------------------------------------------ gun (origin on the trunnion)
    G = Part("Gun")
    ty, tz = TRUNNION[1], TRUNNION[2]
    G.box((0, ty + 0.12, tz + 0.02), (0.86, 0.75, 0.52))                         # mantlet
    G.box((0, ty + 0.45, tz - 0.02), (0.5, 0.25, 0.36))
    prof = [(S.y(268) - ty, 0.15), (S.y(268) - ty, 0.13), (S.y(215) - ty, 0.12), (S.y(212) - ty, 0.16),
            (S.y(165) - ty, 0.16), (S.y(160) - ty, 0.11), (MUZZLE_Y - 0.12 - ty, 0.105), (MUZZLE_Y - 0.1 - ty, 0.12),
            (MUZZLE_Y - ty, 0.12), (MUZZLE_Y - ty, 0.06)]
    vk.lathe(G, (0, ty, tz), prof, seg=14, axis="y")
    # muzzle reference sensor
    G.box((0, MUZZLE_Y - 0.25, tz + 0.15), (0.06, 0.12, 0.08))
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, TRUNNION)
    vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (0, MUZZLE_Y + 0.02, tz), parent=gun)

    # ------------------------------------------------------------ running gear (left; right mirrored later)
    gear = vk.build_running_gear(TRACK, mat)
    o.update(gear)
    left_gear = list(gear.keys())

    # ------------------------------------------------------------ team colour panels
    tm = Part("TeamTurret")
    for s, (a, b) in ((-1, (45, 100)), (1, (295, 335))):
        xo = T.x(a) if s < 0 else T.x(b)
        tm.box((xo + s * 0.012, T.y(510), 2.5), (0.02, 0.9, 0.14))
    tm.box((0, S.y(730) - 0.012, S.z(170)), (1.6, 0.02, 0.12))
    ctx.team.append(("Turret", tm))
    th = Part("TeamHull")
    for s in (-1, 1):
        th.box((s * 1.98, S.y(700), S.z(262)), (0.02, 0.8, 0.1))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(vk.mirror_gear(objs, left_gear))

    hubs = {n: (gear[n].location.y, gear[n].location.z, None) for n in left_gear}
    for n in left_gear:
        if n.startswith("Wheel"):
            hubs[n] = (gear[n].location.y, gear[n].location.z, TRACK.wheel_r - 0.05)
    return dict(
        uv=["Hull", "Turret", "Gun"] + left_gear, post_uv=post_uv, tracks=TRACK,
        track_rect=(230, 377, 670, 388),
        roots=["Hull", "Turret", "TrackL", "TrackR"] + [f"Wheel{s}{i}" for s in "LR" for i in range(7)]
        + ["IdlerL", "IdlerR", "SprocketL", "SprocketR"],
        cams={"front34": 40.0, "rear34": 140.0},
        cfg=dict(mud_h=1.0, hubs=hubs),
        preview=dict(length=10.2, width=4.0, height=3.7, rts_dist=21, close_dist=16, close_az=-40),
        extra=[f"turret pivot {TURRET_O}, gun trunnion {tuple(round(v, 3) for v in TRUNNION)}, "
               f"muzzle y {MUZZLE_Y:.3f}", f"road wheel r {TRACK.wheel_r}, idler r {TRACK.idler[2]}, "
               f"sprocket r {TRACK.sprocket[2]}"],
    )


if __name__ == "__main__":
    vk.run_vehicle("abrams", S, T, build, "Steel Accord M2 - Abrams-style MBT - Cycles CPU preview")
