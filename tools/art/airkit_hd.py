"""Steel Accord - B3 HD kit for the strategic bombers (bpy 5.x).

Shared by air_b52_hd.py, air_b1_hd.py, air_b2_hd.py (the M3 generators air_b*_3d.py and airkit.py are imported
read-only for their measured frames and builders; their outputs are not changed).

What the HD pass adds over the M3 pipeline:
  * fully procedural paint (no concept-image projection): base paint, per-panel tone variation, panel lines and
    rivet rows, control-surface hinge gaps, flow streaks, exhaust soot, leading-edge wear, low-visibility insignia
  * three maps per aircraft: albedo 4096 px (JPEG, AO multiplied in), normal 2048 px (from a procedural height
    field in UV space: panel lines, gaps, rivets), roughness/metal 2048 px (glTF packing G = roughness,
    B = metallic; R = baked AO, not wired to occlusion because AO is already in the albedo)
  * separately exported, pivoted moving parts: bomb-bay doors Door<i>L/R (hinge on the outer edge; open by
    rotating about Godot Z: L negative, R positive), B-1 outer wings WingL/WingR (pivot; sweep about Godot Y)
  * empties Bay<i>a / Bay<i>b (forward / aft end of the stowed-weapon line inside bay i)
  * glass as its own material (SA_Glass) joined into Body

Conventions as airkit: metres; forward = Blender +Y (Godot -Z); up = +Z; aircraft left = -X.
"""
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

import airkit as K  # noqa: E402

L = K.L
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

PI = math.pi


# ============================================================================ geometry helpers
def shell_patch(P, fn, nu, nv, thick, close=True):
    """Thin shell from a parametric surface fn(u, v) -> (point, outward normal), u, v in 0..1.
    Outer sheet at the points, inner sheet `thick` inside, edge walls closing the slab."""
    bm = P.bm
    out = [[None] * (nv + 1) for _ in range(nu + 1)]
    inn = [[None] * (nv + 1) for _ in range(nu + 1)]
    for i in range(nu + 1):
        for j in range(nv + 1):
            p, n = fn(i / nu, j / nv)
            p, n = Vector(p), Vector(n).normalized()
            out[i][j] = bm.verts.new(p)
            inn[i][j] = bm.verts.new(p - n * thick)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((out[i][j], out[i + 1][j], out[i + 1][j + 1], out[i][j + 1]))
            bm.faces.new((inn[i][j + 1], inn[i + 1][j + 1], inn[i + 1][j], inn[i][j]))
    if close:
        for i in range(nu):
            bm.faces.new((out[i + 1][0], out[i][0], inn[i][0], inn[i + 1][0]))
            bm.faces.new((out[i][nv], out[i + 1][nv], inn[i + 1][nv], inn[i][nv]))
        for j in range(nv):
            bm.faces.new((out[0][j], out[0][j + 1], inn[0][j + 1], inn[0][j]))
            bm.faces.new((out[nu][j + 1], out[nu][j], inn[nu][j], inn[nu][j + 1]))


