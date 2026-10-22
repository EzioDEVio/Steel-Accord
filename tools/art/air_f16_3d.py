"""Steel Accord - M3 3D aircraft: F-16-style single-engine multirole fighter (bpy 5.x).

Run:  python3 -I tools/art/air_f16_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/f16/f16.glb (+ f16_albedo.png), docs/screens/m3_f16_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the cleaned top
sprite godot/assets/aircraft/f16/f16_top.png. The concept top view is much stubbier than the side view
(length/span 1.13 vs 1.52 real), so X uses the real span and Y is rectified through 4 landmarks.
Landing gear is added (concept is gear-up). Nodes: Body, Gun (left wing-root cannon), Exhaust0 (nozzle),
Hardpoint0..5 (left tip, left outer, left tank, right tank, right outer, right tip).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "f16"
SHEET = os.path.join(K.INC_X, "contact_sheets", "F-16_Fighting_Falcon_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(15.06 / 785.0, (20 + 805) / 2.0, 938.0)
T = K.TopFrame(4.72 / 265.0, 328.0, [(3, S.y(20)), (190, S.y(295)), (490, S.y(640)), (640, S.y(805))])

FUS_TOP = [(52, 862), (80, 850), (110, 840), (160, 827), (190, 820), (300, 815), (425, 807), (540, 808), (640, 803),
           (700, 808), (735, 818)]
FUS_BOT = [(52, 866), (80, 872), (110, 876), (160, 877), (265, 878), (420, 879), (560, 873), (640, 868), (735, 864)]
CANOPY = [(188, 821), (220, 799), (250, 787), (290, 781), (335, 786), (380, 796), (430, 808)]
FUS_HW = [(5, 2), (15, 4), (30, 8), (60, 17), (100, 27), (150, 34), (200, 37), (300, 38), (500, 38), (560, 37),
          (590, 34), (610, 30)]
CANOPY_HW = [(110, 2), (125, 14), (150, 22), (190, 25), (230, 22), (265, 12), (285, 2)]
Z_W = 1.35


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(52), S.y(735)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 2.0, 12), np.linspace(y_n - 2.2, y_t + 0.05, 28)])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.4, seg=32)
    F.rod((0, S.y(20), float(S.z(864))), (0, y_n - 0.05, float(S.z(863))), 0.03, seg=6)       # pitot
    ct = K.polyline_fn([S(px, py) for px, py in CANOPY])
    chw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in CANOPY_HW])
    K.fuselage(F, np.linspace(S.y(190), S.y(428), 14), ct, lambda y: ztop(y) - 0.2, lambda y: max(chw(y), 0.04),
               n=2.2, seg=20)
    # chin intake duct
    yi0, yi1 = S.y(270), S.y(500)
    zi_t = float(S.z(876))
    for_y = np.linspace(yi0, yi1, 8)
    rings = []
    for k, y in enumerate(for_y):
        f = k / (len(for_y) - 1)
        zb = float(S.z(905)) + (float(S.z(878)) - float(S.z(905))) * max(0.0, (f - 0.55) / 0.45) ** 1.5
        rings.append(K.superellipse_ring(y, 0, 0.5, (zi_t + zb) / 2, max((zi_t - zb) / 2, 0.05), 3.0, 16))
    F.rings(rings)
    # wing + LERX (one thin surface), z_w, no dihedral
    W = [(328, 150, 474, 0.035), (364, 165, 474, 0.035), (374, 200, 474, 0.038), (390, 250, 474, 0.042),
         (409, 285, 474, 0.05), (420, 297, 474, 0.05), (480, 356, 474, 0.045), (520, 387, 474, 0.042),
         (560, 417, 474, 0.04), (584, 426, 474, 0.035)]
    right = [((float(T.x(px)), float(T.y(le)), Z_W), (float(T.x(px)), float(T.y(te)), Z_W), t, (0, 0, 1))
             for px, le, te, t in W]
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # horizontal stabilisers (anhedral 10 deg)
    zs = float(S.z(856))
    st = []
    for px, le, te in ((362, 505, 614), (400, 518, 618), (440, 550, 621), (480, 581, 616), (485, 592, 612)):
        x = float(T.x(px))
        st.append(((x, float(T.y(le)), zs - x * math.tan(math.radians(10))), (x, float(T.y(te)), zs - x * math.tan(math.radians(10))),
                   0.05, (0, 0, 1)))
    K.surface(F, K.mirror_sections(st[1:]) + st)
    # fin + root fairing
    K.surface(F, K.fin_sections(S, [(640, 778, 800), (700, 798, 730), (756, 815, 682)], x=0, t_root=0.06, t_tip=0.05))
    F.box((0, S.y(712), float(S.z(795))), (0.3, 70 * S.s, 0.3))
    # ventral fins
    for sg in (-1, 1):
        F.beam((sg * 0.45, S.y(690), float(S.z(866))), (sg * 0.62, S.y(735), float(S.z(888))), 0.04, 0.35, up=(sg, 0, 0))
    # nozzle
    zn = float(S.z(845))
    K.body_rev(F, (0, S.y(806), zn), (0, S.y(728), zn), [(0, 0.44), (0.4, 0.5), (0.9, 0.53), (1, 0.53)], seg=24)
    objs["air"] = F.build(mat, smooth=50)
    D = K.Part("Dark")
    K.disc(D, (0, S.y(806) - 0.012, zn), 0.4)
    K.disc(D, (0, yi0 + 0.012, (zi_t + float(S.z(905))) / 2), 0.42, squash=0.62)
    objs["dark"] = D.build(mat, smooth=40)

    # stores
    Sx = K.Part("Stores")
    hard = []
    for sg in (-1, 1):
        lst = [(593, 352, 500, "tip"), (543, 306, 500, "aam"), (440, 232, 505, "tank")]
        if sg > 0:
            lst = lst[::-1]
        for px, nose, tail, kind in lst:
            x = -abs(float(T.x(px))) if sg < 0 else abs(float(T.x(px)))
            yn, yt = float(T.y(nose)), float(T.y(tail))
            if kind == "tip":
                Sx.box((x * 0.985, (yn + yt) / 2 - 0.3, Z_W), (0.2, (yn - yt) * 0.7, 0.08))
                K.missile(Sx, (x + (0.08 if x > 0 else -0.08), yn, Z_W), yn - yt, 0.065)
                hard.append((x, (yn + yt) / 2, Z_W))
            elif kind == "aam":
                K.pylon(Sx, (x, (yn + yt) / 2 - 0.4, Z_W), 1.3, 0.28, 0.08)
                K.missile(Sx, (x, yn, Z_W - 0.38), yn - yt, 0.075)
                hard.append((x, (yn + yt) / 2, Z_W - 0.38))
            else:
                K.pylon(Sx, (x, (yn + yt) / 2 - 0.3, Z_W), 1.6, 0.22, 0.1)
                zc = Z_W - 0.2 - 0.36
                K.body_rev(Sx, (x, yt, zc), (x, yn, zc), [(0, 0.05), (0.08, 0.2), (0.25, 0.34), (0.6, 0.36),
                                                          (0.85, 0.28), (1, 0.03)], seg=16)
                for k in range(3):
                    a = math.pi / 2 + k * 2 * math.pi / 3
                    Sx.beam((x, yt + 0.25, zc), (x + 0.45 * math.cos(a), yt + 0.1, zc + 0.45 * math.sin(a)), 0.02, 0.35,
                            up=(0, 1, 0))
                hard.append((x, (yn + yt) / 2, zc))
    objs["stores"] = Sx.build(mat, smooth=40)

    G = K.Part("Gear")
    ym = float(T.y(445))
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.18, ym, 0.36), 0.36, 0.22, (sg * 0.55, ym + 0.1, float(zbot(ym)) + 0.1))
    yng = S.y(300)
    K.gear_leg(G, (0, yng, 0.28), 0.28, 0.16, (0, yng - 0.05, float(S.z(904)) + 0.05))
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, [(754, 814, 686), (760, 819, 673)], x=0, t_root=0.07, t_tip=0.06))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    empties = {"Gun": (-0.62, S.y(232), float(S.z(840))), "Exhaust0": (0, S.y(807), zn)}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_F16", None, rough=0.55)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-5.4, -8.2, -0.1), (5.4, 8.2, 5.2)),
             (15.1, 9.9, 5.0), "Steel Accord M3 - F-16 multirole fighter - Cycles CPU preview",
             flat={"gear": (0.16, 0.16, 0.16), "dark": K.DARK})


if __name__ == "__main__":
    main()
