"""Steel Accord - Iran wave 1 - BMP-2-style infantry fighting vehicle, 3D (bpy 5.x). Kit: tools/art/vehkit_ir.py.

Run:  python3 tools/art/veh_ir_bmp2_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Out:  godot/assets/units3d/ir_bmp2/ir_bmp2.glb (+ ir_bmp2_albedo.png, ir_bmp2_track.png copies)
Reference: docs/reference/iran_pack/01_ground_vehicle_catalog.png panel 05 (perspective concept; silhouette and
camouflage only). Real-size authoring: hull 6.72 m, 3.15 m wide, 2.15 m to the turret roof (ATGM / sights ~2.45 m).
Long shallow ribbed glacis, drive sprocket at the FRONT, idler at the rear, 6 road wheels, two-man turret with a
30 mm-class autocannon and a roof ATGM tube, rear troop doors.
Nodes: Hull, Turret (yaw) > Gun (trunnion) > Muzzle, WheelL0..5/WheelR0..5, SprocketL/R (front), IdlerL/R (rear),
TrackL/TrackR (SA_TrackScroll).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit_ir as ik  # noqa: E402
from vehkit_ir import TPart, PI  # noqa: E402

VID = "ir_bmp2"
NOSE, REAR = 3.36, -3.36
TRACK = ik.vk.TrackSpec(track_x=1.36, width=0.32, thick=0.08, wheel_r=0.33,
                        wheel_ys=[2.05, 1.30, 0.55, -0.20, -0.95, -1.75],
                        idler=(-2.86, 0.50, 0.26), sprocket=(2.86, 0.62, 0.25),
                        rollers=[(1.68, 0.86, 0.075), (0.18, 0.86, 0.075), (-1.35, 0.86, 0.075)],
                        pitch=0.14, links_per_tile=6, wheel_w=0.12, wheel_gap=0.085, sprocket_teeth=13)
CY = 0.40
TURRET_O = (0.0, CY, 1.62)
TRUNNION = (0.0, CY + 0.62, 1.98)
MUZZLE_Y = 3.98
HW = 1.55


def usect(hw, z0, zs, z1, t):
    """6-vertex section: vertical side from z0 to zs, sloped upper side to the roof (half-width t) at z1."""
    return [(-hw, z0), (hw, z0), (hw, zs), (t, z1), (-t, z1), (-hw, zs)]


def build(ctx):
    mat, o = ctx.mat, ctx.objs
    # ------------------------------------------------------------ hull
    H = TPart("Hull")
    H.loft([(NOSE, usect(1.38, 0.82, 0.86, 0.88, 1.34)),
            (2.70, usect(HW, 1.05, 1.12, 1.14, 1.50)),
            (1.30, usect(HW, 1.05, 1.30, 1.62, 1.22)),
            (-2.95, usect(HW, 1.05, 1.30, 1.62, 1.22)),
            (REAR, usect(HW, 1.05, 1.30, 1.48, 1.22))])
    H.side([(2.95, 0.42), (3.30, 0.80), (3.05, 0.97), (2.60, 1.10), (REAR + 0.06, 1.10), (REAR + 0.06, 0.55),
            (REAR + 0.32, 0.42)], -1.18, 1.18)
    shell = ik.build(H, mat, bevel=0.02, smooth=12)
    D = TPart("HullDetail")
    # glacis ribs (corrugated upper glacis) and folded trim vane on the nose
    for k in range(5):
        y = 3.22 - k * 0.12
        z = 0.82 + (NOSE - y) / (NOSE - 2.70) * 0.32 + 0.02
        D.t("camo").box((0, y, z), (2.4, 0.04, 0.05))
    D.obox((0, NOSE + 0.04, 0.70), (2.5, 0.05, 0.30), (0, 0.6, 1.0))
    # side skirts along the track top
    for s in (-1, 1):
        D.t("skirt").box((s * (HW + 0.02), -0.10, 0.98), (0.035, 5.70, 0.26))
    # driver's and commander's hatches (front left), troop roof hatches, firing ports
    D.t("camo")
    D.obox((-0.62, 1.62, 1.50), (0.50, 0.55, 0.06), (0, 0.94, 0.33))                # driver's hatch on the glacis
    D.t("glass").obox((-0.62, 1.93, 1.43), (0.30, 0.04, 0.08), (0, 0.6, 0.8))
    D.t("camo")
    for s in (-1, 1):
        for y in (-0.95, -1.95):
            D.box((s * 0.55, y, 1.645), (0.62, 0.80, 0.05))
        for y in (0.2, -0.6, -1.4):
            D.t("dark").tube((s * (HW + 0.02), y, 1.21), 0.06, 0.06, "x", seg=10)
            D.t("camo").tube((s * (HW + 0.01), y, 1.21), 0.10, 0.03, "x", seg=12)
    # rear doors (two, with stowage-type bulges) + tail lights
    for s in (-1, 1):
        D.box((s * 0.42, REAR + 0.02, 0.88), (0.72, 0.10, 0.80))
        D.t("redlens").box((s * 1.30, REAR - 0.01, 1.28), (0.10, 0.04, 0.07))
        D.t("metal").box((s * 0.42, REAR - 0.04, 0.88), (0.10, 0.04, 0.10))
        D.t("camo")
    # headlights and front tow hooks
    for s in (-1, 1):
        ik.light_cluster(D, (s * 1.25, 2.72, 1.24), facing=1, w=0.16, h=0.13, n=1)
        D.t("metal").box((s * 0.6, 3.05, 0.82), (0.12, 0.12, 0.10))
    # exhaust on the right sponson, stowage boxes on the rear fenders
    D.t("dark").box((HW - 0.05, 1.10, 1.20), (0.12, 0.40, 0.16))
    D.t("camo")
    for s in (-1, 1):
        D.box((s * 1.30, -2.60, 1.70), (0.42, 0.70, 0.18))
    # return rollers
    for s in (-1, 1):
        for (y, z, r) in TRACK.rollers:
            D.t("metal").cyl((s * TRACK.track_x, y, z), r, 0.2, (0, PI / 2, 0), seg=10)
    ik.antenna(D, (-1.20, -2.20, 1.62), 1.8)
    det = ik.build(D, mat)
    o["Hull"] = ik.join(shell, [det])

    # ------------------------------------------------------------ turret (origin on the yaw axis)
    T = TPart("Turret")
    oct_ = lambda r, ry: [(r * math.sin(2 * PI * (k + 0.5) / 8), CY + ry * math.cos(2 * PI * (k + 0.5) / 8))
                          for k in range(8)]
    T.slab(oct_(1.00, 1.05), 1.64, oct_(0.74, 0.80), 2.13)
    T.cyl((0, CY, 1.65), 1.02, 0.06, seg=24)
    tshell = ik.build(T, mat, bevel=0.02)
    TD = TPart("TurretDetail")
    # mantlet housing in the front face
    TD.slab([(-0.36, CY + 0.70), (0.36, CY + 0.70), (0.36, CY + 0.95), (-0.36, CY + 0.95)], 1.80,
            [(-0.30, CY + 0.70), (0.30, CY + 0.70), (0.30, CY + 0.88), (-0.30, CY + 0.88)], 2.14)
    # gunner's sight (right) and commander's sight (left)
    TD.box((0.38, CY + 0.28, 2.24), (0.26, 0.30, 0.22))
    TD.t("glass").box((0.38, CY + 0.435, 2.25), (0.18, 0.02, 0.12))
    TD.t("camo").cyl((-0.36, CY - 0.05, 2.20), 0.22, 0.14, seg=14)
    TD.box((-0.36, CY + 0.02, 2.33), (0.22, 0.22, 0.14))
    TD.t("glass").box((-0.36, CY + 0.135, 2.33), (0.16, 0.02, 0.08))
    TD.t("camo")
    ik.hatch(TD, (-0.36, CY - 0.05, 2.27), 0.18, h=0.03, hinge=False)
    # ATGM launch tube on a bracket (right rear of the roof), static part of the turret
    TD.box((0.55, CY - 0.10, 2.22), (0.10, 0.16, 0.20))
    TD.t("olive").tube((0.62, CY + 0.05, 2.40), 0.085, 1.15, "y", seg=12)
    TD.t("dark").tube((0.62, CY + 0.625, 2.40), 0.07, 0.01, "y", seg=12)
    TD.t("metal").box((0.62, CY - 0.10, 2.32), (0.18, 0.06, 0.08))
    TD.t("camo")
    # smoke-grenade cluster (left rear), two rows of 3
    ik.smoke_launchers(TD, (-0.80, CY - 0.30, 2.05), 3, yaw=-70, pitch=0.6, spacing=0.12, rows=2)
    ik.smoke_launchers(TD, (0.80, CY - 0.30, 2.05), 3, yaw=70, pitch=0.6, spacing=0.12, rows=1)
    # turret rear stowage box (flat faces carry the team colour)
    TD.box((0, CY - 0.82, 1.86), (1.10, 0.26, 0.30))
    ik.antenna(TD, (-0.55, CY - 0.60, 2.10), 1.6)
    tdet = ik.build(TD, mat)
    tur = ik.join(tshell, [tdet])
    ik.set_origin(tur, TURRET_O)
    o["Turret"] = tur

    # ------------------------------------------------------------ gun: 30 mm autocannon + coaxial MG
    G = TPart("Gun")
    ty, tz = TRUNNION[1], TRUNNION[2]
    G.t("camo").box((0, ty + 0.22, tz), (0.30, 0.30, 0.26))
    G.t("barrel")
    Lb = MUZZLE_Y - ty
    ik.gun_barrel(G, ty, tz, [(0.37, 0.085), (0.95, 0.075), (1.00, 0.05), (Lb - 0.22, 0.045), (Lb - 0.22, 0.062),
                              (Lb, 0.062), (Lb, 0.03)], seg=12)
    G.t("dark").tube((0, MUZZLE_Y - 0.004, tz), 0.025, 0.01, "y", seg=8)
    G.t("metal").tube((0.20, ty + 0.55, tz - 0.04), 0.022, 0.40, "y", seg=6)
    G.t("camo")
    gun = ik.build(G, mat, smooth=40)
    ik.set_origin(gun, TRUNNION)
    ik.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = ik.empty("Muzzle", (0, MUZZLE_Y + 0.02, tz), parent=gun)

    gear = ik.vk.build_running_gear(TRACK, mat)
    o.update(gear)
    left_gear = list(gear.keys())

    # ------------------------------------------------------------ team colour panels
    tm = TPart("TeamTurret")
    tm.box((0, CY - 0.96, 1.86), (0.9, 0.02, 0.10))
    for s in (-1, 1):
        tm.box((s * 0.56, CY - 0.82, 1.86), (0.02, 0.20, 0.10))
    ctx.team.append(("Turret", tm))
    th = TPart("TeamHull")
    for s in (-1, 1):
        th.box((s * (HW + 0.01), -2.10, 1.20), (0.02, 1.3, 0.12))
    ctx.team.append(("Hull", th))

    def post_uv(objs):
        objs.update(ik.vk.mirror_gear(objs, left_gear))

    hubs = {}
    for nm in left_gear:
        ob = o[nm]
        r = TRACK.wheel_r if nm.startswith("Wheel") else (TRACK.idler[2] if nm.startswith("Idler") else TRACK.sprocket[2])
        kind = "road" if nm.startswith("Wheel") else ("idler" if nm.startswith("Idler") else "sprocket")
        hubs[nm] = ((ob.location.y, ob.location.z, r, None), kind)
    cfg = dict(
        seams_y=[1.30, -0.55, -2.95], seams_x=[0.95], skirt_pitch=0.95, skirt_y0=2.75, skirt_bolt_z=(1.07, None),
        mud_h=0.95, camo_scale=1.3, seed=5,
        decals=[dict(kind="flag", axis=ax, c=(-0.55, 1.19), size=(0.36, 0.20), obj="Hull", depth=dx, dtol=0.03)
                for ax, dx in (("-x", -HW), ("+x", HW))] + [
            dict(kind="louvre", axis="+z", c=(0.62, 2.00), size=(0.75, 0.95), pitch=0.07, dir="v", obj="Hull"),
            dict(kind="rect", axis="+z", c=(-0.62, 0.20), size=(0.70, 0.55), obj="Hull"),
        ],
    )
    return dict(
        uv=["Hull", "Turret", "Gun"] + left_gear, post_uv=post_uv, tracks=TRACK,
        roots=["Hull", "Turret"] + ik.gear_roots(6), hubs=hubs, cfg=cfg,
        preview=dict(length=7.2, width=3.2, height=2.5, rts_dist=17, close_dist=12, close_az=-40),
        extra=[f"turret pivot {TURRET_O}, gun trunnion {TRUNNION}, muzzle y {MUZZLE_Y}",
               "hull 6.72 m (nose 3.36 .. rear -3.36), 3.15 m wide, turret roof 2.13 m, ATGM tube top 2.49 m",
               f"road wheel r {TRACK.wheel_r}, sprocket (front) r {TRACK.sprocket[2]}, idler (rear) r {TRACK.idler[2]}"],
    )


if __name__ == "__main__":
    ik.run(VID, build, "Steel Accord Iran W1 - BMP-2-style IFV (ir_bmp2) - Cycles CPU preview")