def cut_bay(obj, x_lo, x_hi, y0, y1, z_max, nz_max=-0.3):
    """Delete the down-facing faces of obj whose centroid lies inside the bay footprint.
    Returns the actual hole extents (x_min, x_max, y_min, y_max) taken from the removed faces."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.normal_update()
    kill = [f for f in bm.faces if f.normal.z < nz_max and x_lo < f.calc_center_median().x < x_hi
            and y0 < f.calc_center_median().y < y1 and f.calc_center_median().z < z_max]
    vs = [v.co.copy() for f in kill for v in f.verts]
    bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
    bm.to_mesh(obj.data); bm.free()
    obj.data.update()
    if not vs:
        raise RuntimeError(f"cut_bay removed nothing on {obj.name}")
    return (min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs))


def bay_box(P, x0, x1, y0, y1, zb_fn, z_ceil, ribs=6):
    """Open-bottom bay interior (inward-facing walls + ceiling) with frame ribs. zb_fn(x, y): lower wall edge."""
    bm = P.bm
    ny = 10
    ys = np.linspace(y0, y1, ny + 1)
    # side walls
    for x, flip in ((x0, False), (x1, True)):
        lo = [bm.verts.new((x, y, zb_fn(x, y) - 0.01)) for y in ys]
        hi = [bm.verts.new((x, y, z_ceil)) for y in ys]
        for k in range(ny):
            f = (lo[k], lo[k + 1], hi[k + 1], hi[k])
            bm.faces.new(f[::-1] if flip else f)
    # end walls
    nx = 8
    xs = np.linspace(x0, x1, nx + 1)
    for y, flip in ((y0, True), (y1, False)):
        lo = [bm.verts.new((x, y, zb_fn(x, y) - 0.01)) for x in xs]
        hi = [bm.verts.new((x, y, z_ceil)) for x in xs]
        for k in range(nx):
            f = (lo[k], lo[k + 1], hi[k + 1], hi[k])
            bm.faces.new(f[::-1] if flip else f)
    # ceiling (faces down)
    c = [bm.verts.new(p) for p in ((x0, y0, z_ceil), (x1, y0, z_ceil), (x1, y1, z_ceil), (x0, y1, z_ceil))]
    bm.faces.new(c[::-1])
    # ribs (frames) hanging from the ceiling and a central weapons beam
    for y in np.linspace(y0, y1, ribs + 2)[1:-1]:
        P.box(((x0 + x1) / 2, y, z_ceil - 0.09), (x1 - x0 - 0.02, 0.08, 0.18))
    P.box(((x0 + x1) / 2, (y0 + y1) / 2, z_ceil - 0.16), (0.16, y1 - y0 - 0.1, 0.3))


def build_inward(P, mat, smooth=30):
    """Build a Part keeping the authored winding (no recalc), for inward-facing interiors."""
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(P.name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth))
    return o


def set_origin(obj, pivot):
    """Move the object's origin to `pivot` (world) keeping the geometry in place."""
    pv = Vector(pivot)
    obj.data.transform(__import__("mathutils").Matrix.Translation(-pv))
    obj.location = pv
    return obj


def glass_material():
    m = bpy.data.materials.get("SA_Glass")
    if m is None:
        m = bpy.data.materials.new("SA_Glass")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.03, 0.045, 0.055, 1)
        b.inputs["Roughness"].default_value = 0.08
        b.inputs["Metallic"].default_value = 0.6
    return m


def glass_patch(P, ring_fn, ys, a0, a1, off=0.012, na=8):
    """Window pane on a lofted fuselage: ring_fn(y, angle) -> point on the skin; angles in radians
    (0 = +X, pi/2 = top). Builds a thin slab `off` proud of the skin."""
    def fn(u, v):
        y = ys[0] + (ys[1] - ys[0]) * u
        a = a0 + (a1 - a0) * v
        p = Vector(ring_fn(y, a))
        q = Vector(ring_fn(y, a + 0.01)) - p
        r = Vector(ring_fn(y + 0.01, a)) - p
        n = r.cross(q).normalized()
        if n.dot(p - Vector(ring_fn(y, a + PI))) < 0:
            n = -n
        return p + n * off, n
    shell_patch(P, fn, 3, na, off * 0.8)


