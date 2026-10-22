"""Steel Accord - M3 3D aircraft: F/A-18-style twin-engine carrier multirole fighter (bpy 5.x).

Run:  python3 -I tools/art/air_fa18_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/fa18/fa18.glb (+ fa18_albedo.png), docs/screens/m3_fa18_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the cleaned top
sprite godot/assets/aircraft/fa18/fa18_top.png (X: real span 13.6 m incl. tip missiles; Y rectified through
nose, canopy and nozzle landmarks). The concept fins are taller than real (overall height ~5.4 m).
Nodes: Body, Gun (nose cannon), Exhaust0/1 (left/right nozzles), Hardpoint0..6 (left tip, left outer,
left inner, right inner, right outer, right tip, centreline tank).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "fa18"
SHEET = os.path.join(K.INC_X, "contact_sheets", "F-A-18_Hornet_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(17.1 / 765.0, (20 + 785) / 2.0, 925.0)
T = K.TopFrame(6.8 / 321.0, 343.0, [(27, S.y(20)), (250, S.y(280)), (600, S.y(785))])

FUS_TOP = [(22, 845), (50, 830), (100, 815), (150, 803), (190, 795), (300, 790), (400, 786), (500, 790), (560, 795),
           (650, 800), (700, 806), (750, 814)]
FUS_BOT = [(22, 848), (50, 856), (100, 862), (150, 863), (250, 864), (330, 867), (400, 877), (500, 878), (600, 876),
           (700, 868), (750, 860)]
CANOPY = [(185, 796), (210, 781), (240, 769), (270, 764), (300, 766), (330, 773), (360, 782), (392, 789)]
FUS_HW = [(27, 1), (32, 4), (60, 16), (100, 25), (150, 28), (180, 32), (200, 37), (300, 47), (400, 52), (500, 52),
          (560, 49), (595, 46)]
CANOPY_HW = [(185, 3), (200, 16), (230, 22), (270, 22), (300, 16), (320, 4)]


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(22), S.y(750)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 2.2, 12), np.linspace(y_n - 2.4, y_t, 28)])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.5, seg=32)
    ct = K.polyline_fn([S(px, py) for px, py in CANOPY])
    chw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in CANOPY_HW])
    K.fuselage(F, np.linspace(S.y(186), S.y(390), 14), ct, lambda y: ztop(y) - 0.25, lambda y: max(chw(y), 0.05),
               n=2.2, seg=20)
    zw = float(S.z(840))
    W = [(343, 140, 490, 0.03), (371, 150, 490, 0.03), (381, 180, 490, 0.035), (394, 200, 489, 0.04),
         (415, 250, 489, 0.045), (433, 300, 488, 0.05), (456, 330, 486, 0.055), (550, 367, 475, 0.05),
         (640, 403, 464, 0.04), (650, 406, 462, 0.035)]
    right = [((float(T.x(px)), float(T.y(le)), zw), (float(T.x(px)), float(T.y(te)), zw), t, (0, 0, 1))
             for px, le, te, t in W]
    K.surface(F, K.mirror_sections(right[1:]) + right)
    zs = float(S.z(855))
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), 0.05, (0, 0, 1))
          for px, le, te in ((380, 478, 604), (450, 514, 590), (480, 537, 599), (508, 565, 597))]
    K.surface(F, st)
    K.surface(F, K.mirror_sections(st))
    fin = [(575, 708, 802), (605, 716, 740), (635, 725, 684)]
    for sg in (-1, 1):
        K.surface(F, K.fin_sections(S, fin, x=sg * 0.95, cant_deg=20, side_sign=sg, t_root=0.05, t_tip=0.045))
    zn = float(S.z(837))
    xn = 27 * T.sx
    for sg in (-1, 1):
        K.body_rev(F, (sg * xn, S.y(786), zn), (sg * xn, S.y(735), zn), [(0, 0.38), (0.5, 0.42), (1, 0.44)], seg=20)
    # intakes under the LEX
    for sg in (-1, 1):
        y0, y1 = S.y(380), S.y(520)
        F.box((sg * 0.95, (y0 + y1) / 2, float(S.z(868))), (0.55, y0 - y1, 0.55))
    objs["air"] = F.build(mat, smooth=50)
    D = K.Part("Dark")
    for sg in (-1, 1):
        K.disc(D, (sg * xn, S.y(786) - 0.012, zn), 0.34)
        D.box((sg * 0.95, S.y(380) + 0.01, float(S.z(868))), (0.45, 0.03, 0.45))
    objs["dark"] = D.build(mat, smooth=40)

    Sx = K.Part("Stores")
    hard = []
    for sg in (-1, 1):
        lst = [(664, 380, 470, "tip"), (551, 330, 445, "aam"), (507, 318, 440, "aam")]
        if sg > 0:
            lst = lst[::-1]
        for px, nose, tail, kind in lst:
            x = abs(float(T.x(px))) * sg
            yn, yt = float(T.y(nose)), float(T.y(tail))
            if kind == "tip":
                Sx.box((x * 0.985, (yn + yt) / 2, zw), (0.2, (yn - yt) * 0.8, 0.08))
                K.missile(Sx, (x, yn, zw), yn - yt, 0.065)
                hard.append((x, (yn + yt) / 2, zw))
            else:
                K.pylon(Sx, (x, (yn + yt) / 2 - 0.4, zw), 1.4, 0.3, 0.08)
                K.missile(Sx, (x, yn, zw - 0.42), yn - yt, 0.09)
                hard.append((x, (yn + yt) / 2, zw - 0.42))
    yc = S.y(470)
    zc = float(zbot(yc)) - 0.5
    K.pylon(Sx, (0, yc, float(zbot(yc)) + 0.05), 1.2, 0.2, 0.12)
    K.body_rev(Sx, (0, yc - 2.0, zc), (0, yc + 2.0, zc), [(0, 0.05), (0.1, 0.25), (0.3, 0.36), (0.7, 0.36), (0.9, 0.25), (1, 0.04)], seg=16)
    hard.append((0, yc, zc))
    objs["stores"] = Sx.build(mat, smooth=40)

    G = K.Part("Gear")
    ym = float(T.y(470))
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.55, ym, 0.42), 0.42, 0.24, (sg * 1.0, ym + 0.15, float(zbot(ym)) + 0.1))
    yng = S.y(200)
    K.gear_leg(G, (0, yng, 0.3), 0.3, 0.13, (0, yng - 0.1, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    dz = (802 - 696) * S.s
    for sg in (-1, 1):
        K.surface(Tm, K.fin_sections(S, [(630, 724, 696), (636, 726, 682)], x=sg * (0.95 + dz * math.tan(math.radians(20))),
                                     cant_deg=20, side_sign=sg, t_root=0.06, t_tip=0.055))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    empties = {"Gun": (0, S.y(40), float(S.z(828))), "Exhaust0": (-xn, S.y(787), zn), "Exhaust1": (xn, S.y(787), zn)}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_FA18", None, rough=0.55)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-7.2, -9.2, -0.1), (7.2, 9.2, 5.8)),
             (17.1, 13.6, 5.4), "Steel Accord M3 - F/A-18 carrier fighter - Cycles CPU preview",
             flat={"gear": (0.16, 0.16, 0.16), "dark": K.DARK})


if __name__ == "__main__":
    main()
