"""Steel Accord - Iran wave 1 - tracked combat-engineer / recovery vehicle with dozer blade and crane
(the Iranian builder unit; same role as the U.S. M88 "Dozer"), 3D (bpy 5.x). Kit: tools/art/vehkit_ir.py.

Run:  python3 tools/art/veh_ir_engineer_dozer_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/ir_engineer_dozer/ir_engineer_dozer.glb (+ _albedo.png, _track.png copies)
Reference: docs/reference/iran_pack/01_ground_vehicle_catalog.png panel 12 (perspective concept; silhouette and
camouflage only). Real-size authoring on the T-72-family chassis of the kit: hull 6.9 m, 7.55 m blade tip to hull
rear, blade 3.70 m wide, 2.32 m to the casemate roof, crane boom tip at 3.75 m.
Static Hull carries the blade, push arms and rams, crane (turntable, boom, ram, chain and hook), winch and stowage
(as on the M88). Small MG mount: Turret (yaw) > Gun (pitch) > Muzzle.
Nodes: Hull, Turret > Gun > Muzzle, WheelL0..5/WheelR0..5, IdlerL/R (front), SprocketL/R (rear), TrackL/TrackR.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit_ir as ik  # noqa: E402
from vehkit_ir import TPart, PI  # noqa: E402

VID = "ir_engineer_dozer"
C = ik.T72
MG_O = (-0.70, -0.55, 2.32)
MG_TRUNNION = (-0.68, -0.40, 2.62)       # (x, y, z)
MG_MUZZLE_Y = 0.62
BLADE_Y = 3.98                            # blade cutting edge (front)
BLADE_W = 3.70


def blade(P):
    """Curved moldboard (concave forward), cutting edge, end plates and teeth."""
    n = 9
    front, back = [], []
    for k in range(n + 1):
        t = k / n
        z = 0.06 + 1.04 * t
        y = BLADE_Y - 0.26 * math.sin(PI * t * 0.95) + 0.06 * t
        front.append((y, z))
        back.append((y - 0.07, z))
    prof = front + back[::-1]
    P.t("camo").side(prof, -BLADE_W / 2, BLADE_W / 2)
    # back ribs
    for x in (-1.3, -0.45, 0.45, 1.3):
        P.side([(BLADE_Y - 0.10, 0.10), (BLADE_Y - 0.36, 0.55), (BLADE_Y - 0.20, 1.05), (BLADE_Y - 0.10, 1.00),
                (BLADE_Y - 0.28, 0.55), (BLADE_Y - 0.06, 0.12)], x - 0.04, x + 0.04)
    # end plates
    for s in (-1, 1):
        P.side([(BLADE_Y + 0.04, 0.06), (BLADE_Y - 0.06, 1.10), (BLADE_Y - 0.48, 1.00), (BLADE_Y - 0.42, 0.10)],
               s * BLADE_W / 2 - 0.03, s * BLADE_W / 2 + 0.03)
    # cutting edge (worn steel) and teeth
    P.t("steel").obox((0, BLADE_Y + 0.02, 0.10), (BLADE_W - 0.02, 0.06, 0.10), (0, 1, 0.25))
    for k in range(9):
        x = (k - 4) * 0.41
        P.obox((x, BLADE_Y + 0.10, 0.10), (0.12, 0.30, 0.07), (0, 1, -0.25))
    P.t("camo")


def build(ctx):
    mat, o = ctx.mat, ctx.objs
    d = C["deck"]
    # ------------------------------------------------------------ hull
    H = TPart("Hull")
    ik.t72_hull(H, C)
    # armoured casemate (crew compartment) on the left / rear of the deck
    H.slab([(-1.62, 0.35), (0.50, 0.35), (0.50, -3.15), (-1.62, -3.15)], d,
           [(-1.52, -0.05), (0.40, -0.05), (0.40, -3.05), (-1.52, -3.05)], 2.30)
    shell = ik.build(H, mat, bevel=0.025)
    D = TPart("HullDetail")
    ik.t72_skirts(D, C, kind="plain", y0=2.25)
    ik.t72_details(D, C, rear_log=False, drums=False, louvres=False, fender_boxes=False, exhaust=False)
    for s in (-1, 1):
        for (y, z, r) in C["track"].rollers:
            D.t("metal").cyl((s * C["track"].track_x, y, z), r, 0.3, (0, PI / 2, 0), seg=10)
    D.t("camo")
    # casemate details: vision blocks, hatches, side stowage, grille on the right rear deck, exhaust
    for x in (-1.10, -0.55, 0.0):
        D.t("glass").obox((x, 0.18, 1.88), (0.26, 0.03, 0.10), (0, 0.72, 0.69))
    D.t("camo")
    ik.hatch(D, (-1.05, -1.40, 2.30), 0.30)
    D.box((-0.55, -2.40, 2.33), (0.80, 0.70, 0.06))
    for s_y in (-0.8, -1.9):
        D.box((-1.72, s_y, 1.85), (0.16, 0.80, 0.45))
    D.t("grille").box((1.05, -2.30, d + 0.02), (1.00, 1.40, 0.04))
    D.t("dark").box((1.40, -1.30, d + 0.08), (0.30, 0.45, 0.14))
    D.t("camo")
    # rear stowage cage (right rear)
    D.t("metal")
    for x in (0.70, 1.55):
        for y in (-2.95, -3.40):
            D.beam((x, y, d), (x, y, d + 0.55), 0.035, 0.035)
    for z in (d + 0.28, d + 0.55):
        D.beam((0.70, -2.95, z), (1.55, -2.95, z), 0.03, 0.03); D.beam((0.70, -3.40, z), (1.55, -3.40, z), 0.03, 0.03)
        D.beam((0.70, -2.95, z), (0.70, -3.40, z), 0.03, 0.03); D.beam((1.55, -2.95, z), (1.55, -3.40, z), 0.03, 0.03)
    D.t("canvas").box((1.12, -3.18, d + 0.20), (0.75, 0.38, 0.36))
    D.t("camo")
    # spare track links on the glacis, front winch drum
    for k, x in enumerate((-0.80, -0.40)):
        D.t("metal").obox((x, 2.75, 1.21), (0.36, 0.16, 0.05), (0, 0.30, 0.95))
    D.t("dark").tube((0.65, 2.70, 1.40), 0.20, 0.70, "x", seg=14)
    D.t("metal").tube((0.65, 2.70, 1.40), 0.21, 0.04, "x", seg=14)
    D.t("camo")
    # blade + push arms + lift rams
    blade(D)
    for s in (-1, 1):
        D.beam((s * 1.50, BLADE_Y - 0.25, 0.45), (s * 1.80, 1.60, 0.72), 0.12, 0.16)
        D.t("metal").rod((s * 0.95, BLADE_Y - 0.25, 0.95), (s * 0.95, 2.95, 1.18), 0.07, seg=8)
        D.t("steel").rod((s * 0.95, BLADE_Y - 0.25, 0.95), (s * 0.95, 3.40, 1.06), 0.045, seg=8)
        D.t("camo").box((s * 0.95, 2.92, 1.18), (0.18, 0.14, 0.18))
    # crane: turntable on the right front deck, boom rising forward, hydraulic ram, chain and hook
    cx, cy0, cz0 = 1.05, 0.95, d
    D.cyl((cx, cy0, cz0 + 0.12), 0.55, 0.24, seg=20)
    D.box((cx, cy0 - 0.05, cz0 + 0.50), (0.60, 0.70, 0.55))
    piv = (cx, cy0 - 0.15, cz0 + 0.70)
    tip = (cx, 3.05, 3.70)
    D.beam(piv, tip, 0.30, 0.34)
    mid = tuple(piv[i] + (tip[i] - piv[i]) * 0.45 for i in range(3))
    D.beam(mid, tip, 0.22, 0.26)                                                  # telescopic inner section
    D.box((cx, tip[1] + 0.08, tip[2] - 0.05), (0.26, 0.30, 0.34))                 # sheave head
    D.t("metal").rod((cx, cy0 + 0.30, cz0 + 0.45), tuple(piv[i] + (tip[i] - piv[i]) * 0.38 + (-0.12 if i == 2 else 0)
                                                         for i in range(3)), 0.085, seg=8)
    D.t("steel").rod((cx, cy0 + 0.70, cz0 + 0.90), tuple(piv[i] + (tip[i] - piv[i]) * 0.38 + (-0.12 if i == 2 else 0)
                                                         for i in range(3)), 0.055, seg=8)
    D.t("chain")
    zc = tip[2] - 0.25
    for k in range(7):
        z = zc - k * 0.13
        D.obox((cx, tip[1] + 0.12, z), (0.03 if k % 2 else 0.10, 0.03 if k % 2 == 0 else 0.10, 0.15), (0, 1, 0))
    hz = zc - 7 * 0.13
    D.t("metal").box((cx, tip[1] + 0.12, hz - 0.05), (0.16, 0.10, 0.18))
    D.t("chain").cyl((cx, tip[1] + 0.12, hz - 0.28), 0.12, 0.05, (0, PI / 2, 0), seg=10)
    D.t("camo")
    for s in (-1, 1):
        ik.light_cluster(D, (s * 1.42, 3.05, 1.17), facing=1, w=0.22, h=0.13)
    ik.antenna(D, (-1.35, -2.80, 2.30), 2.0)
    det = ik.build(D, mat)
    o["Hull"] = ik.join(shell, [det])

    # ------------------------------------------------------------ small MG mount (Turret > Gun > Muzzle)
    T = TPart("Turret")
    mx, my, mz = MG_O
    T.cyl((mx, my, mz + 0.05), 0.34, 0.10, seg=18)
    T.box((mx, my, mz + 0.22), (0.20, 0.25, 0.30))
    T.obox((mx, my + 0.22, mz + 0.42), (0.62, 0.05, 0.36), (0, 1, 0.1))           # gun shield
    tur = ik.build(T, mat)
    ik.set_origin(tur, MG_O)
    o["Turret"] = tur
    G = TPart("Gun")
    gx, gy, gz = MG_TRUNNION
    G.t("metal").box((gx, gy + 0.10, gz), (0.11, 0.55, 0.13))
    G.tube((gx, (gy + 0.37 + MG_MUZZLE_Y) / 2, gz), 0.024, MG_MUZZLE_Y - gy - 0.37, "y", seg=6)
    G.box((gx + 0.10, gy + 0.05, gz - 0.04), (0.10, 0.20, 0.12))
    gun = ik.build(G, mat, smooth=40)
    ik.set_origin(gun, MG_TRUNNION); ik.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = ik.empty("Muzzle", (gx, MG_MUZZLE_Y + 0.01, gz), parent=gun)

    left_gear = ik.t72_gear(ctx, C)

    # ------------------------------------------------------------ team colour panels
    th = TPart("TeamHull")
    th.box((-1.635, -1.40, 2.05), (0.02, 1.80, 0.12))          # casemate left side
    th.box((0.515, -1.80, 2.05), (0.02, 1.80, 0.12))           # casemate right side
    for s in (-1, 1):
        th.box((s * 1.775, -1.90, 1.28), (0.02, 1.5, 0.10))   # skirts
    th.box((cx, (cy0 + tip[1]) / 2 + 0.35, (cz0 + tip[2]) / 2 + 0.55), (0.32, 0.6, 0.02))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(ik.vk.mirror_gear(objs, left_gear))

    cfg = dict(
        seams_y=[2.05, -1.20], seams_z=[1.85], seams_x=[], skirt_pitch=0.95, skirt_y0=2.25,
        skirt_bolt_z=(1.38, None), mud_h=1.05, camo_scale=1.5, seed=17,
        decals=[dict(kind="flag", axis="-x", c=(-0.25, 1.95), size=(0.42, 0.26), obj="Hull", depth=-1.585, dtol=0.06),
                dict(kind="flag", axis="+y", c=(-0.55, 2.10), size=(0.36, 0.22), obj="Hull"),
                dict(kind="rect", axis="+x", c=(-0.90, 1.85), size=(0.80, 0.60), obj="Hull", depth=0.45, dtol=0.06),
                dict(kind="rect", axis="-y", c=(0.0, 1.00), size=(1.20, 0.55), obj="Hull", depth=C["rear"], dtol=0.08),
                dict(kind="ring", c=(0.0, 2.02, d + 0.05), r=0.36, obj="Hull")],
    )
    return dict(
        uv=["Hull", "Turret", "Gun"] + left_gear, post_uv=post_uv, tracks=C["track"],
        roots=["Hull", "Turret"] + ik.gear_roots(6), hubs=ik.gear_hubs(ctx, left_gear, C), cfg=cfg,
        preview=dict(length=8.0, width=3.8, height=4.0, rts_dist=21, close_dist=15, close_az=-40),
        extra=[f"MG mount pivot {MG_O}, trunnion {MG_TRUNNION}, muzzle y {MG_MUZZLE_Y}",
               f"blade cutting edge y {BLADE_Y} (teeth to ~{BLADE_Y + 0.24:.2f}), blade width {BLADE_W} m, hull rear "
               f"{C['rear']}; crane boom pivot {tuple(round(v, 2) for v in piv)}, tip {tip}",
               f"road wheel r {C['track'].wheel_r}, idler (front) r {C['track'].idler[2]}, "
               f"sprocket (rear) r {C['track'].sprocket[2]}"],
    )


if __name__ == "__main__":
    ik.run(VID, build, "Steel Accord Iran W1 - combat engineer / recovery dozer (ir_engineer_dozer) - Cycles CPU preview")
