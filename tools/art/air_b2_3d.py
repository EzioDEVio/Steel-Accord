"""Steel Accord - M3 3D aircraft: B-2-style flying-wing stealth bomber (bpy 5.x).

Run:  python3 -I tools/art/air_b2_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/b2/b2.glb (+ b2_albedo.png), docs/screens/m3_b2_sheet.png

Geometry: one lofted surface across the span. Each spanwise section runs from the leading edge to the
saw-tooth trailing edge measured on the cleaned top sprite godot/assets/aircraft/b2/b2_top.png; its upper and
lower contours blend from the concept side-view profile (centre body / cockpit / engine humps, expanded
contact sheet bottom-left cell) to a thin aerofoil outboard. The concept top view is ~40% deeper than the
real aircraft; X uses the real span (52.4 m), Y the side-view length (21 m).
Nodes: Body, Exhaust0..3 (upper-surface exhaust slots, left -> right), Hardpoint0/1 (left/right bomb bays).
Team colour: small SA_Team panels near both wingtips (no fin).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "b2"
SHEET = os.path.join(K.INC_X, "contact_sheets", "B-2_Spirit_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(21.0 / 768.0, (29 + 797) / 2.0, 912.0)
T = K.TopFrame(52.4 / 756.0, 388.0, [(175, S.y(29)), (599, S.y(797))])

TOP_LINE = [(30, 802), (40, 795), (60, 783), (80, 768), (100, 753), (150, 730), (200, 724), (250, 723), (300, 726),
            (350, 730), (400, 737), (450, 748), (500, 760), (550, 764), (600, 765), (700, 768), (750, 773), (780, 798),
            (797, 812)]
BOT_LINE = [(30, 802), (40, 803), (60, 809), (80, 819), (100, 830), (150, 841), (250, 843), (350, 845), (400, 844),
            (450, 841), (500, 836), (550, 831), (600, 822), (650, 818), (700, 817), (750, 815), (780, 814), (797, 813)]
# right-half trailing edge (top px, py); leading edge is the straight line from the apex to the tip
TE = [(388, 599), (462, 541), (480, 543), (500, 549), (580, 491), (700, 597), (766, 548)]
LE_TIP = (766, 546)


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in TOP_LINE])
    zbot = K.polyline_fn([S(px, py) for px, py in BOT_LINE])
    te_f = K.polyline_fn(TE)
    z_mid = float(S.z(806))
    xs_px = sorted(set(list(np.linspace(388, 766, 26)) + [p[0] for p in TE]))
    xcs = [1.0, 0.88, 0.75, 0.6, 0.45, 0.32, 0.2, 0.11, 0.05, 0.015, 0.0]
    rings = []
    order = [-p for p in xs_px[::-1] if p != 388] + xs_px      # signed px offsets, left tip -> right tip
    for spx in order:
        px = abs(spx)
        x = float(T.x(px)) * (1 if spx >= 0 else -1)
        f = (px - 388) / (LE_TIP[0] - 388)
        le_py = 175 + (LE_TIP[1] - 175) * f
        te_py = float(te_f(px))
        if px >= 765.9:
            te_py = le_py + 3
        yle, yte = float(T.y(le_py)), float(T.y(te_py))
        ax = abs(x)
        w = float(np.clip(1 - (ax - 3.0) / 4.5, 0, 1)) ** 1.5           # 1 = centre body, 0 = outer wing
        ring = []
        pts = [(xc, +1) for xc in xcs] + [(xc, -1) for xc in xcs[::-1][1:-1]]
        ch = yle - yte
        t_out = 0.075 - 0.035 * min(ax / 26.0, 1)
        for xc, sg in pts:
            y = yle - ch * xc
            wing = sg * K.naca_t(xc, t_out) * ch
            if sg > 0:
                body = float(ztop(y)) - z_mid
            else:
                body = float(zbot(y)) - z_mid
            # body contours are taken along absolute Y, faded to the trailing edge for clean closure
            fade = min(1.0, (1 - xc) / 0.08) if xc > 0.92 else 1.0
            z = z_mid + w * body * fade + (1 - w) * wing
            if sg < 0 and w > 0:
                z = min(z, z_mid + (1 - w) * wing)
            ring.append((x, y, z))
        rings.append(ring)
    F = K.Part("Airframe")
    F.rings(rings)
    # engine humps above the inboard wing (intake to exhaust)
    for sg in (-1, 1):
        xc_ = sg * (388 - 316) * T.sx
        y0, y1 = float(T.y(300)), float(T.y(540))
        rr = []
        for t in np.linspace(0, 1, 12):
            y = y0 + (y1 - y0) * t
            f = math.sin(math.pi * min(1.0, 0.04 + 0.96 * t)) ** 0.5
            zt = float(ztop(y)) - 0.9 * (1 - f)
            rr.append(K.superellipse_ring(y, xc_, 1.6 * max(f, 0.25), zt - 0.55, 0.55 * max(f, 0.2), 2.4, 20))
        F.rings(rr)
    objs["air"] = F.build(mat, smooth=40)

    G = K.Part("Gear")
    zb = float(zbot(0.0))
    for sg in (-1, 1):
        y = float(T.y(430))
        K.gear_leg(G, (sg * 6.1, y, 0.55), 0.55, 0.34, (sg * 6.1, y, z_mid - 0.3), twin=True)
    yng = float(T.y(270))
    K.gear_leg(G, (0, yng, 0.45), 0.45, 0.24, (0, yng, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    for sg in (-1, 1):
        x = sg * float(T.x(735))
        y = float(T.y(560))
        Tm.box((x, y, z_mid + 0.12), (1.6, 0.6, 0.08), rot=(0, 0, sg * math.radians(36)))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    empties = {}
    for i, px in enumerate((300, 332, 444, 476)):
        x = float(T.x(px))
        y = float(T.y(540))
        empties[f"Exhaust{i}"] = (x, y, float(ztop(y)) - 0.2)
    yb = float(T.y(420))
    for i, sg in enumerate((-1, 1)):
        empties[f"Hardpoint{i}"] = (sg * 1.6, yb, float(zbot(yb)) - 0.05)
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_B2", None, rough=0.55)
    objs, empties = build(mat)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-27.0, -11.5, -0.1), (27.0, 11.5, 6.0)),
             (21.0, 52.4, 5.2), "Steel Accord M3 - B-2 stealth bomber - Cycles CPU preview",
             flat={"gear": (0.1, 0.1, 0.1)}, cell=0.05, ao=0.4)


if __name__ == "__main__":
    main()