class FusFrame:
    """Superellipse fuselage from the M3 measured outlines (side top / bottom lines, top-view half width)."""

    def __init__(self, S, T, top, bot, hw, n):
        self.ztop = K.polyline_fn([S(px, py) for px, py in top])
        self.zbot = K.polyline_fn([S(px, py) for px, py in bot])
        self.hw = K.polyline_fn([(float(T.y(py)), w * T.sx) for py, w in hw])
        self.n = n

    def sec(self, y):
        zt, zb = float(self.ztop(y)), float(self.zbot(y))
        return max(float(self.hw(y)), 0.04), (zt + zb) / 2, max((zt - zb) / 2, 0.04)

    def ring_pt(self, y, a):
        hw, zc, h = self.sec(y)
        c, s = math.cos(a), math.sin(a)
        n = self.n
        return (hw * math.copysign(abs(c) ** (2 / n), c), y, zc + h * math.copysign(abs(s) ** (2 / n), s))

    def bottom_z(self, x, y):
        hw, zc, h = self.sec(y)
        q = min(abs(x) / hw, 0.999)
        return zc - h * (1 - q ** self.n) ** (1 / self.n)

    def angle(self, P):
        hw = self.hw(P[:, 1]); zt = self.ztop(P[:, 1]); zb = self.zbot(P[:, 1])
        zc = (zt + zb) / 2; h = np.maximum((zt - zb) / 2, 0.05)
        return np.arctan2((P[:, 2] - zc) / h, P[:, 0] / np.maximum(hw, 0.05)), (hw + h) / 2


