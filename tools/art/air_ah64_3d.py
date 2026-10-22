"""Steel Accord - M3 3D aircraft: AH-64-style attack helicopter (bpy 5.x).

Run:  python3 -I tools/art/air_ah64_3d.py [out_dir] [--no-previews] [--fit fit.png]
Out:  godot/assets/units3d/ah64/ah64.glb (+ ah64_albedo.png, ah64_blade.png), docs/screens/m3_ah64_sheet.png

Geometry fitted to the concept side view (expanded contact sheet, bottom-left cell) and the blade-free top
view godot/assets/us/rotors/ah64_body.png (hub px from content/manifest/us_packs.json rotors.ah64);
texture = depth-tested projection of both views (airkit.Shade). Blade strip sampled from ah64_blades.png.
Nodes: Body (static: fuselage, stub wings + stores, mast-top radome, gear), RotorMain (origin = main hub,
spin about local Y in Godot), RotorTail (origin = tail-rotor hub on the left of the fin; its local X is the
shaft), Gun (chin cannon muzzle), Hardpoint0..3 (left outboard, left inboard, right inboard, right outboard).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import numpy as np  # noqa: E402

ID = "ah64"
SHEET = os.path.join(K.INC_X, "contact_sheets", "AH-64_Apache_4-view.png")
TOP_PNG = os.path.join(K.ROTOR_PNG, "ah64_body.png")
BLADES_PNG = os.path.join(K.ROTOR_PNG, "ah64_blades.png")
HUB_PX = (378.8, 333.5)

R_MAIN = 7.3
S = K.SideFrame(R_MAIN / 355.0, (58 + 848) / 2.0, 944.0)          # blade tip px 15 .. hub px 370 = rotor radius
T = K.TopFrame(R_MAIN / 368.0, HUB_PX[0], [(22, S.y(58)), (HUB_PX[1], S.y(370)), (672, S.y(815)), (745, S.y(850))])

FUS_TOP = [(95, 832), (115, 815), (155, 790), (200, 772), (240, 762), (280, 756), (320, 752), (360, 750), (420, 752),
           (480, 760), (540, 790), (600, 812), (660, 824), (740, 833), (800, 838), (850, 842)]
FUS_BOT = [(95, 872), (130, 882), (200, 886), (300, 888), (440, 890), (530, 893), (600, 885), (680, 876), (760, 868),
           (850, 852)]
FUS_HW = [(30, 14), (40, 30), (60, 44), (100, 54), (200, 57), (250, 60), (300, 62), (400, 58), (440, 46), (480, 30),
          (520, 22), (600, 18), (660, 14), (720, 9), (748, 4)]


def build(mat):
    objs = {}
    ztop = K.polyline_fn([S(px, py) for px, py in FUS_TOP])
    zbot = K.polyline_fn([S(px, py) for px, py in FUS_BOT])
    hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in FUS_HW])
    y_nose, y_tail = S.y(95), S.y(850)
    F = K.Part("Airframe")
    ys = np.concatenate([np.linspace(y_nose - 0.01, y_nose - 1.2, 9), np.linspace(y_nose - 1.4, y_tail + 0.6, 30),
                         np.linspace(y_tail + 0.5, y_tail + 0.01, 4)])
    tn = lambda y: float(np.clip((y_nose - y) / 1.2, 0, 1))
    K.fuselage(F, ys, ztop, zbot, lambda y: hw(y) * (0.55 + 0.45 * tn(y) ** 0.5), n=lambda y: 2.4 + 1.4 * tn(y), seg=32)
    # nose sensor turret (ball + upper box)
    ys_ = S.y(80); zs_ = float(S.z(845))
    K.body_rev(F, (0, ys_ - 0.45, zs_), (0, ys_ + 0.45, zs_), [(0, 0.05), (0.2, 0.33), (0.5, 0.42), (0.8, 0.33), (1, 0.08)],
               seg=18)
    F.box((0, S.y(82), float(S.z(817))), (0.5, 0.55, 0.22))
    # engine nacelles either side of the hump
    x_e = 60 * T.sx
    ze = float(S.z(785))
    for sg in (-1, 1):
        K.body_rev(F, (sg * x_e, S.y(540), ze), (sg * x_e, S.y(385), ze),
                   [(0, 0.24), (0.06, 0.34), (0.2, 0.42), (0.85, 0.42), (1, 0.36)], seg=16)
    # stub wings
    zw = float(S.z(826))
    secs = []
    for px, le, te, t in ((HUB_PX[0], 288, 368, 0.14), (300, 292, 362, 0.13), (205, 300, 352, 0.11)):
        x = -float(T.x(px)) if px != HUB_PX[0] else 0.0
        secs.append(((x, float(T.y(le)), zw), (x, float(T.y(te)), zw), t, (0, 0, 1)))
    right = secs
    K.surface(F, K.mirror_sections(right[1:]) + right)
    # horizontal stabiliser + fin
    zst = float(S.z(856))
    st = []
    for px, le, te in ((282, 652, 696), (HUB_PX[0], 650, 698), (466, 652, 696)):
        x = float(T.x(px))
        st.append(((x, float(T.y(le)), zst), (x, float(T.y(te)), zst), 0.1, (0, 0, 1)))
    K.surface(F, st)
    K.surface(F, K.fin_sections(S, [(744, 848, 842), (760, 840, 790), (780, 832, 740), (798, 826, 712)], x=0.0,
                                t_root=0.14, t_tip=0.1))
    # mast standpipe + mast-top radome (static)
    yh, zh = S(370, 715)
    F.rod((0, yh, float(ztop(yh)) - 0.1), (0, yh, zh - 0.15), 0.16, seg=12)
    F.rod((0, yh, zh + 0.2), (0, yh, zh + 0.75), 0.12, seg=10)
    K.body_rev(F, (0, yh, zh + 0.7), (0, yh, zh + 1.35), [(0, 0.55), (0.15, 0.74), (0.75, 0.76), (1, 0.45)], seg=24)
    # chin gun turret + barrel
    yg, zg = S(165, 884)
    K.body_rev(F, (0, yg - 0.22, zg), (0, yg + 0.22, zg), [(0, 0.08), (0.5, 0.22), (1, 0.08)], seg=12)
    F.rod((0, yg, zg - 0.05), (0, S.y(108), zg - 0.07), 0.05, seg=8)
    # sponson steps / exhaust boxes (small silhouette detail)
    for sg in (-1, 1):
        F.box((sg * x_e, S.y(548), ze + 0.05), (0.3, 0.35, 0.3))
    objs["air"] = F.build(mat, smooth=48)

    # stores: inboard rocket pod, outboard 2x2 missile rack
    Sx = K.Part("Stores")
    hard = []
    zp = zw - 0.18
    for sg in (-1, 1):
        lst = ((212, "rack"), (252, "pod")) if sg < 0 else ((252, "pod"), (212, "rack"))
        for px, kind in lst:
            x = sg * abs(float(T.x(px)))
            yc = float(T.y(300))
            K.pylon(Sx, (x, yc, zw), 0.8, 0.3, 0.12)
            if kind == "pod":
                K.body_rev(Sx, (x, yc - 0.85, zp - 0.4), (x, yc + 0.85, zp - 0.4),
                           [(0, 0.26), (0.05, 0.3), (0.95, 0.3), (1, 0.26)], seg=14)
                hard.append((x, yc, zp - 0.4))
            else:
                Sx.box((x, yc, zp - 0.12), (0.5, 1.2, 0.08))
                for dx in (-0.12, 0.12):
                    for dz in (-0.2, -0.45):
                        K.missile(Sx, (x + dx, yc + 0.8, zp + dz), 1.6, 0.09, fins=False, seg=8)
                hard.append((x, yc, zp - 0.33))
    objs["stores"] = Sx.build(mat, smooth=40)

    # landing gear: main legs under the cockpit/sponsons, tail wheel under the fin
    G = K.Part("Gear")
    rw = 19 * S.s
    ym = S.y(275)
    for sg in (-1, 1):
        K.gear_leg(G, (sg * 1.05, ym, rw), rw, 0.22, (sg * 0.55, ym + 0.35, float(zbot(ym)) + 0.15))
        G.rod((sg * 1.05, ym, rw), (sg * 0.5, ym - 0.6, float(zbot(ym)) + 0.1), 0.05, seg=6)
    yt = S.y(810)
    K.gear_leg(G, (0, yt, 0.2), 0.2, 0.14, (0, yt - 0.25, float(zbot(yt)) + 0.05))
    objs["gear"] = G.build(mat, smooth=40)

    Tm = K.Part("Team")                                    # fin cap + stabiliser tips
    K.surface(Tm, K.fin_sections(S, [(796, 827, 716), (799, 825, 706)], x=0.0, t_root=0.15, t_tip=0.12))
    for sg in (-1, 1):
        x = sg * float(T.x(466)) if sg > 0 else float(T.x(282))
        Tm.box((x, float(T.y(674)), zst), (0.08, 0.9, 0.14))
    objs["team"] = Tm.build(K.team_material(), smooth=40)

    empties = {"Gun": (0, S.y(108), zg - 0.07)}
    for i, h in enumerate(hard):
        empties[f"Hardpoint{i}"] = h
    return objs, empties, (yh, zh)


def main():
    o = K.parse_args(ID)
    L.reset_scene()
    side_rgba = K.sheet_cell(SHEET, "bl")
    top_rgba = K.load_rgba(TOP_PNG)
    refs = {"side": K.ref_from_rgba(side_rgba, erode=2, keep_largest=True),
            "top": K.ref_from_rgba(top_rgba, erode=2, keep_largest=True)}
    L.gain_to(refs["top"], refs["side"]["mean"], strength=0.6)
    mat = L.image_material("SA_AH64", None, rough=0.7)
    bmat = L.image_material("SA_AH64_Blade", None, rough=0.8)
    objs, empties, (yh, zh) = build(mat)
    tex_objs = [objs["air"], objs["stores"], objs["gear"]]
    # rotors
    rm = K.rotor("RotorMain", (0, yh, zh), 4, R_MAIN, 0.53, bmat, root_r=0.55, phase=math.radians(45), hub_r=0.32,
                 coning=1.5, mast=0.4)
    yt, zt = S(812, 747)
    rt = K.rotor("RotorTail", (-0.42, yt, zt), 4, 1.42, 0.25, bmat, root_r=0.18, axis="x", hub_r=0.12, coning=0,
                 twist=(6, 0), thick=0.04, phase=math.radians(20), sign_x=-1)
    if o["fit_png"]:
        K.fit_overlay(tex_objs + [objs["team"], rm, rt], S, T, side_rgba, top_rgba, o["fit_png"])
    L.smart_uv(tex_objs, margin=0.003)
    shade = K.Shade(refs, T, S, modes={2: ("flat", (0.11, 0.11, 0.1))}, grime=0.12)
    albedo = os.path.join(o["out"], f"{ID}_albedo.png")
    _, cover = K.texture_atlas(tex_objs, shade, 2048, 1024, 0.45, 0.03, ((-4.5, -9.0, -0.1), (4.5, 9.0, 6.5)), albedo,
                               depth_objs=tex_objs + [objs["team"]])
    K.attach_texture(mat, albedo, f"{ID}_albedo")
    blade_png = os.path.join(o["out"], f"{ID}_blade.png")
    bref = K.ref_from_rgba(K.load_rgba(BLADES_PNG), erode=1)
    a = math.radians(45)
    K.blade_texture(bref, (HUB_PX[0] + 70 * math.cos(a), HUB_PX[1] + 70 * math.sin(a)),
                    (HUB_PX[0] + 362 * math.cos(a), HUB_PX[1] + 362 * math.sin(a)), 24, blade_png)
    K.attach_texture(bmat, blade_png, f"{ID}_blade")
    body = K.join(tex_objs, "Body")
    body = K.join_team(body, objs["team"])
    body.name = "Body"; body.data.name = "Body"
    ems = [K.empty(n, p) for n, p in empties.items()]
    export = [body, rm, rt] + ems
    glb = os.path.join(o["out"], f"{ID}.glb")
    K.export_glb(export, glb)
    print(f"AH64 atlas coverage {cover:.3f}")
    print(K.report(export, body))
    print("AH64 GLB", glb)
    if o["prev"]:
        K.preview_sheet(ID, "Steel Accord M3 - AH-64 attack helicopter - Cycles CPU preview", 17.7, 14.6, 5.5, o["sheet"])
        print("AH64 sheet", o["sheet"])


if __name__ == "__main__":
    main()
