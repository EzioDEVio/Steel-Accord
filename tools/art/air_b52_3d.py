"""Steel Accord - M3 3D aircraft: B-52-style eight-engine strategic bomber (bpy 5.x).

Run:  python3 -I tools/art/air_b52_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/b52/b52.glb (+ b52_albedo.png), docs/screens/m3_b52_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the cleaned top
sprite godot/assets/aircraft/b52/b52_top.png (X: span 56.4 m; Y: nose/tail landmarks, length 48.5 m).
The concept fin is shorter than the real one; it is kept. Bicycle main gear (4 twin trucks) is added;
wingtip outrigger wheels are omitted (see docs/M3_AIRCRAFT.md).
Nodes: Body, Exhaust0..7 (engine exits, left outboard -> right outboard), Hardpoint0..3 (bomb-bay release
points 0/1, inner-wing pylons 2/3).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "b52"
SHEET = os.path.join(K.INC_X, "contact_sheets", "B-52_Stratofortress_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(48.5 / 785.0, (12 + 797) / 2.0, 858.0)
T = K.TopFrame(28.2 / 372.5, 383.5, [(100, S.y(12)), (665, S.y(797))])

FUS_TOP = [(13, 800), (25, 789), (40, 781), (60, 767), (80, 761), (100, 759), (150, 757), (620, 757), (700, 760),
           (760, 766), (780, 779), (792, 788)]
FUS_BOT = [(13, 806), (25, 816), (40, 823), (60, 831), (80, 838), (150, 840), (500, 840), (600, 832), (650, 820),
           (700, 811), (730, 806), (760, 801), (780, 793), (792, 789)]
FUS_HW = [(100, 2), (110, 8.5), (130, 16.5), (160, 22), (200, 23), (500, 22.5), (560, 20), (600, 16), (620, 12.5),
          (640, 10), (660, 3)]
PODS = [(-231.5, 285, 350), (-126.5, 236, 300), (126.5, 236, 300), (231.5, 285, 350)]


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(13), S.y(792)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 6.0, 14), np.linspace(y_n - 6.5, y_t + 0.3, 34), [y_t + 0.05]])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.8, seg=36)
    zw = float(S.z(770))
    W = [(383.5, 226, 362, 0.12), (410, 240, 369, 0.12), (460, 270, 386, 0.11), (550, 322, 416, 0.1),
         (650, 379, 447, 0.09), (700, 406, 463, 0.08), (752, 437, 478, 0.06)]
    right = []
    for px, le, te, t in W:
        x = float(T.x(px))
        z = zw - abs(x) * math.tan(math.radians(1.5))
        right.append(((x, float(T.y(le)), z), (x, float(T.y(te)), z), t, (0, 0, 1)))
    K.surface(F, K.mirror_sections(right[1:]) + right)
    zs = float(S.z(782))
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), t, (0, 0, 1))
          for px, le, te, t in ((383.5, 515, 614, 0.09), (410, 528, 614, 0.09), (460, 560, 615, 0.08), (500, 585, 616, 0.07),
                                (507, 592, 616, 0.05))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    K.surface(F, K.fin_sections(S, [(645, 755, 760), (680, 752, 700), (705, 749, 633)], x=0, t_root=0.1, t_tip=0.08))
    # twin engine pods on 4 pylons
    exh = []
    dark = []
    for xo, py0, py1 in PODS:
        xc = xo * T.sx
        y0, y1 = float(T.y(py0)), float(T.y(py1))
        zwx = zw - abs(xc) * math.tan(math.radians(1.5))
        zp = zwx - 1.55
        F.beam((xc, y0 - 1.0, zwx - 0.2), (xc, y1 + 0.3, zwx - 0.2), 0.3, 0.1)
        F.box((xc, (y0 + y1) / 2 - 0.6, zwx - 0.7), (0.35, (y0 - y1) * 0.7, 1.1))
        for dx in (-0.78, 0.78):
            K.body_rev(F, (xc + dx, y1, zp), (xc + dx, y0, zp),
                       [(0, 0.42), (0.1, 0.56), (0.5, 0.68), (0.85, 0.68), (0.97, 0.62), (1, 0.55)], seg=16)
            exh.append((xc + dx, y1 - 0.05, zp))
            dark.append(((xc + dx, y1 + 0.01, zp), 0.36))
            dark.append(((xc + dx, y0 - 0.01, zp), 0.48))
    objs["air"] = F.build(mat, smooth=45)
    D = K.Part("Dark")
    for p, r in dark:
        K.disc(D, p, r, seg=12)
    objs["dark"] = D.build(mat, smooth=40)

    G = K.Part("Gear")
    for gp in (250, 285, 470, 505):
        for sg in (-1, 1):
            K.gear_leg(G, (sg * 1.05, S.y(gp), 0.55), 0.55, 0.38, (sg * 0.9, S.y(gp), float(zbot(S.y(gp))) + 0.2))
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, [(700, 749, 645), (705, 749, 631)], x=0, t_root=0.11, t_tip=0.1))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    exh.sort(key=lambda p: p[0])
    empties = {f"Exhaust{i}": p for i, p in enumerate(exh)}
    yb = S.y(380)
    zb = float(zbot(yb)) - 0.05
    empties.update({"Hardpoint0": (-0.45, yb, zb), "Hardpoint1": (0.45, yb, zb)})
    ywp = float(T.y(330))
    for i, sg in ((2, -1), (3, 1)):
        x = sg * 70 * T.sx
        empties[f"Hardpoint{i}"] = (x, ywp, zw - abs(x) * math.tan(math.radians(1.5)) - 0.9)
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_B52", None, rough=0.62)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-28.8, -25.0, -0.1), (28.8, 25.0, 14.5)),
             (48.5, 56.4, 14.2), "Steel Accord M3 - B-52 strategic bomber - Cycles CPU preview",
             flat={"gear": (0.12, 0.12, 0.12), "dark": K.DARK}, cell=0.06, ao=0.4)


if __name__ == "__main__":
    main()