def bottom_fn(obj):
    """z of the lowest surface of obj above (x, y) (ray cast up from below); for doors on non-lofted bellies."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, dg)

    def fz(x, y):
        hit = tree.ray_cast(Vector((x, y, -50.0)), Vector((0, 0, 1)))
        return hit[0].z if hit[0] is not None else 0.0
    return fz


def top_fn(obj):
    """z of the highest surface of obj below (x, y) (ray cast down from above)."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())

    def fz(x, y):
        hit = tree.ray_cast(Vector((x, y, 50.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else 0.0
    return fz


def rect_outline(x, y, x0, x1, y0, y1, w=0.03):
    inside = (x > x0 - w) & (x < x1 + w) & (y > y0 - w) & (y < y1 + w)
    d = np.minimum(np.minimum(np.abs(x - x0), np.abs(x - x1)), np.minimum(np.abs(y - y0), np.abs(y - y1)))
    return np.where(inside, groove(d, w), 0.0)


def door_pair(mat, bay_idx, hole, z_fn, nu=10, nv=6, inner_x=None):
    """Two clamshell doors closing a bay hole (x0, x1, y0, y1); hinges on the outer edges, meeting at inner_x
    (default: the hole centre). Returns {name: obj} with origins on the hinge lines."""
    bx0, bx1, by0, by1 = hole
    xm = (bx0 + bx1) / 2 if inner_x is None else inner_x
    out = {}
    for side, xh in (("L", bx0), ("R", bx1)):
        Dp = K.Part(f"Door{bay_idx}{side}")

        def fn(u, v, xh=xh):
            y = by0 + (by1 - by0) * u
            x = xh + (xm - xh) * v
            return (x, y, z_fn(x, y) - 0.012), (0, 0, -1)
        shell_patch(Dp, fn, nu, nv, 0.04)
        d = Dp.build(mat, smooth=40)
        ym = (by0 + by1) / 2
        set_origin(d, (xh, ym, z_fn(xh, ym)))
        out[f"Door{bay_idx}{side}"] = d
    return out


# ============================================================================ paint helpers (numpy, vectorised)
def line_dist(c, spacing, offset=0.0):
    q = (c - offset) / spacing
    return np.abs(q - np.round(q)) * spacing


def stations_dist(c, st):
    st = np.sort(np.asarray(st, float))
    i = np.clip(np.searchsorted(st, c), 1, len(st) - 1)
    return np.minimum(np.abs(c - st[i - 1]), np.abs(c - st[i]))


def groove(d, w=0.024):
    return np.clip(1.0 - d / w, 0.0, 1.0) ** 1.5


def rivets(d_line, along, pitch=0.18, off=0.06, r=0.016):
    """Rivet bumps on both sides of a line; d_line = distance to the line, along = coordinate along it."""
    a = line_dist(along, pitch)
    dd = np.sqrt((np.abs(d_line) - off) ** 2 + a ** 2)
    return np.clip(1.0 - dd / r, 0.0, 1.0)


def hash01(*ints):
    h = np.zeros_like(ints[0], dtype=np.int64)
    for k, a in enumerate(ints):
        h = h * 73856093 ^ (a.astype(np.int64) * (19349663 + 7919 * k))
    h = (h ^ (h >> 13)) * 1274126177
    return ((h >> 8) & 0xFFFF).astype(np.float64) / 65535.0


def aniso_noise(P, scale_xyz, seed=0):
    return L.value_noise(P / np.asarray(scale_xyz, float), 1.0, seed=seed)


def star_mask(u, v, R):
    """Five-point star of outer radius R centred at 0 (point up)."""
    r = np.sqrt(u ** 2 + v ** 2)
    a = np.arctan2(u, v)                                  # 0 = up
    k = (a % (2 * PI / 5)) / (2 * PI / 5)                 # 0..1 between two tips
    tri = np.abs(k - 0.5) * 2                             # 1 at a tip, 0 between
    rin = R * 0.382
    bound = rin + (R - rin) * tri ** 1.6
    return r < bound


def insignia(P, N, centre, nrm, up, R, depth_tol=0.8):
    """Low-visibility star-and-bar: returns (outline_mask) where the dark mark is painted.
    centre: point on the skin, nrm: facing direction, up: decal up vector."""
    c, n, upv = np.asarray(centre, float), np.asarray(nrm, float), np.asarray(up, float)
    n = n / np.linalg.norm(n)
    upv = upv - n * upv.dot(n); upv /= np.linalg.norm(upv)
    rt = np.cross(upv, n)
    d = P - c
    u, v = d @ rt, d @ upv
    face = (N @ n > 0.45) & (np.abs(d @ n) < depth_tol)
    disc = np.sqrt(u ** 2 + v ** 2)
    ring = (disc < R) & (disc > R * 0.9)
    star = star_mask(u, v, R * 0.93)
    star_in = star_mask(u, v, R * 0.80)
    bars = (np.abs(v + R * 0.08) < R * 0.33) & (np.abs(u) > R * 0.98) & (np.abs(u) < R * 2.0)
    bars_in = (np.abs(v + R * 0.08) < R * 0.24) & (np.abs(u) > R * 1.07) & (np.abs(u) < R * 1.91)
    mark = (ring | (star & ~star_in) | (bars & ~bars_in))
    return face & mark


# ============================================================================ baking
def _area_down(a, f):
    H, W = a.shape[:2]
    return a.reshape(H // f, f, W // f, f, *a.shape[2:]).mean(axis=(1, 3))


def uv_unwrap(objs, margin=0.0015):
    """Smart UV project, then a concave-shape island pack for better atlas coverage."""
    L.smart_uv(objs, margin=margin, angle=60)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(rotate=True, margin=margin, shape_method="CONCAVE")
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def texel_size(objs, size):
    P, Nn, U, I = L.world_tris(objs, with_uv=True)
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    e1, e2 = U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]
    a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    return float(np.sqrt(a3.sum() / max(a2.sum(), 1e-9))) / size


def uv_raster_ids(U, size):
    """Compact UV rasteriser: per texel the triangle index (-1 = empty) and two barycentric weights (float32).
    Image order row 0 = v 0. ~12 bytes per texel instead of the 28 of a position + normal raster."""
    tid = np.full((size, size), -1, np.int32)
    w0m = np.zeros((size, size), np.float32); w1m = np.zeros((size, size), np.float32)
    UV = U * size
    for t in range(len(UV)):
        r = L._tri_pixels(UV[t, 0], UV[t, 1], UV[t, 2], size, size)
        if r is None:
            continue
        ys, xs, w0, w1, _ = r
        tid[ys, xs] = t; w0m[ys, xs] = w0; w1m[ys, xs] = w1
    return tid, w0m, w1m


def pad_islands(arr, mask, iters=12):
    """Grow texel values outward from the UV islands by `iters` pixels (neighbour average); the rest gets the mean."""
    m = mask.astype(np.float32)
    chans = arr[..., None] if arr.ndim == 2 else arr
    for _ in range(iters):
        cnt = ndimage.uniform_filter(m, 3, mode="nearest")
        grow = (cnt > 0) & (m == 0)
        if not grow.any():
            break
        for c in range(chans.shape[-1]):
            acc = ndimage.uniform_filter(chans[..., c] * m, 3, mode="nearest")
            chans[..., c][grow] = acc[grow] / cnt[grow]
        m[grow] = 1.0
    rest = m == 0
    for c in range(chans.shape[-1]):
        chans[..., c][rest] = float(chans[..., c][mask].mean()) if mask.any() else 0.5
    return arr


def bake_maps(objs, paint, out_dir, aid, size=4096, aux=2048, ao_size=2048, ao_samples=12, ao_dist=1.6,
              ao_strength=0.55, normal_strength=1.0, chunk=1_000_000):
    """paint(P, N, O) -> dict(col (n,3) 0..1, rough (n), metal (n), height (n) in mm, negative = groove).
    Returns (albedo_path, normal_path, orm_path, info). Memory-lean: AO first, compact raster, bounded padding."""
    ao_lo = None
    if ao_strength > 0:
        ao_lo = (np.clip(L.bake_ao(objs, ao_size, samples=ao_samples, distance=ao_dist), 0, 1) * 255).astype(np.uint8)
    P, Nn, U, I = L.world_tris(objs, with_uv=True)
    P = P.astype(np.float32); Nn = Nn.astype(np.float32); I = I.astype(np.int32)
    ts = texel_size(objs, size)
    tid, w0m, w1m = uv_raster_ids(U, size)
    del U
    msk = tid >= 0
    idx = np.flatnonzero(msk.ravel())
    col = np.zeros((size * size, 3), np.float32)
    rough = np.full(size * size, 0.6, np.float32)
    metal = np.zeros(size * size, np.float32)
    hgt = np.zeros(size * size, np.float32)
    tf, w0f, w1f = tid.ravel(), w0m.ravel(), w1m.ravel()
    for s in range(0, len(idx), chunk):
        ii = idx[s:s + chunk]
        t = tf[ii]
        a0 = w0f[ii][:, None].astype(np.float64); a1 = w1f[ii][:, None].astype(np.float64)
        Pc = a0 * P[t, 0] + a1 * P[t, 1] + (1.0 - a0 - a1) * P[t, 2]
        r = paint(Pc, Nn[t].astype(np.float64), I[t])
        col[ii] = r["col"]; rough[ii] = r["rough"]; metal[ii] = r["metal"]; hgt[ii] = r["height"]
        del Pc, r
    del tid, w0m, w1m, tf, w0f, w1f, P, Nn, I
    col *= (1.0 - 0.32 * np.clip(-hgt / 2.0, 0, 1))[:, None]      # dirt settles in panel lines and gaps
    col *= (1.0 + 0.05 * np.clip(hgt / 0.3, 0, 1))[:, None]        # rivet heads catch a little light
    col = col.reshape(size, size, 3); rough = rough.reshape(size, size)
    metal = metal.reshape(size, size); hgt = hgt.reshape(size, size)
    if ao_lo is not None:
        ao = np.asarray(Image.fromarray(ao_lo).resize((size, size), Image.BILINEAR), np.float32) / 255.0
        col *= (1 - ao_strength + ao_strength * ao)[..., None]
        del ao
    os.makedirs(out_dir, exist_ok=True)
    pa = os.path.join(out_dir, f"{aid}_albedo.jpg")
    pn = os.path.join(out_dir, f"{aid}_normal.png")
    po = os.path.join(out_dir, f"{aid}_orm.png")
    pad_islands(col, msk)
    Image.fromarray(np.clip(col[::-1] * 255 + 0.5, 0, 255).astype(np.uint8), "RGB").save(pa, quality=92)
    del col
    f = size // aux
    pad_islands(rough, msk); pad_islands(metal, msk); pad_islands(hgt, msk)
    ao_aux = (np.asarray(Image.fromarray(ao_lo).resize((size // f, size // f), Image.BILINEAR), np.float32) / 255.0
              if ao_lo is not None else np.ones((size // f, size // f), np.float32))
    orm = np.stack([ao_aux, _area_down(rough, f), _area_down(metal, f)], -1)
    del rough, metal
    Image.fromarray(np.clip(orm[::-1] * 255 + 0.5, 0, 255).astype(np.uint8), "RGB").save(po, optimize=True)
    # normal map from the height field (mm) in UV space; tangent = +u, bitangent = +v (OpenGL / glTF)
    h_m = ndimage.gaussian_filter(hgt, 0.6) * np.float32(0.001 / ts)
    del hgt
    k = np.float32(14.0 * normal_strength)          # exaggeration: mm-scale grooves read at game distances
    gy, gx = np.gradient(h_m)
    del h_m
    gx *= -k; gy *= -k
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nrm = np.stack([_area_down(gx * inv, f), _area_down(gy * inv, f), _area_down(inv, f)], -1)
    del gx, gy, inv
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Image.fromarray(np.clip((nrm[::-1] * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8), "RGB").save(pn, optimize=True)
    info = {"texel_m": ts, "coverage": float(msk.mean())}
    return pa, pn, po, info


def hd_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m


def attach_maps(mat, pa, pn, po, aid):
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = L.load_image(pa, f"{aid}_albedo")
    nt.links.new(ta.outputs["Color"], b.inputs["Base Color"])
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = L.load_image(pn, f"{aid}_normal")
    tn.image.colorspace_settings.name = "Non-Color"
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    to = nt.nodes.new("ShaderNodeTexImage"); to.image = L.load_image(po, f"{aid}_orm")
    to.image.colorspace_settings.name = "Non-Color"
    sp = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs["Color"], sp.inputs["Color"])
    nt.links.new(sp.outputs["Green"], b.inputs["Roughness"])
    nt.links.new(sp.outputs["Blue"], b.inputs["Metallic"])


def export_glb(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = [o for o in objs if o.type == "MESH"][0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_image_format="AUTO")


# ============================================================================ review renders
def art_sheet(aid, title, views, out_png, res=(960, 540), samples=14, pose=None, length=40.0):
    """views: [(label, az, el, target, dist, lens, pose_name)]. pose(name) sets moving parts before a render.
    Grey-blue sky backdrop with a sun; no ground (aircraft in flight). Writes one contact sheet (2 columns)."""
    cam = L.setup_preview_scene(ground=False)
    sc = bpy.context.scene
    sc.cycles.samples = samples
    w = sc.world
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.5, 0.6, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    tmp = tempfile.mkdtemp(prefix=f"hd_{aid}_")
    shots = []
    for i, (lab, az, el, tgt, dist, lens, pname) in enumerate(views):
        if pose:
            pose(pname)
        L.aim(cam, tgt, az, el, dist, lens=lens)
        cam.data.clip_end = 2000; cam.data.clip_start = 0.05
        p = os.path.join(tmp, f"v{i}.png")
        L.render(p, res)
        shots.append((p, lab))
    L.contact_sheet(shots, out_png, cols=2, cell=res, title=title)
    for p, _ in shots:
        os.remove(p)
    os.rmdir(tmp)
    return out_png


def report(export):
    lines = [f"tris total {L.tri_count([o for o in export if o.type == 'MESH'])}"]
    for o in export:
        if o.type == "MESH":
            lines.append(f"  {o.name:12s} tris {L.tri_count([o]):7d} origin {tuple(round(v, 3) for v in o.location)}")
        else:
            lines.append(f"  {o.name:12s} empty        origin {tuple(round(v, 3) for v in o.location)}")
    return "\n".join(lines)
