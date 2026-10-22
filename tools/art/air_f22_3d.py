"""Steel Accord - M3 3D aircraft: F-22-style twin-engine stealth air-superiority fighter (bpy 5.x).

Run:  python3 -I tools/art/air_f22_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/f22/f22.glb (+ f22_albedo.png), docs/screens/m3_f22_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the cleaned top
sprite godot/assets/aircraft/f22/f22_top.png (X: span 13.6 m; Y rectified through nose, canopy and nozzle
landmarks). The concept side view shows both canted fins offset by perspective; the near fin is used.
Concept fuselage is deeper than real (overall height ~5.6 m). Clean configuration (internal bays).
Nodes: Body, Gun (right shoulder cannon), Exhaust0/1 (left/right nozzles), Hardpoint0..3 (bay release points).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "f22"
SHEET = os.path.join(K.INC_X, "contact_sheets", "F-22_Raptor_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(18.9 / 832.0, (23 + 855) / 2.0, 930.0)
T = K.TopFrame(6.8 / 254.5, 296.5, [(9, S.y(23)), (120, S.y(212)), (540, S.y(830))])

FUS_TOP = [(25, 840), (50, 825), (100, 810), (140, 801), (200, 795), (280, 791), (400, 793), (500, 799), (600, 801),
           (700, 806), (780, 816), (815, 830)]
FUS_BOT = [(25, 842), (50, 853), (100, 863), (150, 869), (200, 873), (250, 877), (300, 881), (400, 887), (500, 887),
           (600, 886), (650, 879), (700, 871), (750, 866), (815, 858)]
CANOPY = [(138, 802), (160, 786), (185, 772), (210, 766), (240, 769), (268, 782), (288, 794)]
FUS_HW = [(9, 1), (15, 4), (30, 14), (60, 24), (100, 33), (140, 40), (155, 52), (170, 70), (180, 81), (200, 85),
          (300, 88), (400, 85), (450, 78), (480, 66), (510, 52), (530, 44)]
CANOPY_HW = [(55, 3), (70, 15), (100, 22), (140, 21), (170, 12), (185, 3)]


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(25), S.y(815)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 2.6, 14), np.linspace(y_n - 2.8, y_t, 28)])
    K.fuselage(F, ys, ztop, zbot, hw, n=lambda y: 2.2 if y > S.y(150) else 3.4, seg=32)
    ct = K.polyline_fn([S(px, py) for px, py in CANOPY])
    chw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in CANOPY_HW])
    K.fuselage(F, np.linspace(S.y(139), S.y(287), 14), ct, lambda y: ztop(y) - 0.25, lambda y: max(chw(y), 0.05),
               n=2.2, seg=20)
    zw = float(S.z(840))
    W = [(296.5, 200, 485, 0.04), (382, 228, 482, 0.045), (400, 247, 480, 0.045), (431, 278, 480, 0.042),
         (470, 315, 468, 0.04), (500, 341, 459, 0.035), (530, 370, 441, 0.03), (547, 386, 430, 0.025)]
    right = [((float(T.x(px)), float(T.y(le)), zw), (float(T.x(px)), float(T.y(te)), zw), t, (0, 0, 1))
             for px, le, te, t in W]
    K.surface(F, K.mirror_sections(right[1:]) + right)
    zs = float(S.z(850))
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), 0.04, (0, 0, 1))
          for px, le, te in ((380, 482, 585), (400, 485, 580), (430, 495, 569), (460, 506, 556), (474, 518, 545))]
    K.surface(F, st)
    K.surface(F, K.mirror_sections(st))
    fin = [(640, 790, 806), (668, 762, 745), (695, 736, 686)]
    for sg in (-1, 1):
        K.surface(F, K.fin_sections(S, fin, x=sg * 1.37, cant_deg=28, side_sign=sg, t_root=0.05, t_tip=0.045))
    zn = float(S.z(843))
    xn = 25 * T.sx
    for sg in (-1, 1):
        F.box((sg * xn, S.y(810), zn), (0.85, 0.9, 0.62))                                       # 2D nozzle
    objs["air"] = F.build(mat, smooth=50)
    D = K.Part("Dark")
    for sg in (-1, 1):
        D.box((sg * xn, S.y(810) - 0.46, zn), (0.7, 0.03, 0.45))
    objs["dark"] = D.build(mat, smooth=40)

    G = K.Part("Gear")
    ym = float(T.y(400))
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.6, ym, 0.45), 0.45, 0.26, (sg * 1.1, ym + 0.1, float(zbot(ym)) + 0.1))
    yng = S.y(180)
    K.gear_leg(G, (0, yng, 0.33), 0.33, 0.16, (0, yng - 0.05, float(zbot(yng)) + 0.1))
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    dz = (806 - 697) * S.s
    for sg in (-1, 1):
        K.surface(Tm, K.fin_sections(S, [(690, 741, 697), (696, 736, 684)], x=sg * (1.37 + dz * math.tan(math.radians(28))),
                                     cant_deg=28, side_sign=sg, t_root=0.06, t_tip=0.055))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    yb = float(T.y(330))
    empties = {"Gun": (1.25, S.y(300), float(S.z(800))), "Exhaust0": (-xn, S.y(832), zn), "Exhaust1": (xn, S.y(832), zn)}
    for i, (x, dy) in enumerate(((-1.0, 0.8), (-0.45, 0.0), (0.45, 0.0), (1.0, 0.8))):
        empties[f"Hardpoint{i}"] = (x, yb + dy, float(zbot(yb)) - 0.05)
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_F22", None, rough=0.5)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-7.2, -10.0, -0.1), (7.2, 10.0, 6.0)),
             (18.9, 13.6, 5.6), "Steel Accord M3 - F-22 air-superiority fighter - Cycles CPU preview",
             flat={"gear": (0.16, 0.16, 0.16), "dark": K.DARK})


if __name__ == "__main__":
    main()
