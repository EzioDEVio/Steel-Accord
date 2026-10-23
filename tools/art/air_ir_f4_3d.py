"""Steel Accord - Iran wave 1: F-4-style twin-engine fighter-bomber (bpy 5.x).

Run:  python3 -I tools/art/air_ir_f4_3d.py [out_dir] [--no-previews] [--quick] [--sheet png]
Out:  godot/assets/units3d/ir_f4/ir_f4.glb (+ ir_f4_albedo.png), docs/screens/ir_f4_sheet.png

Reference: iran_pack/02_aircraft_and_uav_catalog.png panel 02 (perspective concept: silhouette, desert camo,
fin flash placement). Authored from real-world proportions: length ~19.2 m, span 11.7 m, height 5.0 m;
45 deg wing with 12 deg dihedral outer panels, 23 deg anhedral stabilators, side intakes with splitter
plates, long two-seat canopy, under-nose gun fairing. Albedo painted procedurally (airkit_ir).
Nodes: Body, Gun (nose gun muzzle), Exhaust0/1 (left, right nozzle exits),
Hardpoint0..5 (L wing tank, L inboard AAM, L aft fuselage AAM, R aft fuselage AAM, R inboard AAM, R wing tank).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402

K, L = A.K, A.L
import numpy as np  # noqa: E402

ID = "ir_f4"
Y_NOSE, Y_TAIL = 9.55, -9.55
Z_W = 1.70
X_FOLD = 3.90
DIH = math.tan(math.radians(12))

ZTOP = A.fn([(9.55, 1.95), (9.1, 2.20), (8.2, 2.45), (7.2, 2.58), (6.6, 2.62), (4.0, 2.70), (2.0, 2.86), (-2.0, 2.86),
             (-5.0, 2.78), (-7.0, 2.70), (-9.55, 2.55)])
ZBOT = A.fn([(9.55, 1.95), (9.1, 1.70), (8.2, 1.52), (6.0, 1.40), (2.0, 1.30), (-2.0, 1.30), (-4.5, 1.38), (-5.8, 1.52),
             (-6.3, 2.00), (-9.55, 2.40)])
HW = A.fn([(9.55, 0.02), (9.2, 0.25), (8.5, 0.44), (7.5, 0.55), (6.5, 0.60), (5.0, 0.62), (3.0, 0.75), (0.0, 0.95),
           (-3.0, 1.02), (-5.4, 0.98), (-6.3, 0.55), (-8.0, 0.36), (-9.55, 0.22)])
CAN_TOP = A.fn([(6.75, 2.62), (6.25, 3.00), (5.4, 3.17), (4.6, 3.20), (3.8, 3.20), (3.0, 3.13), (2.5, 2.96), (2.1, 2.86)])
CAN_HW = A.fn([(6.75, 0.05), (6.3, 0.38), (5.5, 0.50), (3.5, 0.50), (2.6, 0.40), (2.1, 0.10)])


def fin_le(z):
    return -4.6 - (3.0 / 2.15) * (z - 2.85)


def fin_te(z):
    return -9.2 + (0.3 / 2.15) * (z - 2.85)


def wing_le(x):
    return 2.6 - (x - 1.0) if x <= X_FOLD else 2.6 - (X_FOLD - 1.0) - (x - X_FOLD)


def build(mat):
    objs = {}
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(Y_NOSE - 0.005, Y_NOSE - 1.6, 10), np.linspace(Y_NOSE - 1.8, Y_TAIL + 0.03, 32)])
    K.fuselage(F, ys, ZTOP, ZBOT, HW, n=lambda y: 2.2 + 0.7 * float(np.clip((Y_NOSE - y) / 3.0, 0, 1)), seg=32)
    F.rod((0, Y_NOSE + 0.3, 1.95), (0, Y_NOSE - 0.05, 1.95), 0.025, seg=6)
    # intakes: D-shaped faces beside the cockpit, blending into the fuselage sides
    for sg in (-1, 1):
        rings = []
        for y, xc, hw, hh, n, zc in ((4.45, 1.00, 0.36, 0.62, 5.0, 1.98), (3.6, 0.98, 0.40, 0.64, 4.5, 1.96),
                                     (1.5, 0.92, 0.42, 0.66, 3.6, 1.92), (-1.0, 0.75, 0.40, 0.66, 2.8, 1.92),
                                     (-3.0, 0.55, 0.35, 0.60, 2.4, 1.90)):
            rings.append(K.superellipse_ring(y, sg * xc, hw, zc, hh, n, 22))
        F.rings(rings)
        F.box((sg * 0.66, 4.55, 1.98), (0.04, 0.9, 1.2))                       # splitter plate
    # wing: flat inner panel to the fold, 12 deg dihedral outer panel
    secs = [((1.0, 2.6, Z_W), (1.0, -3.65, Z_W), 0.055, (0, 0, 1)),
            ((X_FOLD, wing_le(X_FOLD), Z_W), (X_FOLD, -3.95, Z_W), 0.05, (0, 0, 1)),
            ((5.85, wing_le(5.85), Z_W + 1.95 * DIH), (5.85, -4.05, Z_W + 1.95 * DIH), 0.045, (0, 0, 1))]
    K.surface(F, K.mirror_sections(secs[1:]) + secs)
    # wing root strake (inner, through the fuselage)
    K.surface(F, [((-1.0, 2.6, Z_W), (-1.0, -3.65, Z_W), 0.05, (0, 0, 1)), ((1.0, 2.6, Z_W), (1.0, -3.65, Z_W), 0.05, (0, 0, 1))])
    # stabilators, 23 deg anhedral
    za = 2.55
    dz = 2.55 * math.tan(math.radians(23))
    st = [((0.30, -7.55, za), (0.30, -9.55, za), 0.05, (0, 0, 1)),
          ((2.85, -8.95, za - dz), (2.85, -9.85, za - dz), 0.04, (0, 0, 1))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    # fin
    A.fin(F, (fin_le(2.80), 2.80), (fin_te(2.80), 2.80), (fin_le(4.95), 4.95), (fin_te(4.95), 4.95), t_root=0.05, t_tip=0.05)
    # under-nose gun fairing
    K.body_rev(F, (0, 6.6, 1.48), (0, 9.15, 1.48), [(0, 0.12), (0.2, 0.22), (0.8, 0.2), (1, 0.08)], seg=14, squash=0.8)
    F.box((0, 0.5, 2.88), (0.12, 1.0, 0.12))                                   # spine antenna
    objs["air"] = F.build(mat, smooth=48)

    Gl = K.Part("Canopy")
    K.fuselage(Gl, np.linspace(6.75, 2.1, 18), CAN_TOP, lambda y: ZTOP(y) - 0.18, lambda y: max(float(CAN_HW(y)), 0.05),
               n=2.3, seg=22)
    objs["glass"] = Gl.build(mat, smooth=60)

    D = K.Part("Dark")
    for sg in (-1, 1):
        D.box((sg * 1.02, 4.465, 1.98), (0.60, 0.03, 1.10))
        K.disc(D, (sg * 0.55, -5.97, 1.55), 0.36)
    D.rod((0, 9.2, 1.48), (0, 9.25, 1.48), 0.05, seg=8)
    objs["dark"] = D.build(mat, smooth=40)

    N = K.Part("Nozzle")
    ex = []
    for sg in (-1, 1):
        K.body_rev(N, (sg * 0.55, -5.98, 1.55), (sg * 0.55, -4.9, 1.55), [(0, 0.42), (0.3, 0.45), (1, 0.50)], seg=20)
        ex.append((sg * 0.55, -5.98, 1.55))
    objs["nozzle"] = N.build(mat, smooth=50)

    Sx = K.Part("Stores")
    hard = []
    zl = Z_W - 0.08
    for sg in (-1, 1):
        lst = [("tank", 3.40), ("aam", 2.05), ("sp", 0.62)]
        if sg > 0:
            lst = lst[::-1]
        for kind, ax in lst:
            x = sg * ax
            if kind == "tank":
                K.pylon(Sx, (x, -0.6, zl), 1.8, 0.32, 0.1)
                zc = zl - 0.30 - 0.38
                K.body_rev(Sx, (x, -3.4, zc), (x, 2.3, zc), [(0, 0.04), (0.1, 0.24), (0.3, 0.38), (0.65, 0.38),
                                                             (0.88, 0.27), (1, 0.03)], seg=18)
                for k in range(3):
                    a = math.pi / 2 + k * 2 * math.pi / 3
                    Sx.beam((x, -3.0, zc), (x + 0.5 * math.cos(a), -3.25, zc + 0.5 * math.sin(a)), 0.02, 0.4, up=(0, 1, 0))
                hard.append((x, -0.55, zc))
            elif kind == "aam":
                K.pylon(Sx, (x, 0.2, zl), 1.4, 0.28, 0.1)
                Sx.box((x, 0.2, zl - 0.3), (0.5, 1.2, 0.06))
                for dx in (-0.2, 0.2):
                    K.missile(Sx, (x + dx, 1.6, zl - 0.42), 2.9, 0.065)
                hard.append((x, 0.2, zl - 0.42))
            else:
                for yn in (3.9, -0.6):
                    K.missile(Sx, (x, yn, 1.20), 3.6, 0.10)
                hard.append((x, -2.4, 1.20))
    objs["stores"] = Sx.build(mat, smooth=40)

    G = K.Part("Gear")
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 2.72, -1.55, 0.42), 0.42, 0.26, (sg * 2.6, -1.4, Z_W - 0.05))
        G.box((sg * 2.48, -1.4, 1.0), (0.04, 1.1, 0.9))                         # gear door
    K.gear_leg(G, (0, 5.55, 0.32), 0.32, 0.13, (0, 5.4, 1.40), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    A.fin(Tm, (fin_le(4.82), 4.82), (fin_te(4.82), 4.82), (fin_le(5.0), 5.0), (fin_te(5.0), 5.0), t_root=0.065, t_tip=0.06)
    objs["team"] = Tm.build(K.team_material(), smooth=40)

    empties = {"Gun": (0, 9.25, 1.48), "Exhaust0": ex[0], "Exhaust1": ex[1]}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def painter():
    dec = A.fin_flash(-6.35, -7.45, 3.75, 4.35, -0.6, -0.6, lambda P: np.abs(P[:, 0]) < 0.16)
    for sg in (-1, 1):
        zr = Z_W + (4.75 - X_FOLD) * DIH
        for side in (1, -1):
            dec.append(A.Roundel((sg * 4.75, -2.55), 0.5, "z", side=side,
                                 slab=lambda P: (np.abs(P[:, 2] - (Z_W + (np.abs(P[:, 0]) - X_FOLD) * DIH)) < 0.25) &
                                 (np.abs(P[:, 0]) > X_FOLD + 0.1), objs=("air",)))
        dec.append(A.Roundel((0.2, 2.0), 0.40, "x", side=sg, slab=A.slab_absx(0.9, 1.6), objs=("air",)))
    zones = [(lambda P, N: P[:, 1] > 8.05, A.RADOME_BLACK, ("air",)),
             (lambda P, N: (P[:, 1] > 6.7) & (P[:, 1] < 8.05) & (N[:, 2] > 0.55) & (np.abs(P[:, 0]) < 0.4),
              (0.20, 0.21, 0.18), ("air",)),
             (lambda P, N: (P[:, 1] < -5.9) & (P[:, 1] > -7.6) & (P[:, 2] < 2.2) & (N[:, 2] < 0.2),
              (0.33, 0.31, 0.28), ("air",))]                                     # heat-stained tail underside
    return dict(scheme="desert", camo_scale=4.4, under=A.UNDER_GREY, under_keys=("air",),
                flat={"dark": K.DARK, "nozzle": A.NOZZLE, "stores": A.STORE_GREY, "gear": A.GEAR},
                glass={"glass": [6.28, 6.05, 5.15, 4.25, 3.30]}, zones=zones, decals=dec,
                panel=dict(dy=1.25, dx=1.05, lon_z=(1.60, 2.35), keys=("air",)), seed=2)


def main():
    o = A.parse_args(ID)
    L.reset_scene()
    mat = L.image_material("SA_IR_F4", None, rough=0.6)
    objs, empties = build(mat)
    A.finish_ir(ID, o, mat, objs, empties, painter(), ((-6.5, -10.5, -0.2), (6.5, 10.5, 5.3)),
                (19.6, 11.7, 5.0), "Steel Accord Iran wave 1 - F-4-style fighter-bomber - Cycles CPU preview")


if __name__ == "__main__":
    main()
