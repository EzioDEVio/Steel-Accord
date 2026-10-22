"""Steel Accord - pilot 3D model: CH-47-style tandem-rotor heavy-lift helicopter, bpy 5.x.

Run:  python3 tools/art/air_ch47_3d.py <out_dir> [--previews <dir>] [--no-previews]
Out:  <out_dir>/ch47.glb (+ ch47_albedo.png, ch47_blade.png inspectable copies; embedded in the GLB)

Same method as veh_m88_3d.py (whose library half this script imports): the airframe is lofted from
profiles measured in pixels on the concept side view (nose left) and the blade-free top view
(nose up), and textured by depth-tested projection of those two views into one baked atlas.
The concept top view is not proportionally consistent with the side view (its nose section is
~1.9x longer relative to the rotor spacing), so it is mapped with a piecewise-linear Y rectification
through 4 landmarks: nose tip, front hub, rear hub, tail.

Nodes: Body (static, incl. sponsons, pylons, engines, landing gear), RotorFront, RotorRear (mesh
objects, origin at the hub, 3 real blades each; spin about local Z in Blender = local Y in Godot).
Origin: ground contact (wheel bottoms) under the fuselage midpoint. Forward = Blender +Y (Godot -Z).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veh_m88_3d as L  # noqa: E402  (library half only; its main() is guarded)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

PI = math.pi
INC = "/home/claude/incoming/a/individual_views/CH-47_Chinook"
SIDE_PNG = os.path.join(INC, "CH-47_Chinook_side_profile.png")
OVER_PNG = os.path.join(INC, "CH-47_Chinook_overhead_game_view.png")
TOP_PNG = os.path.join(L.REPO, "godot", "assets", "us", "rotors", "ch47_body.png")

# side view: front hub px 180, rear hub px 693 -> real CH-47 hub spacing 11.94 m
SS = 11.94 / (693 - 180)
SIDE_CX = (75 + 768) / 2.0      # nose tip px 75, tail px 768 -> origin at fuselage midpoint
GROUND_PY = 433.0               # wheel bottoms


def S(px, py):
    return ((SIDE_CX - px) * SS, (GROUND_PY - py) * SS)


Y_NOSE, Y_HUBF = S(75, 0)[0], S(180, 0)[0]
Y_HUBR, Y_TAIL = S(693, 0)[0], S(768, 0)[0]
TOP_PY = [535.0, 478.0, 145.0, 12.0]          # tail, rear hub, front hub, nose (top view rows)
TOP_YW = [Y_TAIL, Y_HUBR, Y_HUBF, Y_NOSE]
SX = 0.030                                    # top view metres per px across (sponsons ~3.6 m)


def top_py(y):
    return np.interp(y, TOP_YW, TOP_PY)


def top_px(x):
    return 300.0 + np.asarray(x) / SX


def top_half_width(y, measured):
    """half width (m) at world y from the measured top-view silhouette rows."""
    rows, half = measured
    return np.interp(top_py(y), rows, half)


def measure_top_widths():
    from PIL import Image
    a = np.asarray(Image.open(TOP_PNG))[..., 3] > 128
    rows, half = [], []
    for r in range(10, 540, 2):
        c = np.where(a[r])[0]
        if len(c):
            rows.append(r); half.append(max(300 - c.min(), c.max() - 300) * SX)
    return np.array(rows, float), np.array(half)


# ------------------------------------------------------------------ profiles (side-view px)
TOP_LINE = [(75, 333), (80, 312), (90, 296), (105, 283), (125, 272), (150, 265), (200, 262), (300, 259),
            (590, 258), (700, 259), (768, 262)]
BOT_LINE = [(75, 333), (78, 348), (92, 366), (115, 379), (155, 389), (220, 397), (300, 401), (600, 403),
            (680, 401), (700, 388), (735, 360), (768, 334)]


def prof(line, y):
    pts = sorted((S(px, py) for px, py in line), key=lambda p: p[0])
    return np.interp(y, [p[0] for p in pts], [p[1] for p in pts])


def superellipse_ring(y, xc, half_w, zc, half_h, n, seg, z_bias=0.0):
    ring = []
    for k in range(seg):
        a = 2 * PI * k / seg
        c, s = math.cos(a), math.sin(a)
        x = xc + half_w * math.copysign(abs(c) ** (2 / n), c)
        z = zc + half_h * math.copysign(abs(s) ** (2 / n), s)
        ring.append((x, y, z))
    return ring


def build_ch47(mat, blade_mat):
    widths = measure_top_widths()
    B = L.Part("Body")
    # ---- fuselage loft
    ys = np.concatenate([np.linspace(Y_NOSE - 0.02, Y_NOSE - 1.6, 12), np.linspace(Y_NOSE - 1.8, Y_TAIL + 1.6, 26),
                         np.linspace(Y_TAIL + 1.4, Y_TAIL + 0.02, 8)])
    rings = []
    for y in ys:
        zt, zb = prof(TOP_LINE, y), prof(BOT_LINE, y)
        hw = min(float(top_half_width(y, widths)), 1.35)
        tn = np.clip((Y_NOSE - y) / 1.6, 0, 1)                  # 0 at nose tip -> 1 aft
        tt = np.clip((y - Y_TAIL) / 1.4, 0, 1)
        hw = hw * min(1.0, 0.25 + 0.75 * tn ** 0.5) * min(1.0, 0.55 + 0.45 * tt)
        h = max((zt - zb) / 2, 0.05)
        n = 2.4 + 1.6 * min(tn, tt)
        rings.append(superellipse_ring(y, 0.0, max(hw, 0.08), (zt + zb) / 2, h, n, 40))
    B.rings(rings)
    # ---- sponsons (side px 260..693, py 337..397), out to the top-view sponson width
    y0, y1 = S(262, 0)[0], S(693, 0)[0]
    zc, hh = S(0, 367)[1], (397 - 337) / 2 * SS
    for s in (-1, 1):
        rr = []
        for t in np.concatenate([np.linspace(0, 0.08, 5), np.linspace(0.12, 0.9, 6), np.linspace(0.93, 1, 4)]):
            y = y0 + (y1 - y0) * t
            f = min(1.0, math.sin(min(t / 0.08, 1) * PI / 2) ** 0.6) * (1 - 0.35 * max(0, (t - 0.9) / 0.1))
            ff = max(f, 0.15)
            rr.append(superellipse_ring(y, s * 1.42, 0.40 * ff, zc - 0.05 * (1 - ff), hh * (0.4 + 0.6 * ff), 3.0, 20))
        B.rings(rr)
    # ---- forward pylon (side px 143..282, top 205) and aft pylon (585..768, top 189)
    fp = [S(140, 264), S(150, 226), S(168, 208), S(255, 205), S(268, 226), S(284, 260)]
    B.side(fp, -0.92, 0.92)
    ap = [S(582, 261), S(600, 232), S(622, 205), S(660, 191), S(758, 189), S(767, 200), S(767, 262)]
    B.side(ap, -0.9, 0.9)
    # rotor masts / transmission domes
    for (hp, top) in ((180, 205), (693, 189)):
        y, z = S(hp, top)
        B.cyl((0, y, z + 0.1), 0.55, 0.2, seg=20)
        B.cyl((0, y, z + 0.22), 0.22, 0.25, seg=12)
    # ---- engine nacelles on the aft pylon (side px 605..740 at py 275, top px 262/339)
    ey0, ey1 = S(605, 0)[0], S(742, 0)[0]
    ez = S(0, 276)[1]
    for s in (-1, 1):
        rr = []
        for t, r in ((0.0, 0.32), (0.04, 0.44), (0.12, 0.5), (0.6, 0.5), (0.8, 0.46), (0.93, 0.36), (1.0, 0.33)):
            y = ey0 + (ey1 - ey0) * t
            rr.append(superellipse_ring(y, s * 1.38, r, ez, r, 2.0, 18))
        B.rings(rr)
        B.box((s * 1.07, (ey0 + ey1) / 2 + 0.3, ez - 0.05), (0.42, 1.6, 0.35))   # nacelle pylon
    # ---- cargo hook well, steps, antennas (small silhouette details)
    for px in (500, 560, 640):
        y = S(px, 0)[0]
        B.rod((0, y, prof(TOP_LINE, y)), (0, y, prof(TOP_LINE, y) + 0.25), 0.03, seg=6)
    # ---- landing gear: front twin wheels (side px 303), rear single wheels (px 663); r 16 px
    wr = 16 * SS
    for gy_px, twin in ((303, True), (663, False)):
        gy = S(gy_px, 0)[0]
        for s in (-1, 1):
            xs = (s * 1.36, s * 1.70) if twin else (s * 1.55,)
            for x in xs:
                B.cyl((x, gy, wr), wr, 0.2, (0, PI / 2, 0), seg=16)
                B.cyl((x, gy, wr), wr * 0.45, 0.24, (0, PI / 2, 0), seg=10)
            B.rod((s * 1.53, gy, wr), (s * 1.48, gy + 0.15, zc - hh + 0.1), 0.08, seg=8)   # oleo strut
            B.rod((s * 1.53, gy, wr), (s * 1.2, gy - 0.5, 0.9), 0.05, seg=6)               # drag brace
            B.box((s * 1.53, gy, wr), (0.5 if twin else 0.3, 0.12, 0.1))                     # axle
    body = B.build(mat, bevel=0.0, smooth=50)

    rotors = {}
    for name, hp, hz in (("RotorFront", 180, 193), ("RotorRear", 693, 175)):
        hy, hzw = S(hp, hz)
        R = L.Part(name)
        R.cyl((0, 0, 0), 0.32, 0.36, seg=16)                 # hub
        R.cyl((0, 0, 0.26), 0.16, 0.2, seg=10)               # hub cap
        R.cyl((0, 0, -0.35), 0.18, 0.4, seg=10)              # upper mast
        rings_all = []
        for b in range(3):
            a = 2 * PI * b / 3 + (PI / 3 if name == "RotorRear" else 0)
            d = Vector((math.cos(a), math.sin(a), 0))
            p = Vector((-math.sin(a), math.cos(a), 0))
            R.beam(d * 0.25, d * 0.85, 0.2, 0.14)               # blade grip / pitch housing
            rr = []
            for t in np.linspace(0, 1, 6):
                r = 0.8 + t * (9.15 - 0.8)
                chord = 0.64 * (1 - 0.15 * t)
                th = 0.07 * (1 - 0.4 * t)
                tw = math.radians(8 - 12 * t)                      # blade twist
                cz = math.sin(math.radians(2.5)) * r                # coning
                ring = []
                for (u, v) in ((-0.5, 0), (-0.2, 0.5), (0.5, 0.15), (0.5, -0.15), (-0.2, -0.5)):
                    c_ = u * chord; z_ = v * th
                    cc = c_ * math.cos(tw) - z_ * math.sin(tw); zz = c_ * math.sin(tw) + z_ * math.cos(tw)
                    q = d * r + p * cc
                    ring.append((q.x, q.y, cz + zz))
                rr.append(ring)
            rings_all.append(rr)
        hub_obj = R.build(blade_mat, bevel=0.0, smooth=40, location=(0, hy, hzw))
        # blades as a second object joined in, with span-wise UVs (U along chord, V along span)
        import bmesh
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for rr in rings_all:
            V = [[bm.verts.new(c) for c in ring] for ring in rr]
            nr = len(rr[0])
            us = [0.0, 0.25, 0.5, 0.75, 1.0]
            for i in range(len(V) - 1):
                for j in range(nr):
                    f = bm.faces.new((V[i][j], V[i][(j + 1) % nr], V[i + 1][(j + 1) % nr], V[i + 1][j]))
                    for lp in f.loops:
                        ii = i if lp.vert in V[i] else i + 1
                        jj = V[ii].index(lp.vert)
                        uu = us[jj] if not (jj == 0 and lp.vert is V[ii][0] and j == nr - 1) else 1.0
                        lp[uvl].uv = (uu * 0.95 + 0.025, 0.06 + 0.92 * ii / (len(V) - 1))
            bm.faces.new(V[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name + "_blades"); bm.to_mesh(me); bm.free()
        me.materials.append(blade_mat)
        bo = bpy.data.objects.new(name + "_blades", me); bpy.context.scene.collection.objects.link(bo)
        bo.location = hub_obj.location
        # hub UVs: map into the root strip of the blade texture (v < 0.05)
        me_h = hub_obj.data
        if not me_h.uv_layers:
            me_h.uv_layers.new(name="UVMap")
        for d_ in me_h.uv_layers.active.data:
            d_.uv = (0.5, 0.02)
        bpy.ops.object.select_all(action="DESELECT")
        hub_obj.select_set(True); bo.select_set(True); bpy.context.view_layer.objects.active = hub_obj
        bpy.ops.object.join()
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
        rotors[name] = hub_obj
    return body, rotors


def make_blade_texture(path_png):
    """Blade albedo strip sampled along the upper-left blade of the concept overhead view
    (root px ~(352,112) -> tip px ~(220,20)); U = chord, V = span (root at V 0)."""
    from PIL import Image
    ref = L.load_ref(OVER_PNG, erode=1)
    root, tip = np.array([346.0, 106.0]), np.array([222.0, 22.0])
    d = (tip - root) / np.linalg.norm(tip - root); p = np.array([-d[1], d[0]])
    Ht, Wt = 512, 64
    v = (np.arange(Ht) + 0.5) / Ht; u = (np.arange(Wt) + 0.5) / Wt
    V_, U_ = np.meshgrid(v, u, indexing="ij")
    pts = root[None, None] + (tip - root)[None, None] * V_[..., None] + p[None, None] * ((U_ - 0.5) * 26)[..., None]
    col = L.sample(ref, pts[..., 0].ravel(), pts[..., 1].ravel()).reshape(Ht, Wt, 3)
    col[: int(0.05 * Ht)] = np.array([0.07, 0.07, 0.065])        # hub / grips: dark steel
    L.save_png(col, path_png)


def shade_ch47(P, N, refs, depth):
    top, side = refs["top"], refs["side"]
    k = 3.0
    nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]
    c_top = L.sample(top, top_px(P[:, 0]), top_py(P[:, 1]))
    spx = SIDE_CX - P[:, 1] / SS; spy = GROUND_PY - P[:, 2] / SS
    c_side = L.sample(side, spx, spy)
    tol = 0.08
    v_top = L.visible(depth["top"], P, tol + 0.04 * np.sqrt(np.clip(1 - nz ** 2, 0, 1)) / np.maximum(nz, 0.25))
    v_side = np.where(nx < 0, L.visible(depth["left"], P, tol), L.visible(depth["right"], P, tol))
    w_t = np.clip(nz, 0, 1) ** k * v_top
    w_s = np.abs(nx) ** k * v_side
    w_y = np.abs(ny) ** k                                # nose / tail faces: side view colour at that station
    w_b = np.clip(-nz, 0, 1) ** k
    under = side["mean"] * 0.55
    num = c_top * w_t[:, None] + c_side * (w_s + w_y)[:, None] + under * w_b[:, None]
    den = w_t + w_s + w_y + w_b
    num0 = c_top * (np.clip(nz, 0, 1) ** k)[:, None] + c_side * (np.abs(nx) ** k)[:, None]
    den0 = np.clip(nz, 0, 1) ** k + np.abs(nx) ** k
    col = np.where((den > 0.02)[:, None], num / np.maximum(den, 1e-6)[:, None],
                   0.6 * num0 / np.maximum(den0, 1e-6)[:, None])
    col *= (0.94 + 0.1 * L.value_noise(P, 0.8, seed=5))[:, None]
    grime = np.clip((1.2 - P[:, 2]) / 1.2, 0, 1) * 0.25 * L.value_noise(P, 0.5, seed=9)
    col = col * (1 - grime[:, None]) + np.array([0.28, 0.25, 0.19]) * grime[:, None]
    return np.clip(col, 0, 1)


def main():
    out, prev = L.parse_args("ch47")
    L.reset_scene()
    refs = {"side": L.load_ref(SIDE_PNG, erode=2, keep_largest=True),
            "top": L.load_ref(TOP_PNG, erode=2, keep_largest=True)}
    L.gain_to(refs["top"], refs["side"]["mean"], strength=0.85)
    mat = L.image_material("SA_CH47", None, rough=0.7)
    blade_mat = L.image_material("SA_CH47_Blade", None, rough=0.85)
    blade_mat.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.25
    body, rotors = build_ch47(mat, blade_mat)
    L.smart_uv([body], margin=0.003)
    albedo = os.path.join(out, "ch47_albedo.png")
    _, cover = L.texture_atlas([body], refs, shade_ch47, 2048, 1024, 0.5, 0.03,
                               ((-2.5, -8.6, -0.1), (2.5, 8.6, 6.4)), albedo, depth_objs=[body])
    bl = os.path.join(out, "ch47_blade.png")
    make_blade_texture(bl)
    for m, png, nm in ((mat, albedo, "ch47_albedo"), (blade_mat, bl, "ch47_blade")):
        img = L.load_image(png, nm)
        nt = m.node_tree; t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    export = [body, rotors["RotorFront"], rotors["RotorRear"]]
    glb = os.path.join(out, "ch47.glb")
    L.export_glb(export, glb)
    print(f"CH47 tris total {L.tri_count(export)}; atlas coverage {cover:.3f}")
    for o in export:
        print(f"  {o.name:11s} tris {L.tri_count([o]):6d} origin {tuple(round(v, 3) for v in o.location)}")
    bb = np.array([list(o.matrix_world @ Vector(c)) for c in body.bound_box for o in [body]])
    print("CH47 body bounds min", bb.min(0).round(2), "max", bb.max(0).round(2))
    print("CH47 GLB", glb)
    if prev:
        cam, shots = L.preview_set("pilot3d_ch47", prev, 30.0, 18.4, 6.4, rts_dist=46, close_dist=26, close_az=-40)
        # extra: body-only side for direct comparison with the concept side profile
        for o in rotors.values():
            o.hide_render = True
        L.aim(cam, (0, 0, 3.0), -90, 0, 60, ortho=17.5)
        p = os.path.join(prev, "pilot3d_ch47_side_body.png"); L.render(p)
        shots.append((p, "side, rotors hidden"))
        L.contact_sheet(shots, os.path.join(prev, "pilot3d_ch47_sheet.png"), cols=4, cell=(480, 360),
                        title="Steel Accord pilot 3D - CH-47 heavy-lift helicopter - Cycles CPU preview")
        print("CH47 previews in", prev)


if __name__ == "__main__":
    main()
