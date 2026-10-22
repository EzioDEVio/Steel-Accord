"""Steel Accord - M3 3D aircraft: C-17-style four-jet strategic airlifter (bpy 5.x).

Run:  python3 -I tools/art/air_c17_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/c17/c17.glb (+ c17_albedo.png), docs/screens/m3_c17_sheet.png

References: incoming_airlift/aircraft_image_assets/c17_globemaster_turnaround.png (side = bottom-left cell, nose
left; top = top-right cell, drawn nose DOWN -> rotated 180 deg). Touching views are separated with
airkit.sheet_cell(split=4). Top and side views agree in scale (~0.087 m/px top, length 53 m, span 51.8 m).
Nodes: Body (fuselage, anhedral wing with winglets, 4 podded engines, T-tail, sponsons, gear),
Exhaust0..3 (engine exits, left outer -> right outer). Cargo ramp closed; no weapons.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "c17"
SHEET = os.path.join(K.INC_LIFT, "c17_globemaster_turnaround.png")

S = K.SideFrame(53.0 / 865.0, (6 + 871) / 2.0, 950.0)
T = K.TopFrame(25.9 / 295.0, 362.0, [(396, S.y(6)), (1003, S.y(871))])

FUS_TOP = [(8, 875), (20, 862), (40, 848), (60, 832), (80, 824), (100, 818), (150, 812), (200, 808), (300, 806),
           (400, 806), (500, 802), (600, 800), (700, 802), (750, 804), (780, 812), (800, 815), (815, 818)]
FUS_BOT = [(8, 893), (20, 905), (40, 918), (60, 923), (100, 925), (150, 929), (200, 931), (300, 933), (450, 933),
           (500, 928), (550, 915), (600, 901), (650, 885), (700, 869), (750, 840), (780, 830), (800, 823), (815, 819)]
FUS_HW = [(396, 3), (400, 9), (410, 17), (430, 27), (460, 38), (500, 45), (550, 50), (650, 50), (750, 45), (800, 43),
          (850, 37), (880, 28), (900, 17.5), (930, 13.5), (990, 6), (994, 2)]
NACS = [(-191, 563, 625), (-113, 529, 592), (113, 529, 592), (191, 563, 625)]
ANH = math.radians(-3.0)


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_n, y_t = S.y(8), S.y(815)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 6.0, 14), np.linspace(y_n - 6.5, y_t + 0.3, 34), [y_t + 0.05]])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.3, seg=36)
    # sponsons
    zsp = float(S.z(925))
    for sg in (-1, 1):
        y0, y1 = S.y(270), S.y(430)
        rr = []
        for t in np.linspace(0, 1, 10):
            y = y0 + (y1 - y0) * t
            f = math.sin(math.pi * min(1.0, 0.08 + 0.92 * t)) ** 0.35
            rr.append(K.superellipse_ring(y, sg * 3.1, 0.75 * max(f, 0.2), zsp, 1.0 * max(f, 0.3), 2.8, 16))
        F.rings(rr)
    zw = float(S.z(815))
    F.box((0, float(T.y(615)), zw - 0.45), (3.2, float(T.y(562)) - float(T.y(675)), 0.9))
    W = [(362, 556, 672, 0.15), (412, 562, 675, 0.15), (450, 585, 695, 0.14), (500, 614, 701, 0.13),
         (600, 672, 723, 0.11), (640, 694, 731, 0.1), (656, 704, 736, 0.09)]
    right = []
    for px, le, te, t in W:
        x = float(T.x(px))
        z = zw + abs(x) * math.tan(ANH)
        right.append(((x, float(T.y(le)), z), (x, float(T.y(te)), z), t, (0, 0, 1)))
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # winglets
    for sg in (-1, 1):
        x = sg * float(T.x(656))
        z0 = zw + abs(x) * math.tan(ANH)
        y0, y1 = float(T.y(704)), float(T.y(736))
        secs = [((x, y0 - 0.2, z0), (x, y1, z0), 0.08, (sg, 0, 0)),
                ((x + sg * 0.5, y0 - 1.3, z0 + 2.4), (x + sg * 0.5, y1 - 0.3, z0 + 2.4), 0.06, (sg, 0, 0))]
        K.surface(F, secs)
    # engines on pylons
    zn = float(S.z(843))
    exh = []
    dark = []
    for xo, p0, p1 in NACS:
        x = xo * T.sx
        zwx = zw + abs(x) * math.tan(ANH)
        znx = zn + (zwx - zw)
        y0, y1 = float(T.y(p0)), float(T.y(p1))
        K.body_rev(F, (x, y1, znx), (x, y0, znx), [(0, 0.8), (0.1, 1.15), (0.3, 1.42), (0.8, 1.45), (0.95, 1.38), (1, 1.3)],
                   seg=22)
        F.beam((x, y1 + 1.0, znx + 1.2), (x, y0 - 3.5, zwx - 0.2), 0.3, 0.9)
        exh.append((x, y1 - 0.05, znx))
        dark.append(((x, y1 + 0.01, znx), 0.62))
        dark.append(((x, y0 - 0.01, znx), 1.15))
    # T-tail
    K.surface(F, K.fin_sections(S, [(640, 745, 806), (680, 795, 720), (727, 808, 657)], x=0, t_root=0.12, t_tip=0.1))
    zs = float(S.z(660))
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), t, (0, 0, 1))
          for px, le, te, t in ((362, 935, 994, 0.1), (400, 945, 992, 0.1), (450, 966, 998, 0.09), (480, 978, 1001, 0.08),
                                (498, 988, 1003, 0.06))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    objs["air"] = F.build(mat, smooth=45)
    D = K.Part("Dark")
    for p, r in dark:
        K.disc(D, p, r)
    objs["dark"] = D.build(mat, smooth=40)

    G = K.Part("Gear")
    for sg in (-1, 1):
        for gp in (310, 345, 380):
            K.gear_leg(G, (sg * 3.1, S.y(gp), 0.62), 0.62, 0.45, (sg * 3.1, S.y(gp), zsp - 0.5))
    yng = S.y(45)
    K.gear_leg(G, (0, yng, 0.5), 0.5, 0.28, (0, yng, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    for sg in (-1, 1):
        x = sg * float(T.x(498))
        Tm.box((x, float(T.y(995)), zs), (0.14, 1.4, 0.3))
    K.surface(Tm, K.fin_sections(S, [(722, 806, 668), (727, 808, 655)], x=0, t_root=0.14, t_tip=0.12))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    exh.sort(key=lambda p: p[0])
    return objs, {f"Exhaust{i}": p for i, p in enumerate(exh)}


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_cell="tr", top_rot=2, split=4)
    mat = L.image_material("SA_C17", None, rough=0.62)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-27.0, -27.5, -0.1), (27.0, 27.5, 19.0)),
             (53.0, 51.8, 18.4), "Steel Accord M3 - C-17 strategic airlifter - Cycles CPU preview",
             flat={"gear": (0.12, 0.12, 0.12), "dark": K.DARK}, cell=0.07, ao=0.4)


if __name__ == "__main__":
    main()
