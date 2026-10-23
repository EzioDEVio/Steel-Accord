"""Steel Accord - Iran wave 1: F-14-style variable-sweep twin-engine fighter (bpy 5.x).

Run:  python3 -I tools/art/air_ir_f14_3d.py [out_dir] [--no-previews] [--quick] [--sheet png]
Out:  godot/assets/units3d/ir_f14/ir_f14.glb (+ ir_f14_albedo.png), docs/screens/ir_f14_sheet.png

Reference: docs/reference/iran_pack/02_aircraft_and_uav_catalog.png panel 01 (3/4 perspective concept: used for
silhouette, desert camouflage and marking placement only). Geometry is authored from real-world proportions
(length ~19.1 m, span 19.5 m at minimum sweep, height 4.9 m); the albedo is painted procedurally (airkit_ir).
Wings are modelled spread (20 deg leading-edge sweep) as separate nodes WingL / WingR whose origin is the
glove pivot (identity rotation): the game can sweep them by rotating about local Y (Godot) = Blender Z.
Nodes: Body (fuselage, glove, nacelles, tails, stores, gear, team fin caps), WingL, WingR, Gun (left M61
muzzle), Exhaust0/1 (left, right nozzle exits), Hardpoint0..5 (L glove, L tank, L tunnel, R tunnel, R tank,
R glove).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402

K, L = A.K, A.L
import numpy as np  # noqa: E402

ID = "ir_f14"
Y_NOSE, Y_TAIL = 9.30, -8.45
Z_GLOVE = 2.25
X_NAC, Z_NAC = 1.40, 1.85
PIVOT = 2.75, -1.90
CANT = 5.0
FIN_X = 1.55

ZTOP = A.fn([(9.30, 1.92), (8.9, 2.18), (8.2, 2.40), (7.2, 2.56), (6.2, 2.66), (4.0, 2.74), (2.0, 2.74), (0.0, 2.62),
             (-3.0, 2.52), (-6.0, 2.42), (-7.6, 2.28), (-8.45, 2.10)])
ZBOT = A.fn([(9.30, 1.92), (8.9, 1.66), (8.2, 1.50), (7.0, 1.40), (5.0, 1.36), (3.0, 1.40), (0.0, 1.55), (-4.0, 1.68),
             (-7.6, 1.80), (-8.45, 1.88)])
HW = A.fn([(9.30, 0.02), (9.0, 0.24), (8.5, 0.45), (7.8, 0.58), (7.0, 0.66), (5.5, 0.70), (3.5, 0.72), (2.0, 0.80),
           (0.0, 0.95), (-3.0, 1.0), (-6.0, 0.92), (-7.6, 0.70), (-8.45, 0.40)])
CAN_TOP = A.fn([(6.35, 2.66), (5.85, 2.98), (5.1, 3.18), (4.1, 3.23), (3.2, 3.15), (2.55, 2.92), (2.2, 2.74)])
CAN_HW = A.fn([(6.35, 0.06), (5.95, 0.40), (5.1, 0.54), (3.5, 0.55), (2.7, 0.42), (2.2, 0.08)])


def fin_le(z):
    return -3.9 - 1.375 * (z - 2.45)


def fin_te(z):
    return -7.6 - 0.375 * (z - 2.45)


def build(mat):
    objs = {}
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(Y_NOSE - 0.005, Y_NOSE - 1.6, 10), np.linspace(Y_NOSE - 1.8, Y_TAIL + 0.03, 30)])
    K.fuselage(F, ys, ZTOP, ZBOT, lambda y: HW(y), n=lambda y: 2.2 + 0.8 * float(np.clip((Y_NOSE - y) / 3.0, 0, 1)),
               seg=32)
    F.rod((0, Y_NOSE + 0.35, 1.92), (0, Y_NOSE - 0.05, 1.92), 0.025, seg=6)               # pitot
    # intake ducts -> nacelles (rectangular face blending into round nacelle), one loft per side
    for sg in (-1, 1):
        rings = []
        for y, xc, hw, hh, n, zc in ((3.25, 1.48, 0.50, 0.62, 6.0, 1.90), (2.2, 1.47, 0.52, 0.63, 5.0, 1.90),
                                     (0.5, 1.45, 0.58, 0.65, 3.6, 1.88), (-1.5, 1.42, 0.64, 0.66, 2.4, 1.86),
                                     (-4.5, X_NAC, 0.65, 0.65, 2.0, Z_NAC), (-6.8, X_NAC, 0.60, 0.60, 2.0, Z_NAC),
                                     (-7.6, X_NAC, 0.56, 0.56, 2.0, Z_NAC)):
            rings.append(K.superellipse_ring(y, sg * xc, hw, zc, hh, n, 24))
        F.rings(rings)
    # glove (fixed inner wing / pancake), thin, swept 66 deg
    glove = [((0.75, 3.70, Z_GLOVE), (0.75, -5.6, Z_GLOVE), 0.035, (0, 0, 1)),
             ((1.9, 1.2, Z_GLOVE), (1.9, -5.2, Z_GLOVE), 0.04, (0, 0, 1)),
             ((3.0, -1.25, Z_GLOVE), (3.0, -3.70, Z_GLOVE), 0.05, (0, 0, 1))]
    K.surface(F, K.mirror_sections(glove[1:]) + glove)
    # glove vane fairing (oversized pivot fairing on the upper deck)
    for sg in (-1, 1):
        K.body_rev(F, (sg * 2.55, -3.8, Z_GLOVE + 0.05), (sg * 2.55, -0.4, Z_GLOVE + 0.05),
                   [(0, 0.05), (0.2, 0.16), (0.7, 0.17), (1, 0.03)], seg=10, squash=0.6)
    # twin canted fins
    for sg in (-1, 1):
        A.fin(F, (fin_le(2.45), 2.45), (fin_te(2.45), 2.45), (fin_le(4.72), 4.72), (fin_te(4.72), 4.72),
              t_root=0.055, t_tip=0.05, x=sg * FIN_X, cant_deg=CANT, side_sign=sg)
    # stabilators (slight anhedral)
    st = [((1.85, -5.9, 1.95), (1.85, -8.9, 1.95), 0.05, (0, 0, 1)),
          ((5.0, -8.35, 1.80), (5.0, -9.45, 1.80), 0.04, (0, 0, 1))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    # ventral fins
    for sg in (-1, 1):
        F.beam((sg * 1.55, -5.4, 1.30), (sg * 1.62, -7.3, 1.22), 0.04, 0.42, up=(sg, 0, 0))
    # beaver tail (speed-brake fairing) between the nozzles
    F.box((0, -8.55, 2.0), (0.85, 0.5, 0.08))
    # dorsal antenna / spine fairings
    F.box((0, 0.8, 2.66), (0.10, 1.4, 0.10))
    objs["air"] = F.build(mat, smooth=48)

    Gl = K.Part("Canopy")
    K.fuselage(Gl, np.linspace(6.35, 2.2, 16), CAN_TOP, lambda y: ZTOP(y) - 0.18, lambda y: max(float(CAN_HW(y)), 0.05),
               n=2.3, seg=22)
    objs["glass"] = Gl.build(mat, smooth=60)

    D = K.Part("Dark")
    for sg in (-1, 1):
        D.box((sg * 1.48, 3.265, 1.90), (0.86, 0.03, 1.10))
        K.disc(D, (sg * X_NAC, -8.42, Z_NAC), 0.44)
    objs["dark"] = D.build(mat, smooth=40)

    N = K.Part("Nozzle")
    ex = []
    for sg in (-1, 1):
        K.body_rev(N, (sg * X_NAC, -8.45, Z_NAC), (sg * X_NAC, -7.5, Z_NAC),
                   [(0, 0.47), (0.25, 0.50), (0.7, 0.55), (1, 0.57)], seg=20)
        ex.append((sg * X_NAC, -8.45, Z_NAC))
    objs["nozzle"] = N.build(mat, smooth=50)

    # stores: glove AAM, tank under each intake, Phoenix-style AAM pair in the tunnel
    Sx = K.Part("Stores")
    hard = []
    for sg in (-1, 1):
        tk = [(sg * 2.40, "aam"), (sg * 1.45, "tank"), (sg * 0.45, "lr")]
        if sg > 0:
            tk = tk[::-1]
        for x, kind in tk:
            if kind == "aam":
                K.pylon(Sx, (x, 0.3, Z_GLOVE - 0.03), 1.6, 0.26, 0.08)
                K.missile(Sx, (x, 2.0, Z_GLOVE - 0.40), 3.6, 0.10)
                hard.append((x, 0.2, Z_GLOVE - 0.40))
            elif kind == "tank":
                zc = 0.86
                K.pylon(Sx, (x, 0.6, 1.25), 1.4, 0.2, 0.1)
                K.body_rev(Sx, (x, -1.25, zc), (x, 2.35, zc), [(0, 0.04), (0.1, 0.22), (0.3, 0.32), (0.65, 0.32),
                                                               (0.88, 0.24), (1, 0.03)], seg=18)
                hard.append((x, 0.55, zc))
            else:
                Sx.box((x, -2.0, 1.40), (0.30, 2.2, 0.16))
                K.missile(Sx, (x, -0.1, 1.12), 3.9, 0.19, seg=12)
                hard.append((x, -2.0, 1.12))
    objs["stores"] = Sx.build(mat, smooth=40)

    G = K.Part("Gear")
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 2.50, -1.95, 0.50), 0.50, 0.30, (sg * 2.20, -1.6, Z_GLOVE - 0.12))
        G.rod((sg * 2.5, -1.95, 0.5), (sg * 1.9, -2.6, 1.9), 0.05, seg=6)
    K.gear_leg(G, (0, 6.35, 0.34), 0.34, 0.14, (0, 6.15, 1.40), twin=True)
    G.box((0, 7.0, 1.30), (0.3, 0.6, 0.03))
    objs["gear"] = G.build(mat, smooth=40)

    # wings (separate nodes, origin at the glove pivot)
    secs = [((2.15, -0.70, Z_GLOVE), (2.15, -4.15, Z_GLOVE), 0.085, (0, 0, 1)),
            ((5.5, -1.92, Z_GLOVE - 0.03), (5.5, -4.45, Z_GLOVE - 0.03), 0.075, (0, 0, 1)),
            ((9.72, -3.45, Z_GLOVE - 0.07), (9.72, -4.82, Z_GLOVE - 0.07), 0.06, (0, 0, 1))]
    WR = K.Part("WingR"); K.surface(WR, secs)
    WL = K.Part("WingL"); K.surface(WL, K.mirror_sections(secs))
    objs["WingL"] = A.set_origin(WL.build(mat, smooth=40), (-PIVOT[0], PIVOT[1], Z_GLOVE))
    objs["WingR"] = A.set_origin(WR.build(mat, smooth=40), (PIVOT[0], PIVOT[1], Z_GLOVE))

    Tm = K.Part("Team")
    for sg in (-1, 1):
        A.fin(Tm, (fin_le(4.70), 4.70), (fin_te(4.70), 4.70), (fin_le(4.86), 4.86), (fin_te(4.86), 4.86),
              t_root=0.07, t_tip=0.065, x=sg * FIN_X + sg * math.tan(math.radians(CANT)) * 0.0, cant_deg=CANT,
              side_sign=sg)
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    # team cap root sits at the fin's canted position: shift so the cap follows the fin lean
    tm = objs["team"]
    for v in tm.data.vertices:
        v.co.x += np.sign(v.co.x) * math.tan(math.radians(CANT)) * (4.70 - 2.45)

    empties = {"Gun": (-0.62, 6.3, 1.62), "Exhaust0": ex[0], "Exhaust1": ex[1]}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def painter():
    fin_slab = lambda P: np.abs(np.abs(P[:, 0]) - (FIN_X + math.tan(math.radians(CANT)) * (P[:, 2] - 2.45))) < 0.18
    dec = []
    dec += A.fin_flash(-5.95, -7.05, 3.55, 4.20, -0.9, -0.9, fin_slab)
    for sg in (-1, 1):
        wk = "WingL" if sg < 0 else "WingR"
        for side in (1, -1):
            dec.append(A.Roundel((sg * 7.0, -3.55), 0.55, "z", side=side, objs=(wk,)))
        dec.append(A.Roundel((0.9, 1.9), 0.42, "x", side=sg, slab=A.slab_absx(1.7, 2.3), objs=("air",)))
    zones = [(lambda P, N: P[:, 1] > 8.15, A.RADOME_BLACK, ("air",)),
             (lambda P, N: (P[:, 1] > 6.6) & (P[:, 1] < 8.15) & (N[:, 2] > 0.55) & (np.abs(P[:, 0]) < 0.4),
              (0.20, 0.21, 0.18), ("air",))]                              # anti-glare panel
    return dict(scheme="desert", camo_scale=4.6, under=A.UNDER_GREY, under_keys=("air", "WingL", "WingR"),
                flat={"dark": K.DARK, "nozzle": A.NOZZLE, "stores": A.STORE_GREY, "gear": A.GEAR},
                glass={"glass": [5.80, 5.55, 4.62, 3.30]}, zones=zones, decals=dec,
                panel=dict(dy=1.3, dx=1.15, lon_z=(1.55, 2.30), keys=("air", "WingL", "WingR")), seed=1)


def main():
    o = A.parse_args(ID)
    L.reset_scene()
    mat = L.image_material("SA_IR_F14", None, rough=0.6)
    objs, empties = build(mat)
    A.finish_ir(ID, o, mat, objs, empties, painter(), ((-10.5, -10.0, -0.2), (10.5, 10.0, 5.2)),
                (19.1, 19.5, 4.9), "Steel Accord Iran wave 1 - F-14-style swing-wing fighter - Cycles CPU preview",
                separate=("WingL", "WingR"))


if __name__ == "__main__":
    main()
