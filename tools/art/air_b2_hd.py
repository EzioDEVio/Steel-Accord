"""Steel Accord - B3 HD strategic bomber: B-2-style flying wing (bpy 5.x).

Run:  python3 -I tools/art/air_b2_hd.py [--no-sheet]
Out:  godot/assets/units3d/b2_hd/b2_hd.glb (+ b2_hd_albedo.jpg 4096, b2_hd_normal.png 2048, b2_hd_orm.png 2048)
      docs/screens/b3_b2_hd_sheet.png

Planform and centre-body profile re-lofted at higher density from the M3 measured frames (air_b2_3d.py, imported
read-only): straight swept leading edge, double-W saw-tooth trailing edge, centre body, engine humps. New and
procedural: recessed upper intakes with jagged lips, exhaust troughs with heat tiles, cockpit glazing (four panes),
two side-by-side weapons bays with frames and paired doors, procedural paint (RAM tape lines, elevon and split drag
rudder gaps). Flight configuration: gear retracted.
Nodes: Body, Door0L/R (left bay), Door1L/R (right bay) (hinges on each bay's outer edges; open about Godot Z:
L negative, R positive), empties Exhaust0..3, Bay0a/b, Bay1a/b.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402
import airkit_hd as H  # noqa: E402
import air_b2_3d as B  # noqa: E402  (measured frames and outlines only)

L = K.L
import numpy as np  # noqa: E402

PI = math.pi
ID = "b2_hd"
S, T = B.S, B.T
OUT = os.path.join(K.OUT3D, ID)
SHEET = os.path.join(K.SCREENS, "b3_b2_hd_sheet.png")
ZTOP = K.polyline_fn([S(px, py) for px, py in B.TOP_LINE])
ZBOT = K.polyline_fn([S(px, py) for px, py in B.BOT_LINE])
TE_F = K.polyline_fn(B.TE)
Z_MID = float(S.z(806))
TIP = float(T.x(B.LE_TIP[0]))
YB = float(T.y(420))
BAYS = [(-3.1, -0.35), (0.35, 3.1)]
BAY_Y = (YB - 3.0, YB + 3.0)
HUMP_X = (388 - 316) * T.sx


def le_y(ax):
    f = (np.asarray(ax) / T.sx) / (B.LE_TIP[0] - 388)
    return T.y(175 + (B.LE_TIP[1] - 175) * np.clip(f, 0, 1))


def te_y(ax):
    px = 388 + np.asarray(ax) / T.sx
    return T.y(TE_F(px))


def build(mat):
    objs = {}
    xs_px = sorted(set(list(np.linspace(388, 766, 64)) + [p[0] for p in B.TE]))
    xcs = list(np.linspace(1, 0.2, 9)) + [0.15, 0.1, 0.06, 0.03, 0.012, 0.0]
    order = [-p for p in xs_px[::-1] if p != 388] + xs_px
    rings = []
    for spx in order:
        px = abs(spx)
        x = float(T.x(px)) * (1 if spx >= 0 else -1)
        f = (px - 388) / (B.LE_TIP[0] - 388)
        le_py = 175 + (B.LE_TIP[1] - 175) * f
        te_py = float(TE_F(px))
        if px >= 765.9:
            te_py = le_py + 3
        yle, yte = float(T.y(le_py)), float(T.y(te_py))
        ax = abs(x)
        w = float(np.clip(1 - (ax - 3.0) / 4.5, 0, 1)) ** 1.5
        ch = yle - yte
        t_out = 0.075 - 0.035 * min(ax / 26.0, 1)
        pts = [(xc, +1) for xc in xcs] + [(xc, -1) for xc in xcs[::-1][1:-1]]
        ring = []
        for xc, sg in pts:
            y = yle - ch * xc
            wing = sg * K.naca_t(xc, t_out) * ch
            body = (float(ZTOP(y)) if sg > 0 else float(ZBOT(y))) - Z_MID
            fade = min(1.0, (1 - xc) / 0.08) if xc > 0.92 else 1.0
            z = Z_MID + w * body * fade + (1 - w) * wing
            if sg < 0 and w > 0:
                z = min(z, Z_MID + (1 - w) * wing)
            ring.append((x, y, z))
        rings.append(ring)
    A = K.Part("Air")
    A.rings(rings)
    air = A.build(mat, smooth=40)
    zb_fn = H.bottom_fn(air)
    zt_fn = H.top_fn(air)
    holes = [H.cut_bay(air, x0, x1, BAY_Y[0], BAY_Y[1], Z_MID) for x0, x1 in BAYS]
    objs["air"] = air
    # engine humps with recessed intakes and exhaust troughs
    Hp = K.Part("Humps")
    D = K.Part("Dark")
    ex = []
    y0, y1 = float(T.y(300)), float(T.y(540))
    for sg in (-1, 1):
        xc_ = sg * HUMP_X
        rr = []
        for t in np.linspace(0, 1, 26):
            y = y0 + (y1 - y0) * t
            f = math.sin(math.pi * min(1.0, 0.04 + 0.96 * t)) ** 0.5
            zt = float(ZTOP(y)) - 0.9 * (1 - f)
            rr.append(K.superellipse_ring(y, xc_, 1.6 * max(f, 0.25), zt - 0.55, 0.55 * max(f, 0.2), 2.4, 32))
        Hp.rings(rr)
        # intake: dark recess just behind the hump's front with a raised jagged lip (two teeth)
        yi = y0 - 1.6
        zi = zt_fn(xc_, yi) - 0.25
        D.box((xc_, yi - 0.05, zi), (2.1, 0.5, 0.42), rot=(math.radians(-18), 0, 0))
        for dx in (-0.55, 0.55):
            Hp.beam((xc_ + dx - 0.5, yi + 0.35, zi + 0.22), (xc_ + dx, yi + 0.75, zi + 0.24), 0.08, 0.06, up=(0, 0, 1))
            Hp.beam((xc_ + dx + 0.5, yi + 0.35, zi + 0.22), (xc_ + dx, yi + 0.75, zi + 0.24), 0.08, 0.06, up=(0, 0, 1))
        # exhaust slots at the aft end of each hump
        for dx in (-0.7, 0.7):
            ye = y1 + 0.4
            ze = zt_fn(xc_ + dx, ye) - 0.07
            D.box((xc_ + dx, ye, ze), (0.95, 0.5, 0.12))
            ex.append((xc_ + dx, ye - 0.3, ze))
    objs["humps"] = Hp.build(mat, smooth=40)
    objs["dark"] = D.build(mat, smooth=30)
    Bp = K.Part("Bay")
    doors = {}
    for i, hole in enumerate(holes):
        bx0, bx1, by0, by1 = hole
        H.bay_box(Bp, bx0, bx1, by0, by1, zb_fn, Z_MID + 0.25, ribs=6)
        doors.update(H.door_pair(mat, i, hole, zb_fn))
    objs["bay"] = H.build_inward(Bp, mat)
    # glazing: four panes on the crew compartment
    Gl = K.Part("Glass")
    yc0, yc1 = float(S.y(150)), float(S.y(118))

    def top_pt(y, a):
        x = 1.15 * math.cos(a)
        return (x, y, float(ZTOP(y)) + 0.01 - 0.05 * abs(math.cos(a)))
    for a0, a1 in ((0.55, 0.95), (1.0, 1.5), (1.64, 2.14), (2.19, 2.59)):
        def fn(u, v, a0=a0, a1=a1):
            y = yc0 + (yc1 - yc0) * u
            a = a0 + (a1 - a0) * v
            p = top_pt(y, a)
            return (p[0], p[1], p[2] + 0.015), (0, 0.3, 1)
        H.shell_patch(Gl, fn, 3, 4, 0.02)
    glass = Gl.build(H.glass_material(), smooth=20)
    Tm = K.Part("Team")
    for sg in (-1, 1):
        x = sg * float(T.x(735))
        Tm.box((x, float(T.y(560)), Z_MID + 0.12), (1.6, 0.6, 0.08), rot=(0, 0, sg * math.radians(36)))
    team = Tm.build(K.team_material(), smooth=40)
    empties = {}
    for i, p in enumerate(sorted(ex, key=lambda q: q[0])):
        empties[f"Exhaust{i}"] = p
    for i, hole in enumerate(holes):
        bx0, bx1, by0, by1 = hole
        xm = (bx0 + bx1) / 2
        yc = (by0 + by1) / 2
        z = zb_fn(xm, yc) + 0.5
        empties[f"Bay{i}a"] = (xm, yc + 0.05, z)
        empties[f"Bay{i}b"] = (xm, yc - 0.05, z)
    return objs, doors, glass, team, empties, holes


BASE = np.array([0.19, 0.2, 0.212])


def paint(P, N, O, keys, holes):
    n = len(P)
    k = {name: i for i, name in enumerate(keys)}
    col = np.tile(BASE, (n, 1))
    rough = np.full(n, 0.5); metal = np.zeros(n); hgt = np.zeros(n)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    tone = 0.95 + 0.1 * H.hash01(np.floor((y - ax * 0.62) / 2.2).astype(np.int64), np.floor(ax / 2.6).astype(np.int64), (z > Z_MID).astype(np.int64))
    col *= tone[:, None]
    streak = H.aniso_noise(P, (0.25, 3.5, 0.25), seed=21)
    col *= (0.97 + 0.06 * streak)[:, None]
    rough += 0.07 * (streak - 0.5)
    m = (O == k["air"]) | (O == k["humps"])
    if m.any():
        Pm = P[m]; am = np.abs(Pm[:, 0])
        le, te = le_y(am), te_y(am)
        ch = np.maximum(le - te, 0.3)
        cf = (le - Pm[:, 1]) / ch
        # panels parallel to the leading edge + spanwise joints; RAM tape (lighter) along the leading edge
        sweep = (float(T.y(175)) - float(T.y(B.LE_TIP[1]))) / TIP
        d_le = H.line_dist(Pm[:, 1] + am * sweep, 1.9, 0.4) / math.sqrt(1 + sweep * sweep)
        d_sp = H.line_dist(am, 2.4, 0.3)
        hm = -0.8 * np.maximum(H.groove(d_le), H.groove(d_sp))
        hm += 0.2 * H.rivets(d_le, am)
        # elevons and beavertail (aft of 85% chord on the outer wing / centre tail), split drag rudders at the tips
        surf = [(5.0, 11.5), (11.8, 17.5), (17.8, 22.5)]
        for a0, a1 in surf:
            inside = (am > a0 - 0.03) & (am < a1 + 0.03)
            outl = np.minimum(np.abs(cf - 0.82) * ch, np.where(cf > 0.82, np.minimum(np.abs(am - a0), np.abs(am - a1)), 9.0))
            hm = np.minimum(hm, np.where(inside, -2.6 * H.groove(outl, 0.035), 0))
        dr = (am > 22.8) & (am < TIP - 0.6)
        outl = np.minimum(np.abs(cf - 0.72) * ch, np.where(cf > 0.72, np.minimum(np.abs(am - 22.8), np.abs(am - TIP + 0.6)), 9.0))
        hm = np.minimum(hm, np.where(dr, -2.6 * H.groove(outl, 0.035), 0))
        hm = np.minimum(hm, np.where(am < 1.6, -2.6 * H.groove(np.abs(cf - 0.86) * ch, 0.035), 0))
        # gear and crew hatch outlines on the belly
        under = N[m, 2] < -0.3
        for xc, yc, wx, ly in ((-4.8, float(T.y(430)), 1.2, 4.2), (4.8, float(T.y(430)), 1.2, 4.2), (0.0, float(T.y(270)), 0.7, 2.6)):
            hm += -2.0 * H.rect_outline(Pm[:, 0], Pm[:, 1], xc - wx, xc + wx, yc - ly / 2, yc + ly / 2) * under
        hgt[m] = hm
        c = col[m]
        tape = (cf < 0.025) | (np.abs(cf - 0.82) * ch < 0.05) & (am > 5.0)
        c[tape] = c[tape] * 1.28
        # exhaust troughs: heat tiles behind the humps (upper surface), sooted at the trailing edge
        tr = (np.abs(am - HUMP_X) < 1.5) & (Pm[:, 1] < float(T.y(540)) + 0.6) & (N[m, 2] > 0.3)
        tile = 0.9 + 0.1 * H.hash01(np.floor(Pm[:, 0] / 0.3).astype(np.int64), np.floor(Pm[:, 1] / 0.3).astype(np.int64))
        hot = np.array([0.36, 0.35, 0.33])
        c[tr] = hot * tile[tr][:, None] * (0.6 + 0.4 * np.clip((Pm[tr, 1] - te[tr]) / 3.0, 0, 1))[:, None]
        hgt_m = hgt[m]
        hgt_m[tr] -= 0.6 * H.groove(np.minimum(H.line_dist(Pm[tr, 0], 0.3), H.line_dist(Pm[tr, 1], 0.3)), 0.02)
        hgt[m] = hgt_m
        rg = rough[m]; rg[tr] = 0.7; rough[m] = rg
        col[m] = c
    m = O == k["dark"]
    if m.any():
        col[m] = np.array([0.04, 0.04, 0.045]); rough[m] = 0.55; metal[m] = 0.4
    m = O == k["bay"]
    if m.any():
        col[m] = np.array([0.33, 0.34, 0.33]) * (0.85 + 0.2 * L.value_noise(P[m], 0.5, seed=8))[:, None]
        rough[m] = 0.75
    for nm in [kk for kk in keys if kk.startswith("Door")]:
        m = O == k[nm]
        if m.any():
            inner = N[m, 2] > 0.2
            c = col[m]; c[inner] = np.array([0.33, 0.34, 0.33]); col[m] = c
            hgt[m] = -0.8 * H.groove(H.line_dist(P[m, 1], 1.5, BAY_Y[0]))
    mk = np.zeros(n, bool)
    xw = 18.5
    yw = float((le_y(xw) + te_y(xw)) / 2)
    zw = float(Z_MID)
    mk |= H.insignia(P, N, (-xw, yw, zw), (0, 0, 1), (0, 1, 0), 0.8, depth_tol=1.0) & (O == k["air"])
    mk |= H.insignia(P, N, (xw, yw, zw), (0, 0, -1), (0, 1, 0), 0.8, depth_tol=1.0) & (O == k["air"])
    col[mk] *= 0.5
    return {"col": np.clip(col, 0, 1), "rough": np.clip(rough, 0.05, 1), "metal": np.clip(metal, 0, 1), "height": hgt}


def main():
    no_sheet = "--no-sheet" in sys.argv
    L.reset_scene()
    mat = H.hd_material("SA_B2HD")
    objs, doors, glass, team, empties, holes = build(mat)
    order = ["air", "humps", "dark", "bay"]
    keys = order + list(doors)
    tex = [objs[k] for k in order] + list(doors.values())
    H.uv_unwrap(tex)
    pa, pn, po, info = H.bake_maps(tex, lambda P, N, O: paint(P, N, O, keys, holes), OUT, ID)
    H.attach_maps(mat, pa, pn, po, ID)
    print("B2HD texel %.4f m coverage %.3f" % (info["texel_m"], info["coverage"]))
    body = K.join([objs[k] for k in order], "Body")
    body = K.join_team(body, team)
    glass.data.uv_layers.new(name=body.data.uv_layers.active.name)
    body = K.join([body, glass], "Body")
    ems = [K.empty(nm, p) for nm, p in empties.items()]
    export = [body] + list(doors.values()) + ems
    H.export_glb(export, os.path.join(OUT, f"{ID}.glb"))
    print(H.report(export))
    if not no_sheet:
        def pose(name):
            op = name == "open"
            for nm, d in doors.items():
                d.rotation_euler = (0, math.radians(100 if nm.endswith("L") else -100) if op else 0, 0)
        views = [("3/4 front, high", -35, 26, (0, 0, 2.0), 66, 50, "closed"),
                 ("underside, both bays open", 160, -32, (0, -1, 1.5), 48, 50, "open"),
                 ("crew compartment and intakes close-up", -30, 18, (0, float(S.y(200)), 3.2), 14, 45, "closed"),
                 ("exhaust troughs and saw-tooth trailing edge", 150, 30, (-7, float(T.y(560)), 2.0), 18, 45, "closed")]
        H.art_sheet(ID, "Steel Accord B3 - B-2-style flying wing HD (Cycles CPU review render)", views, SHEET, pose=pose)
        print("sheet", SHEET)


if __name__ == "__main__":
    main()
