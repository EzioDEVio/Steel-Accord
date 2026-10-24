"""Steel Accord - B3 HD strategic bomber: B-1-style swing-wing bomber (bpy 5.x).

Run:  python3 -I tools/art/air_b1_hd.py [--no-sheet]
Out:  godot/assets/units3d/b1_hd/b1_hd.glb (+ b1_hd_albedo.jpg 4096, b1_hd_normal.png 2048, b1_hd_orm.png 2048)
      docs/screens/b3_b1_hd_sheet.png

Outline re-lofted at higher density from the M3 measured frames (air_b1_3d.py, imported read-only). New and
procedural: the outer wing panels are separate pivoting nodes WingL / WingR (modelled at the intermediate sweep of
the concept, ~27 deg leading edge; the game sweeps them back a further 38 deg for the strike run), fixed gloves,
nose vanes, cockpit glazing, rectangular intakes with splitters, four nozzles with petals, dorsal antennas, three
weapons bays with frames and paired doors, procedural paint. Flight configuration: gear retracted.
Nodes: Body, WingL, WingR (pivot origin; sweep = rotate about Godot Y: L positive, R negative),
Door0L/R, Door1L/R, Door2L/R (forward, mid, aft bay; hinge origins; open about Godot Z: L negative, R positive),
empties Exhaust0..3, Bay0a/b, Bay1a/b, Bay2a/b.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402
import airkit_hd as H  # noqa: E402
import air_b1_3d as B  # noqa: E402  (measured frames and outlines only)

L = K.L
import numpy as np  # noqa: E402

PI = math.pi
ID = "b1_hd"
S, T = B.S, B.T
OUT = os.path.join(K.OUT3D, ID)
SHEET = os.path.join(K.SCREENS, "b3_b1_hd_sheet.png")
F_ = H.FusFrame(S, T, B.FUS_TOP, B.FUS_BOT, B.FUS_HW, 2.4)
Y_N, Y_T = S.y(19), S.y(840)
ZW = float(S.z(828))
ZN = float(S.z(866))
ZS = float(S.z(780))
W = [(326, 190, 470, 0.06), (345, 205, 470, 0.06), (360, 235, 470, 0.07), (376, 250, 466, 0.08),
     (392, 280, 405, 0.08), (410, 300, 399, 0.075), (470, 330, 412, 0.07), (550, 368, 429, 0.06),
     (600, 392, 441, 0.05), (640, 417, 450, 0.04)]
GLOVE = W[:6]
OUTER = W[5:]
PIV_X = float(T.x(410))
PIV_Y = float(T.y(335))
ST = ((326, 505, 590, 0.07), (350, 520, 590, 0.07), (380, 535, 593, 0.065), (400, 550, 600, 0.06),
      (430, 573, 611, 0.05), (448, 590, 617, 0.04))
FIN = [(672, 792, 790), (725, 797, 735), (770, 806, 690)]
BAYS = [(S.y(300), 4.4), (S.y(380), 4.4), (S.y(560), 4.4)]      # (centre y, length)
BAY_HALF = 1.05
NAC_X = 58 * T.sx


def secs(rows, z):
    return [((float(T.x(px)), float(T.y(le)), z), (float(T.x(px)), float(T.y(te)), z), t, (0, 0, 1)) for px, le, te, t in rows]


def interp(rows):
    xs = np.array([float(T.x(r[0])) for r in rows])
    le = np.array([float(T.y(r[1])) for r in rows]); te = np.array([float(T.y(r[2])) for r in rows])
    return (lambda ax: np.interp(ax, xs, le)), (lambda ax: np.interp(ax, xs, te))


WLE, WTE = interp(W)
SLE, STE = interp(ST)
_fin = K.fin_sections(S, FIN, x=0, t_root=0.1, t_tip=0.07)
FIN_Z = np.array([s[0][2] for s in _fin]); FIN_LE = np.array([s[0][1] for s in _fin]); FIN_TE = np.array([s[1][1] for s in _fin])
EXH = []


def build(mat):
    objs = {}
    Fp = K.Part("Fus")
    ys = np.concatenate([np.linspace(Y_N - 0.01, Y_N - 6.0, 30), np.linspace(Y_N - 6.3, Y_T, 64)])
    K.fuselage(Fp, ys, F_.ztop, F_.zbot, F_.hw, n=2.4, seg=64)
    fus = Fp.build(mat, smooth=50)
    holes = []
    for yc, ln in BAYS:
        holes.append(H.cut_bay(fus, -BAY_HALF, BAY_HALF, yc - ln / 2, yc + ln / 2, F_.sec(yc)[1] - 0.2))
    objs["fus"] = fus
    # fixed gloves (blended into the fuselage) and the pivoting outer wings
    Gp = K.Part("Glove")
    g = secs(GLOVE, ZW)
    K.surface(Gp, K.mirror_sections(g[1:]) + g, npts=14)
    objs["glove"] = Gp.build(mat, smooth=40)
    wings = {}
    for side, sg in (("L", -1), ("R", 1)):
        Wp = K.Part(f"Wing{side}")
        o = secs(OUTER, ZW)
        # root section tucked 0.6 m into the glove so the swept wing never shows a gap
        le0, te0, t0, n0 = o[0]
        o = [((le0[0] - 0.6, le0[1], le0[2]), (te0[0] - 0.6, te0[1], te0[2]), t0, n0)] + o
        if sg < 0:
            o = K.mirror_sections(o)
        K.surface(Wp, o, npts=14)
        wo = Wp.build(mat, smooth=40)
        H.set_origin(wo, (sg * PIV_X, PIV_Y, ZW))
        wings[f"Wing{side}"] = wo
    Sp = K.Part("Stab")
    st = secs(ST, ZS)
    K.surface(Sp, K.mirror_sections(st[1:]) + st, npts=12)
    objs["stab"] = Sp.build(mat, smooth=40)
    Fn = K.Part("Fin")
    K.surface(Fn, _fin, npts=12)
    Fn.box((0, S.y(720), float(S.z(800))), (0.7, 3.6, 0.5))           # stabiliser root fairing on the fin
    objs["fin"] = Fn.build(mat, smooth=40)
    # nacelles with rectangular intakes and four nozzles
    Np = K.Part("Nac")
    D = K.Part("Dark")
    for sg in (-1, 1):
        xc = sg * NAC_X
        y0, y1 = float(T.y(322)), float(T.y(468))
        rr = []
        for t in np.linspace(0, 1, 22):
            y = y0 + (y1 - y0) * t
            f = min(1.0, 0.55 + 3.0 * t) * (1 - 0.12 * max(0, (t - 0.85) / 0.15))
            rr.append(K.superellipse_ring(y, xc, 1.55 * f, ZN + 0.15, 0.95 * f, 3.2, 32))
        Np.rings(rr)
        # intake boxes at the nacelle front (splitter plate between them)
        for dx in (-0.78, 0.78):
            D.box((xc + dx, y0 + 0.03, ZN + 0.1), (1.1, 0.06, 0.95))
        Np.box((xc, y0 + 0.4, ZN + 0.1), (0.08, 1.4, 1.1))
        for dx in (-0.85, 0.85):
            K.body_rev(Np, (xc + dx, y1 - 1.2, ZN), (xc + dx, y1 + 0.2, ZN), [(0, 0.6), (0.5, 0.63), (1, 0.66)], seg=24)
            # nozzle petals: a slightly flared ring with a dark throat
            K.body_rev(Np, (xc + dx, y1 - 1.2, ZN), (xc + dx, y1 - 0.9, ZN), [(0, 0.6), (1, 0.57)], seg=24)
            K.disc(D, (xc + dx, y1 - 0.95, ZN), 0.5, seg=20)
            EXH.append((xc + dx, y1 - 1.25, ZN))
    objs["nac"] = Np.build(mat, smooth=40)
    objs["dark"] = D.build(mat, smooth=30)
    # nose vanes, dorsal / ventral blades, tail cone
    M = K.Part("Misc")
    yv = S.y(85)
    hw, zc, h = F_.sec(yv)
    for sg in (-1, 1):
        a = math.radians(30)
        p0 = (sg * hw * 0.9, yv, zc - h * 0.2)
        M.beam(p0, (p0[0] + sg * math.cos(a) * 1.2, yv - 0.35, p0[2] - math.sin(a) * 1.2), 0.7, 0.05, up=(0, 1, 0))
    for y, up in ((S.y(230), 1), (S.y(420), 1), (S.y(620), 1), (S.y(200), -1)):
        hw, zc, h = F_.sec(y)
        z = zc + up * h
        M.beam((0, y + 0.25, z), (0, y - 0.3, z + up * 0.45), 0.04, 0.3, up=(0, 1, 0))
    hw, zc, h = F_.sec(Y_T + 0.6)
    K.body_rev(M, (0, Y_T + 0.6, zc + 0.15), (0, Y_T - 1.0, zc + 0.25), [(0, 0.45), (0.6, 0.32), (1, 0.05)], seg=20)
    objs["misc"] = M.build(mat, smooth=40)
    # bays and doors
    doors = {}
    Bp = K.Part("Bay")
    for i, hole in enumerate(holes):
        bx0, bx1, by0, by1 = hole
        yc = (by0 + by1) / 2
        H.bay_box(Bp, bx0, bx1, by0, by1, lambda x, y: F_.bottom_z(x, y), F_.sec(yc)[1] + 0.3, ribs=4)
        doors.update(H.door_pair(mat, i, hole, F_.bottom_z))
    objs["bay"] = H.build_inward(Bp, mat)
    # glazing: four windscreen panes and two side windows
    Gl = K.Part("Glass")
    for a0, a1 in ((0.55, 0.98), (1.04, 1.5), (1.64, 2.1), (2.16, 2.59)):
        H.glass_patch(Gl, F_.ring_pt, (S.y(158), S.y(128)), a0, a1)
    for sg in (-1, 1):
        a0, a1 = (0.3, 0.5) if sg > 0 else (PI - 0.5, PI - 0.3)
        H.glass_patch(Gl, F_.ring_pt, (S.y(178), S.y(164)), a0, a1)
    glass = Gl.build(H.glass_material(), smooth=20)
    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, [(765, 805, 696), (771, 806, 687)], x=0, t_root=0.1, t_tip=0.09))
    team = Tm.build(K.team_material(), smooth=40)
    empties = {}
    for i, p in enumerate(sorted(EXH, key=lambda q: q[0])):
        empties[f"Exhaust{i}"] = p
    for i, hole in enumerate(holes):
        bx0, bx1, by0, by1 = hole
        yc = (by0 + by1) / 2
        z = F_.sec(yc)[1] - 0.35
        empties[f"Bay{i}a"] = (0.0, yc + 0.05, z)
        empties[f"Bay{i}b"] = (0.0, yc - 0.05, z)
    return objs, wings, doors, glass, team, empties, holes


BASE = np.array([0.225, 0.238, 0.25])


def paint(P, N, O, keys, holes):
    n = len(P)
    k = {name: i for i, name in enumerate(keys)}
    col = np.tile(BASE, (n, 1))
    rough = np.full(n, 0.52); metal = np.zeros(n); hgt = np.zeros(n)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    tone = 0.95 + 0.1 * H.hash01(np.floor(x / 2.6).astype(np.int64), np.floor(y / 1.5).astype(np.int64), np.floor(z / 1.3).astype(np.int64))
    col *= tone[:, None]
    streak = H.aniso_noise(P, (0.2, 4.5, 0.2), seed=11)
    col *= (0.97 + 0.06 * streak)[:, None]
    rough += 0.08 * (streak - 0.5)
    m = (O == k["fus"]) | (O == k["misc"])
    if m.any():
        Pm = P[m]
        a, r = F_.angle(Pm)
        st = np.concatenate([np.arange(Y_T + 0.8, Y_N - 3.0, 1.45), [S.y(70), S.y(120)]])
        d_fr = H.stations_dist(Pm[:, 1], st)
        d_lg = H.stations_dist(a, [-2.6, -1.9, -1.2, -0.5, 0.5, 1.2, 1.9, 2.6]) * r
        g = np.maximum(H.groove(d_fr), H.groove(d_lg))
        hm = -1.0 * g + 0.3 * np.maximum(H.rivets(d_fr, a * r), H.rivets(d_lg, Pm[:, 1]))
        under = Pm[:, 2] < F_.zbot(Pm[:, 1]) + 0.6
        for yc, ln in ((S.y(190), 3.0), (S.y(487), 3.6)):          # nose and main gear doors
            hm += -2.0 * H.rect_outline(Pm[:, 0], Pm[:, 1], -0.75, 0.75, yc - ln / 2, yc + ln / 2) * under
        hm += -2.0 * H.rect_outline(Pm[:, 0], Pm[:, 1], -0.4, 0.4, S.y(240), S.y(215)) * under   # crew hatch
        hgt[m] = np.where(O[m] == k["fus"], hm, hgt[m])
        c = col[m]
        rad = Pm[:, 1] > S.y(60)
        c[rad] *= 0.8
        glare = (Pm[:, 1] > S.y(160)) & (Pm[:, 1] < S.y(60)) & (a > 0.45) & (a < 2.7)
        c[glare] = np.array([0.1, 0.105, 0.11])
        # heat-stained titanium aft of the nozzles
        hot = Pm[:, 1] < float(T.y(468)) + 0.5
        c[hot] = c[hot] * 0.75 + np.array([0.12, 0.11, 0.13]) * 0.25
        col[m] = c
    for name, le_f, te_f, ribs, spars, surf, axf in (
            ("glove", WLE, WTE, 1.2, (0.15,), [], None),
            ("WingL", WLE, WTE, 1.3, (0.12, 0.6), [(PIV_X + 2.0, PIV_X + 9.5, 0.72), (PIV_X + 9.8, float(T.x(630)), 0.72)], None),
            ("WingR", WLE, WTE, 1.3, (0.12, 0.6), [(PIV_X + 2.0, PIV_X + 9.5, 0.72), (PIV_X + 9.8, float(T.x(630)), 0.72)], None),
            ("stab", SLE, STE, 1.0, (0.15,), [], None)):
        m = O == k[name]
        if not m.any():
            continue
        Pm = P[m]
        aa = np.abs(Pm[:, 0])
        le, te = le_f(aa), te_f(aa)
        ch = np.maximum(le - te, 0.3)
        cf = (le - Pm[:, 1]) / ch
        d_rib = H.line_dist(aa, ribs, 0.2)
        hm = -1.0 * H.groove(d_rib) * (cf > 0.05)
        for sp in spars:
            hm = np.minimum(hm, -1.0 * H.groove(np.abs(cf - sp) * ch))
        for a0, a1, c0 in surf:
            inside = (aa > a0 - 0.03) & (aa < a1 + 0.03)
            outl = np.minimum(np.abs(cf - c0) * ch, np.where(cf > c0, np.minimum(np.abs(aa - a0), np.abs(aa - a1)), 9.0))
            hm = np.minimum(hm, np.where(inside, -2.6 * H.groove(outl, 0.035), 0))
            # leading-edge slats
            sl = np.minimum(np.abs(cf - 0.1) * ch, np.where(cf < 0.1, np.minimum(np.abs(aa - a0), np.abs(aa - a1)), 9.0))
            hm = np.minimum(hm, np.where(inside, -2.0 * H.groove(sl, 0.03), 0))
        hm += 0.3 * H.rivets(d_rib, Pm[:, 1]) * (cf > 0.05)
        hgt[m] = hm
        lew = np.clip(1 - cf / 0.035, 0, 1)
        col[m] = col[m] * (1 + 0.25 * lew)[:, None]
        rough[m] = rough[m] - 0.15 * lew
        metal[m] = 0.3 * lew
    m = O == k["fin"]
    if m.any():
        Pm = P[m]
        le = np.interp(Pm[:, 2], FIN_Z, FIN_LE); te = np.interp(Pm[:, 2], FIN_Z, FIN_TE)
        ch = np.maximum(le - te, 0.3)
        cf = (le - Pm[:, 1]) / ch
        hm = -1.0 * H.groove(H.line_dist(Pm[:, 2], 1.0, ZS)) * (cf > 0.05)
        for zz in (ZS + 1.0, ZS + 2.4, ZS + 3.8):                   # three rudder segments
            hm = np.minimum(hm, -2.6 * H.groove(np.abs(Pm[:, 2] - zz), 0.03) * (cf > 0.7))
        hm = np.minimum(hm, -2.6 * H.groove(np.abs(cf - 0.7) * ch, 0.035) * (Pm[:, 2] > ZS + 1.0))
        hgt[m] = hm
    m = O == k["nac"]
    if m.any():
        Pm = P[m]
        hgt[m] = -1.0 * H.groove(H.line_dist(Pm[:, 1], 1.2, 0.0))
        hot = Pm[:, 1] < float(T.y(468)) - 0.6
        c = col[m]; c[hot] = np.array([0.2, 0.19, 0.2]); col[m] = c
        mt = metal[m]; mt[hot] = 0.75; metal[m] = mt
        rg = rough[m]; rg[hot] = 0.38; rough[m] = rg
    m = O == k["dark"]
    if m.any():
        col[m] = np.array([0.05, 0.05, 0.055]); metal[m] = 0.5; rough[m] = 0.5
    m = O == k["bay"]
    if m.any():
        col[m] = np.array([0.30, 0.33, 0.29]) * (0.85 + 0.2 * L.value_noise(P[m], 0.5, seed=8))[:, None]
        rough[m] = 0.75
    for nm in [kk for kk in keys if kk.startswith("Door")]:
        m = O == k[nm]
        if m.any():
            inner = N[m, 2] > 0.2
            c = col[m]; c[inner] = np.array([0.30, 0.33, 0.29]); col[m] = c
    mk = np.zeros(n, bool)
    yi = S.y(640)
    hw, zc, h = F_.sec(yi)
    for sg in (-1, 1):
        mk |= H.insignia(P, N, (sg * hw, yi, zc + 0.3), (sg, 0, 0), (0, 0, 1), 0.7) & (O == k["fus"])
    xw = PIV_X + 8.0
    yw = float(WLE(xw) + WTE(xw)) / 2
    mk |= H.insignia(P, N, (-xw, yw, ZW), (0, 0, 1), (0, 1, 0), 1.0) & (O == k["WingL"])
    mk |= H.insignia(P, N, (xw, yw, ZW), (0, 0, -1), (0, 1, 0), 1.0) & (O == k["WingR"])
    col[mk] *= 0.4
    return {"col": np.clip(col, 0, 1), "rough": np.clip(rough, 0.05, 1), "metal": np.clip(metal, 0, 1), "height": hgt}


def main():
    no_sheet = "--no-sheet" in sys.argv
    L.reset_scene()
    mat = H.hd_material("SA_B1HD")
    objs, wings, doors, glass, team, empties, holes = build(mat)
    order = ["fus", "glove", "stab", "fin", "nac", "dark", "misc", "bay"]
    keys = order + list(wings) + list(doors)
    tex = [objs[k] for k in order] + list(wings.values()) + list(doors.values())
    H.uv_unwrap(tex)
    pa, pn, po, info = H.bake_maps(tex, lambda P, N, O: paint(P, N, O, keys, holes), OUT, ID)
    H.attach_maps(mat, pa, pn, po, ID)
    print("B1HD texel %.4f m coverage %.3f" % (info["texel_m"], info["coverage"]))
    body = K.join([objs[k] for k in order], "Body")
    body = K.join_team(body, team)
    glass.data.uv_layers.new(name=body.data.uv_layers.active.name)
    body = K.join([body, glass], "Body")
    ems = [K.empty(nm, p) for nm, p in empties.items()]
    export = [body] + list(wings.values()) + list(doors.values()) + ems
    H.export_glb(export, os.path.join(OUT, f"{ID}.glb"))
    print(H.report(export))
    if not no_sheet:
        def pose(name):
            op = name == "open"
            for nm, d in doors.items():
                d.rotation_euler = (0, math.radians(90 if nm.endswith("L") else -90) if op else 0, 0)
            sw = math.radians(38 if name in ("open", "swept") else 0)
            wings["WingL"].rotation_euler = (0, 0, sw)
            wings["WingR"].rotation_euler = (0, 0, -sw)
        views = [("3/4 front, high (cruise sweep)", -35, 24, (0, 0, 3.0), 62, 50, "closed"),
                 ("underside: wings swept, three bays open", 150, -30, (0, -2, 2.5), 55, 50, "open"),
                 ("cockpit and nose close-up", -50, 10, (0, S.y(150), 4.4), 13, 45, "swept"),
                 ("nacelles and nozzles close-up", -140, 4, (-NAC_X, float(T.y(440)), ZN), 14, 45, "swept")]
        H.art_sheet(ID, "Steel Accord B3 - B-1-style bomber HD (Cycles CPU review render)", views, SHEET, pose=pose)
        print("sheet", SHEET)


if __name__ == "__main__":
    main()
