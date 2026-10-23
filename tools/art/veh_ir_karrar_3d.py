"""Steel Accord - Iran wave 1 - Karrar-style main battle tank, 3D (bpy 5.x). Kit: tools/art/vehkit_ir.py.

Run:  python3 tools/art/veh_ir_karrar_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/ir_karrar/ir_karrar.glb (+ ir_karrar_albedo.png, ir_karrar_track.png copies)
Reference: docs/reference/iran_pack/01_ground_vehicle_catalog.png panel 01 (perspective concept, silhouette and
camouflage only). Dimensions are authored at real size: hull 6.9 m, 9.5 m with the gun forward, 3.6 m over the
skirts, 2.25 m to the turret roof (RWS to ~2.85 m).
Nodes: Hull, Turret (yaw) > Gun (trunnion) > Muzzle, WheelL0..5/WheelR0..5, IdlerL/R (front), SprocketL/R (rear),
TrackL/TrackR (SA_TrackScroll).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit_ir as ik  # noqa: E402
from vehkit_ir import TPart, PI  # noqa: E402

VID = "ir_karrar"
C = ik.T72
TURRET_O = (0.0, 0.35, 1.42)
TRUNNION = (0.0, 1.30, 1.86)
MUZZLE_Y = 6.05


def build(ctx):
    mat, o = ctx.mat, ctx.objs
    d = C["deck"]
    # ------------------------------------------------------------ hull
    H = TPart("Hull")
    ik.t72_hull(H, C)
    shell = ik.build(H, mat, bevel=0.025)
    D = TPart("HullDetail")
    ik.t72_skirts(D, C, kind="armour", y0=2.30)
    ik.t72_details(D, C, rear_log=False, drums=False)
    # add-on armour block on the upper glacis (Karrar's raised, flat-fronted front armour)
    D.t("camo").slab([(-1.05, 2.95), (1.05, 2.95), (1.05, 2.25), (-1.05, 2.25)], 1.12,
                     [(-0.95, 2.62), (0.95, 2.62), (0.95, 2.20), (-0.95, 2.20)], 1.44)
    for s in (-1, 1):
        D.slab([(s * 1.12, 3.32), (s * 1.70, 3.32), (s * 1.70, 2.35), (s * 1.12, 2.35)], 1.06,
               [(s * 1.14, 3.05), (s * 1.70, 3.05), (s * 1.70, 2.35), (s * 1.14, 2.35)], 1.40)
    # return rollers (static, behind the skirts)
    for s in (-1, 1):
        for (y, z, r) in C["track"].rollers:
            D.t("metal").cyl((s * C["track"].track_x, y, z), r, 0.3, (0, PI / 2, 0), seg=10)
    det = ik.build(D, mat)
    o["Hull"] = ik.join(shell, [det])

    # ------------------------------------------------------------ turret (origin on the yaw axis)
    T = TPart("Turret")
    cy = TURRET_O[1]
    zb, zt = d + 0.06, 2.20
    bot = [(-0.42, cy + 1.92), (0.42, cy + 1.92), (1.46, cy + 1.08), (1.52, cy - 0.70), (1.38, cy - 1.32),
           (-1.38, cy - 1.32), (-1.52, cy - 0.70), (-1.46, cy + 1.08)]
    top = [(-0.36, cy + 1.66), (0.36, cy + 1.66), (1.32, cy + 0.95), (1.40, cy - 0.70), (1.28, cy - 1.26),
           (-1.28, cy - 1.26), (-1.40, cy - 0.70), (-1.32, cy + 0.95)]
    T.slab(bot, zb, top, zt)
    T.cyl((0, cy, d + 0.04), 1.20, 0.10, seg=28)                                 # turret ring collar
    tshell = ik.build(T, mat, bevel=0.025)
    TD = TPart("TurretDetail")
    # wedge cheek modules ahead of the turret face, either side of the mantlet
    for s in (-1, 1):
        TD.slab([(s * 0.30, cy + 2.02), (s * 0.40, cy + 2.10), (s * 1.38, cy + 1.20), (s * 1.30, cy + 1.10)], 1.62,
                [(s * 0.32, cy + 1.90), (s * 0.40, cy + 1.96), (s * 1.30, cy + 1.14), (s * 1.24, cy + 1.06)], 2.12)
        # side armour boxes along the turret flanks
        TD.t("skirt").obox((s * 1.56, cy + 0.15, 1.86), (0.12, 1.55, 0.46), (0, 1, 0), (0, 0, 1))
        TD.t("camo").box((s * 1.45, cy - 1.05, 1.95), (0.18, 0.40, 0.40))
        ik.smoke_launchers(TD, (s * 1.20, cy + 1.20, 2.20), 4, yaw=s * 25, pitch=0.55, spacing=0.10)
        ik.antenna(TD, (s * 1.15, cy - 1.20, zt), 1.9)
    # bustle rack (open frame) behind the turret
    ry0, ry1 = cy - 1.32, cy - 1.82
    TD.t("metal")
    for s in (-1, 1):
        for z in (1.70, 1.98, 2.18):
            TD.beam((s * 1.30, ry0, z), (s * 1.30, ry1, z), 0.04, 0.04)
        TD.beam((s * 1.30, ry1, 1.66), (s * 1.30, ry1, 2.20), 0.04, 0.04)
    for z in (1.70, 1.98, 2.18):
        TD.beam((-1.30, ry1, z), (1.30, ry1, z), 0.04, 0.04)
    for k in range(-4, 5):
        TD.beam((k * 0.29, ry1, 1.68), (k * 0.29, ry1, 2.18), 0.025, 0.025)
    TD.t("canvas").box((0.0, (ry0 + ry1) / 2 + 0.03, 1.86), (2.3, 0.40, 0.32))     # stowed tarp / kit in the rack
    TD.t("camo")
    # commander's panoramic sight (left-front) and gunner's sight (right-front)
    TD.box((0.62, cy + 0.85, zt + 0.16), (0.36, 0.42, 0.32))
    TD.t("glass").box((0.62, cy + 1.065, zt + 0.18), (0.26, 0.02, 0.17))
    TD.t("camo").cyl((-0.55, cy + 0.55, zt + 0.12), 0.20, 0.24, seg=14)
    TD.box((-0.55, cy + 0.55, zt + 0.34), (0.30, 0.30, 0.20))
    TD.t("glass").box((-0.55, cy + 0.705, zt + 0.35), (0.22, 0.02, 0.12))
    TD.t("camo")
    # remote weapon station on the roof (static part of the turret): base, sensor head, ammo box, MG
    rx, ry = -0.30, cy - 0.35
    TD.cyl((rx, ry, zt + 0.05), 0.34, 0.10, seg=18)
    TD.box((rx, ry, zt + 0.32), (0.46, 0.55, 0.44))
    TD.box((rx + 0.34, ry + 0.10, zt + 0.42), (0.22, 0.40, 0.30))
    TD.t("glass").box((rx + 0.34, ry + 0.305, zt + 0.43), (0.16, 0.02, 0.18))
    TD.t("camo").box((rx - 0.32, ry, zt + 0.32), (0.18, 0.38, 0.24))
    TD.t("metal").box((rx, ry + 0.38, zt + 0.50), (0.12, 0.40, 0.12))
    TD.tube((rx, ry + 0.95, zt + 0.50), 0.025, 0.85, "y", seg=6)
    TD.t("camo")
    ik.hatch(TD, (0.48, cy - 0.40, zt), 0.30)                                     # loader's hatch
    # weather sensor mast, rear
    TD.t("metal").cyl((0.95, cy - 1.0, zt + 0.25), 0.02, 0.5, seg=5)
    TD.cyl((0.95, cy - 1.0, zt + 0.52), 0.05, 0.06, seg=8)
    TD.t("camo")
    tdet = ik.build(TD, mat)
    tur = ik.join(tshell, [tdet])
    ik.set_origin(tur, TURRET_O)
    o["Turret"] = tur

    # ------------------------------------------------------------ gun (origin on the trunnion)
    G = TPart("Gun")
    ty, tz = TRUNNION[1], TRUNNION[2]
    G.t("camo").slab([(-0.42, ty + 0.25), (0.42, ty + 0.25), (0.42, ty + 0.92), (-0.42, ty + 0.92)], tz - 0.26,
                     [(-0.36, ty + 0.25), (0.36, ty + 0.25), (0.36, ty + 0.85), (-0.36, ty + 0.85)], tz + 0.24)
    G.t("barrel")
    L = MUZZLE_Y - ty
    prof = [(0.92, 0.17), (1.05, 0.13), (2.15, 0.125), (2.20, 0.16), (2.85, 0.16), (2.90, 0.12), (3.80, 0.115),
            (3.84, 0.125), (3.90, 0.11), (L - 0.15, 0.10), (L - 0.13, 0.115), (L, 0.115), (L, 0.06)]
    ik.gun_barrel(G, ty, tz, prof, seg=14)
    G.t("dark").tube((0, MUZZLE_Y - 0.005, tz), 0.075, 0.012, "y", seg=12)                # bore shadow
    G.t("metal").box((0, MUZZLE_Y - 0.3, tz + 0.15), (0.06, 0.12, 0.06))              # muzzle reference
    G.t("camo")
    gun = ik.build(G, mat, smooth=40)
    ik.set_origin(gun, TRUNNION)
    ik.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = ik.empty("Muzzle", (0, MUZZLE_Y + 0.02, tz), parent=gun)

    # ------------------------------------------------------------ running gear
    left_gear = ik.t72_gear(ctx, C)

    # ------------------------------------------------------------ team colour panels (SA_Team)
    tm = TPart("TeamTurret")
    for s in (-1, 1):
        tm.box((s * 1.63, cy + 0.15, 1.98), (0.02, 1.20, 0.12))
    tm.box((0, cy - 1.835, 2.02), (1.4, 0.02, 0.10))
    ctx.team.append(("Turret", tm))
    th = TPart("TeamHull")
    for s in (-1, 1):
        th.box((s * 1.83, -1.70, 1.25), (0.02, 1.6, 0.12))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(ik.vk.mirror_gear(objs, left_gear))

    flag = [dict(kind="flag", axis=ax, c=(cy - 0.05, 1.80), size=(0.42, 0.26), obj="Turret") for ax in ("-x", "+x")]
    flag += [dict(kind="flag", axis="-y", c=(0.85, 1.20), size=(0.36, 0.22), obj="Hull", depth=C["rear"], dtol=0.08)]
    cfg = dict(
        seams_y=[2.05, 0.55, -0.85, -1.70], seams_x=[0.88], seams_z=[],
        skirt_pitch=0.68, skirt_y0=2.30, skirt_bolt_z=(1.36, 0.70), mud_h=1.0,
        decals=flag + [
            dict(kind="ring", c=(0.0, 2.02, C["deck"] + 0.05), r=0.36, obj="Hull"),
            dict(kind="rect", axis="+z", c=(0.0, -1.20), size=(1.90, 0.80), obj="Hull"),
            dict(kind="louvre", axis="+z", c=(0.0, -2.35), size=(1.66, 1.26), pitch=0.075, obj="Hull"),
            dict(kind="rect", axis="-y", c=(0.0, 1.00), size=(1.20, 0.55), obj="Hull", depth=C["rear"], dtol=0.08),
        ],
    )
    return dict(
        uv=["Hull", "Turret", "Gun"] + left_gear, post_uv=post_uv, tracks=C["track"],
        roots=["Hull", "Turret"] + ik.gear_roots(6), hubs=ik.gear_hubs(ctx, left_gear, C), cfg=cfg,
        preview=dict(length=9.6, width=3.7, height=2.9, rts_dist=21, close_dist=15, close_az=-40),
        extra=[f"turret pivot {TURRET_O}, gun trunnion {TRUNNION}, muzzle y {MUZZLE_Y}",
               "hull 6.90 m (nose 3.45 .. rear -3.45), 9.50 m with gun, 3.60 m over skirts, turret roof 2.20 m",
               f"road wheel r {C['track'].wheel_r}, idler (front) r {C['track'].idler[2]}, "
               f"sprocket (rear) r {C['track'].sprocket[2]}"],
    )


if __name__ == "__main__":
    ik.run(VID, build, "Steel Accord Iran W1 - Karrar-style MBT (ir_karrar) - Cycles CPU preview")
