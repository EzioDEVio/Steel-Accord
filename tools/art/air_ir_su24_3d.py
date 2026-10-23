"""Steel Accord - Iran wave 1: Su-24-style variable-sweep strike aircraft (bpy 5.x).

Run:  python3 -I tools/art/air_ir_su24_3d.py [out_dir] [--no-previews] [--quick] [--sheet png]
Out:  godot/assets/units3d/ir_su24/ir_su24.glb (+ ir_su24_albedo.png), docs/screens/ir_su24_sheet.png

Reference: iran_pack/02_aircraft_and_uav_catalog.png panel 07 (perspective concept: silhouette, grey scheme,
light radome, fin flash and intake roundel placement). Authored from real-world proportions: length ~22.7 m,
span 17.6 m at minimum sweep, height 6.2 m; broad box fuselage, side-by-side canopy, rectangular side
intakes with splitter plates, shoulder glove, large swept fin with dorsal fillet, twin ventral fins.
Wings are modelled spread (16 deg sweep) as separate nodes WingL / WingR, origin at the glove pivot.
Nodes: Body, WingL, WingR, Gun (belly cannon muzzle), Exhaust0/1 (left, right),
Hardpoint0..3 (L glove missile, L fuselage bomb, R fuselage bomb, R glove missile).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402

K, L = A.K, A.L
import numpy as np  # noqa: E402

ID = "ir_su24"
Y_NOSE, Y_TAIL = 11.25, -10.70
Z_G = 3.05
PIVOT = (2.70, -0.90)

ZTOP = A.fn([(11.25, 2.25), (10.5, 2.58), (9.2, 2.92), (7.5, 3.10), (5.0, 3.28), (3.0, 3.36), (0.0, 3.32), (-5.0, 3.22),
             (-8.0, 3.02), (-10.7, 2.72)])
ZBOT = A.fn([(11.25, 2.25), (10.5, 1.95), (9.2, 1.74), (7.0, 1.62), (3.0, 1.55), (-3.0, 1.55), (-7.0, 1.66),
             (-10.7, 1.70)])
HW = A.fn([(11.25, 0.02), (10.8, 0.30), (10.0, 0.52), (8.6, 0.74), (7.0, 0.90), (5.0, 1.02), (2.0, 1.12), (-3.0, 1.18),
           (-7.0, 1.20), (-9.5, 1.18), (-10.7, 1.12)])
CAN_TOP = A.fn([(7.45, 3.08), (6.9, 3.45), (6.0, 3.66), (5.2, 3.67), (4.6, 3.48), (4.2, 3.34)])
CAN_HW = A.fn([(7.45, 0.20), (6.9, 0.62), (6.0, 0.78), (5.0, 0.76), (4.4, 0.45), (4.2, 0.15)])


def fin_le(z):
    return -4.0 - (4.3 / 2.95) * (z - 3.2)


def fin_te(z):
    return -9.85 - (0.35 / 2.95) * (z - 3.2)


def build(mat):
    objs = {}
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(Y_NOSE - 0.005, Y_NOSE - 2.0, 11), np.linspace(Y_NOSE - 2.2, Y_TAIL + 0.03, 32)])
    K.fuselage(F, ys, ZTOP, ZBOT, HW, n=lambda y: 2.1 + 1.5 * float(np.clip((Y_NOSE - 2.0 - y) / 4.0, 0, 1)), seg=32)
    F.rod((0, Y_NOSE + 1.1, 2.25), (0, Y_NOSE - 0.05, 2.25), 0.03, seg=6)                 # long pitot boom
    for sg in (-1, 1):                                                                      # rectangular side intakes
        rings = []
        for y, xc, hw, hh, n, zc in ((4.65, 1.48, 0.40, 0.62, 6.0, 2.30), (3.8, 1.46, 0.42, 0.63, 5.5, 2.30),
                                     (1.0, 1.36, 0.42, 0.64, 4.5, 2.28), (-2.0, 1.12, 0.36, 0.62, 3.5, 2.30)):
            rings.append(K.superellipse_ring(y, sg * xc, hw, zc, hh, n, 22))
        F.rings(rings)
        F.box((sg * 1.06, 4.8, 2.30), (0.04, 0.9, 1.25))                                   # splitter plate
    # fixed glove (shoulder)
    glove = [((0.95, 4.2, Z_G), (0.95, -3.7, Z_G), 0.04, (0, 0, 1)),
             ((2.95, 0.55, Z_G), (2.95, -3.5, Z_G), 0.05, (0, 0, 1))]
    K.surface(F, K.mirror_sections(glove[1:]) + glove)
    # dorsal fillet + fin
    F.beam((0, -1.5, 3.30), (0, -4.6, 3.55), 0.18, 0.3)
    A.fin(F, (fin_le(3.2), 3.2), (fin_te(3.2), 3.2), (fin_le(6.1), 6.1), (fin_te(6.1), 6.1), t_root=0.05, t_tip=0.05)
    for sg in (-1, 1):                                                                      # ventral fins
        A.fin(F, (-7.2, 1.70), (-9.6, 1.68), (-8.6, 1.05), (-9.7, 1.05), t_root=0.05, t_tip=0.05,
              x=sg * 0.8, cant_deg=-15, side_sign=sg)
    st = [((1.15, -7.3, 2.30), (1.15, -10.65, 2.30), 0.05, (0, 0, 1)),
          ((4.15, -9.85, 2.05), (4.15, -11.25, 2.05), 0.04, (0, 0, 1))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    # belly gun fairing
    K.body_rev(F, (0.48, 0.5, 1.55), (0.48, 3.1, 1.55), [(0, 0.06), (0.15, 0.17), (0.85, 0.17), (1, 0.08)], seg=12, squash=0.8)
    objs["air"] = F.build(mat, smooth=48)

    Gl = K.Part("Canopy")
    K.fuselage(Gl, np.linspace(7.45, 4.2, 16), CAN_TOP, lambda y: ZTOP(y) - 0.2, lambda y: max(float(CAN_HW(y)), 0.05),
               n=2.6, seg=24)
    objs["glass"] = Gl.build(mat, smooth=60)

    D = K.Part("Dark")
    for sg in (-1, 1):
        D.box((sg * 1.48, 4.665, 2.30), (0.70, 0.03, 1.12))
        K.disc(D, (sg * 0.62, -10.72, 2.12), 0.40)
    D.rod((0.48, 3.1, 1.55), (0.48, 3.15, 1.55), 0.05, seg=8)
    objs["dark"] = D.build(mat, smooth=40)

    N = K.Part("Nozzle")
    ex = []
    for sg in (-1, 1):
        K.body_rev(N, (sg * 0.62, -10.75, 2.12), (sg * 0.62, -9.9, 2.12), [(0, 0.46), (0.4, 0.50), (1, 0.54)], seg=20)
        ex.append((sg * 0.62, -10.75, 2.12))
    objs["nozzle"] = N.build(mat, smooth=50)

    Sx = K.Part("Stores")
    hard = []
    for sg in (-1, 1):
        lst = [("glove", 2.15), ("bomb", 0.72)]
        if sg > 0:
            lst = lst[::-1]
        for kind, ax in lst:
            x = sg * ax
            if kind == "glove":
                K.pylon(Sx, (x, -0.8, Z_G - 0.03), 2.0, 0.35, 0.1)
                K.missile(Sx, (x, 1.1, Z_G - 0.55), 3.7, 0.14, seg=12)
                hard.append((x, -0.75, Z_G - 0.55))
            else:
                K.pylon(Sx, (x, -1.0, 1.58), 1.4, 0.18, 0.1)
                K.bomb(Sx, (x, 0.3, 1.18), 2.7, 0.21)
                hard.append((x, -1.05, 1.18))
    objs["stores"] = Sx.build(mat, smooth=40)

    G = K.Part("Gear")
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.68, -1.4, 0.47), 0.47, 0.3, (sg * 1.2, -1.2, 1.62))
        G.rod((sg * 1.68, -1.4, 0.47), (sg * 1.1, -2.2, 1.6), 0.05, seg=6)
        G.box((sg * 1.30, -1.3, 1.25), (0.04, 1.3, 0.8))
    K.gear_leg(G, (0, 6.8, 0.33), 0.33, 0.14, (0, 6.6, 1.62), twin=True)
    G.box((0, 6.85, 0.75), (0.75, 0.6, 0.04))                                               # mudguard
    objs["gear"] = G.build(mat, smooth=40)

    secs = [((2.35, 0.40, Z_G), (2.35, -3.35, Z_G), 0.08, (0, 0, 1)),
            ((8.82, 0.40 - 6.47 * math.tan(math.radians(16)), Z_G - 0.30), (8.82, -3.20, Z_G - 0.30), 0.06, (0, 0, 1))]
    WR = K.Part("WingR"); K.surface(WR, secs)
    WL = K.Part("WingL"); K.surface(WL, K.mirror_sections(secs))
    objs["WingL"] = A.set_origin(WL.build(mat, smooth=40), (-PIVOT[0], PIVOT[1], Z_G))
    objs["WingR"] = A.set_origin(WR.build(mat, smooth=40), (PIVOT[0], PIVOT[1], Z_G))

    Tm = K.Part("Team")
    A.fin(Tm, (fin_le(5.95), 5.95), (fin_te(5.95), 5.95), (fin_le(6.17), 6.17), (fin_te(6.17), 6.17), t_root=0.065, t_tip=0.06)
    objs["team"] = Tm.build(K.team_material(), smooth=40)

    empties = {"Gun": (0.48, 3.15, 1.55), "Exhaust0": ex[0], "Exhaust1": ex[1]}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def painter():
    dec = A.fin_flash(-6.85, -8.05, 4.95, 5.60, -0.85, -0.85, lambda P: np.abs(P[:, 0]) < 0.16)
    for sg in (-1, 1):
        wk = "WingL" if sg < 0 else "WingR"
        for side in (1, -1):
            dec.append(A.Roundel((sg * 6.9, -2.05), 0.55, "z", side=side, objs=(wk,)))
        dec.append(A.Roundel((2.9, 2.30), 0.40, "x", side=sg, slab=A.slab_absx(1.5, 2.0), objs=("air",)))
    zones = [(lambda P, N: P[:, 1] > 9.4, (0.80, 0.81, 0.79), ("air",)),
             (lambda P, N: (P[:, 1] > 7.5) & (P[:, 1] < 9.4) & (N[:, 2] > 0.6) & (np.abs(P[:, 0]) < 0.3),
              (0.22, 0.23, 0.24), ("air",))]
    return dict(scheme="grey", camo_scale=5.0, under=(0.72, 0.74, 0.75), under_keys=("air", "WingL", "WingR"),
                flat={"dark": K.DARK, "nozzle": A.NOZZLE, "stores": (0.80, 0.80, 0.78), "gear": (0.30, 0.31, 0.30)},
                glass={"glass": {"y": [6.9, 6.75, 5.0], "x": [0.0]}}, zones=zones, decals=dec,
                panel=dict(dy=1.3, dx=1.2, lon_z=(1.95, 2.95), keys=("air", "WingL", "WingR"), k=0.84), seed=3,
                grime=0.08)


def main():
    o = A.parse_args(ID)
    L.reset_scene()
    mat = L.image_material("SA_IR_SU24", None, rough=0.55)
    objs, empties = build(mat)
    A.finish_ir(ID, o, mat, objs, empties, painter(), ((-9.5, -11.6, -0.2), (9.5, 12.6, 6.5)),
                (22.9, 17.6, 6.2), "Steel Accord Iran wave 1 - Su-24-style strike aircraft - Cycles CPU preview",
                separate=("WingL", "WingR"))


if __name__ == "__main__":
    main()
