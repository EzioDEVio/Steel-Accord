"""Steel Accord - M3 3D aircraft: AC-130-style side-firing gunship (bpy 5.x).

Run:  python3 -I tools/art/air_ac130_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/ac130/ac130.glb (+ ac130_albedo.png, ac130_prop.png), docs/screens/m3_ac130_sheet.png

Same airframe builder as air_c130_3d.py (imported), re-measured on the gunship concept
incoming_airlift/aircraft_image_assets/ac130_spooky_turnaround.png (side = bottom-left cell, top = top-right
cell, nose up; the sheet's touching views are separated with airkit.sheet_cell(split=4)). The concept has
its nacelles further outboard and a larger tailplane than the C-130 concept; both are followed.
Extra geometry: three left-side guns (light cannon, medium cannon, howitzer) with mounts, nose sensor ball,
two under-wing tanks. Nodes: Body, Prop0..3 (as C-130), Gun0..2 (muzzles of the left-side guns, front to rear).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402
import air_c130_3d as C  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "ac130"
SHEET = os.path.join(K.INC_LIFT, "ac130_spooky_turnaround.png")

S = K.SideFrame(29.8 / 780.0, (10 + 790) / 2.0, 972.0)
T = K.TopFrame(20.2 / 321.0, 1174.0, [(22, S.y(10)), (200, S.y(240)), (598, S.y(790))])

M = {
    "cx": 1174.0, "nose_px": 12, "tail_px": 788,
    "fus_top": [(12, 896), (20, 880), (40, 868), (60, 856), (80, 840), (100, 828), (130, 822), (560, 822), (700, 821),
                (788, 820)],
    "fus_bot": [(12, 905), (20, 918), (40, 930), (60, 936), (100, 944), (150, 947), (300, 947), (500, 945), (550, 933),
                (600, 907), (620, 895), (640, 884), (660, 872), (680, 860), (720, 836), (760, 826), (788, 821)],
    "fus_hw": [(22, 4), (25, 13.5), (40, 19.5), (60, 29.5), (100, 43.5), (150, 44), (300, 44), (400, 41.5),
               (450, 39.5), (500, 34), (540, 25), (560, 20), (580, 12), (595, 3)],
    "sponson": (300, 480, 935, 2.65),
    "zw_py": 826, "root_box": (244, 334, 290),
    "wing": [(1174, 244, 334, 0.16), (1120, 244, 334, 0.16), (1050, 245, 333, 0.155), (1000, 248, 325, 0.15),
             (900, 252, 308, 0.12), (840, 254, 297, 0.1), (830, 255, 296, 0.09)],
    "x_nac": [-210, -109, 109, 210], "nac": (320, 195, 845, 270),
    "stab_py": 820,
    "stab": [(1174, 490, 575, 0.1), (1120, 497, 564, 0.1), (1050, 512, 557, 0.09), (1004, 522, 548, 0.07)],
    "fin": [(625, 780, 805), (641, 769, 750), (660, 760, 700), (694, 737, 620)],
    "fin_tip": [(690, 739, 632), (695, 736, 618)],
    "gear_main": (320, 362), "gear_nose": 100,
}
GUNS = [(255, 905, 1.7, 0.07), (345, 905, 2.0, 0.09), (470, 912, 2.6, 0.13)]   # side px, side py, barrel m, radius


def build_extra(mat, fus):
    ztop, zbot, hw = fus
    X = K.Part("Guns")
    muzzles = []
    for px, py, ln, r in GUNS:
        y, z = S(px, py)
        xs = -float(hw(y)) * 0.92
        X.box((xs + 0.05, y, z), (0.5, 1.0 + r * 3, 0.7 + r * 2))                     # mount / door frame
        tip = (xs - ln, y + 0.05, z - ln * math.tan(math.radians(8)))
        X.rod((xs, y, z), tip, r, seg=10)
        X.rod((xs - 0.1, y, z), (xs - 0.55, y, z - 0.07), r * 1.8, seg=10)        # recoil housing
        muzzles.append(tip)
    # nose sensor ball, under-wing tanks
    yb, zb = S(45, 935)
    K.body_rev(X, (0, yb - 0.38, zb), (0, yb + 0.38, zb), [(0, 0.06), (0.3, 0.34), (0.7, 0.34), (1, 0.06)], seg=14)
    zw = float(S.z(M["zw_py"]))
    for sg in (-1, 1):
        x = sg * 184 * T.sx
        zwx = zw + max(0.0, abs(x) - 2.5) * math.tan(math.radians(2.5))
        y0, y1 = float(T.y(335)), float(T.y(250))
        K.pylon(X, (x, (y0 + y1) / 2, zwx - 0.3), 1.6, 0.4, 0.15)
        K.body_rev(X, (x, y0, zwx - 1.25), (x, y1, zwx - 1.25), [(0, 0.08), (0.12, 0.42), (0.35, 0.55), (0.7, 0.55),
                                                                  (0.9, 0.4), (1, 0.06)], seg=16)
    return X.build(mat, smooth=40), muzzles


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba, top_rgba, refs = K.load_views(SHEET, "bl", top_cell="tr", split=4)
    mat = L.image_material("SA_AC130", None, rough=0.65)
    pmat = L.image_material("SA_AC130_Prop", None, rough=0.6)
    objs, empties, hubs, fus = C.build(mat, S, T, M)
    guns, muzzles = build_extra(mat, fus)
    objs = {"air": objs["air"], "guns": guns, "gear": objs["gear"], "team": objs["team"]}
    for i, m in enumerate(muzzles):
        empties[f"Gun{i}"] = m
    props, prop_png = C.make_props(hubs, pmat, o["out"], ID)
    K.finish(ID, o, mat, objs, empties, refs, S, T, side_rgba, top_rgba, ((-21.0, -15.5, -0.1), (21.0, 15.5, 14.0)),
             (29.8, 40.4, 13.6), "Steel Accord M3 - AC-130 gunship - Cycles CPU preview",
             flat={"gear": (0.12, 0.12, 0.12)}, extra_export=props, blade=(pmat, prop_png, f"{ID}_prop"), cell=0.05)


if __name__ == "__main__":
    main()
