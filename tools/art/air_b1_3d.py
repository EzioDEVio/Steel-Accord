"""Steel Accord - M3 3D aircraft: B-1-style swing-wing supersonic bomber (bpy 5.x).

Run:  python3 -I tools/art/air_b1_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/b1/b1.glb (+ b1_albedo.png), docs/screens/m3_b1_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the cleaned top
sprite godot/assets/aircraft/b1/b1_top.png. The wings are modelled at the concept's intermediate sweep
(fixed; no wing-sweep animation node), span 41.8 m; length 44.5 m from the side view.
Nodes: Body, Exhaust0..3 (left outer -> right outer nozzles), Hardpoint0..2 (forward/mid/aft bomb bays).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "b1"
SHEET = os.path.join(K.INC_X, "contact_sheets", "B-1_Lancer_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(44.5 / 834.0, (16 + 850) / 2.0, 906.0)
T = K.TopFrame(41.8 / 627.0, 326.0, [(33, S.y(18)), (115, S.y(160)), (608, S.y(845))])

FUS_TOP = [(19, 840), (30, 834), (50, 827), (75, 820), (100, 814), (140, 801), (170, 791), (200, 786), (250, 784),
           (300, 787), (400, 794), (500, 794), (600, 791), (700, 795), (750, 806), (800, 821), (840, 828)]
FUS_BOT = [(19, 842), (30, 845), (50, 849), (75, 852), (100, 853), (250, 854), (400, 855), (500, 855), (600, 851),
           (700, 848), (780, 847), (810, 845), (840, 834)]
FUS_HW = [(33, 1), (40, 4.5), (60, 11), (100, 18), (150, 24.5), (200, 30), (250, 33), (300, 34), (400, 34), (470, 33),
          (500, 30), (550, 22), (590, 12), (608, 4)]


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(19), S.y(840)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 6.0, 14), np.linspace(y_n - 6.4, y_t, 32)])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.4, seg=36)
    # blended glove + outer wing as one thin surface (glove leading edge from the fuselage blend)
    zw = float(S.z(828))
    W = [(326, 190, 470, 0.06), (345, 205, 470, 0.06), (360, 235, 470, 0.07), (376, 250, 466, 0.08),
         (392, 280, 405, 0.08), (410, 300, 399, 0.075), (470, 330, 412, 0.07), (550, 368, 429, 0.06),
         (600, 392, 441, 0.05), (640, 417, 450, 0.04)]
    right = [((float(T.x(px)), float(T.y(le)), zw), (float(T.x(px)), float(T.y(te)), zw), t, (0, 0, 1))
             for px, le, te, t in W]
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # engine nacelles (two pairs under the glove)
    zn = float(S.z(866))
    exh = []
    dark = []
    for sg in (-1, 1):
        xc = sg * 58 * T.sx
        y0, y1 = float(T.y(322)), float(T.y(468))
        rr = []
        for t in np.linspace(0, 1, 12):
            y = y0 + (y1 - y0) * t
            f = min(1.0, 0.55 + 3.0 * t) * (1 - 0.12 * max(0, (t - 0.85) / 0.15))
            rr.append(K.superellipse_ring(y, xc, 1.55 * f, zn + 0.15, 0.95 * f, 3.2, 20))
        F.rings(rr)
        for dx in (-0.85, 0.85):
            K.body_rev(F, (xc + dx, y1 - 0.9, zn), (xc + dx, y1 + 0.2, zn), [(0, 0.62), (1, 0.66)], seg=14)
            exh.append((xc + dx, y1 - 0.92, zn))
            dark.append((xc + dx, y1 - 0.91, zn))
    zs = float(S.z(780))
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), t, (0, 0, 1))
          for px, le, te, t in ((326, 505, 590, 0.07), (350, 520, 590, 0.07), (380, 535, 593, 0.065), (400, 550, 600, 0.06),
                                (430, 573, 611, 0.05), (448, 590, 617, 0.04))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    K.surface(F, K.fin_sections(S, [(672, 792, 790), (725, 797, 735), (770, 806, 690)], x=0, t_root=0.1, t_tip=0.07))
    objs["air"] = F.build(mat, smooth=45)
    D = K.Part("Dark")
    for p in dark:
        K.disc(D, p, 0.55)
    objs["dark"] = D.build(mat, smooth=40)

    G = K.Part("Gear")
    for sg in (-1, 1):
        for gp in (470, 505):
            K.gear_leg(G, (sg * 2.3, S.y(gp), 0.55), 0.55, 0.32, (sg * 2.3, S.y(gp), zn - 0.7), twin=True)
    yng = S.y(190)
    K.gear_leg(G, (0, yng, 0.5), 0.5, 0.26, (0, yng, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, [(765, 805, 696), (771, 806, 687)], x=0, t_root=0.1, t_tip=0.09))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    exh.sort(key=lambda p: p[0])
    empties = {f"Exhaust{i}": p for i, p in enumerate(exh)}
    for i, gp in enumerate((300, 380, 560)):
        y = S.y(gp)
        empties[f"Hardpoint{i}"] = (0, y, float(zbot(y)) - 0.05)
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_B1", None, rough=0.55)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-21.5, -23.0, -0.1), (21.5, 23.0, 12.5)),
             (44.5, 41.8, 11.8), "Steel Accord M3 - B-1 supersonic bomber - Cycles CPU preview",
             flat={"gear": (0.12, 0.12, 0.12), "dark": K.DARK}, cell=0.06, ao=0.4)


if __name__ == "__main__":
    main()
