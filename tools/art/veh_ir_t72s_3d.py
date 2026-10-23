"""Steel Accord - Iran wave 1 - T-72S-style main battle tank with explosive reactive armour, 3D (bpy 5.x).
Kit: tools/art/vehkit_ir.py.

Run:  python3 tools/art/veh_ir_t72s_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/ir_t72s/ir_t72s.glb (+ ir_t72s_albedo.png, ir_t72s_track.png copies)
Reference: docs/reference/iran_pack/01_ground_vehicle_catalog.png panel 03 (perspective concept; silhouette and
camouflage only). Real-size authoring: hull 6.9 m, 9.5 m with gun forward, 3.55 m over the skirts, 2.2 m to the
dome roof (cupola MG to ~2.55 m). Cast dome turret with brick-style ERA on the dome, glacis and front skirts,
rear fuel drums and unditching beam.
Nodes: Hull, Turret (yaw) > Gun (trunnion) > Muzzle, WheelL0..5/WheelR0..5, IdlerL/R (front), SprocketL/R (rear),
TrackL/TrackR (SA_TrackScroll).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit_ir as ik  # noqa: E402
from vehkit_ir import TPart, PI  # noqa: E402

VID = "ir_t72s"
C = ik.T72
CY = 0.30
TURRET_O = (0.0, CY, 1.42)
TRUNNION = (0.0, CY + 0.80, 1.88)
MUZZLE_Y = 6.05
# dome profile: (height above the deck, radius)
DOME = [(0.00, 1.10), (0.10, 1.13), (0.26, 1.10), (0.42, 0.98), (0.56, 0.78), (0.66, 0.52), (0.71, 0.26)]
SY_F, SY_R = 1.06, 1.14          # dome elongation forward / rearward


def dome_r(h):
    H = [p[0] for p in DOME]; R = [p[1] for p in DOME]
    return float(np.interp(h, H, R))


def dome_point(theta_deg, h):
    """Surface point and outward normal of the dome at azimuth theta (deg from +Y towards +X), height h."""
    th = math.radians(theta_deg)
    r = dome_r(h)
    dh = 0.02
    dr = (dome_r(h + dh) - dome_r(h - dh)) / (2 * dh)
    sy = SY_F if math.cos(th) > 0 else SY_R
    p = (r * math.sin(th), CY + r * math.cos(th) * sy, C["deck"] + h)
    radial = np.array([math.sin(th), math.cos(th) / sy, 0.0]); radial /= np.linalg.norm(radial)
    n = radial * 1.0 + np.array([0, 0, -dr])
    n /= np.linalg.norm(n)
    return np.array(p), n


def dome(T, seg=32):
    rings = []
    for h, r in DOME:
        ring = []
        for k in range(seg):
            a = 2 * PI * k / seg
            sy = SY_F if math.cos(a) > 0 else SY_R
            ring.append((r * math.sin(a), CY + r * math.cos(a) * sy, C["deck"] + h))
        rings.append(ring)
    T.rings(rings, caps=True)


def build(ctx):
    mat, o = ctx.mat, ctx.objs
    d = C["deck"]
    # ------------------------------------------------------------ hull
    H = TPart("Hull")
    ik.t72_hull(H, C)
    shell = ik.build(H, mat, bevel=0.02)
    D = TPart("HullDetail")
    ik.t72_skirts(D, C, kind="rubber", y0=2.35)
    ik.t72_details(D, C, rear_log=True, drums=True, rear_boxes=False)
    # glacis ERA (rows of bricks on the upper glacis)
    gl = np.array([C["nose"], 0.98]); gr = np.array([C["glacis_y"], d])
    tang = (gr - gl) / np.linalg.norm(gr - gl)
    nrm = np.array([-tang[1], tang[0]]) if tang[0] < 0 else np.array([tang[1], -tang[0]])
    nrm = np.array([abs(nrm[0]), abs(nrm[1])]) * np.array([1, 1])          # points forward-up
    L = np.linalg.norm(gr - gl)
    for t in (0.18, 0.42, 0.66):
        py, pz = gl + tang * L * t + nrm * 0.045
        for k in range(-5, 6):
            x = k * 0.285
            if t > 0.6 and abs(x) < 0.4:
                continue
            D.t("era").obox((x, py, pz), (0.26, 0.07, 0.30), (0, nrm[0], nrm[1]))
    # skirt ERA on the front part of the rubber side skirts
    xs = C["half_hi"] + 0.02 + 0.0175 + 0.035
    for s in (-1, 1):
        for z in (0.98, 1.26):
            for k in range(8):
                D.t("era").box((s * xs, 2.05 - k * 0.29, z), (0.07, 0.26, 0.24))
    for s in (-1, 1):
        for (y, z, r) in C["track"].rollers:
            D.t("metal").cyl((s * C["track"].track_x, y, z), r, 0.3, (0, PI / 2, 0), seg=10)
    # snorkel tube stowed along the rear left of the deck
    D.t("olive").tube((-0.95, -2.95, d + 0.10), 0.09, 1.0, "x", seg=8)
    det = ik.build(D, mat)
    o["Hull"] = ik.join(shell, [det])

    # ------------------------------------------------------------ turret: cast dome + ERA (origin on the yaw axis)
    T = TPart("Turret")
    dome(T)
    T.cyl((0, CY, d + 0.03), 1.16, 0.08, seg=28)
    tshell = ik.build(T, mat, smooth=50)
    TD = TPart("TurretDetail")
    # ERA bricks: lower front band, upper band, roof row (gap around the gun)
    for h, step, span, gap in ((0.16, 12.5, 82, 12), (0.38, 14.0, 70, 12), (0.58, 17.0, 52, 15)):
        th = -span
        while th <= span + 1e-6:
            if abs(th) >= gap:
                p, n = dome_point(th, h)
                c = p + n * 0.04
                TD.t("era").obox(tuple(c), (0.24 if h < 0.5 else 0.22, 0.07, 0.20), tuple(n))
            th += step
    TD.t("camo")
    # stowage boxes on the turret rear flanks (flat faces carry the team colour)
    for s in (-1, 1):
        TD.box((s * 1.02, CY - 0.75, 1.72), (0.30, 0.80, 0.34))
    # smoke dischargers, two banks of 4 on the front-left and front-right of the dome
    for s in (-1, 1):
        p, n = dome_point(s * 52, 0.40)
        ik.smoke_launchers(TD, tuple(p + n * 0.13), 4, yaw=s * 40, pitch=0.5, spacing=0.10, rows=1)
    # commander's cupola (right) with heavy MG; gunner's sight (left); IR searchlight right of the gun
    cx, cyy, cz = 0.45, CY - 0.15, d + 0.66
    TD.cyl((cx, cyy, cz + 0.06), 0.36, 0.14, seg=20)
    TD.cyl((cx, cyy, cz + 0.16), 0.30, 0.06, seg=20)
    for k in range(4):
        a = math.radians(-60 + k * 40)
        TD.t("glass").box((cx + 0.33 * math.sin(a), cyy + 0.33 * math.cos(a), cz + 0.08), (0.10, 0.06, 0.06))
    TD.t("metal").box((cx, cyy + 0.05, cz + 0.30), (0.10, 0.25, 0.20))
    TD.box((cx, cyy + 0.40, cz + 0.36), (0.12, 0.55, 0.12))
    TD.tube((cx, cyy + 1.05, cz + 0.36), 0.022, 0.80, "y", seg=6)
    TD.box((cx + 0.14, cyy + 0.30, cz + 0.30), (0.10, 0.25, 0.16))                # ammo box
    TD.t("camo")
    TD.box((-0.48, CY + 0.42, d + 0.70), (0.26, 0.30, 0.22))
    TD.t("glass").box((-0.48, CY + 0.575, d + 0.72), (0.18, 0.02, 0.10))
    TD.t("camo")
    ik.hatch(TD, (-0.42, CY - 0.30, d + 0.70), 0.30)
    TD.cyl((0.42, CY + 0.95, d + 0.48), 0.14, 0.24, (PI / 2, 0, 0), seg=14)
    TD.t("lens").tube((0.42, CY + 1.075, d + 0.48), 0.11, 0.02, "y", seg=14)
    TD.t("camo")
    ik.antenna(TD, (-0.70, CY - 0.70, d + 0.55), 2.1)
    TD.t("metal").box((0, CY - 1.20, d + 0.30), (0.9, 0.12, 0.10))              # rear rail
    TD.t("camo")
    tdet = ik.build(TD, mat)
    tur = ik.join(tshell, [tdet])
    ik.set_origin(tur, TURRET_O)
    o["Turret"] = tur

    # ------------------------------------------------------------ gun
    G = TPart("Gun")
    ty, tz = TRUNNION[1], TRUNNION[2]
    G.t("canvas")
    ik.lathe(G, (0, ty, tz), [(0.10, 0.26), (0.30, 0.27), (0.48, 0.20), (0.55, 0.15)], seg=14, axis="y")
    G.t("barrel")
    Lb = MUZZLE_Y - ty
    prof = [(0.50, 0.13), (1.40, 0.12), (1.44, 0.13), (2.30, 0.13), (2.35, 0.165), (2.95, 0.165), (3.00, 0.12),
            (3.70, 0.115), (3.74, 0.13), (3.80, 0.115), (4.40, 0.11), (4.44, 0.125), (4.50, 0.11),
            (Lb - 0.02, 0.105), (Lb, 0.105), (Lb, 0.06)]
    ik.gun_barrel(G, ty, tz, prof, seg=14)
    G.t("dark").tube((0, MUZZLE_Y - 0.005, tz), 0.07, 0.012, "y", seg=12)
    G.t("camo")
    gun = ik.build(G, mat, smooth=40)
    ik.set_origin(gun, TRUNNION)
    ik.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = ik.empty("Muzzle", (0, MUZZLE_Y + 0.02, tz), parent=gun)

    left_gear = ik.t72_gear(ctx, C)

    # ------------------------------------------------------------ team colour panels
    tm = TPart("TeamTurret")
    for s in (-1, 1):
        tm.box((s * 1.18, CY - 0.75, 1.76), (0.02, 0.70, 0.12))
    ctx.team.append(("Turret", tm))
    th = TPart("TeamHull")
    for s in (-1, 1):
        th.box((s * 1.77, -1.75, 1.28), (0.02, 1.5, 0.12))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(ik.vk.mirror_gear(objs, left_gear))

    sk = C["half_hi"] + 0.0375
    cfg = dict(
        seams_y=[2.05, -0.85], seams_x=[0.88], skirt_pitch=0.58, skirt_y0=2.35, skirt_bolt_z=(1.38, None),
        mud_h=1.0, camo_scale=1.4, seed=3,
        decals=[dict(kind="flag", axis=ax, c=(-0.55, 1.10), size=(0.40, 0.24), obj="Hull", depth=dx, dtol=0.03)
                for ax, dx in (("-x", -sk), ("+x", sk))] + [
            dict(kind="ring", c=(0.0, 2.02, d + 0.05), r=0.36, obj="Hull"),
            dict(kind="louvre", axis="+z", c=(0.0, -2.35), size=(1.66, 1.26), pitch=0.075, obj="Hull"),
            dict(kind="rect", axis="+z", c=(0.0, -1.25), size=(1.80, 0.70), obj="Hull"),
        ],
    )
    return dict(
        uv=["Hull", "Turret", "Gun"] + left_gear, post_uv=post_uv, tracks=C["track"],
        roots=["Hull", "Turret"] + ik.gear_roots(6), hubs=ik.gear_hubs(ctx, left_gear, C), cfg=cfg,
        preview=dict(length=9.6, width=3.6, height=2.7, rts_dist=21, close_dist=15, close_az=-40),
        extra=[f"turret pivot {TURRET_O}, gun trunnion {TRUNNION}, muzzle y {MUZZLE_Y}",
               "hull 6.90 m, 9.50 m with gun, 3.55 m over skirts+ERA, dome roof 2.13 m, cupola MG 2.44 m",
               f"road wheel r {C['track'].wheel_r}, idler (front) r {C['track'].idler[2]}, "
               f"sprocket (rear) r {C['track'].sprocket[2]}"],
    )


if __name__ == "__main__":
    ik.run(VID, build, "Steel Accord Iran W1 - T-72S-style MBT with ERA (ir_t72s) - Cycles CPU preview")
