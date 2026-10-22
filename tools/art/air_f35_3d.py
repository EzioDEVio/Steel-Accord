"""Steel Accord - M3 3D aircraft: F-35-style stealth multirole fighter (bpy 5.x).

Run:  python3 -I tools/art/air_f35_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/f35/f35.glb (+ f35_albedo.png), docs/screens/m3_f35_sheet.png

Reference: incoming_f35/f35_turnaround.png (2x2: front 3/4, side (top-right, nose left), top (bottom-left,
nose RIGHT -> rotated 90 deg CCW to nose up), rear 3/4). The concept airframe is deeper than the real one,
so its proportions are kept (length 15.7 m from the side view, span 10.7 m from the top view; height ~5 m).
Clean configuration (internal bays): Hardpoint0..3 are bay release points under the fuselage.
Nodes: Body, Gun (left shoulder cannon), Exhaust0 (nozzle), Hardpoint0..3.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "f35"
SHEET = os.path.join(K.INC_F35, "f35_turnaround.png")

S = K.SideFrame(15.7 / 795.0, (734 + 1529) / 2.0, 415.0)
T = K.TopFrame(10.7 / 550.0, 699.0, [(716, S.y(734)), (830, S.y(925)), (1332, S.y(1500))])

FUS_TOP = [(736, 308), (760, 293), (800, 279), (850, 264), (900, 257), (1000, 244), (1100, 241), (1200, 248),
           (1300, 253), (1350, 258), (1400, 268), (1445, 282)]
FUS_BOT = [(736, 310), (760, 324), (800, 338), (850, 344), (900, 348), (1000, 356), (1100, 366), (1200, 367),
           (1300, 367), (1350, 360), (1400, 350), (1445, 336)]
CANOPY = [(848, 262), (870, 246), (900, 231), (930, 225), (960, 227), (985, 237), (1005, 245)]
FUS_HW = [(716, 2), (720, 4), (740, 15), (760, 21), (800, 30), (840, 40), (870, 45), (880, 70), (900, 79),
          (950, 80), (1000, 82), (1100, 84), (1200, 80), (1250, 70), (1290, 55), (1310, 45)]
CANOPY_HW = [(770, 3), (790, 17), (820, 24), (850, 24), (880, 18), (900, 6)]
Z_W = (415 - 305) * S.s


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(736), S.y(1445)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 2.4, 14), np.linspace(y_n - 2.6, y_t, 26)])
    K.fuselage(F, ys, ztop, zbot, hw, n=lambda y: 2.2 if y > S.y(850) else 3.2, seg=32)
    ct = K.polyline_fn([S(px, py) for px, py in CANOPY])
    chw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in CANOPY_HW])
    K.fuselage(F, np.linspace(S.y(850), S.y(1003), 14), ct, lambda y: ztop(y) - 0.25, lambda y: max(chw(y), 0.05),
               n=2.2, seg=20)
    # wing
    W = [(699, 940, 1225, 0.05), (780, 958, 1222, 0.05), (800, 990, 1220, 0.05), (850, 1023, 1199, 0.045),
         (900, 1055, 1195, 0.04), (950, 1087, 1190, 0.035), (977, 1105, 1185, 0.03)]
    right = [((float(T.x(px)), float(T.y(le)), Z_W), (float(T.x(px)), float(T.y(te)), Z_W), t, (0, 0, 1))
             for px, le, te, t in W]
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # stabilisers
    zs = (415 - 311) * S.s
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), 0.04, (0, 0, 1))
          for px, le, te in ((760, 1200, 1372), (800, 1235, 1372), (850, 1276, 1357), (877, 1300, 1340))]
    K.surface(F, st)
    K.surface(F, K.mirror_sections(st))
    # twin canted fins
    fin = [(1338, 1458, 252), (1390, 1472, 200), (1440, 1490, 148)]
    for sg in (-1, 1):
        K.surface(F, K.fin_sections(S, fin, x=sg * 1.05, cant_deg=25, side_sign=sg, t_root=0.05, t_tip=0.04))
    # nozzle
    zn = (415 - 308) * S.s
    K.body_rev(F, (0, S.y(1500), zn), (0, S.y(1435), zn), [(0, 0.46), (0.5, 0.52), (1, 0.56)], seg=24)
    objs["air"] = F.build(mat, smooth=50)
    D = K.Part("Dark")
    K.disc(D, (0, S.y(1500) - 0.01, zn), 0.42)
    objs["dark"] = D.build(mat, smooth=40)

    G = K.Part("Gear")
    ym = float(T.y(1150))
    zb = float(zbot(ym))
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.75, ym, 0.38), 0.38, 0.24, (sg * 1.3, ym + 0.1, zb + 0.1))
    yn_ = S.y(880)
    K.gear_leg(G, (0, yn_, 0.3), 0.3, 0.16, (0, yn_ - 0.05, float(zbot(yn_)) + 0.1))
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    for sg in (-1, 1):
        K.surface(Tm, K.fin_sections(S, [(1430, 1487, 157), (1442, 1491, 145)], x=sg * 1.05 + sg * (252 - 157) * S.s * math.tan(math.radians(25)),
                                     cant_deg=25, side_sign=sg, t_root=0.06, t_tip=0.05))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    yb = S.y(1150)
    empties = {"Gun": (-1.15, S.y(1000), float(S.z(262))), "Exhaust0": (0, S.y(1501), zn)}
    for i, (x, dy) in enumerate(((-0.95, 0.6), (-0.55, 0.0), (0.55, 0.0), (0.95, 0.6))):
        empties[f"Hardpoint{i}"] = (x, yb + dy, float(zbot(yb)) - 0.05)
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "tr", top_cell="bl", top_rot=1)
    mat = L.image_material("SA_F35", None, rough=0.5)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-5.8, -8.4, -0.1), (5.8, 8.4, 5.6)),
             (15.7, 10.7, 5.2), "Steel Accord M3 - F-35 stealth fighter - Cycles CPU preview",
             flat={"gear": (0.16, 0.16, 0.16), "dark": K.DARK})


if __name__ == "__main__":
    main()
