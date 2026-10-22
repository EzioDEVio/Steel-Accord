"""Steel Accord - M3 3D aircraft: A-10-style twin-engine close-support jet (bpy 5.x).

Run:  python3 -I tools/art/air_a10_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/a10/a10.glb (+ a10_albedo.png inspectable copy, embedded in the GLB)
      docs/screens/m3_a10_sheet.png

Method = CH-47 pilot pipeline via airkit.py: geometry fitted to the concept side view (contact sheet,
bottom-left cell; the cropped individual side view cuts off the tail) and the cleaned nose-up top sprite,
texture = depth-tested projection of both views into one 2048 atlas + AO.
Nodes: Body, Gun (GAU muzzle), Exhaust0/1 (left/right nacelle exits), Hardpoint0..7 (store centres,
left wing outboard->inboard then right wing inboard->outboard).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "a10"
SHEET = os.path.join(K.INC_X, "contact_sheets", "A-10_Thunderbolt_II_Warthog_4-view.png")
TOP_PNG = os.path.join(K.SPRITES, ID, f"{ID}_top.png")

# ---- side view (sheet px, nose left): gun tip 23 .. tail 820 = 16.26 m; ground below the fins (4.47 m tall)
S = K.SideFrame(16.26 / 797.0, (23 + 820) / 2.0, 905.0)
# ---- top view (cleaned sprite, nose up): span 12..748 = 17.5 m; Y rectified through gun tip, intake, exhaust, tail
T = K.TopFrame(17.5 / 736.0, 380.0, [(76, S.y(23)), (445, S.y(470)), (568, S.y(645)), (650, S.y(805))])

FUS_TOP = [(40, 815), (50, 803), (70, 790), (100, 779), (130, 768), (155, 758), (180, 752), (300, 747), (400, 750),
           (470, 754), (560, 760), (640, 775), (700, 790), (760, 798), (805, 806), (822, 812)]
FUS_BOT = [(40, 822), (52, 834), (75, 841), (100, 843), (300, 844), (430, 843), (560, 838), (650, 832), (720, 825),
           (780, 818), (822, 812)]
CANOPY_TOP = [(155, 758), (170, 742), (190, 728), (215, 722), (245, 722), (268, 729), (285, 740), (300, 747)]
FUS_HW = [(98, 4), (104, 12), (112, 18), (125, 22), (145, 26), (165, 28), (200, 30), (300, 30), (400, 29), (440, 26),
          (480, 22), (560, 18), (600, 15), (630, 12), (650, 7), (660, 2)]
CANOPY_HW = [(188, 2), (198, 12), (215, 17), (250, 18), (285, 17), (305, 13), (320, 3)]

Z_WING = 1.52
X_POD = (492 - 380) * T.sx


def wing_z(x):
    ax = abs(x)
    return Z_WING + max(0.0, ax - X_POD) * math.tan(math.radians(7))


def build(mat):
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_nose, y_tail = S.y(40), S.y(822)
    objs = {}
    # ---------------------------------------------------------------- airframe
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_nose - 0.01, y_nose - 1.4, 10), np.linspace(y_nose - 1.6, y_tail + 1.0, 30),
                         np.linspace(y_tail + 0.8, y_tail + 0.01, 5)])
    tn = lambda y: float(np.clip((y_nose - y) / 1.4, 0, 1))
    K.fuselage(F, ys, ztop, zbot, lambda y: hw(y) * (0.35 + 0.65 * tn(y) ** 0.5), n=lambda y: 2.2 + 1.0 * tn(y), seg=32)
    # canopy bubble
    ct = K.polyline_fn([S(px, py) for px, py in CANOPY_TOP])
    chw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in CANOPY_HW])
    yc0, yc1 = S.y(156), S.y(300)
    cys = np.linspace(yc0 - 0.02, yc1 + 0.02, 14)
    K.fuselage(F, cys, ct, lambda y: ztop(y) - 0.25, lambda y: max(chw(y), 0.05), n=2.3, seg=20)
    # wing: left tip -> right tip
    W = [(380, 318, 440, 0.16), (492, 318, 440, 0.15), (600, 334, 441, 0.13), (700, 355, 442, 0.11),
         (728, 364, 441, 0.10), (742, 380, 436, 0.07)]
    right = []
    for px, le, te, t in W:
        x = float(T.x(px))
        right.append(((x, float(T.y(le)), wing_z(x)), (x, float(T.y(te)), wing_z(x)), t, (0, 0, 1)))
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # horizontal stabiliser across the tail cone
    zs = 1.78
    st = []
    for px, le, te, t in ((268, 588, 646, 0.07), (300, 585, 646, 0.09), (380, 584, 646, 0.1), (460, 585, 646, 0.09),
                          (492, 588, 646, 0.07)):
        x = float(T.x(px))
        st.append(((x, float(T.y(le)), zs), (x, float(T.y(te)), zs), t, (0, 0, 1)))
    K.surface(F, st)
    # twin fins on the stabiliser tips (side-view outline of the near fin)
    x_fin = (497 - 380) * T.sx
    fin_pts = [(742, 819, 840), (745, 820, 790), (751, 818, 740), (757, 812, 705), (761, 808, 698)]
    for sgn in (-1, 1):
        K.surface(F, K.fin_sections(S, fin_pts, x=sgn * x_fin, t_root=0.07, t_tip=0.06))
    # engine nacelles + pylons
    y_in, y_out = float(T.y(444)), float(T.y(574))
    z_eng = float(S.z(745))
    x_eng = (445 - 380) * T.sx
    for sgn in (-1, 1):
        K.body_rev(F, (sgn * x_eng, y_out, z_eng), (sgn * x_eng, y_in, z_eng),
                   [(0, 0.40), (0.05, 0.52), (0.14, 0.66), (0.3, 0.74), (0.85, 0.76), (0.96, 0.74), (1, 0.66)], seg=24)
        K.body_rev(F, (sgn * x_eng, y_in + 0.02, z_eng), (sgn * x_eng, y_in + 0.06, z_eng), [(0, 0.6), (1, 0.6)], seg=20)
        F.box((sgn * x_eng * 0.55, y_in - 1.9, z_eng - 0.55), (0.7, 2.3, 0.35))
    # main-gear pods ahead of the wing at the centre/outer panel joint
    for sgn in (-1, 1):
        K.body_rev(F, (sgn * X_POD, float(T.y(336)), Z_WING - 0.2), (sgn * X_POD, float(T.y(262)), Z_WING - 0.2),
                   [(0, 0.22), (0.15, 0.33), (0.7, 0.34), (0.92, 0.26), (1, 0.08)], seg=16)
    # GAU-8 barrel cluster
    zg = float(S.z(838))
    K.body_rev(F, (0, S.y(62), zg), (0, S.y(23), zg), [(0, 0.2), (0.3, 0.17), (1, 0.15)], seg=12)
    # antenna / blade on the spine (side px 330, py 745)
    F.box((0, S.y(330), float(S.z(745)) + 0.12), (0.04, 0.25, 0.3))
    objs["air"] = F.build(mat, smooth=48)

    # ---------------------------------------------------------------- stores
    Sx = K.Part("Stores")
    stores = [(122, 262, 336, 0.075, "missile"), (182, 258, 334, 0.19, "bomb"), (228, 224, 318, 0.24, "bomb"),
              (305, 270, 316, 0.11, "missile")]
    hard = []
    for side_sgn in (-1, 1):
        lst = stores if side_sgn < 0 else stores[::-1]
        for px, nose, tail, r, kind in lst:
            x = float(T.x(px)) if side_sgn < 0 else -float(T.x(px))
            yn, yt = float(T.y(nose)), float(T.y(tail))
            zw = wing_z(x) - 0.2
            zc = zw - 0.22 - r
            K.pylon(Sx, (x, (yn + yt) / 2 - 0.25, zw + 0.05), min(1.6, (yn - yt) * 0.6), 0.27 + 0.05)
            if kind == "bomb":
                K.bomb(Sx, (x, yn, zc), yn - yt, r)
            else:
                K.missile(Sx, (x, yn, zc), yn - yt, r)
            hard.append((x, (yn + yt) / 2, zc))
    objs["stores"] = Sx.build(mat, smooth=40)

    # ---------------------------------------------------------------- landing gear (concept is gear-up; added)
    G = K.Part("Gear")
    for sgn in (-1, 1):
        K.gear_leg(G, (sgn * X_POD, float(T.y(300)), 0.42), 0.42, 0.26, (sgn * X_POD, float(T.y(300)) + 0.1, Z_WING - 0.3))
    yg = float(T.y(170))
    K.gear_leg(G, (0.32, yg, 0.33), 0.33, 0.2, (0.3, yg + 0.1, float(zbot(yg)) + 0.1))
    objs["gear"] = G.build(mat, smooth=40)

    # ---------------------------------------------------------------- team-colour fin tips
    Tm = K.Part("Team")
    for sgn in (-1, 1):
        K.surface(Tm, K.fin_sections(S, [(760, 809, 700), (764, 802, 687)], x=sgn * x_fin, t_root=0.085, t_tip=0.07))
    objs["team"] = Tm.build(K.team_material(), smooth=40)

    empties = {"Gun": (0, S.y(23), zg),
               "Exhaust0": (-x_eng, y_out - 0.05, z_eng), "Exhaust1": (x_eng, y_out - 0.05, z_eng)}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba = K.sheet_cell(SHEET, "bl")
    top_rgba = K.load_rgba(TOP_PNG)
    refs = {"side": K.ref_from_rgba(side_rgba, erode=2, keep_largest=True),
            "top": K.ref_from_rgba(top_rgba, erode=2, keep_largest=True)}
    L.gain_to(refs["top"], refs["side"]["mean"], strength=0.6)
    mat = L.image_material("SA_A10", None, rough=0.62)
    objs, empties = build(mat)
    tex_objs = [objs["air"], objs["stores"], objs["gear"]]
    if o["fit_png"]:
        K.fit_overlay(tex_objs + [objs["team"]], S, T, side_rgba, top_rgba, o["fit_png"])
    L.smart_uv(tex_objs, margin=0.003)
    shade = K.Shade(refs, T, S, modes={2: ("flat", (0.16, 0.16, 0.16))}, grime=0.1)
    albedo = os.path.join(o["out"], f"{ID}_albedo.png")
    _, cover = K.texture_atlas(tex_objs, shade, 2048, 1024, 0.45, 0.03, ((-9.2, -8.6, -0.1), (9.2, 8.6, 4.8)), albedo,
                               depth_objs=tex_objs + [objs["team"]])
    K.attach_texture(mat, albedo, f"{ID}_albedo")
    body = K.join(tex_objs, "Body")
    body = K.join_team(body, objs["team"])
    body.name = "Body"; body.data.name = "Body"
    ems = [K.empty(n, p) for n, p in empties.items()]
    export = [body] + ems
    glb = os.path.join(o["out"], f"{ID}.glb")
    K.export_glb(export, glb)
    print(f"A10 atlas coverage {cover:.3f}")
    print(K.report(export, body))
    print("A10 GLB", glb)
    if o["prev"]:
        K.preview_sheet(ID, "Steel Accord M3 - A-10 close-support jet - Cycles CPU preview", 16.3, 17.5, 4.5, o["sheet"])
        print("A10 sheet", o["sheet"])


if __name__ == "__main__":
    main()
