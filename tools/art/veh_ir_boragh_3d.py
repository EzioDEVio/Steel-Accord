"""Steel Accord - Iran wave 1 - 8x8 wheeled APC with remote weapon station ("Boragh" per the reference README),
3D (bpy 5.x). Kit: tools/art/vehkit_ir.py.

Run:  python3 tools/art/veh_ir_boragh_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/ir_boragh/ir_boragh.glb (+ ir_boragh_albedo.png copy)
Reference: docs/reference/iran_pack/01_ground_vehicle_catalog.png panel 06 (perspective concept; silhouette and
camouflage only). Note: the real vehicle of that name is tracked; this model follows the wheeled panel as asked.
Real-size authoring: 7.6 m long, 2.84 m body / 2.98 m over tyres, 2.20 m to the roof, RWS to ~2.95 m.
Nodes: Hull, Turret (RWS base, yaw) > Gun (cradle + MG, pitch) > Muzzle; SteerFL/FR > WheelFL/FR,
SteerML/MR > WheelML/MR, WheelM2L/M2R, WheelRL/RR (hub origins, spin about local X; Steer empties yaw).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit_ir as ik  # noqa: E402
from vehkit_ir import TPart, PI  # noqa: E402

VID = "ir_boragh"
NOSE, REAR = 3.80, -3.80
WR, TW, RIM = 0.58, 0.42, 0.33
WX = 1.28
AXLES = [("F", 2.40), ("M", 1.05), ("M2", -0.75), ("R", -2.10)]
RING = (0.0, 0.10, 2.20)
TRUNNION = (0.10, 2.66)          # (y, z)
MUZZLE_Y = 1.62
HW = 1.42


def bsect(b, zb, lo, zc, zsh, hw, zs, z1, t):
    """12-vertex hull section: V belly, narrow lower hull between the wheels, overhanging upper body (sponson)
    with a sloped roof edge."""
    return [(-b, zb), (b, zb), (lo, zc), (lo, zsh), (hw, zsh), (hw, zs), (t, z1),
            (-t, z1), (-hw, zs), (-hw, zsh), (-lo, zsh), (-lo, zc)]


def build(ctx):
    mat, o = ctx.mat, ctx.objs
    # ------------------------------------------------------------ hull
    H = TPart("Hull")
    mid = bsect(0.70, 0.55, 1.0, 0.85, 1.22, HW, 1.80, 2.20, 1.18)
    H.loft([(NOSE, bsect(0.55, 0.85, 0.80, 0.95, 1.20, 1.15, 1.35, 1.45, 1.05)),
            (3.40, bsect(0.70, 0.62, 1.0, 0.85, 1.22, HW, 1.55, 1.78, 1.25)),
            (2.10, mid), (-3.50, mid),
            (REAR, bsect(0.70, 0.65, 1.0, 0.88, 1.22, 1.38, 1.75, 2.10, 1.15))])
    shell = ik.build(H, mat, bevel=0.02, smooth=12)
    D = TPart("HullDetail")
    # driver / commander vision windows on the glacis
    for s in (-1, 1):
        D.t("glass").obox((s * 0.48, 2.86, 2.00), (0.62, 0.03, 0.30), (0, 0.32, 0.95))
    D.t("camo")
    # headlight clusters, tow eyes, front bumper bar
    for s in (-1, 1):
        ik.light_cluster(D, (s * 0.80, NOSE + 0.02, 1.30), facing=1, w=0.26, h=0.12)
        D.t("metal").box((s * 0.55, NOSE + 0.02, 1.05), (0.14, 0.10, 0.10))
        D.t("redlens").box((s * 1.15, REAR - 0.02, 1.85), (0.12, 0.04, 0.07))
        D.t("camo")
    # wheel-arch flaps between the axles (vertical plates under the sponson)
    for s in (-1, 1):
        for y, w in ((0.15, 0.40), (-2.95, 0.30), (3.12, 0.20)):
            D.box((s * 1.36, y, 1.05), (0.10, w, 0.34))
    # side door outline bulge, vision blocks, grab rails, stowage boxes
    for s in (-1, 1):
        for y in (0.6, -0.6, -1.8):
            D.t("glass").box((s * (HW + 0.005), y, 1.88), (0.02, 0.18, 0.08))
        D.t("metal").beam((s * (HW + 0.04), -0.2, 1.62), (s * (HW + 0.04), -2.6, 1.62), 0.03, 0.03)
        D.t("camo").box((s * (HW + 0.06), 2.35, 1.48), (0.12, 0.70, 0.36))
    # rear ramp (slightly proud), rear stowage
    D.box((0, REAR + 0.01, 1.30), (1.60, 0.10, 1.10))
    D.t("metal").box((0.55, REAR - 0.05, 1.30), (0.10, 0.04, 0.12))
    D.t("camo")
    # roof: hatches, two sensor / sight boxes on the front corners, exhaust grille right
    for s in (-1, 1):
        D.box((s * 0.85, 1.85, 2.34), (0.36, 0.32, 0.28))
        D.t("glass").box((s * 0.85, 2.015, 2.35), (0.26, 0.02, 0.16))
        D.t("camo")
        D.box((s * 0.55, -1.60, 2.225), (0.70, 0.95, 0.05))
    ik.hatch(D, (-0.55, 2.35, 2.12), 0.26)
    D.t("grille").box((1.02, 1.05, 2.21), (0.30, 0.90, 0.04))
    D.t("camo")
    ik.antenna(D, (-1.05, -2.90, 2.15), 2.0)
    ik.antenna(D, (1.05, -2.90, 2.15), 1.6)
    det = ik.build(D, mat)
    o["Hull"] = ik.join(shell, [det])

    # ------------------------------------------------------------ RWS: Turret = base + sensor + ammo, Gun = cradle + MG
    rx, ry, rz = RING
    gy, gz = TRUNNION
    T = TPart("Turret")
    T.cyl((rx, ry, rz + 0.06), 0.42, 0.12, seg=20)
    T.box((rx, ry - 0.05, rz + 0.30), (0.56, 0.70, 0.40))
    T.box((rx + 0.40, gy + 0.05, gz + 0.05), (0.24, 0.52, 0.40))                    # sensor head (right)
    T.t("glass").box((rx + 0.40, gy + 0.315, gz + 0.08), (0.18, 0.02, 0.22))
    T.t("camo").box((rx - 0.38, gy - 0.05, gz - 0.06), (0.24, 0.48, 0.30))          # ammo box (left)
    for s in (-1, 1):
        T.box((rx + s * 0.18, gy, gz - 0.06), (0.04, 0.42, 0.36))
    ik.smoke_launchers(T, (rx, ry - 0.42, rz + 0.40), 4, yaw=180, pitch=0.5, spacing=0.11)
    tur = ik.build(T, mat)
    ik.set_origin(tur, RING)
    o["Turret"] = tur
    G = TPart("Gun")
    G.t("metal").box((rx, gy, gz), (0.20, 0.70, 0.18))
    G.tube((rx, gy + 0.50, gz), 0.05, 0.30, "y", seg=10)
    G.tube((rx, (gy + 0.65 + MUZZLE_Y) / 2, gz), 0.03, MUZZLE_Y - gy - 0.65, "y", seg=8)
    G.tube((rx, MUZZLE_Y - 0.06, gz), 0.045, 0.12, "y", seg=8)
    gun = ik.build(G, mat, smooth=40)
    ik.set_origin(gun, (rx, gy, gz)); ik.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = ik.empty("Muzzle", (rx, MUZZLE_Y + 0.01, gz), parent=gun)

    # ------------------------------------------------------------ wheels (left authored; right mirrored after UV)
    left = []
    for suf, y in AXLES:
        nm = f"Wheel{suf}L"
        o[nm] = ik.vk.tyre_part(nm, WR, TW, RIM, outer=-1, seg=24).build(mat, bevel=0.0, smooth=50,
                                                                        location=(-WX, y, WR))
        left.append(nm)

    # ------------------------------------------------------------ team colour panels
    th = TPart("TeamHull")
    for s in (-1, 1):
        th.box((s * (HW + 0.01), -1.20, 1.45), (0.02, 1.80, 0.12))
    th.box((0, REAR - 0.045, 1.70), (1.2, 0.02, 0.10))
    ctx.team.append(("Hull", th))
    tm = TPart("TeamTurret")
    tm.box((rx - 0.51, gy - 0.05, gz - 0.06), (0.02, 0.36, 0.10))
    ctx.team.append(("Turret", tm))

    def post_uv(objs):
        ik.vk.finish_wheels(objs, left, steer=("FL", "FR", "ML", "MR"))

    hubs = {nm: ((o[nm].location.y, o[nm].location.z, WR, RIM), "tyre") for nm in left}
    cfg = dict(
        seams_y=[2.10, 0.95, -0.20, -2.40], seams_z=[1.50], seams_x=[0.75], mud_h=1.1, camo_scale=1.5, seed=11,
        decals=[dict(kind="flag", axis=ax, c=(1.45, 1.70), size=(0.40, 0.24), obj="Hull", depth=dx, dtol=0.03)
                for ax, dx in (("-x", -HW), ("+x", HW))] + [
            dict(kind="rect", axis="-y", c=(0.0, 1.30), size=(1.60, 1.10), obj="Hull", depth=REAR + 0.01 - 0.05,
                 dtol=0.06),
            dict(kind="rect", axis="+x", c=(-1.10, 1.62), size=(0.70, 0.70), obj="Hull", depth=HW, dtol=0.03),
            dict(kind="rect", axis="-x", c=(-1.10, 1.62), size=(0.70, 0.70), obj="Hull", depth=-HW, dtol=0.03),
            dict(kind="ring", c=(-0.55, 2.35, 2.17), r=0.30, obj="Hull"),
        ],
    )
    roots = ["Hull", "Turret", "SteerFL", "SteerFR", "SteerML", "SteerMR", "WheelM2L", "WheelM2R",
             "WheelRL", "WheelRR"]
    return dict(
        uv=["Hull", "Turret", "Gun"] + left, post_uv=post_uv, tracks=None, roots=roots, hubs=hubs, cfg=cfg,
        preview=dict(length=7.7, width=3.0, height=3.0, rts_dist=17, close_dist=12.5, close_az=-40),
        extra=[f"RWS ring {RING}, trunnion (y,z) {TRUNNION}, muzzle y {MUZZLE_Y}",
               f"wheel radius {WR} m, tyre width {TW} m, rim r {RIM}, wheel track x +-{WX}, axles y "
               + ", ".join(f"{s}:{y}" for s, y in AXLES),
               "8 wheels: WheelFL/FR, WheelML/MR, WheelM2L/M2R, WheelRL/RR; first two axles steer "
               "(SteerFL/FR, SteerML/MR empties)"],
    )


if __name__ == "__main__":
    ik.run(VID, build, "Steel Accord Iran W1 - 8x8 APC with RWS (ir_boragh) - Cycles CPU preview")
