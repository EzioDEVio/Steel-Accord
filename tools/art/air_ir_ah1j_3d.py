"""Steel Accord - Iran wave 1: AH-1J-style twin-engine attack helicopter (bpy 5.x).

Run:  python3 -I tools/art/air_ir_ah1j_3d.py [out_dir] [--no-previews] [--quick] [--sheet png]
Out:  godot/assets/units3d/ir_ah1j/ir_ah1j.glb (+ ir_ah1j_albedo.png, ir_ah1j_blade.png), docs/screens/ir_ah1j_sheet.png

Reference: iran_pack/02_aircraft_and_uav_catalog.png panel 09 (perspective concept: silhouette, desert camo,
fin flash). Authored from real-world proportions: fuselage ~13.6 m long and ~1 m wide, 2-blade main rotor
13.4 m diameter, height ~4.1 m, stub wings ~3.3 m span, skids, three-barrel chin cannon.
Nodes: Body (fuselage, stub wings + pods, skids, static mast, tail), RotorMain (2 blades; origin = hub; spins
about local Y in Godot), RotorTail (right side of the fin; origin = hub; local X is the shaft),
Gun (chin cannon barrels as a mesh, origin = turret pivot so the game's recoil offset moves the barrels),
Muzzle (barrel tip), Hardpoint0..3 (L outer, L inner, R inner, R outer pod centres).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402

K, L = A.K, A.L
import numpy as np  # noqa: E402

PI = math.pi

ID = "ir_ah1j"
Y_NOSE, Y_TAIL = 6.80, -6.80
HUB = (0.0, 0.70, 4.00)
R_MAIN = 6.70
TR_HUB = (0.30, -6.45, 3.00)
TURRET = (0.0, 5.55, 0.52)

ZTOP = A.fn([(6.80, 1.20), (6.55, 1.50), (6.15, 1.70), (5.0, 1.76), (2.6, 1.80), (2.3, 2.15), (1.9, 2.55), (1.4, 2.74),
             (0.0, 2.80), (-1.4, 2.72), (-2.4, 2.32), (-3.2, 1.98), (-4.2, 1.86), (-6.8, 1.76)])
ZBOT = A.fn([(6.80, 1.20), (6.55, 0.95), (6.1, 0.80), (4.5, 0.72), (0.0, 0.72), (-2.0, 0.86), (-3.0, 1.22), (-4.2, 1.45),
             (-6.8, 1.56)])
HW = A.fn([(6.80, 0.03), (6.6, 0.24), (6.2, 0.40), (5.4, 0.48), (0.0, 0.49), (-2.0, 0.45), (-3.0, 0.31), (-4.5, 0.22),
           (-6.8, 0.13)])
CAN_TOP = A.fn([(6.22, 1.66), (5.75, 2.02), (5.1, 2.18), (4.4, 2.21), (3.95, 2.40), (3.4, 2.52), (2.8, 2.52), (2.35, 2.25)])
CAN_HW = A.fn([(6.22, 0.12), (5.8, 0.38), (5.0, 0.45), (3.0, 0.45), (2.45, 0.30), (2.3, 0.12)])


def fin_le(z):
    return -5.4 - (1.15 / 1.7) * (z - 1.75)


def fin_te(z):
    return -6.85 - (0.3 / 1.7) * (z - 1.75)


def build(mat):
    objs = {}
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(Y_NOSE - 0.005, Y_NOSE - 0.9, 8), np.linspace(Y_NOSE - 1.0, Y_TAIL + 0.02, 34)])
    K.fuselage(F, ys, ZTOP, ZBOT, HW, n=lambda y: 2.6 + 0.8 * float(np.clip((Y_NOSE - y) / 1.2, 0, 1)), seg=28)
    # engine intakes and exhaust stacks on the hump
    for sg in (-1, 1):
        K.body_rev(F, (sg * 0.47, 1.55, 2.30), (sg * 0.47, 0.6, 2.30), [(0, 0.20), (0.3, 0.25), (1, 0.22)], seg=12)
        K.body_rev(F, (sg * 0.40, -1.3, 2.35), (sg * 0.52, -2.35, 2.55), [(0, 0.20), (0.6, 0.20), (1, 0.18)], seg=12)
    # static mast + transmission fairing
    F.rod((0, HUB[1], 2.7), (0, HUB[1], HUB[2] - 0.45), 0.13, seg=12)
    K.body_rev(F, (0, HUB[1], 2.7), (0, HUB[1], 3.15), [(0, 0.40), (0.6, 0.32), (1, 0.16)], seg=16)
    # stub wings (slight anhedral)
    zw = 1.35
    secs = [((0.40, 0.55, zw), (0.40, -0.50, zw), 0.14, (0, 0, 1)),
            ((1.64, 0.42, zw - 0.08), (1.64, -0.40, zw - 0.08), 0.12, (0, 0, 1))]
    K.surface(F, K.mirror_sections(secs[1:]) + secs)
    # elevators on the boom
    el = [((0.12, -3.55, 1.66), (0.12, -4.35, 1.66), 0.1, (0, 0, 1)), ((1.05, -3.85, 1.66), (1.05, -4.35, 1.66), 0.08, (0, 0, 1))]
    K.surface(F, K.mirror_sections(el[1:]) + el)
    # swept fin + tail-rotor gearbox + tail skid
    A.fin(F, (fin_le(1.70), 1.70), (fin_te(1.70), 1.70), (fin_le(3.45), 3.45), (fin_te(3.45), 3.45), t_root=0.14, t_tip=0.12)
    F.box((0.16, TR_HUB[1], TR_HUB[2]), (0.2, 0.3, 0.3))
    F.rod((0, -5.6, 1.55), (0, -6.0, 1.05), 0.03, seg=6)
    # chin turret housing
    K.body_rev(F, (TURRET[0], TURRET[1], TURRET[2] - 0.05), (TURRET[0], TURRET[1], TURRET[2] + 0.28),
               [(0, 0.24), (0.4, 0.30), (1, 0.26)], seg=16)
    # nose sight / pitot
    F.rod((-0.25, 6.3, 1.50), (-0.25, 7.1, 1.50), 0.025, seg=6)
    objs["air"] = F.build(mat, smooth=48)

    Gl = K.Part("Canopy")
    K.fuselage(Gl, np.linspace(6.22, 2.3, 18), CAN_TOP, lambda y: ZTOP(y) - 0.12, lambda y: max(float(CAN_HW(y)), 0.05),
               n=2.6, seg=22)
    objs["glass"] = Gl.build(mat, smooth=60)

    D = K.Part("Dark")
    for sg in (-1, 1):
        K.disc(D, (sg * 0.47, 1.56, 2.30), 0.17)
        K.disc(D, (sg * 0.52, -2.36, 2.55), 0.16)
    objs["dark"] = D.build(mat, smooth=40)

    Sx = K.Part("Stores")
    hard = []
    for sg in (-1, 1):
        lst = [(1.45, 0.17, 1.55), (0.88, 0.21, 1.70)]
        if sg > 0:
            lst = lst[::-1]
        for ax, r, ln in lst:
            x = sg * ax
            K.pylon(Sx, (x, 0.0, zw - 0.02), 0.6, 0.18, 0.08)
            zc = zw - 0.18 - r
            K.body_rev(Sx, (x, -ln / 2, zc), (x, ln / 2, zc), [(0, r * 0.85), (0.05, r), (0.9, r), (1, r * 0.7)], seg=14)
            hard.append((x, 0.0, zc))
    objs["stores"] = Sx.build(mat, smooth=40)

    # skids
    G = K.Part("Skids")
    for sg in (-1, 1):
        x = sg * 1.06
        pts = [(x, -1.7, 0.06), (x, 2.4, 0.06), (x, 2.75, 0.14), (x, 2.95, 0.32)]
        for a, b in zip(pts[:-1], pts[1:]):
            G.rod(a, b, 0.05, seg=8)
        for yc in (1.75, -0.65):
            G.rod((x, yc, 0.06), (sg * 0.98, yc, 0.45), 0.045, seg=8)
            G.rod((sg * 0.98, yc, 0.45), (sg * 0.38, yc, 0.76), 0.045, seg=8)
    objs["gear"] = G.build(mat, smooth=40)

    # chin gun: three barrels + breech, own node, origin at the turret pivot
    Gn = K.Part("Gun")
    zg = TURRET[2] - 0.06
    K.body_rev(Gn, (0, TURRET[1] - 0.1, zg), (0, TURRET[1] + 0.55, zg), [(0, 0.12), (0.6, 0.12), (1, 0.08)], seg=10)
    for k in range(3):
        a = PI / 2 + k * 2 * PI / 3
        Gn.rod((0.045 * math.cos(a), TURRET[1] + 0.5, zg + 0.045 * math.sin(a)),
               (0.045 * math.cos(a), TURRET[1] + 1.55, zg + 0.045 * math.sin(a)), 0.022, seg=6)
    Gn.cyl((0, TURRET[1] + 1.35, zg), 0.08, 0.06, (PI / 2, 0, 0), seg=10)
    objs["Gun"] = A.set_origin(Gn.build(mat, smooth=40), TURRET)

    Tm = K.Part("Team")
    A.fin(Tm, (fin_le(3.33), 3.33), (fin_te(3.33), 3.33), (fin_le(3.50), 3.50), (fin_te(3.50), 3.50), t_root=0.15, t_tip=0.13)
    for sg in (-1, 1):
        Tm.box((sg * 1.05, -4.1, 1.66), (0.06, 0.55, 0.13))
    objs["team"] = Tm.build(K.team_material(), smooth=40)

    empties = {"Muzzle": (0, TURRET[1] + 1.56, zg)}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def painter():
    fin_slab = lambda P: np.abs(P[:, 0]) < 0.2
    dec = A.fin_flash(-5.95, -6.62, 2.20, 2.62, -0.62, -0.25, fin_slab)
    for sg in (-1, 1):
        dec.append(A.Roundel((-0.9, 1.45), 0.30, "x", side=sg, slab=A.slab_absx(0.3, 0.6), objs=("air",)))
    zones = [(lambda P, N: (P[:, 1] < -1.2) & (P[:, 1] > -2.9) & (P[:, 2] > 2.0) & (np.abs(P[:, 0]) > 0.3),
              (0.22, 0.20, 0.18), ("air",))]                                     # exhaust soot
    return dict(scheme="desert", camo_scale=3.0, flat={"dark": K.DARK, "stores": (0.36, 0.38, 0.30), "gear": (0.62, 0.55, 0.38),
                                                        "Gun": (0.14, 0.14, 0.14)},
                glass={"glass": [5.78, 5.0, 4.0, 2.85]}, zones=zones, decals=dec,
                panel=dict(dy=0.9, lon_z=(1.25, 1.70), keys=("air",), k=0.83), seed=4, frame_w=0.05)


def main():
    o = A.parse_args(ID)
    L.reset_scene()
    mat = L.image_material("SA_IR_AH1J", None, rough=0.7)
    bmat = L.image_material("SA_IR_AH1J_Blade", None, rough=0.8)
    objs, empties = build(mat)
    rm = K.rotor("RotorMain", HUB, 2, R_MAIN, 0.69, bmat, root_r=0.55, phase=math.radians(30), hub_r=0.30,
                 coning=1.5, mast=0.45, thick=0.08)
    rt = K.rotor("RotorTail", TR_HUB, 2, 1.30, 0.21, bmat, root_r=0.14, axis="x", hub_r=0.1, coning=0,
                 twist=(6, 0), thick=0.04, phase=math.radians(70), sign_x=1)
    bl = A.blade_png(o["out"], ID, rgb=(0.10, 0.10, 0.10), tip=(0.85, 0.72, 0.12))
    A.finish_ir(ID, o, mat, objs, empties, painter(), ((-2.0, -7.6, -0.2), (2.0, 7.6, 4.6)),
                (14.2, 13.4, 4.4), "Steel Accord Iran wave 1 - AH-1J-style attack helicopter - Cycles CPU preview",
                separate=("Gun",), extra_export=[rm, rt], blade=(bmat, bl, f"{ID}_blade"), cell=0.02)


if __name__ == "__main__":
    main()
