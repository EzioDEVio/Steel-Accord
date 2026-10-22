"""Steel Accord - M3 3D aircraft: C-130-style four-turboprop tactical airlifter (bpy 5.x).

Run:  python3 -I tools/art/air_c130_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/c130/c130.glb (+ c130_albedo.png, c130_prop.png), docs/screens/m3_c130_sheet.png

References: incoming_airlift/aircraft_image_assets/c130_airlift_turnaround.png (side view = bottom-left cell,
nose left) and the cleaned nose-up top sprite godot/assets/aircraft/c130/c130_top.png. The top view places
the wing ~10% further forward than the side view; Y is rectified through nose, propeller plane and tail.
Nodes: Body (fuselage, wing, nacelles, sponsons, tail, gear), Prop0..3 (left outer, left inner, right inner,
right outer; origin = prop hub; 4 real blades; spin about local Z in Godot = the shaft, pointing forward).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "c130"
SHEET = os.path.join(K.INC_LIFT, "c130_airlift_turnaround.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

S = K.SideFrame(29.8 / 824.0, (10 + 834) / 2.0, 934.0)
T = K.TopFrame(20.2 / 345.0, 346.5, [(90, S.y(10)), (215, S.y(300)), (620, S.y(834))])

M = {
    "cx": 346.5, "nose_px": 12, "tail_px": 828,
    "fus_top": [(12, 862), (30, 846), (50, 836), (75, 814), (100, 801), (150, 792), (200, 790), (600, 789), (700, 789),
                (790, 789), (828, 789)],
    "fus_bot": [(12, 878), (30, 893), (50, 902), (75, 910), (150, 916), (300, 913), (500, 912), (550, 903), (600, 876),
                (650, 849), (700, 820), (750, 803), (800, 796), (828, 792)],
    "fus_hw": [(90, 6), (100, 15), (120, 25), (150, 34), (200, 37.5), (300, 38.5), (400, 38), (450, 36), (500, 32),
               (540, 27), (580, 22), (600, 18), (615, 12), (620, 6)],
    "sponson": (370, 545, 895, 1.95),           # side px start/end, side py centre, |x| m
    "zw_py": 790, "root_box": (265, 370, 315),  # wing-root fairing: top py LE / TE / centre
    "wing": [(346.5, 264, 366, 0.16), (300, 265, 364, 0.16), (250, 266, 363, 0.155), (180, 268, 352, 0.14),
             (100, 270, 333, 0.12), (50, 272, 323, 0.11), (14, 275, 316, 0.09)],
    "x_nac": [-166.5, -82.5, 82.5, 166.5], "nac": (350, 213, 810, 300),   # top py rear, top py prop plane, side py centre, fairing py
    "stab_py": 792,
    "stab": [(346.5, 512, 602, 0.1), (300, 521, 596, 0.1), (250, 534, 591, 0.09), (180, 552, 584, 0.08), (175, 555, 583, 0.06)],
    "fin": [(668, 812, 795), (690, 806, 760), (712, 796, 690), (735, 772, 584)],
    "fin_tip": [(731, 775, 598), (735, 772, 579)],
    "gear_main": (378, 415), "gear_nose": 100,
}


def build(mat, S, T, M):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in M["fus_top"]])
    zbot = K.polyline_fn([S(px, py) for px, py in M["fus_bot"]])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in M["fus_hw"]])
    y_n, y_t = S.y(M["nose_px"]), S.y(M["tail_px"])
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_n - 0.01, y_n - 3.5, 12), np.linspace(y_n - 3.8, y_t + 0.2, 32), [y_t + 0.05]])
    K.fuselage(F, ys, ztop, zbot, hw, n=lambda y: 2.3, seg=36)
    # sponsons (main-gear fairings) and wing-root fairing
    sp0, sp1, sppy, spx = M["sponson"]
    zsp = float(S.z(sppy))
    for sg in (-1, 1):
        y0, y1 = S.y(sp0), S.y(sp1)
        rr = []
        for t in np.linspace(0, 1, 10):
            y = y0 + (y1 - y0) * t
            f = math.sin(math.pi * min(1.0, 0.08 + 0.92 * t)) ** 0.35
            rr.append(K.superellipse_ring(y, sg * spx, 0.55 * max(f, 0.2), zsp, 0.72 * max(f, 0.3), 2.8, 16))
        F.rings(rr)
    zw = float(S.z(M["zw_py"]))
    rb0, rb1, rbc = M["root_box"]
    F.box((0, float(T.y(rbc)), zw - 0.35), (2.2, float(T.y(rb0)) - float(T.y(rb1)), 0.7))
    # wing (high, straight, slight dihedral outboard of the root)
    secs = []
    for px, le, te, t in M["wing"]:
        x = float(T.x(px))
        z = zw + max(0.0, abs(x) - 2.5) * math.tan(math.radians(2.5))
        secs.append(((x, float(T.y(le)), z), (x, float(T.y(te)), z), t, (0, 0, 1)))
    K.surface(F, K.mirror_sections(secs[1:]) + secs)
    # nacelles
    n_rear, n_prop, n_zpy, n_fair = M["nac"]
    zn = float(S.z(n_zpy))
    yp = float(T.y(n_prop))
    hubs = []
    for xp in M["x_nac"]:
        x = xp * T.sx
        zwx = zw + max(0.0, abs(x) - 2.5) * math.tan(math.radians(2.5))
        znx = zn + (zwx - zw)
        K.body_rev(F, (x, float(T.y(n_rear)), znx + 0.15), (x, yp - 0.35, znx),
                   [(0, 0.15), (0.12, 0.45), (0.3, 0.68), (0.75, 0.7), (0.93, 0.62), (1, 0.42)], seg=18)
        F.box((x, float(T.y(n_fair)), znx + 0.55), (0.7, 3.2, 0.7))                 # nacelle-to-wing fairing
        K.body_rev(F, (x, yp - 0.4, znx), (x, yp + 0.55, znx), [(0, 0.42), (0.4, 0.38), (0.8, 0.22), (1, 0.03)], seg=14)
        hubs.append((x, yp, znx))
    # empennage
    zs = float(S.z(M["stab_py"]))
    st = [((float(T.x(px)), float(T.y(le)), zs), (float(T.x(px)), float(T.y(te)), zs), t, (0, 0, 1))
          for px, le, te, t in M["stab"]]
    K.surface(F, K.mirror_sections(st[1:]) + st)
    K.surface(F, K.fin_sections(S, M["fin"], x=0, t_root=0.13, t_tip=0.1))
    objs["air"] = F.build(mat, smooth=45)

    G = K.Part("Gear")
    for sg in (-1, 1):
        for gp in M["gear_main"]:
            K.gear_leg(G, (sg * spx, S.y(gp), 0.6), 0.6, 0.4, (sg * spx, S.y(gp), zsp - 0.4))
    yng = S.y(M["gear_nose"])
    K.gear_leg(G, (0, yng, 0.45), 0.45, 0.24, (0, yng, float(zbot(yng)) + 0.1), twin=True)
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, M["fin_tip"], x=0, t_root=0.14, t_tip=0.12))
    objs["team"] = Tm.build(K.team_material(), smooth=40)
    return objs, {}, hubs, (ztop, zbot, hw)


def make_props(hubs, pmat, out_dir, aid):
    props = []
    for i, (x, y, z) in enumerate(hubs):
        props.append(K.rotor(f"Prop{i}", (x, y, z), 4, 2.05, 0.36, pmat, root_r=0.35, axis="y", hub_r=0.2,
                             coning=0, twist=(30, 10), thick=0.06, paddle=True, phase=math.radians(45 + 10 * i),
                             flip_pitch=x < 0))
    prop_png = os.path.join(out_dir, f"{aid}_prop.png")
    K.flat_texture((0.075, 0.08, 0.085), prop_png, tip=(0.62, 0.58, 0.2))
    return props, prop_png


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_png=TOP_PNG)
    mat = L.image_material("SA_C130", None, rough=0.65)
    pmat = L.image_material("SA_C130_Prop", None, rough=0.6)
    objs, empties, hubs, _ = build(mat, S, T, M)
    props, prop_png = make_props(hubs, pmat, o["out"], ID)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-20.6, -15.5, -0.1), (20.6, 15.5, 12.8)),
             (29.8, 40.4, 12.6), "Steel Accord M3 - C-130 tactical airlifter - Cycles CPU preview",
             flat={"gear": (0.12, 0.12, 0.12)}, extra_export=props, blade=(pmat, prop_png, f"{ID}_prop"), cell=0.05)


if __name__ == "__main__":
    main()
