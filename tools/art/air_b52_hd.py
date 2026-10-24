"""Steel Accord - B3 HD strategic bomber: B-52-style eight-engine bomber (bpy 5.x).

Run:  python3 -I tools/art/air_b52_hd.py [--no-sheet]
Out:  godot/assets/units3d/b52_hd/b52_hd.glb (+ b52_hd_albedo.jpg 4096, b52_hd_normal.png 2048, b52_hd_orm.png 2048)
      docs/screens/b3_b52_hd_sheet.png

Outline geometry re-lofted at higher density from the M3 measured frames (air_b52_3d.py, imported read-only);
everything else is procedural and original: cockpit glazing, intakes with spinners, exhaust cones, pylons,
external tanks, outrigger fairings, blade antennas, a cut-out bomb bay with frames and a weapons beam, two
clamshell bay doors, two wing-pylon racks with six generic 500-lb-class bombs each, procedural paint.
Flight configuration: gear retracted (doors closed, outlined in the paint).
Nodes: Body, Door0L, Door0R (hinge origin; open = rotate about Godot Z, L negative / R positive),
StoresL, StoresR (pylon racks with bombs; hidden by the game as they release), empties Exhaust0..7,
Bay0a / Bay0b (fore / aft ends of the stowed-weapon line), PB0..PB11 (pylon bomb positions, L then R).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402
import airkit_hd as H  # noqa: E402
import air_b52_3d as B  # noqa: E402  (measured frames and outlines only)

L = K.L
import numpy as np  # noqa: E402

ID = "b52_hd"
S, T = B.S, B.T
OUT = os.path.join(K.OUT3D, ID)
SHEET = os.path.join(K.SCREENS, "b3_b52_hd_sheet.png")
NFUS = 2.8
PI = math.pi


class Fus:
    def __init__(self):
        self.ztop = K.polyline_fn([S(px, py) for px, py in B.FUS_TOP])
        self.zbot = K.polyline_fn([S(px, py) for px, py in B.FUS_BOT])
        self.hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in B.FUS_HW])

    def sec(self, y):
        zt, zb = float(self.ztop(y)), float(self.zbot(y))
        return max(float(self.hw(y)), 0.04), (zt + zb) / 2, max((zt - zb) / 2, 0.04)

    def ring_pt(self, y, a):
        hw, zc, h = self.sec(y)
        c, s = math.cos(a), math.sin(a)
        return (hw * math.copysign(abs(c) ** (2 / NFUS), c), y, zc + h * math.copysign(abs(s) ** (2 / NFUS), s))

    def bottom_z(self, x, y):
        hw, zc, h = self.sec(y)
        q = min(abs(x) / hw, 0.999)
        return zc - h * (1 - q ** NFUS) ** (1 / NFUS)


F_ = Fus()
Y_N, Y_T = S.y(13), S.y(792)
ZW = float(S.z(770))
W = [(383.5, 226, 362, 0.12), (410, 240, 369, 0.12), (460, 270, 386, 0.11), (550, 322, 416, 0.1),
     (650, 379, 447, 0.09), (700, 406, 463, 0.08), (752, 437, 478, 0.06)]
ST = ((383.5, 515, 614, 0.09), (410, 528, 614, 0.09), (460, 560, 615, 0.08), (500, 585, 616, 0.07), (507, 592, 616, 0.05))
FIN = [(645, 755, 760), (680, 752, 700), (705, 749, 633)]
YB = S.y(380)
BAY = (YB - 4.7, YB + 4.1)
BAY_HALF = 1.0
SEMI = float(T.x(752))
ZS = float(S.z(782))


def wing_z(x):
    return ZW - abs(x) * math.tan(math.radians(1.5))


def interp_sections(rows, xcol=0):
    xs = np.array([float(T.x(r[0])) for r in rows])
    le = np.array([float(T.y(r[1])) for r in rows]); te = np.array([float(T.y(r[2])) for r in rows])
    return (lambda ax: np.interp(ax, xs, le)), (lambda ax: np.interp(ax, xs, te))


WLE, WTE = interp_sections(W)
SLE, STE = interp_sections(ST)
_fin = K.fin_sections(S, FIN, x=0)
FIN_Z = np.array([s[0][2] for s in _fin]); FIN_LE = np.array([s[0][1] for s in _fin]); FIN_TE = np.array([s[1][1] for s in _fin])
PODS = B.PODS
EXH = []


def build(mat):
    objs = {}
    # ---- fuselage
    Fp = K.Part("Fus")
    ys = np.concatenate([np.linspace(Y_N - 0.01, Y_N - 7.0, 30), np.linspace(Y_N - 7.3, Y_T + 0.3, 70), [Y_T + 0.05]])
    K.fuselage(Fp, ys, F_.ztop, F_.zbot, F_.hw, n=NFUS, seg=64)
    fus = Fp.build(mat, smooth=50)
    hole = H.cut_bay(fus, -BAY_HALF, BAY_HALF, BAY[0], BAY[1], F_.sec(YB)[1] - 0.3)
    objs["fus"] = fus
    # ---- wing, stabiliser, fin
    Wp = K.Part("Wing")
    right = [((float(T.x(px)), float(T.y(le)), wing_z(float(T.x(px)))), (float(T.x(px)), float(T.y(te)), wing_z(float(T.x(px)))), t, (0, 0, 1))
             for px, le, te, t in W]
    K.surface(Wp, K.mirror_sections(right[1:]) + right, npts=16)
    objs["wing"] = Wp.build(mat, smooth=40)
    Sp = K.Part("Stab")
    st = [((float(T.x(px)), float(T.y(le)), ZS), (float(T.x(px)), float(T.y(te)), ZS), t, (0, 0, 1)) for px, le, te, t in ST]
    K.surface(Sp, K.mirror_sections(st[1:]) + st, npts=14)
    objs["stab"] = Sp.build(mat, smooth=40)
    Fn = K.Part("Fin")
    K.surface(Fn, _fin, npts=14)
    objs["fin"] = Fn.build(mat, smooth=40)
    # ---- engine pods: twin nacelles on four pylons, intake lips, spinners, exhaust cones
    Pp = K.Part("Pods")
    D = K.Part("Dark")
    for xo, py0, py1 in PODS:
        xc = xo * T.sx
        y0, y1 = float(T.y(py0)), float(T.y(py1))
        zwx = wing_z(xc)
        zp = zwx - 1.55
        Pp.beam((xc, y0 - 1.6, zwx - 0.15), (xc, y1 + 0.6, zwx - 0.15), 0.32, 0.14)            # pylon top fairing
        Pp.beam((xc, (y0 + y1) / 2 - 0.9, zwx - 0.35), (xc, y0 - 0.6, zwx - 0.95), 0.3, 0.7)   # pylon web (raked)
        Pp.box((xc, (y0 + y1) / 2 - 0.6, zwx - 0.75), (0.34, (y0 - y1) * 0.62, 1.0))
        for dx in (-0.78, 0.78):
            K.body_rev(Pp, (xc + dx, y1, zp), (xc + dx, y0, zp),
                       [(0, 0.40), (0.04, 0.45), (0.1, 0.56), (0.3, 0.64), (0.5, 0.68), (0.8, 0.68), (0.93, 0.64),
                        (0.975, 0.6), (0.99, 0.57), (1, 0.53)], seg=28)
            # intake lip ring and recessed fan face with spinner
            K.body_rev(Pp, (xc + dx, y0 - 0.01, zp), (xc + dx, y0 - 0.35, zp), [(0, 0.5), (1, 0.47)], seg=28)
            K.disc(D, (xc + dx, y0 - 0.36, zp), 0.48, seg=24)
            K.body_rev(D, (xc + dx, y0 - 0.37, zp), (xc + dx, y0 - 0.05, zp), [(0, 0.17), (0.5, 0.12), (1, 0.02)], seg=16)
            # exhaust: dark hot section with a protruding tail cone
            K.disc(D, (xc + dx, y1 + 0.02, zp), 0.37, seg=24)
            K.body_rev(D, (xc + dx, y1 + 0.03, zp), (xc + dx, y1 - 0.75, zp), [(0, 0.24), (0.6, 0.16), (1, 0.03)], seg=16)
            EXH.append((xc + dx, y1 - 0.6, zp))
    objs["pods"] = Pp.build(mat, smooth=40)
    objs["dark"] = D.build(mat, smooth=40)
    # ---- misc: external tanks, outrigger fairings, antennas, tail cone, inner pylons
    M = K.Part("Misc")
    for sg in (-1, 1):
        xt = sg * 16.6
        yt = float(WLE(abs(xt))) - 2.0
        M.beam((xt, yt + 1.5, wing_z(xt) - 0.1), (xt, yt - 3.0, wing_z(xt) - 0.1), 0.18, 0.6)
        K.body_rev(M, (xt, yt - 5.4, wing_z(xt) - 0.95), (xt, yt + 3.2, wing_z(xt) - 0.95),
                   [(0, 0.05), (0.08, 0.32), (0.25, 0.52), (0.6, 0.55), (0.85, 0.45), (1, 0.06)], seg=22)
        for k in range(2):        # small tank fins
            M.beam((xt, yt - 5.0, wing_z(xt) - 0.95), (xt + sg * (0.4 if k else 0.0), yt - 4.4, wing_z(xt) - 0.95 - (0 if k else 0.45)),
                   0.03, 0.5, up=(0, 1, 0))
        xo = sg * 24.4
        yo = float(WLE(abs(xo))) - 1.2
        K.body_rev(M, (xo, yo - 2.6, wing_z(xo) - 0.35), (xo, yo + 0.4, wing_z(xo) - 0.35),
                   [(0, 0.06), (0.25, 0.28), (0.7, 0.3), (1, 0.08)], seg=16, squash=1.3)
    for y, up in ((S.y(200), 1), (S.y(330), 1), (S.y(520), 1), (S.y(230), -1), (S.y(560), -1)):
        hw, zc, h = F_.sec(y)
        z = zc + up * h
        M.beam((0, y + 0.25, z), (0, y - 0.35, z + up * 0.5), 0.04, 0.3, up=(0, 1, 0))
    yc = Y_T + 0.1
    hw, zc, h = F_.sec(Y_T + 1.0)
    K.body_rev(M, (0, yc + 1.4, zc + 0.05), (0, yc - 1.1, zc + 0.1), [(0, 0.5), (0.5, 0.42), (0.85, 0.3), (1, 0.06)], seg=20)
    # ---- bomb bay interior + doors
    bx0, bx1, by0, by1 = hole
    zc_bay = F_.sec(YB)[1]
    Bp = K.Part("Bay")
    H.bay_box(Bp, bx0, bx1, by0, by1, lambda x, y: F_.bottom_z(x, y), zc_bay + 0.35, ribs=7)
    objs["bay"] = H.build_inward(Bp, mat)
    doors = {}
    for side, sg in (("L", -1), ("R", 1)):
        xh = bx1 if sg > 0 else bx0
        Dp = K.Part(f"Door0{side}")

        def fn(u, v, xh=xh):
            y = by0 + (by1 - by0) * u
            x = xh * (1 - v)
            z = F_.bottom_z(x, y) - 0.012
            n = (math.copysign(0.25, x) if abs(x) > 0.05 else 0, 0, -1)
            return (x, y, z), n
        H.shell_patch(Dp, fn, 10, 6, 0.04)
        d = Dp.build(mat, smooth=40)
        ym = (by0 + by1) / 2
        H.set_origin(d, (xh, ym, F_.bottom_z(xh, ym)))
        doors[f"Door0{side}"] = d
    # ---- wing pylon racks with six bombs each
    stores = {}
    pb = []
    ywp = float(T.y(330))
    for side, sg in (("L", -1), ("R", 1)):
        x = sg * 70 * T.sx
        zt = wing_z(x)
        Sp2 = K.Part(f"Stores{side}")
        # pylon and multiple-ejector beam stay on the airframe (Misc -> Body); only the bombs are in Stores<side>
        M.beam((x, ywp + 2.0, zt - 0.1), (x, ywp - 1.8, zt - 0.1), 0.22, 0.7)
        M.box((x, ywp, zt - 0.7), (0.26, 3.2, 0.5))
        M.box((x, ywp, zt - 1.0), (0.9, 3.6, 0.14))
        for dy in (-1.2, 1.2):
            for dx, dz in ((-0.42, -1.45), (0.42, -1.45), (0.0, -1.62)):
                nose = (x + dx, ywp + dy + 1.12, zt + dz)
                K.bomb(Sp2, nose, 2.25, 0.2, seg=14)
                pb.append((x + dx, ywp + dy, zt + dz))
        so = Sp2.build(mat, smooth=40)
        H.set_origin(so, (x, ywp, zt - 1.0))
        stores[f"Stores{side}"] = so
    objs["misc"] = M.build(mat, smooth=40)
    # ---- glazing (separate material)
    Gp = K.Part("Glass")
    for a0, a1 in ((0.62, 1.02), (1.08, 1.5), (1.64, 2.06), (2.12, 2.52)):
        H.glass_patch(Gp, F_.ring_pt, (S.y(92), S.y(76)), a0, a1)
    for sg in (-1, 1):
        for y0p, y1p in ((108, 96), (124, 112)):
            a0, a1 = (0.36, 0.55) if sg > 0 else (PI - 0.55, PI - 0.36)
            H.glass_patch(Gp, F_.ring_pt, (S.y(y0p), S.y(y1p)), a0, a1)
    glass = Gp.build(H.glass_material(), smooth=20)
    # ---- team panel on the fin (tail band)
    Tm = K.Part("Team")
    K.surface(Tm, K.fin_sections(S, [(700, 749, 645), (705, 749, 631)], x=0, t_root=0.11, t_tip=0.1))
    team = Tm.build(K.team_material(), smooth=40)
    empties = {}
    for i, p in enumerate(sorted(EXH, key=lambda q: q[0])):
        empties[f"Exhaust{i}"] = p
    zst = zc_bay - 0.2
    empties["Bay0a"] = (0.0, by1 - 1.3, zst)
    empties["Bay0b"] = (0.0, by0 + 1.3, zst)
    for i, p in enumerate(pb):
        empties[f"PB{i}"] = p
    return objs, doors, stores, glass, team, empties


# ---------------------------------------------------------------------------- paint
BASE = np.array([0.355, 0.375, 0.385])


def fus_angle(P):
    hw = F_.hw(P[:, 1]); zt = F_.ztop(P[:, 1]); zb = F_.zbot(P[:, 1])
    zc = (zt + zb) / 2; h = np.maximum((zt - zb) / 2, 0.05)
    a = np.arctan2((P[:, 2] - zc) / h, P[:, 0] / np.maximum(hw, 0.05))
    return a, (hw + h) / 2


def paint(P, N, O):
    n = len(P)
    keys = ["fus", "wing", "stab", "fin", "pods", "dark", "misc", "bay", "Door0L", "Door0R", "StoresL", "StoresR"]
    k = {name: i for i, name in enumerate(keys)}
    col = np.tile(BASE, (n, 1))
    rough = np.full(n, 0.58); metal = np.zeros(n); hgt = np.zeros(n)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    # per-panel tone variation + flow streaks
    tone = 0.96 + 0.08 * hash01_cells(P, 1.6)
    col *= tone[:, None]
    streak = H.aniso_noise(P, (0.22, 5.0, 0.22), seed=3)
    col *= (0.97 + 0.06 * streak)[:, None]
    rough += 0.08 * (streak - 0.5)
    # ---- fuselage: frames, stringers, doors, radome, anti-glare
    m = (O == k["fus"]) | (O == k["misc"])
    if m.any():
        Pm = P[m]
        a, r = fus_angle(Pm)
        st = np.concatenate([np.arange(Y_T + 1.0, Y_N - 3.0, 1.55), [S.y(60), S.y(130), S.y(140)]])
        d_fr = H.stations_dist(Pm[:, 1], st)
        d_lg = H.stations_dist(a, [-2.75, -2.05, -1.1, -0.42, 0.42, 1.1, 2.05, 2.75]) * r
        g = np.maximum(H.groove(d_fr), H.groove(d_lg))
        hm = -1.0 * g + 0.3 * np.maximum(H.rivets(d_fr, a * r), H.rivets(d_lg, Pm[:, 1]))
        # main gear doors and crew hatch outlines (belly)
        for py0, py1 in ((236, 300), (456, 520)):
            hm += -2.0 * rect_outline(Pm[:, 0], Pm[:, 1], -1.15, 1.15, S.y(py1), S.y(py0)) * (Pm[:, 2] < F_.sec(S.y(270))[1])
        hm += -2.0 * rect_outline(Pm[:, 0], Pm[:, 1], -0.45, 0.45, S.y(150), S.y(118)) * (Pm[:, 2] < F_.sec(S.y(130))[1])
        hgt[m] = np.where(O[m] == k["fus"], hm, hgt[m])
        c = col[m]
        rad = Pm[:, 1] > S.y(42)
        c[rad] = c[rad] * 0.68
        glare = (Pm[:, 1] > S.y(92)) & (Pm[:, 1] < S.y(42)) & (a > 0.5) & (a < 2.6) & (O[m] == k["fus"])
        c[glare] = np.array([0.12, 0.125, 0.13])
        # walkway / bay surround soot and belly grime
        belly = np.clip(-N[m, 2], 0, 1) * (Pm[:, 1] < S.y(300))
        c *= (1 - 0.08 * belly)[:, None]
        col[m] = c
        rg = rough[m]; rg[rad] = 0.45; rough[m] = rg
    # ---- lifting surfaces: ribs, spars, control surfaces, leading-edge wear
    for name, le_f, te_f, ribs, spars, surf in (
            ("wing", WLE, WTE, 1.45, (0.1, 0.62), [(2.2, 0.56 * SEMI, 0.74, "both"), (0.44 * SEMI, 0.86 * SEMI, 0.6, "top")]),
            ("stab", SLE, STE, 1.2, (0.12,), [(1.2, float(T.x(505)), 0.7, "both")])):
        m = O == k[name]
        if not m.any():
            continue
        Pm = P[m]
        aa = np.abs(Pm[:, 0])
        le, te = le_f(aa), te_f(aa)
        ch = np.maximum(le - te, 0.3)
        cf = (le - Pm[:, 1]) / ch
        d_rib = H.line_dist(aa, ribs, 0.3)
        hm = -1.0 * H.groove(d_rib) * (cf > 0.04)
        for sp in spars:
            hm = np.minimum(hm, -1.0 * H.groove(np.abs(cf - sp) * ch))
        top = N[m, 2] > 0
        for a0, a1, c0, which in surf:
            inside = (aa > a0) & (aa < a1)
            if which == "top":
                inside &= top
                seg = H.line_dist(aa, 1.4, a0)
                outl = np.minimum(np.abs(cf - c0) * ch, np.where(cf > c0, seg, 9.0))
                outl = np.where(cf < 0.73, outl, 9.0)
            else:
                outl = np.minimum(np.abs(cf - c0) * ch, np.where(cf > c0, np.minimum(np.abs(aa - a0), np.abs(aa - a1)), 9.0))
            hm = np.minimum(hm, np.where(inside | (np.abs(aa - a0) < 0.03) | (np.abs(aa - a1) < 0.03), -2.6 * H.groove(outl, 0.035), 0))
        hm += 0.3 * H.rivets(d_rib, Pm[:, 1]) * (cf > 0.04)
        hgt[m] = hm
        lew = np.clip(1 - cf / 0.035, 0, 1)
        col[m] = col[m] * (1 + 0.18 * lew)[:, None]
        rough[m] = rough[m] - 0.15 * lew
        metal[m] = 0.35 * lew
    m = O == k["fin"]
    if m.any():
        Pm = P[m]
        le = np.interp(Pm[:, 2], FIN_Z, FIN_LE); te = np.interp(Pm[:, 2], FIN_Z, FIN_TE)
        ch = np.maximum(le - te, 0.3)
        cf = (le - Pm[:, 1]) / ch
        hm = -1.0 * H.groove(H.line_dist(Pm[:, 2], 1.1, ZS)) * (cf > 0.05)
        hm = np.minimum(hm, -2.6 * H.groove(np.abs(cf - 0.72) * ch, 0.035) * (Pm[:, 2] > ZS + 0.8))
        hgt[m] = hm
        lew = np.clip(1 - cf / 0.03, 0, 1)
        col[m] = col[m] * (1 + 0.15 * lew)[:, None]
    # ---- pods: intake lips bare metal, panel bands, soot behind exhausts
    m = O == k["pods"]
    if m.any():
        Pm = P[m]
        front = np.zeros(len(Pm), bool)
        for xo, py0, py1 in PODS:
            y0 = float(T.y(py0))
            front |= (np.abs(Pm[:, 0] - xo * T.sx) < 1.5) & (Pm[:, 1] > y0 - 0.4)
        c = col[m]; c[front] = np.array([0.58, 0.59, 0.6]); col[m] = c
        mt = metal[m]; mt[front] = 0.85; metal[m] = mt
        rg = rough[m]; rg[front] = 0.3; rough[m] = rg
        hgt[m] = -1.0 * H.groove(H.line_dist(Pm[:, 1], 1.3, 0.2))
    m = O == k["dark"]
    if m.any():
        col[m] = np.array([0.07, 0.07, 0.075]) * (0.8 + 0.4 * L.value_noise(P[m], 0.3, seed=2))[:, None]
        metal[m] = 0.7; rough[m] = 0.45
    m = O == k["bay"]
    if m.any():
        col[m] = np.array([0.30, 0.33, 0.29]) * (0.85 + 0.2 * L.value_noise(P[m], 0.5, seed=8))[:, None]
        rough[m] = 0.75
    for nm in ("Door0L", "Door0R"):
        m = O == k[nm]
        if m.any():
            inner = N[m, 2] > 0.2           # door inner face: interior primer
            c = col[m]; c[inner] = np.array([0.30, 0.33, 0.29]); col[m] = c
            hgt[m] = -1.0 * H.groove(H.line_dist(P[m, 1], 1.4, BAY[0]))
    for nm in ("StoresL", "StoresR"):
        m = O == k[nm]
        if m.any():
            Pm = P[m]
            isb = Pm[:, 2] < wing_z(Pm[:, 0]) - 1.12
            c = col[m]
            c[isb] = np.array([0.33, 0.35, 0.25])          # bombs: olive drab
            nose = isb & (H.line_dist(Pm[:, 1] - ywp_c(), 2.4, 1.2 + 0.98) < 0.06)
            c[nose] = np.array([0.75, 0.62, 0.12])         # yellow nose band
            col[m] = c
    # soot behind the engines (pods, flaps, wing underside)
    soot = np.zeros(n)
    for ex, ey, ez in EXH:
        behind = np.clip(ey - y, 0, None)
        lat = (x - ex) ** 2 + ((z - ez) * 0.7) ** 2
        soot += np.exp(-lat / (0.35 + 0.08 * behind) ** 2) * np.exp(-behind / 7.0) * (y < ey + 0.3)
    soot = np.clip(soot, 0, 1)
    col *= (1 - 0.55 * soot)[:, None]
    rough += 0.15 * soot
    # low-visibility insignia: fuselage sides aft, upper left wing, lower right wing
    mk = np.zeros(n, bool)
    yi = S.y(600)
    hw, zc, h = F_.sec(yi)
    for sg in (-1, 1):
        mk |= H.insignia(P, N, (sg * hw, yi, zc + 0.15), (sg, 0, 0), (0, 0, 1), 0.85) & ((O == k["fus"]))
    xw = -0.72 * SEMI
    mk |= H.insignia(P, N, (xw, float(WLE(-xw) + WTE(-xw)) / 2, wing_z(xw)), (0, 0, 1), (0, 1, 0), 1.25) & (O == k["wing"])
    mk |= H.insignia(P, N, (-xw, float(WLE(-xw) + WTE(-xw)) / 2, wing_z(xw)), (0, 0, -1), (0, 1, 0), 1.25) & (O == k["wing"])
    col[mk] = col[mk] * 0.35
    # underside slightly lighter (sky reflection reads too dark in game otherwise), top dust
    col *= (1 + 0.04 * np.clip(-N[:, 2], 0, 1))[:, None]
    return {"col": np.clip(col, 0, 1), "rough": np.clip(rough, 0.05, 1), "metal": np.clip(metal, 0, 1), "height": hgt}


def ywp_c():
    return float(T.y(330))


def hash01_cells(P, s):
    return H.hash01(np.floor(P[:, 0] / (s * 2.2)).astype(np.int64), np.floor(P[:, 1] / s).astype(np.int64),
                    np.floor(P[:, 2] / (s * 0.8)).astype(np.int64))


def rect_outline(x, y, x0, x1, y0, y1, w=0.03):
    inside = (x > x0 - w) & (x < x1 + w) & (y > y0 - w) & (y < y1 + w)
    d = np.minimum(np.minimum(np.abs(x - x0), np.abs(x - x1)), np.minimum(np.abs(y - y0), np.abs(y - y1)))
    return np.where(inside, H.groove(d, w), 0.0)


# ---------------------------------------------------------------------------- main
def main():
    no_sheet = "--no-sheet" in sys.argv
    L.reset_scene()
    mat = H.hd_material("SA_B52HD")
    objs, doors, stores, glass, team, empties = build(mat)
    order = ["fus", "wing", "stab", "fin", "pods", "dark", "misc", "bay"]
    tex = [objs[k] for k in order] + [doors["Door0L"], doors["Door0R"], stores["StoresL"], stores["StoresR"]]
    H.uv_unwrap(tex)
    pa, pn, po, info = H.bake_maps(tex, paint, OUT, ID)
    H.attach_maps(mat, pa, pn, po, ID)
    print("B52HD texel %.4f m coverage %.3f" % (info["texel_m"], info["coverage"]))
    body = K.join([objs[k] for k in order], "Body")
    body = K.join_team(body, team)
    gl = glass
    gl.data.uv_layers.new(name=body.data.uv_layers.active.name)
    body = K.join([body, gl], "Body")
    ems = [K.empty(nm, p) for nm, p in empties.items()]
    export = [body] + list(doors.values()) + list(stores.values()) + ems
    H.export_glb(export, os.path.join(OUT, f"{ID}.glb"))
    print(H.report(export))
    if not no_sheet:
        def pose(name):
            op = name == "open"
            doors["Door0L"].rotation_euler = (0, math.radians(95) if op else 0, 0)
            doors["Door0R"].rotation_euler = (0, math.radians(-95) if op else 0, 0)
        views = [("3/4 front, high", -35, 24, (0, 0, 3.5), 72, 50, "closed"),
                 ("underside, bay open (pylon racks loaded)", 150, -28, (0, -2, 2.5), 60, 50, "open"),
                 ("cockpit and nose close-up", -55, 12, (0, S.y(110), 4.6), 14, 45, "closed"),
                 ("engine pods close-up", -70, 2, (-8.5, float(T.y(290)), ZW - 1.6), 15, 45, "closed")]
        H.art_sheet(ID, "Steel Accord B3 - B-52-style bomber HD (Cycles CPU review render)", views, SHEET, pose=pose)
        print("sheet", SHEET)


if __name__ == "__main__":
    main()
