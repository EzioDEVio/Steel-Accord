"""Steel Accord M2 - M777-style towed 155 mm howitzer, deployed, 3D (bpy 5.x). Pipeline: tools/art/vehkit.py.

Run:  python3 tools/art/veh_m777_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Model is deployed: trails spread (as in the concept top view), gun level at rest (the game pitches `Gun`).
Scale: top view muzzle py 13 .. spade py 700 = 9.5 m (manifest length) -> wheel track 2.74 m; side view
scaled 0.0118 m/px from wheel radius and trail length. The concept side / 3/4 views show the barrel elevated,
so the gun and carriage top are textured from the top view only and the 3/4 views are not projected.
No engine: there are no Track/Sprocket nodes; wheels are WheelL / WheelR (hub origins, spin about local X).
`Turret` = carriage top (yaw about local Y), `Gun` = cradle + barrel (pitch about local X), `Muzzle` at the tip.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
from vehkit import Part, PI  # noqa: E402

T = vk.TopFrame(9.5 / 687.0, 252.0, 356.5)
S = vk.SideFrame(0.0118, 391 + T.y(435) / 0.0118, 277.0)      # side px 391 = axle
AXLE_Y = T.y(435)
WHEEL_R = 0.61
WHEEL_X = abs(T.x(153))
TUR_O = (0.0, -1.6, 0.95)
TRUNNION = (0.0, -2.25, 1.45)
MUZZLE_Y = T.y(13)


def build(ctx):
    mat, o = ctx.mat, ctx.objs
    H = Part("Hull")
    # lower carriage: saddle body, axle beam, firing base (front float), trail hinges
    H.box((0, -1.75, 0.62), (1.3, 2.3, 0.5))
    for k in range(5):                                                          # stiffening ribs
        H.box((0, -0.8 - k * 0.48, 0.9), (1.36, 0.06, 0.08))
    for s in (-1, 1):
        H.cyl((s * 0.7, -1.2, 0.95), 0.12, 0.06, (0, PI / 2, 0), seg=24)       # hand wheels
        H.rod((s * 0.6, -0.6, 0.9), (s * 0.6, -2.8, 0.9), 0.025, seg=6)        # hydraulic lines
    H.box((0, AXLE_Y, WHEEL_R), (2 * WHEEL_X - 0.3, 0.22, 0.2))
    H.cyl((0, AXLE_Y, WHEEL_R), 0.09, 2 * WHEEL_X - 0.1, (0, PI / 2, 0), seg=10)
    H.box((0, 0.25, 0.08), (1.3, 1.0, 0.12))                                   # front firing platform
    H.box((0, 0.25, 0.3), (0.35, 0.5, 0.35))
    for s in (-1, 1):
        H.box((s * 0.42, -0.2, 0.45), (0.14, 1.2, 0.2), (0.25, 0, 0))          # platform struts
        # trails: hinge at the carriage rear, spread to the spades (top view ends at px 40 / 465, py 690)
        hx = s * 0.42
        p0 = (hx, -1.95, 0.55)
        ex, ey = T(40 if s < 0 else 465, 682)
        p1 = (ex * 0.97, ey, 0.22)
        H.beam(p0, p1, 0.42, 0.34)
        for f in (-1, 1):                                                       # flanges
            H.beam((p0[0], p0[1], p0[2] + f * 0.18), (p1[0], p1[1], p1[2] + f * 0.18), 0.5, 0.04)
        for k in range(1, 9):                                                   # lightening rings / clamps
            t = k / 9.0
            c = tuple(p0[i] + (p1[i] - p0[i]) * t for i in range(3))
            H.beam((c[0] - (p1[0] - p0[0]) * 0.01, c[1] - (p1[1] - p0[1]) * 0.01, c[2]),
                   (c[0] + (p1[0] - p0[0]) * 0.01, c[1] + (p1[1] - p0[1]) * 0.01, c[2]), 0.48, 0.4)
        H.beam((hx * 1.05, -2.05, 0.74), (ex * 0.8, ey * 0.85 + (-2.05) * 0.15, 0.4), 0.2, 0.08)   # top rail
        # spade + trail end pad
        H.box((ex, ey - 0.15, 0.12), (0.7, 0.5, 0.18), (0, 0, s * 0.55))
        H.box((ex, ey - 0.35, 0.05), (0.6, 0.06, 0.55), (0.6, 0, s * 0.55))
        # wheel suspension arms / hubs mounts
        H.box((s * (WHEEL_X - 0.28), AXLE_Y, WHEEL_R), (0.2, 0.36, 0.36))
    o["Hull"] = H.build(mat, bevel=0.01)

    # carriage top (Turret): side frames, equilibrators, elevation gear, sight
    Tp = Part("Turret")
    tx, ty, tz = TUR_O
    Tp.cyl((tx, ty, tz - 0.03), 0.55, 0.1, seg=22)
    for s in (-1, 1):
        Tp.side([(ty - 0.6 + a, tz - 0.05 + b) for a, b in ((-1.0, 0.0), (-0.6, 0.62), (0.2, 0.62), (0.6, 0.15),
                                                            (0.6, 0.0))], min(s * 0.32, s * 0.42), max(s * 0.32, s * 0.42))
        Tp.rod((s * 0.5, ty + 0.6, tz + 0.1), (s * 0.5, TRUNNION[1] + 0.2, TRUNNION[2] + 0.1), 0.07, seg=20)
    Tp.box((0.62, ty - 0.1, tz + 0.55), (0.18, 0.3, 0.3))                       # sight unit
    Tp.box((-0.6, ty - 0.2, tz + 0.35), (0.18, 0.5, 0.4))                       # fire-control box
    tur = Tp.build(mat, bevel=0.0)
    vk.set_origin(tur, TUR_O)
    o["Turret"] = tur

    # gun: cradle + recoil cylinders + barrel + muzzle brake + breech
    G = Part("Gun")
    gy, gz = TRUNNION[1], TRUNNION[2]
    L = MUZZLE_Y - gy
    G.box((0, gy + 0.9, gz), (0.5, 2.6, 0.42))                                  # cradle
    G.box((0, gy - 0.25, gz), (0.42, 0.55, 0.42))                               # breech ring
    for s in (-1, 1):
        G.cyl((s * 0.16, gy + 1.6, gz + 0.3), 0.09, 3.0, (PI / 2, 0, 0), seg=24)
        G.cyl((s * 0.16, gy + 3.15, gz + 0.3), 0.11, 0.1, (PI / 2, 0, 0), seg=16)  # recoil / recuperator tubes
    G.cyl((0, gy + 1.6, gz - 0.27), 0.08, 2.6, (PI / 2, 0, 0), seg=20)
    for k in range(6):                                                          # cradle clamps / bands
        G.cyl((0, gy + 0.2 + k * 0.5, gz + 0.02), 0.27, 0.06, (PI / 2, 0, 0), seg=20)
    vk.lathe(G, (0, gy, gz), [(2.2, 0.17), (2.2, 0.13), (L - 0.65, 0.105), (L - 0.65, 0.16), (L, 0.16), (L, 0.07)],
             seg=32, axis="y")
    for s in (-1, 1):
        G.box((s * 0.2, gy + L - 0.3, gz), (0.06, 0.42, 0.26))                  # muzzle brake baffles
    G.cyl((0.0, gy + 0.2, gz + 0.32), 0.05, 0.4, (PI / 2, 0, 0), seg=8)
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, TRUNNION); vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (0, MUZZLE_Y + 0.01, gz), parent=gun)

    # wheels (left authored, right mirrored after UV)
    W = vk.tyre_part("WheelL", WHEEL_R, 0.36, WHEEL_R * 0.58, seg=44)
    o["WheelL"] = W.build(mat, bevel=0.0, smooth=50, location=(-WHEEL_X, AXLE_Y, WHEEL_R))

    tm = Part("TeamTurret")
    for s in (-1, 1):
        tm.box((s * 0.43, ty - 0.35, tz + 0.3), (0.02, 0.5, 0.1))
    ctx.team.append(("Turret", tm))
    th = Part("TeamHull")
    for s in (-1, 1):
        ex, ey = T(40 if s < 0 else 465, 682)
        th.box(((s * 0.42 + ex) / 2, (-1.95 + ey) / 2, 0.55), (0.36, 0.5, 0.02), (0, 0, s * 0.55))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs["WheelR"] = vk.mirror_copy_x(objs["WheelL"], "WheelR")
    hubs = {"WheelL": (AXLE_Y, WHEEL_R, WHEEL_R - 0.06)}
    return dict(uv=["Hull", "Turret", "Gun", "WheelL"], post_uv=post_uv, tracks=None,
                roots=["Hull", "Turret", "WheelL", "WheelR"], cams={},
                cfg=dict(mud_h=0.5, hubs=hubs, top_only=["Gun", "Turret"], mud_amt=0.35),
                preview=dict(length=10.2, width=6.4, height=2.2, rts_dist=19, close_dist=14, close_az=-40),
                extra=[f"carriage-top (Turret) pivot {TUR_O}, trunnion {TRUNNION}, barrel {L:.2f} m from trunnion, "
                       f"muzzle y {MUZZLE_Y:.3f}", f"wheel r {WHEEL_R}, axle y {AXLE_Y:.3f}, track +-{WHEEL_X:.3f}"])


if __name__ == "__main__":
    vk.run_vehicle("m777", S, T, build, "Steel Accord M2 - M777-style towed howitzer (deployed) - Cycles CPU preview")
