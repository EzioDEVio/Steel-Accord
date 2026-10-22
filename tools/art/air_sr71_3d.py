"""Steel Accord - M3 3D aircraft: SR-71-style Mach-3 reconnaissance aircraft (bpy 5.x).

Run:  python3 -I tools/art/air_sr71_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/sr71/sr71.glb (+ sr71_albedo.png), docs/screens/m3_sr71_sheet.png

Geometry: narrow fuselage core lofted from the concept side view (expanded contact sheet, bottom-left cell),
chines + delta wing as one thin lifting surface whose planform is measured on the cleaned top sprite
godot/assets/aircraft/sr71/sr71_top.png, two large nacelles with inlet spikes, inward-canted fins on the
nacelles. The concept top view is very stubby (length/span 1.18 vs 1.93 real): X uses the real span 16.9 m,
Y is rectified (nose, spike tips, tail) to the side-view length 32.7 m. The concept nacelles are larger than
real, so the gear is tall (overall height ~8 m).
Nodes: Body, Exhaust0/1 (left/right nacelle nozzles). No guns or external hardpoints (recon aircraft).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "sr71"
SHEET = os.path.join(K.INC_X, "contact_sheets", "SR-71_Blackbird_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(32.7 / 805.0, (20 + 825) / 2.0, 900.0)
T = K.TopFrame(16.9 / 509.0, 329.0, [(16, S.y(20)), (322, S.y(430)), (611, S.y(805))])

FUS_TOP = [(20, 815), (60, 809), (100, 799), (150, 789), (200, 776), (300, 772), (400, 772), (500, 766), (600, 763),
           (700, 766), (750, 778), (780, 800), (805, 815)]
FUS_BOT = [(20, 815), (60, 818), (100, 826), (150, 831), (200, 834), (300, 836), (400, 837), (500, 838), (600, 838),
           (700, 836), (750, 832), (780, 826), (805, 818)]
FUS_HW = [(16, 0.5), (60, 3), (100, 10), (150, 20), (200, 26), (300, 29), (500, 28), (580, 20), (611, 3)]
PLAN = [(329, 30, 611), (341, 80, 590), (351, 100, 580), (371, 150, 572), (384, 200, 570), (391, 250, 566),
        (400, 350, 560), (430, 360, 556), (460, 370, 548), (490, 380, 540), (500, 400, 539), (527, 450, 537),
        (560, 479, 524), (583, 500, 509)]
X_NAC = 129


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(20), S.y(805)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 8.0, 16), np.linspace(y_n - 8.5, y_t, 26)])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.2, seg=28)
    zw = float(S.z(820))
    right = []
    for px, le, te in PLAN:
        x = float(T.x(px))
        chord_t = 0.03 if px < 400 else 0.035
        right.append(((x, float(T.y(le)), zw), (x, float(T.y(te)), zw), chord_t, (0, 0, 1)))
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # nacelles with inlet spikes
    zn = float(S.z(838))
    xn = X_NAC * T.sx
    y_sp, y_lip, y_end = S.y(430), S.y(486), S.y(795)
    for sg in (-1, 1):
        x = sg * xn
        K.body_rev(F, (x, y_end, zn), (x, y_lip, zn),
                   [(0, 0.85), (0.08, 1.0), (0.3, 1.16), (0.75, 1.16), (0.95, 1.02), (1, 0.95)], seg=26)
        K.body_rev(F, (x, y_lip + 0.3, zn), (x, y_sp, zn), [(0, 0.75), (0.4, 0.55), (0.8, 0.22), (1, 0.02)], seg=16)
    # inward-canted fins on the nacelles
    fin = [(655, 750, 806), (680, 740, 740), (700, 722, 702)]
    for sg in (-1, 1):
        K.surface(F, K.fin_sections(S, fin, x=sg * xn, cant_deg=15, side_sign=-sg, t_root=0.05, t_tip=0.04))
    objs["air"] = F.build(mat, smooth=45)
    D = K.Part("Dark")
    for sg in (-1, 1):
        K.disc(D, (sg * xn, y_end - 0.01, zn), 0.82)
    objs["dark"] = D.build(mat, smooth=40)

    G = K.Part("Gear")
    ym = float(T.y(470))
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 2.6, ym, 0.55), 0.55, 0.3, (sg * 2.4, ym + 0.1, zw - 0.1), twin=True)
    yng = S.y(250)
    K.gear_leg(G, (0, yng, 0.38), 0.38, 0.18, (0, yng, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    dz = (806 - 710) * S.s
    for sg in (-1, 1):
        K.surface(Tm, K.fin_sections(S, [(696, 726, 710), (700, 722, 699)],
                                     x=sg * xn - sg * dz * math.tan(math.radians(15)), cant_deg=15, side_sign=-sg,
                                     t_root=0.05, t_tip=0.045))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    empties = {"Exhaust0": (-xn, y_end - 0.05, zn), "Exhaust1": (xn, y_end - 0.05, zn)}
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_SR71", None, rough=0.5)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-9.0, -17.0, -0.1), (9.0, 17.0, 8.5)),
             (32.7, 16.9, 8.1), "Steel Accord M3 - SR-71 reconnaissance aircraft - Cycles CPU preview",
             flat={"gear": (0.14, 0.14, 0.14), "dark": K.DARK}, cell=0.04)


if __name__ == "__main__":
    main()
