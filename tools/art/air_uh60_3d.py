"""Steel Accord - M3 3D aircraft: UH-60-style utility helicopter (bpy 5.x).

Run:  python3 -I tools/art/air_uh60_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/uh60/uh60.glb (+ uh60_albedo.png, uh60_blade.png), docs/screens/m3_uh60_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the blade-free top
view godot/assets/us/rotors/uh60_body.png (hub px from content/manifest/us_packs.json rotors.uh60).
The concept side view draws the rotor short (foreshortened), so the side scale comes from the fuselage length
(15.4 m) and the rotor radius (8.2 m) from the top view, which agrees with real proportions.
Nodes: Body, RotorMain (main hub; spin about local Y in Godot), RotorTail (tail-rotor hub on the left of the
pylon; local X = shaft), Gun (left door gun muzzle).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "uh60"
SHEET = os.path.join(K.INC_X, "contact_sheets", "UH-60_Black_Hawk_4-view.png")
TOP_PNG = os.path.join(K.ROTOR_PNG, "uh60_body.png")
BLADES_PNG = os.path.join(K.ROTOR_PNG, "uh60_blades.png")
HUB_PX = (314.9, 259.9)
R_MAIN = 8.18

S = K.SideFrame(15.4 / 747.0, (53 + 800) / 2.0, 940.0)
T = K.TopFrame(R_MAIN / 334.0, 315.0, [(8, S.y(53)), (HUB_PX[1], S.y(335)), (620, S.y(800))])

FUS_TOP = [(54, 876), (75, 862), (100, 850), (125, 836), (150, 826), (190, 818), (300, 813), (480, 813), (520, 818),
           (550, 825), (600, 832), (650, 838), (700, 840), (760, 846), (800, 852)]
FUS_BOT = [(54, 882), (75, 897), (100, 905), (150, 909), (200, 913), (400, 912), (450, 908), (500, 903), (550, 900),
           (650, 900), (700, 881), (740, 870), (800, 856)]
FUS_HW = [(8, 4), (15, 9), (30, 30), (50, 43), (80, 51), (110, 55), (140, 56), (170, 55), (200, 54), (290, 54),
          (320, 46), (360, 34), (380, 26), (400, 22), (430, 17), (460, 11), (480, 9), (540, 9), (600, 6), (620, 3)]


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(54), S.y(800)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 1.5, 10), np.linspace(y_n - 1.7, y_t + 0.3, 30),
                         [y_t + 0.15, y_t + 0.01]])
    K.fuselage(F, ys, ztop, zbot, hw, n=lambda y: 2.6 if y > S.y(560) else 2.2, seg=32)
    # engine / transmission hump
    hump_t = K.polyline_fn([S(px, py) for px, py in ((288, 814), (310, 801), (340, 793), (450, 793), (500, 801), (548, 820))])
    K.fuselage(F, np.linspace(S.y(290), S.y(546), 12), hump_t, lambda y: ztop(y) - 0.25,
               lambda y: 0.72 * min(1.0, 0.35 + 0.65 * math.sin(math.pi * np.clip((S.y(290) - y) / (S.y(290) - S.y(546)), 0, 1)) ** 0.4),
               n=2.6, seg=20)
    ze = float(S.z(806))
    for sg in (-1, 1):
        K.body_rev(F, (sg * 0.92, S.y(500), ze), (sg * 0.92, S.y(318), ze),
                   [(0, 0.22), (0.08, 0.3), (0.25, 0.34), (0.85, 0.34), (1, 0.3)], seg=16)
        F.box((sg * 0.92, S.y(505), ze + 0.02), (0.36, 0.3, 0.28))          # exhaust box
    # tail pylon (thick fin) + stabilator
    K.surface(F, K.fin_sections(S, [(696, 798, 850), (722, 778, 805), (734, 783, 782), (744, 786, 758)], x=0,
                                t_root=0.2, t_tip=0.17))
    zs = float(S.z(853))
    st = []
    for px, le, te in ((224, 490, 518), (HUB_PX[0], 487, 522), (405, 490, 518)):
        x = float(T.x(px))
        st.append(((x, float(T.y(le)), zs), (x, float(T.y(te)), zs), 0.1, (0, 0, 1)))
    K.surface(F, st)
    # mast
    yh, zh = S(335, 757)
    F.rod((0, yh, float(hump_t(yh)) - 0.1), (0, yh, zh - 0.2), 0.17, seg=12)
    objs["air"] = F.build(mat, smooth=48)

    G = K.Part("Gear")
    rw = 0.37
    ym = S.y(235)
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.35, ym, rw), rw, 0.24, (sg * 0.9, ym + 0.15, float(zbot(ym)) + 0.15))
        G.rod((sg * 1.35, ym, rw), (sg * 0.85, ym - 0.6, float(zbot(ym)) + 0.15), 0.05, seg=6)
    yt = S.y(680)
    K.gear_leg(G, (0, yt, 0.23), 0.23, 0.14, (0, yt + 0.3, float(zbot(yt)) + 0.05))
    G.rod((-1.25, S.y(230), float(S.z(865))), (-1.75, S.y(230) + 0.5, float(S.z(866))), 0.035, seg=6)  # door gun
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, [(743, 786, 762), (746, 787, 752)], x=0, t_root=0.21, t_tip=0.2))
    for x in (float(T.x(224)), float(T.x(405))):
        Tm.box((x, float(T.y(504)), zs), (0.08, 0.75, 0.12))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    empties = {"Gun": (-1.75, S.y(230) + 0.5, float(S.z(866)))}
    return objs, empties, (yh, zh)


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_UH60", None, rough=0.7)
    bmat = L.image_material("SA_UH60_Blade", None, rough=0.8)
    objs, empties, (yh, zh) = build(mat)
    rm = K.rotor("RotorMain", (0, yh, zh), 4, R_MAIN, 0.53, bmat, root_r=0.6, phase=math.radians(40), hub_r=0.32,
                 coning=2.0, mast=0.3)
    yt, zt = S(748, 742)
    rt = K.rotor("RotorTail", (-0.42, yt, zt), 4, 1.6, 0.25, bmat, root_r=0.18, axis="x", hub_r=0.12, coning=0,
                 twist=(6, 0), thick=0.04, phase=math.radians(10), sign_x=-1)
    blade_png = os.path.join(o["out"], f"{ID}_blade.png")
    bref = K.ref_from_rgba(K.load_rgba(BLADES_PNG), erode=1)
    a = math.radians(40)
    K.blade_texture(bref, (HUB_PX[0] + 60 * math.cos(a), HUB_PX[1] + 60 * math.sin(a)),
                    (HUB_PX[0] + 320 * math.cos(a), HUB_PX[1] + 320 * math.sin(a)), 24, blade_png)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-3.0, -8.5, -0.1), (3.0, 8.5, 5.0)),
             (19.8, 16.4, 5.1), "Steel Accord M3 - UH-60 utility helicopter - Cycles CPU preview",
             flat={"gear": (0.11, 0.11, 0.1)}, extra_export=[rm, rt], blade=(bmat, blade_png, f"{ID}_blade"))


if __name__ == "__main__":
    main()
