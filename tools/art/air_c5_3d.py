"""Steel Accord - B3 3D aircraft: C-5-class strategic airlifter with an opening nose visor (bpy 5.x).

Run:  SA_ASSET_HOME=/home/claude python3 -I tools/art/air_c5_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/c5/c5.glb (+ c5_albedo.png), docs/screens/b3_c5_sheet.png

Original model built with the M3 aircraft kit (airkit.py) from pixel measurements on the client's concept sheet
incoming_airlift/aircraft_image_assets/c5_galaxy_turnaround.png (side = bottom-left cell, nose left; top =
top-right cell, nose up; touching views separated with sheet_cell(split=4)). Side scale 75.3 m / 797 px, top
across-scale 67.9 m / 598 px with a 3-landmark Y rectification (nose, wing-root leading edge, tail cone).
Shape: long tube fuselage with the cockpit hump, high swept wing with anhedral, four podded engines, T-tail,
main-gear sponsons with four six-wheel bogies, twin nose gear.
Nodes: Body, NoseDoor (separate object, origin on the visor hinge at the top of the cut: rotate about its local
X axis to lift the nose; the cut face behind it is a dark cargo-hold opening with a floor), Exhaust0..3
(engine exits, left outer -> right outer), CargoExit (cargo floor at the nose opening, where vehicles leave).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

ID = "c5"
SHEET = os.path.join(K.INC_LIFT, "c5_galaxy_turnaround.png")

S = K.SideFrame(75.3 / 797.0, (8 + 805) / 2.0, 945.0)
T = K.TopFrame(67.9 / 598.0, 1190.0, [(12, S.y(8)), (200, S.y(318)), (600, S.y(805))])

FUS_TOP = [(8, 880), (12, 868), (18, 858), (25, 850), (40, 838), (60, 826), (80, 818), (100, 812), (130, 809),
           (200, 808), (300, 807), (400, 807), (500, 806), (600, 806), (650, 805), (700, 805), (740, 810), (770, 818),
           (790, 826), (805, 836)]
FUS_BOT = [(8, 880), (12, 893), (18, 900), (25, 905), (50, 915), (80, 921), (100, 924), (150, 926), (300, 927),
           (450, 927), (530, 922), (560, 914), (600, 900), (650, 884), (700, 866), (750, 850), (780, 842), (805, 837)]
FUS_HW = [(12, 2), (16, 9), (20, 13), (30, 18), (40, 22), (60, 28), (80, 32), (100, 34.5), (150, 36), (450, 36),
          (480, 33), (500, 28), (520, 22), (550, 15), (580, 9.5), (598, 3)]
CUT_PX = 70            # visor cut (side px): nose tip .. here lifts; the cockpit glazing stays on the fuselage
NACS = [(-180, 237, 292), (-105, 198, 252), (105, 198, 252), (180, 237, 292)]   # top: x px from centre, front py, rear py
ANH = math.radians(-5.5)


def _fuselage_fns():
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    return ztop, zbot, hw


def build(mat):
    objs = {}
    ztop, zbot, hw = _fuselage_fns()
    y_n, y_t, y_c = float(S.y(8)), float(S.y(805)), float(S.y(CUT_PX))
    # --- fuselage behind the visor cut (closed by a dark hold face, see Dark)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_c, y_c - 4.0, 6), np.linspace(y_c - 4.6, y_t + 0.3, 40), [y_t + 0.05]])
    K.fuselage(F, ys, ztop, zbot, hw, n=2.4, seg=40)
    # cockpit hump / upper deck fairing (the concept's raised crown behind the flight deck)
    yh0, yh1 = float(S.y(75)), float(S.y(260))
    rr = []
    for t in np.linspace(0, 1, 12):
        y = yh0 + (yh1 - yh0) * t
        f = math.sin(math.pi * min(1.0, 0.05 + 0.95 * t)) ** 0.5
        rr.append(K.superellipse_ring(y, 0.0, float(hw(y)) * 0.72, float(ztop(y)) - 0.35, 0.55 * max(f, 0.15), 2.2, 24))
    F.rings(rr)
    # main-gear sponsons (long pods low on both sides)
    zsp = float(S.z(915))
    for sg in (-1, 1):
        y0, y1 = float(S.y(270)), float(S.y(540))
        rr = []
        for t in np.linspace(0, 1, 12):
            y = y0 + (y1 - y0) * t
            f = math.sin(math.pi * min(1.0, 0.04 + 0.96 * t)) ** 0.3
            rr.append(K.superellipse_ring(y, sg * 3.05, 0.95 * max(f, 0.2), zsp, 1.25 * max(f, 0.3), 2.6, 18))
        F.rings(rr)
    # wing (high, swept, anhedral) with a centre box through the crown
    zw = float(S.z(818))
    F.box((0, float(T.y(265)), zw - 0.2), (4.2, float(T.y(200)) - float(T.y(335)), 1.1))
    W = [(1190, 200, 335, 0.15), (1225, 200, 335, 0.15), (1300, 244, 352, 0.13), (1400, 302, 376, 0.11),
         (1470, 343, 393, 0.095), (1491, 358, 401, 0.08)]
    right = []
    for px, le, te, t in W:
        x = float(T.x(px))
        z = zw + max(0.0, abs(x) - 3.0) * math.tan(ANH)
        right.append(((x, float(T.y(le)), z), (x, float(T.y(te)), z), t, (0, 0, 1)))
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # flap-track fairings under the trailing edge
    for px in (1265, 1330, 1395, 1450):
        for sg in (-1, 1):
            x = sg * float(T.x(px))
            z = zw + max(0.0, abs(x) - 3.0) * math.tan(ANH)
            yte = float(T.y(np.interp(px, [w[0] for w in W], [w[2] for w in W])))
            K.body_rev(F, (x, yte - 1.6, z - 0.35), (x, yte + 2.6, z - 0.2), [(0, 0.05), (0.3, 0.32), (0.8, 0.28), (1, 0.05)],
                       seg=8, squash=1.3)
    # engines on pylons
    zn = float(S.z(856))
    exh, dark = [], []
    for xo, p0, p1 in NACS:
        x = xo * T.sx
        zwx = zw + max(0.0, abs(x) - 3.0) * math.tan(ANH)
        znx = zn + (zwx - zw)
        y0, y1 = float(T.y(p0)), float(T.y(p1))
        K.body_rev(F, (x, y1, znx), (x, y0, znx), [(0, 0.85), (0.12, 1.2), (0.3, 1.55), (0.75, 1.62), (0.93, 1.55),
                                                    (1, 1.45)], seg=24)
        K.body_rev(F, (x, y1 - 1.4, znx - 0.1), (x, y1 + 0.2, znx), [(0, 0.15), (0.5, 0.55), (1, 0.8)], seg=12)   # core cone
        F.beam((x, y1 + 0.6, znx + 1.3), (x, y0 - 3.0, zwx - 0.25), 0.32, 1.0)
        exh.append((x, y1 - 1.4, znx - 0.1))
        dark.append(((x, y0 - 0.01, znx), 1.38))
    # T-tail: fin, bullet fairing, tailplane
    K.surface(F, K.fin_sections(S, [(685, 792, 805), (718, 806, 752), (752, 826, 700)], x=0, t_root=0.12, t_tip=0.1))
    zs = float(S.z(690))
    yb0, yb1 = float(S.y(735)), float(S.y(845))
    K.body_rev(F, (0, yb1, zs), (0, yb0, zs), [(0, 0.08), (0.15, 0.55), (0.7, 0.62), (1, 0.12)], seg=14)
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), t, (0, 0, 1))
          for px, le, te, t in ((1190, 500, 574, 0.1), (1205, 505, 574, 0.1), (1260, 526, 577, 0.09),
                                (1310, 545, 580, 0.08), (1325, 552, 582, 0.06))]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    objs["air"] = F.build(mat, smooth=45)

    # --- nose visor (separate object, hinge at the top of the cut)
    N = K.Part("NoseDoor")
    ysn = np.concatenate([np.linspace(y_n - 0.01, y_n - 2.0, 10), np.linspace(y_n - 2.4, y_c, 8)])
    K.fuselage(N, ysn, ztop, zbot, hw, n=2.4, seg=40)
    objs["nose"] = N.build(mat, smooth=45)

    # --- dark: engine faces, the hold opening at the cut, inner hold walls
    D = K.Part("Dark")
    for p, r in dark:
        K.disc(D, p, r)
    zc_top, zc_bot = float(ztop(y_c)), float(zbot(y_c))
    K.fuselage(D, [y_c + 0.02, y_c - 0.02], lambda y: zc_top - 0.25, lambda y: zc_bot + 0.25,
               lambda y: float(hw(y_c)) - 0.25, n=2.4, seg=40)
    objs["dark"] = D.build(mat, smooth=40)
    # cargo floor lip at the opening (light grey, flat)
    FL = K.Part("Floor")
    zfl = zc_bot + 1.05
    FL.box((0, y_c - 0.1, zfl), (float(hw(y_c)) * 1.5, 0.5, 0.12))
    objs["floor"] = FL.build(mat, smooth=40)

    # --- gear: four 6-wheel main bogies (3 axles x 2 wheels) + twin nose gear
    G = K.Part("Gear")
    r = 0.62
    for sg in (-1, 1):
        for gpx in (366, 386, 406, 433, 453, 473):
            K.gear_leg(G, (sg * 2.9, float(S.y(gpx)), r), r, 0.42, (sg * 2.9, float(S.y(gpx)), zsp - 0.4), twin=True)
    yng = float(S.y(100))
    K.gear_leg(G, (0, yng, 0.5), 0.5, 0.3, (0, yng, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    # --- team colour: fin cap and tailplane tips
    Tm = K.Part("Team")
    for sg in (-1, 1):
        Tm.box((sg * float(T.x(1322)), float(T.y(566)), zs), (0.16, 1.6, 0.34))
    K.surface(Tm, K.fin_sections(S, [(748, 824, 706), (752, 826, 698)], x=0, t_root=0.14, t_tip=0.12))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    exh.sort(key=lambda p: p[0])
    empties = {f"Exhaust{i}": p for i, p in enumerate(exh)}
    empties["CargoExit"] = (0.0, y_c - 0.5, zfl)
    hinge = (0.0, y_c, zc_top - 0.05)
    return objs, empties, hinge


def finish(o, mat, objs, empties, hinge, refs, side_rgba, top_rgba):
    """K.finish with the visor kept as its own object (pivot on the hinge) instead of joined into Body."""
    keys = [k for k in objs if k != "team"]
    tex_objs = [objs[k] for k in keys]
    if o["fit_png"]:
        K.fit_overlay(tex_objs + [objs["team"]], S, T, side_rgba, top_rgba, o["fit_png"])
    L.smart_uv(tex_objs, margin=0.003)
    flat = {"gear": (0.12, 0.12, 0.12), "dark": (0.05, 0.05, 0.055), "floor": (0.36, 0.37, 0.36)}
    modes = {i: ("flat", flat[k]) for i, k in enumerate(keys) if k in flat}
    shade = K.Shade(refs, T, S, modes=modes, grime=0.12)
    bounds = ((-35.0, -39.5, -0.1), (35.0, 39.5, 26.0))
    albedo = os.path.join(o["out"], f"{ID}_albedo.png")
    _, cover = K.texture_atlas(tex_objs, shade, 2048, 1024, 0.4, 0.07, bounds, albedo, depth_objs=tex_objs + [objs["team"]])
    K.attach_texture(mat, albedo, f"{ID}_albedo")
    nose = objs["nose"]
    body = K.join([objs[k] for k in keys if k != "nose"], "Body")
    body = K.join_team(body, objs["team"])
    body.name = "Body"; body.data.name = "Body"
    nose.data.transform(Matrix.Translation(-Vector(hinge)))
    nose.location = Vector(hinge)
    nose.name = "NoseDoor"; nose.data.name = "NoseDoor"
    ems = [K.empty(n, p) for n, p in empties.items()]
    export = [body, nose] + ems
    glb = os.path.join(o["out"], f"{ID}.glb")
    K.export_glb(export, glb)
    print(f"C5 atlas coverage {cover:.3f}")
    print(K.report(export, body))
    print("C5 GLB", glb)
    if o["prev"]:
        K.preview_sheet(ID, "Steel Accord B3 - C-5-class strategic airlifter - Cycles CPU preview", 75.3, 67.9, 24.6, o["sheet"])
        print("C5 sheet", o["sheet"])


def main():
    o = K.parse_args(ID)
    if o["sheet"].endswith("m3_c5_sheet.png"):
        o["sheet"] = os.path.join(K.SCREENS, "b3_c5_sheet.png")
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_cell="tr", split=4)
    mat = L.image_material("SA_C5", None, rough=0.62)
    objs, empties, hinge = build(mat)
    finish(o, mat, objs, empties, hinge, refs, side_rgba, top_rgba)


if __name__ == "__main__":
    main()
