"""Steel Accord - pilot 3D model: M88-style recovery vehicle ("Dozer" builder), bpy 5.x.

Run:  python3 tools/art/veh_m88_3d.py <out_dir> [--previews <dir>] [--no-previews]
      default previews dir: <repo>/docs/screens
Out:  <out_dir>/m88.glb  (+ m88_albedo.png, m88_track.png as inspectable copies; both are embedded in the GLB)

Method (deterministic, regenerated from the concept art every run):
  * Geometry: primitives / extruded profiles whose coordinates are measured in pixels on the
    concept side view (nose left) and top view (nose up) and converted to metres with one
    uniform scale per view (overall length 8.3 m).
  * UVs: one Smart-UV atlas for every non-track object (Hull, wheels, sprocket, idler, MG).
  * Texture: for every atlas texel we know the world position + face normal (UV-space
    rasteriser below). Its colour is a normal-weighted blend of projections of the concept views:
    top view onto up-facing texels, side view onto +-X facing texels (same image both sides ->
    correctly mirrored), front-3/4 and rear-3/4 views rectified with per-plane homographies onto
    front / rear facing texels. Each projection is depth-tested against an orthographic depth map
    of the model so that occluded faces (under the crane boom, under fenders...) do not receive a
    copy of what is above them. Cycles-baked AO and a light procedural grime pass are multiplied in.
  * Tracks: separate ribbons TrackL/TrackR, material SA_TrackScroll, V runs along the belt.

The library half of this file (everything above `main()`) is imported by air_ch47_3d.py.
Forward = Blender +Y (= Godot -Z). Units: metres. Origin: ground contact under vehicle centre.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Euler, Vector
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

PI = math.pi
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


# ============================================================================ generic helpers
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def parse_args(default_name):
    argv = sys.argv[1:]
    out = "."
    prev = os.path.join(REPO, "docs", "screens")
    do_prev = True
    i = 0
    pos = []
    while i < len(argv):
        a = argv[i]
        if a == "--previews":
            prev = argv[i + 1]; i += 2; continue
        if a == "--no-previews":
            do_prev = False; i += 1; continue
        pos.append(a); i += 1
    if pos:
        out = pos[0]
    os.makedirs(out, exist_ok=True)
    if do_prev:
        os.makedirs(prev, exist_ok=True)
    return out, (prev if do_prev else None)


class Part:
    """Accumulates primitives into one bmesh, then builds one (optionally bevelled) object."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()

    def _add_cube(self, M):
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)

    def box(self, c, size, rot=(0, 0, 0)):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
        self._add_cube(M)

    def beam(self, p0, p1, w, h, up=(0, 0, 1)):
        """Box from p0 to p1 with cross-section w (local x) by h (local z)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        yax = d.normalized()
        xax = yax.cross(Vector(up)).normalized()
        zax = xax.cross(yax)
        R = Matrix((xax, yax, zax)).transposed().to_4x4()
        M = Matrix.Translation((p0 + p1) / 2) @ R @ Matrix.Diagonal((w, L, h, 1))
        self._add_cube(M)

    def cyl(self, c, r, depth, rot=(0, 0, 0), seg=16, r2=None):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=depth, matrix=M)

    def rod(self, p0, p1, r, seg=8):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        M = Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                              radius2=r, depth=d.length, matrix=M)

    def side(self, pts_yz, x0, x1, inset_top=0.0, z_split=None):
        """Extrude a (y,z) profile across x0..x1."""
        bm = self.bm
        A = [bm.verts.new((x0, y, z)) for y, z in pts_yz]
        B = [bm.verts.new((x1, y, z)) for y, z in pts_yz]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def plan(self, pts_xy, z0, z1, top=1.0):
        """Extrude an (x,y) outline from z0 to z1, scaling the top outline by `top` about its centre."""
        bm = self.bm
        cx = sum(p[0] for p in pts_xy) / len(pts_xy); cy = sum(p[1] for p in pts_xy) / len(pts_xy)
        A = [bm.verts.new((x, y, z0)) for x, y in pts_xy]
        B = [bm.verts.new((cx + (x - cx) * top, cy + (y - cy) * top, z1)) for x, y in pts_xy]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def rings(self, rings, caps=True):
        """Loft a list of equal-length closed vertex rings."""
        bm = self.bm
        R = [[bm.verts.new(p) for p in ring] for ring in rings]
        n = len(R[0])
        for a, b in zip(R[:-1], R[1:]):
            for i in range(n):
                bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
        if caps:
            bm.faces.new(R[0][::-1]); bm.faces.new(R[-1])

    def build(self, mat=None, bevel=0.0, angle=35, smooth=33, location=None):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(o)
        if mat is not None:
            me.materials.append(mat)
        if bevel:
            b = o.modifiers.new("bv", "BEVEL")
            b.width = bevel; b.segments = 1; b.limit_method = "ANGLE"; b.angle_limit = math.radians(angle)
            b.use_clamp_overlap = True
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = o; o.select_set(True)
            bpy.ops.object.modifier_apply(modifier=b.name)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth))
        if location is not None:  # geometry was authored around the origin -> place the pivot
            o.location = location
        return o


def mirror_copy_x(src, name):
    """Copy an object mirrored across the world YZ plane (mesh data mirrored, UVs kept)."""
    bm = bmesh.new(); bm.from_mesh(src.data)
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces, flip_multires=False)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in src.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = (-src.location.x, src.location.y, src.location.z)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(33))
    return o


def tri_count(objs):
    n = 0
    for o in objs:
        o.data.calc_loop_triangles()
        n += len(o.data.loop_triangles)
    return n


def smart_uv(objs, margin=0.004, angle=66):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def world_tris(objs, with_uv=False):
    """Return world-space triangle verts (N,3,3), face normals (N,3), uvs (N,3,2), object index (N,)."""
    P, Nn, U, I = [], [], [], []
    for k, o in enumerate(objs):
        me = o.data
        me.calc_loop_triangles()
        mw = np.array(o.matrix_world)
        nm = np.array(o.matrix_world.to_3x3().inverted().transposed())
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        nt = len(me.loop_triangles)
        vi = np.empty(nt * 3, dtype=np.int64); me.loop_triangles.foreach_get("vertices", vi); vi = vi.reshape(-1, 3)
        P.append(co[vi])
        fn = np.empty(nt * 3); me.loop_triangles.foreach_get("normal", fn); fn = fn.reshape(-1, 3) @ nm.T
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
        Nn.append(fn)
        if with_uv:
            li = np.empty(nt * 3, dtype=np.int64); me.loop_triangles.foreach_get("loops", li)
            uv = np.empty(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uv)
            U.append(uv.reshape(-1, 2)[li].reshape(-1, 3, 2))
        I.append(np.full(nt, k))
    out = [np.concatenate(P), np.concatenate(Nn)]
    out.append(np.concatenate(U) if with_uv else None)
    out.append(np.concatenate(I))
    return out


def _tri_pixels(a, b, c, W, H):
    """Pixel centres inside a 2D triangle (pixel units). Returns ys, xs, w0, w1, w2 or None."""
    x0 = max(int(math.floor(min(a[0], b[0], c[0]))), 0); x1 = min(int(math.ceil(max(a[0], b[0], c[0]))), W - 1)
    y0 = max(int(math.floor(min(a[1], b[1], c[1]))), 0); y1 = min(int(math.ceil(max(a[1], b[1], c[1]))), H - 1)
    if x1 < x0 or y1 < y0:
        return None
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(den) < 1e-12:
        return None
    ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    px = xs + 0.5; py = ys + 0.5
    w0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / den
    w1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / den
    w2 = 1 - w0 - w1
    m = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
    if not m.any():
        return None
    return ys[m], xs[m], w0[m], w1[m], w2[m]


def depth_map(P, axes, depth_axis, lo, hi, cell, mode):
    """Orthographic z-buffer of world triangles P (N,3,3).
    axes = (i, j) world axes mapped to image (x, y); returns grid (H,W) of max (mode=+1) or min (-1)
    world coordinate along depth_axis; empty = -inf (max) / +inf (min) in the signed domain."""
    i, j = axes
    W = int(math.ceil((hi[0] - lo[0]) / cell)); H = int(math.ceil((hi[1] - lo[1]) / cell))
    D = np.full((H, W), -np.inf)
    T2 = np.stack([(P[..., i] - lo[0]) / cell, (P[..., j] - lo[1]) / cell], -1)
    Z = P[..., depth_axis] * mode
    for t in range(len(P)):
        r = _tri_pixels(T2[t, 0], T2[t, 1], T2[t, 2], W, H)
        if r is None:
            continue
        ys, xs, w0, w1, w2 = r
        z = w0 * Z[t, 0] + w1 * Z[t, 1] + w2 * Z[t, 2]
        D[ys, xs] = np.maximum(D[ys, xs], z)
    return {"D": D, "lo": lo, "cell": cell, "axes": axes, "ax": depth_axis, "mode": mode}


def depth_lookup(dm, Pw):
    """Signed depth (mode * coord) of the front-most surface at the texels' projected position.
    Uses the max over a 3x3 neighbourhood to be tolerant to rasterisation gaps."""
    D = ndimage.maximum_filter(dm["D"], size=3) if "Dm" not in dm else dm["Dm"]
    dm["Dm"] = D
    i, j = dm["axes"]
    x = ((Pw[:, i] - dm["lo"][0]) / dm["cell"]).astype(int)
    y = ((Pw[:, j] - dm["lo"][1]) / dm["cell"]).astype(int)
    H, W = D.shape
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    out = np.full(len(Pw), -np.inf)
    out[ok] = D[y[ok], x[ok]]
    return out


def visible(dm, Pw, tol):
    return Pw[:, dm["ax"]] * dm["mode"] >= depth_lookup(dm, Pw) - tol


def uv_raster(P, Nn, U, I, size):
    """Rasterise triangles in UV space. Returns per-texel world pos, normal, object idx, mask.
    Arrays are in Blender image order (row 0 = v 0)."""
    S = size
    pos = np.zeros((S, S, 3), np.float32); nor = np.zeros((S, S, 3), np.float32)
    oid = np.full((S, S), -1, np.int32); msk = np.zeros((S, S), bool)
    UV = U * S
    for t in range(len(P)):
        r = _tri_pixels(UV[t, 0], UV[t, 1], UV[t, 2], S, S)
        if r is None:
            continue
        ys, xs, w0, w1, w2 = r
        pos[ys, xs] = (w0[:, None] * P[t, 0] + w1[:, None] * P[t, 1] + w2[:, None] * P[t, 2])
        nor[ys, xs] = Nn[t]
        oid[ys, xs] = I[t]
        msk[ys, xs] = True
    return pos, nor, oid, msk


def fill_nearest(img, mask):
    """Extend valid texels/pixels into invalid ones (padding / edge extension)."""
    if mask.all():
        return img
    _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
    return img[iy, ix]


# ---------------------------------------------------------------------------- reference images
def load_ref(path, erode=2, keep_largest=False, crop=None):
    """Load an RGBA concept image as float RGB in 0..1 with transparent areas edge-extended.
    Returns dict(rgb, a, mean)."""
    im = Image.open(path).convert("RGBA")
    if crop:
        im = im.crop(crop)
    a = np.asarray(im, dtype=np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3]
    m = al > 0.5
    if keep_largest:
        lab, n = ndimage.label(m)
        if n > 1:
            sizes = ndimage.sum(m, lab, range(1, n + 1))
            m = lab == (1 + int(np.argmax(sizes)))
    if erode:
        m = ndimage.binary_erosion(m, iterations=erode)
    rgb = fill_nearest(rgb, m)
    return {"rgb": rgb, "a": m, "mean": rgb[m].mean(0), "path": path}


def gain_to(ref, target_mean, strength=1.0):
    g = (target_mean / np.maximum(ref["mean"], 1e-4)) ** strength
    ref["rgb"] = np.clip(ref["rgb"] * g, 0, 1)
    ref["mean"] = ref["mean"] * g
    return ref


def sample(ref, px, py):
    """Bilinear sample at float pixel coords (pixel centres at i+0.5), clamped."""
    img = ref["rgb"]
    H, W = img.shape[:2]
    x = np.clip(px - 0.5, 0, W - 1.001); y = np.clip(py - 0.5, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    c = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
         + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
    return c


def homography(src, dst):
    """3x3 H with dst ~ H @ src for 4 point pairs."""
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, Vt = np.linalg.svd(np.array(A, float))
    return Vt[-1].reshape(3, 3) / Vt[-1, -1]


def apply_h(Hm, x, y):
    w = Hm[2, 0] * x + Hm[2, 1] * y + Hm[2, 2]
    return (Hm[0, 0] * x + Hm[0, 1] * y + Hm[0, 2]) / w, (Hm[1, 0] * x + Hm[1, 1] * y + Hm[1, 2]) / w


def value_noise(P, scale, seed=0):
    """Deterministic smooth-ish 3D noise in 0..1 from summed sines (no RNG state)."""
    rng = np.random.RandomState(seed)
    acc = np.zeros(len(P))
    for k in range(6):
        d = rng.normal(size=3); d /= np.linalg.norm(d)
        f = (1.7 ** k) / scale
        acc += np.sin(P @ d * f * 2 * PI + rng.uniform(0, 2 * PI)) / (1.4 ** k)
    acc = (acc - acc.min()) / max(acc.max() - acc.min(), 1e-6)
    return acc


# ---------------------------------------------------------------------------- materials / baking
def image_material(name, img, rough=0.75, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if img is not None:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        nt.nodes.active = t
    return m


def bake_ao(objs, size, samples=16, distance=1.0):
    """Cycles AO bake of `objs` (sharing one atlas material) -> float array (size,size) row0 = v0."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = samples
    try:
        sc.world.light_settings.distance = distance
    except Exception:
        pass
    img = bpy.data.images.new("ao_bake", size, size, alpha=False, float_buffer=False)
    mats = {m for o in objs for m in o.data.materials}
    tmp = []
    for m in mats:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img
        m.node_tree.nodes.active = n; tmp.append((m, n))
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type="AO", margin=8)
    a = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a)
    for m, n in tmp:
        m.node_tree.nodes.remove(n)
    bpy.data.images.remove(img)
    return a.reshape(size, size, 4)[..., 0]


def save_png(arr_v0, path):
    """Save float RGB array in Blender order (row0 = v0) as an sRGB PNG (top row = v1)."""
    a = np.clip(arr_v0[::-1] * 255 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGB").save(path)


def load_image(path, name):
    img = bpy.data.images.load(path)
    img.name = name
    img.pack()
    return img


def export_glb(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True)


# ---------------------------------------------------------------------------- previews
def setup_preview_scene(ground=True, ground_col=(0.30, 0.29, 0.26), size=60):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"     # albedo shown as authored (close to Godot's linear tonemap)
    sc.view_settings.look = "None"
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.6, 0.68, 1); bg.inputs[1].default_value = 0.55
    sun = bpy.data.objects.new("PrevSun", bpy.data.lights.new("PrevSun", "SUN"))
    sun.data.energy = 3.2; sun.data.angle = math.radians(4)
    sun.rotation_euler = Euler((math.radians(42), 0, math.radians(-35)))
    sc.collection.objects.link(sun)
    extra = [sun]
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
        g = bpy.context.active_object; g.name = "PrevGround"
        gm = bpy.data.materials.new("PrevGround"); gm.use_nodes = True
        gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*ground_col, 1)
        gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
        g.data.materials.append(gm)
        extra.append(g)
    cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_end = 500
    extra.append(cam)
    return cam


def aim(cam, target, az_deg, el_deg, dist, ortho=None, lens=50, roll_up=None):
    """Place camera: azimuth measured from +Y (front) towards +X (right), elevation above horizon."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = Vector(target) + d * dist
    look = (Vector(target) - cam.location).normalized()
    up = Vector((0, 0, 1)) if roll_up is None else Vector(roll_up)
    if abs(look.dot(up)) > 0.999:
        up = Vector((0, 1, 0))
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    if roll_up is not None or abs(look.z) > 0.999:
        # build explicit basis: camera -Z = look, camera Y = projected up
        z = -look
        y = (up - z * up.dot(z)).normalized()
        x = y.cross(z)
        cam.rotation_euler = Matrix((x, y, z)).transposed().to_euler()
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens


def render(path, res=(800, 600)):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def contact_sheet(paths_labels, out, cols=3, cell=(560, 420), title=""):
    rows = (len(paths_labels) + cols - 1) // cols
    top = 36 if title else 0
    sheet = Image.new("RGB", (cols * cell[0], rows * cell[1] + top), (24, 26, 28))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    if title:
        d.text((10, 8), title, fill=(230, 230, 230), font=font)
    for k, (p, lab) in enumerate(paths_labels):
        im = Image.open(p).convert("RGB")
        im.thumbnail(cell)
        x = (k % cols) * cell[0] + (cell[0] - im.width) // 2
        y = top + (k // cols) * cell[1] + (cell[1] - im.height) // 2
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 8 + 11 * len(lab), y + 26], fill=(0, 0, 0))
        d.text((x + 5, y + 3), lab, fill=(255, 255, 255), font=font)
    sheet.save(out)


# ============================================================================ M88 model
# Reference measurement frames (pixels measured on the normalised concept cut-outs).
SS = 8.3 / 816.0     # side view: blade tip px 12 .. hull rear px 828  -> 8.3 m
ST = 8.3 / 760.0     # top view : blade tip py 15 .. hull rear py 775  -> 8.3 m


def S(px, py):
    """side-view pixel -> (y, z) metres (nose left, ground at py 390)."""
    return ((420.0 - px) * SS, (390.0 - py) * SS)


def T(px, py):
    """top-view pixel -> (x, y) metres (nose up, centre-line px 191.5)."""
    return ((px - 191.5) * ST, (395.0 - py) * ST)


TRACK_X = 1.62        # track centre-line |x|
TRACK_W = 0.56
TRACK_T = 0.12        # belt thickness
WHEEL_R = 0.376
WHEEL_Z = TRACK_T + WHEEL_R
WHEEL_Y = [S(px, 0)[0] for px in (222, 312, 405, 495, 586, 677)]
IDLER = (S(146, 0)[0], 0.80, 0.33)
SPROCKET = (S(768, 0)[0], 0.80, 0.355)
ROLLERS = [(S(px, 0)[0], 1.06, 0.15) for px in (250, 445, 573)]
TRACK_PITCH = 0.16    # nominal link pitch; exact value is adjusted so the loop holds an integer number of tiles
LINKS_PER_TILE = 6


def build_m88(mat):
    objs = {}
    H = Part("Hull")
    # --- base hull (over the tracks, sponson width) : side profile from the concept side view
    base = [S(116, 256), S(150, 249), S(180, 166), S(236, 166), S(236, 180), S(824, 180), S(826, 256)]
    H.side(base, -1.62, 1.62)
    # --- casemate (crew compartment) with sloped front, slightly narrower
    case = [S(234, 180), S(236, 166), S(250, 142), S(466, 142), S(470, 180)]
    H.side(case, -1.52, 1.52)
    # --- lower hull between the tracks
    low = [S(112, 256), S(826, 256), S(826, 300), S(800, 346), S(170, 346)]
    H.side(low, -1.30, 1.30)
    # --- rear fender lips that curve down behind the sprocket (side view px 805..828, 255..290)
    for s in (-1, 1):
        y0, z0 = S(826, 256); y1, z1 = S(836, 292)
        H.beam((s * TRACK_X, y0 + 0.05, z0 - 0.02), (s * TRACK_X, y1, z1), TRACK_W + 0.04, 0.03, up=(0, 1, 0))
        # front mudguard over the idler
        H.beam((s * TRACK_X, S(150, 0)[0], 1.36), (s * TRACK_X, S(118, 0)[0], 1.22), TRACK_W + 0.04, 0.03, up=(0, 1, 0))
    # --- dozer blade (curved mouldboard profile from side view), width from top view px 15..370
    blade = [S(30, 281), S(90, 241), S(98, 251), S(44, 292), S(40, 330), S(55, 362), S(12, 366), S(20, 330)]
    H.side(blade, T(15, 0)[0], T(368, 0)[0])
    # blade push arms (along the hull sides, pivot near the idler) and hydraulic rams
    for s in (-1, 1):
        H.beam((s * 1.18, S(92, 0)[0], 0.75), (s * 1.18, S(160, 0)[0], 0.85), 0.16, 0.22)
        H.rod((s * 1.18, S(80, 0)[0], 1.42), (s * 1.18, S(205, 0)[0], 2.28), 0.075, seg=10)
        H.rod((s * 1.18, S(80, 0)[0], 1.42), (s * 1.18, S(140, 0)[0], 1.86), 0.11, seg=10)
    # --- front winch drum between the rams + its cheek plates
    yw = S(165, 0)[0]
    H.cyl((0.05, yw, 2.0), 0.21, 1.15, (0, PI / 2, 0), seg=18)
    for x in (-0.6, 0.7):
        H.box((x, yw, 1.95), (0.08, 0.5, 0.55))
    # headlight clusters on the front corners
    for s in (-1, 1):
        H.cyl((s * 1.42, S(180, 0)[0] + 0.12, 2.05), 0.1, 0.16, (PI / 2, 0, 0), seg=12)
        H.box((s * 1.42, S(180, 0)[0] + 0.02, 2.05), (0.26, 0.12, 0.26))
    # --- commander's cupola (top view left hatch at px 125,305) and right hatch (px 300,380)
    cx, cy = T(125, 305)
    H.cyl((cx, cy, 2.62), 0.44, 0.2, seg=20)
    H.cyl((cx, cy, 2.75), 0.36, 0.08, seg=20)
    hx, hy = T(292, 380)
    H.cyl((hx, hy, 2.55), 0.4, 0.06, seg=20)
    H.cyl((min(T(345, 410)[0], 1.2), T(345, 410)[1], 2.55), 0.28, 0.05, seg=16)
    # --- rear deck equipment (positions from the top view, heights from side view)
    for (a, b, c, d, z1) in [(60, 455, 125, 530, 2.46), (270, 475, 338, 545, 2.5), (275, 625, 340, 700, 2.4),
                             (55, 560, 120, 640, 2.3)]:
        (x0, y0), (x1, y1) = T(a, b), T(c, d)
        H.box(((x0 + x1) / 2, (y0 + y1) / 2, (2.14 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), z1 - 2.14))
    wx, wy = T(185, 500)
    H.cyl((wx, wy, 2.22), 0.36, 1.05, (0, PI / 2, 0), seg=20)        # main recovery winch drum (mid deck)
    sx, sy = T(117, 688)
    H.cyl((sx, sy, 2.24), 0.48, 0.2, seg=20)                         # spare road wheel on the rear deck
    H.cyl((sx, sy, 2.36), 0.15, 0.06, seg=10)
    rx, ry = T(310, 585)
    H.cyl((rx, ry, 2.3), 0.33, 0.32, seg=18)                         # round stowage drum (right rear)
    # side stowage boxes (side view px 640..765, 132..180 = black box on rear deck, left side)
    for s in (-1, 1):
        H.box((s * 1.3, (S(640, 0)[0] + S(762, 0)[0]) / 2, 2.38), (0.5, S(640, 0)[0] - S(762, 0)[0], 0.48))
    # --- A-frame crane boom (one beam, offset right as in the top view px 200..250)
    bx = T(225, 0)[0]
    p0 = Vector((bx, S(185, 0)[0], 2.48))
    p1 = Vector((bx, S(812, 0)[0], (390 - 30) * SS))
    H.beam(p0, p1, 0.5, 0.27)
    H.beam(p0 + Vector((0, -0.1, 0.16)), p0.lerp(p1, 0.55) + Vector((0, 0, 0.18)), 0.36, 0.1)   # top flange/stiffener
    H.cyl((bx, p0.y + 0.05, p0.z - 0.05), 0.2, 0.7, (0, PI / 2, 0), seg=14)                        # boom foot pivot
    H.box((bx, p0.y + 0.05, (p0.z + 2.2) / 2), (0.62, 0.42, p0.z - 2.2 + 0.1))                  # pivot pedestal
    # support legs (side view px 560..580) from the deck to the boom
    t = (S(570, 0)[0] - p0.y) / (p1.y - p0.y)
    pb = p0.lerp(p1, t) - Vector((0, 0, 0.13))
    for s in (-1, 1):
        H.rod((bx + s * 0.32, pb.y + 0.15, 2.14), (bx + s * 0.18, pb.y, pb.z), 0.065, seg=8)
    H.rod((bx, S(480, 0)[0], 2.6), (bx, pb.y + 0.3, pb.z + 0.02), 0.06, seg=8)
    # tip sheaves, hook block, chain
    H.cyl((bx, p1.y - 0.05, p1.z - 0.05), 0.25, 0.34, (0, PI / 2, 0), seg=18)
    hb = Vector((bx, S(800, 0)[0], (390 - 100) * SS))
    H.rod((bx - 0.1, p1.y, p1.z - 0.1), (bx - 0.1, hb.y, hb.z), 0.025, seg=6)
    H.rod((bx + 0.1, p1.y, p1.z - 0.1), (bx + 0.1, hb.y, hb.z), 0.025, seg=6)
    H.cyl(hb, 0.21, 0.24, (0, PI / 2, 0), seg=16)
    H.rod((bx, hb.y, hb.z - 0.15), (bx, S(812, 0)[0], (390 - 175) * SS), 0.05, seg=6)
    H.box((bx, S(812, 0)[0], (390 - 180) * SS), (0.1, 0.22, 0.18))
    # back-stay cable from a short mast on the casemate roof to the boom tip, radio antenna
    mast = Vector((bx, S(430, 0)[0], (390 - 95) * SS))
    H.rod((bx, mast.y, 2.52), mast, 0.05, seg=8)
    H.rod(mast, (bx, p1.y + 0.1, p1.z + 0.12), 0.02, seg=6)
    H.rod((-1.25, S(442, 0)[0], 2.52), (-1.25, S(442, 0)[0], (390 - 50) * SS), 0.018, seg=6)
    # --- rear plate: recovery winch drum, tail lights, tow shackles (from the rear-3/4 view)
    yr = S(826, 0)[0]
    H.cyl((0.1, yr - 0.16, 1.85), 0.26, 1.3, (0, PI / 2, 0), seg=18)
    for s in (-1, 1):
        H.box((s * 0.68, yr - 0.14, 1.85), (0.12, 0.34, 0.66))
        H.box((s * 1.42, yr - 0.07, 1.95), (0.24, 0.14, 0.2))
        H.box((s * 0.45, yr - 0.1, 1.05), (0.12, 0.2, 0.18))
    # --- return rollers (static, part of the hull)
    for s in (-1, 1):
        for (y, z, r) in ROLLERS:
            H.cyl((s * TRACK_X, y, z), r, 0.32, (0, PI / 2, 0), seg=12)
    objs["Hull"] = H.build(mat, bevel=0.02, angle=35)

    # --- MG on the cupola: origin at the mount pivot (game may yaw it about local Y/up)
    pivot = Vector((cx, cy, 2.8))
    M = Part("MG")
    M.cyl((0, 0, 0.12), 0.06, 0.24, seg=10)                          # pintle post
    M.box((0, 0.05, 0.3), (0.16, 0.62, 0.17))                         # receiver
    M.cyl((0, 0.7, 0.32), 0.035, 0.8, (PI / 2, 0, 0), seg=8)          # barrel
    M.cyl((0, 0.35, 0.32), 0.055, 0.25, (PI / 2, 0, 0), seg=8)        # barrel jacket
    M.box((0.15, 0.0, 0.26), (0.14, 0.24, 0.16))                      # ammo can
    M.box((0, 0.36, 0.32), (0.5, 0.03, 0.34))                         # gun shield
    objs["MG"] = M.build(mat, bevel=0.0, location=pivot)

    # --- running gear, left side (right side is a UV-sharing mirror made later)
    xl = -TRACK_X
    for i, y in enumerate(WHEEL_Y):
        W = Part(f"WheelL{i}")
        for dx in (-0.13, 0.13):
            W.cyl((dx, 0, 0), WHEEL_R, 0.19, (0, PI / 2, 0), seg=22)
        W.cyl((-0.24, 0, 0), 0.13, 0.08, (0, PI / 2, 0), seg=12)     # outer hub cap (outer side = -X)
        objs[f"WheelL{i}"] = W.build(mat, bevel=0.0, smooth=40, location=(xl, y, WHEEL_Z))
    I_ = Part("IdlerL")
    for dx in (-0.12, 0.12):
        I_.cyl((dx, 0, 0), IDLER[2], 0.18, (0, PI / 2, 0), seg=22)
    I_.cyl((-0.23, 0, 0), 0.12, 0.08, (0, PI / 2, 0), seg=12)
    objs["IdlerL"] = I_.build(mat, bevel=0.0, smooth=40, location=(xl, IDLER[0], IDLER[1]))
    SP = Part("SprocketL")
    n_teeth = 11
    for dx in (-0.11, 0.11):                                          # two toothed rings
        ring_o, ring_i = [], []
        for k in range(n_teeth * 4):
            a = 2 * PI * k / (n_teeth * 4)
            rr = SPROCKET[2] + 0.035 if (k % 4) in (1, 2) else SPROCKET[2] - 0.035
            ring_o.append((dx - 0.04, math.cos(a) * rr, math.sin(a) * rr))
            ring_i.append((dx + 0.04, math.cos(a) * rr, math.sin(a) * rr))
        SP.rings([ring_o, ring_i])
    SP.cyl((0, 0, 0), SPROCKET[2] - 0.08, 0.36, (0, PI / 2, 0), seg=16)
    SP.cyl((-0.22, 0, 0), 0.14, 0.1, (0, PI / 2, 0), seg=12)
    objs["SprocketL"] = SP.build(mat, bevel=0.0, smooth=40, location=(xl, SPROCKET[0], SPROCKET[1]))
    return objs


def belt_path(step=0.1):
    """Closed belt centre-line (y,z) around idler, road wheels, sprocket and return rollers.
    Counter-clockwise in (y right, z up): along the ground run the path runs towards +Y (front)."""
    from scipy.spatial import ConvexHull
    circles = [(y, WHEEL_Z, WHEEL_R) for y in WHEEL_Y] + [IDLER, SPROCKET] + ROLLERS
    pts = []
    for (cy, cz, r) in circles:
        rr = r + TRACK_T / 2
        for k in range(96):
            a = 2 * PI * k / 96
            pts.append((cy + rr * math.cos(a), cz + rr * math.sin(a)))
    pts = np.array(pts)
    hull = ConvexHull(pts)
    poly = pts[hull.vertices]                       # CCW order
    # start at the rear end of the ground run so the seam sits behind the sprocket base
    seg = np.diff(np.vstack([poly, poly[:1]]), axis=0)
    L = np.linalg.norm(seg, axis=1)
    total = L.sum()
    n = int(round(total / step))
    cum = np.concatenate([[0], np.cumsum(L)])
    out = []
    for k in range(n):
        d = k * total / n
        i = np.searchsorted(cum, d, side="right") - 1
        t = (d - cum[i]) / max(L[i], 1e-9)
        out.append(poly[i] + seg[i] * t)
    return np.array(out), total


def build_tracks(mat):
    path, total = belt_path(0.1)
    n_links = LINKS_PER_TILE * max(1, round(total / (TRACK_PITCH * LINKS_PER_TILE)))
    m_per_v = total / (n_links / LINKS_PER_TILE)
    n = len(path)
    cen = path.mean(0)
    # per-vertex outward normal in the (y,z) plane
    tang = np.roll(path, -1, 0) - np.roll(path, 1, 0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.stack([tang[:, 1], -tang[:, 0]], 1)          # rotate -90deg: outward for CCW loop
    flip = ((path - cen) * nrm).sum(1) < 0
    nrm[flip] *= -1
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    v_of = list(arc / m_per_v) + [total / m_per_v]       # duplicated closing ring gets V = loop length
    objs = {}
    for s, name in ((-1, "TrackL"), (1, "TrackR")):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        x_in, x_out = s * (TRACK_X - TRACK_W / 2), s * (TRACK_X + TRACK_W / 2)
        # cross-section corners (x, offset along normal) and U coordinates of the layout:
        # outer tread 0..0.5, outer side 0.5..0.6, inner face 0.6..0.9, inner side 0.9..1.0
        h = TRACK_T / 2
        corners = [(x_in, +h), (x_out, +h), (x_out, -h), (x_in, -h)]
        u_ranges = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.9), (0.9, 1.0)]
        ring = []
        for k in range(n + 1):
            i = k % n
            ring.append([bm.verts.new((cx, path[i, 0] + nrm[i, 0] * o, path[i, 1] + nrm[i, 1] * o))
                         for cx, o in corners])
        for k in range(n):
            for e in range(4):
                a, b = ring[k][e], ring[k][(e + 1) % 4]
                c, d = ring[k + 1][(e + 1) % 4], ring[k + 1][e]
                f = bm.faces.new((a, d, c, b)) if s < 0 else bm.faces.new((a, b, c, d))
                u0, u1 = u_ranges[e]
                for lp in f.loops:
                    kk = k if lp.vert in (a, b) else k + 1
                    uu = u0 if lp.vert in (a, d) else u1
                    lp[uvl].uv = (uu, v_of[kk])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        me.materials.append(mat)
        o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
        bpy.ops.object.select_all(action="DESELECT"); bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
        objs[name] = o
    return objs, m_per_v, total, n_links


def make_track_texture(top_ref, side_ref, m_per_v, path_png, size=(256, 512)):
    """Tile (U across belt, V = m_per_v metres = LINKS_PER_TILE links). The concept views show the
    track only as a thin, partly hidden strip, so the link pattern is procedural and its colours are
    taken from the concept's lower track run (side view px 200..700, py 378..389)."""
    Wt, Ht = size
    ys = np.arange(378, 390); xs = np.arange(200, 700)
    strip = side_ref["rgb"][ys][:, xs].reshape(-1, 3)
    lum = strip.mean(1)
    dark = np.median(strip[lum < np.percentile(lum, 30)], 0)
    lite = np.median(strip[lum > np.percentile(lum, 80)], 0)
    v = (np.arange(Ht) + 0.5) / Ht * LINKS_PER_TILE          # link coordinate
    f = v % 1.0                                               # 0..1 within one link
    u = (np.arange(Wt) + 0.5) / Wt
    F, U_ = np.meshgrid(f, u, indexing="ij")
    out = np.zeros((Ht, Wt, 3), np.float32)
    # --- outer tread (u 0..0.5): steel shoe with raised grouser bar and two rubber pads
    ut = U_ / 0.5
    shoe = np.where((F > 0.06) & (F < 0.94), 1.0, 0.25)                 # gap between links
    grouser = np.exp(-((F - 0.5) / 0.08) ** 2)
    pad = ((np.abs(ut - 0.27) < 0.17) | (np.abs(ut - 0.73) < 0.17)) & (F > 0.15) & (F < 0.85)
    tread = dark[None, None] * (0.75 + 0.5 * grouser[..., None]) * shoe[..., None]
    tread = np.where(pad[..., None], dark * 0.55, tread)
    edge = (ut < 0.06) | (ut > 0.94)                                     # end connectors
    tread = np.where(edge[..., None], lite * (0.8 + 0.3 * np.exp(-((F - 0.5) / 0.2) ** 2))[..., None], tread)
    m = U_ < 0.5
    out[m] = tread[m]
    # --- sides (u 0.5..0.6 and 0.9..1.0): connector ends + pins
    side = lite * 0.6 * (0.55 + 0.45 * np.exp(-((F - 0.5) / 0.22) ** 2))[..., None] * np.where((F > 0.05) & (F < 0.95), 1, 0.4)[..., None]
    m = ((U_ >= 0.5) & (U_ < 0.6)) | (U_ >= 0.9)
    out[m] = side[m]
    # --- inner face (u 0.6..0.9): smooth wheel path + centre guide horn
    ui = (U_ - 0.6) / 0.3
    inner = dark * 0.85 * np.where((F > 0.06) & (F < 0.94), 1, 0.35)[..., None]
    horn = (np.abs(ui - 0.5) < 0.08) & (F > 0.3) & (F < 0.7)
    inner = np.where(horn[..., None], lite * 0.9, inner)
    m = (U_ >= 0.6) & (U_ < 0.9)
    out[m] = inner[m]
    rng = np.random.RandomState(11)
    out *= (0.92 + 0.16 * ndimage.gaussian_filter(rng.rand(Ht, Wt), 2.0))[..., None]
    # rows are V-ascending (Blender order, row0 = V0); PNG rows run top-down -> flip
    a = np.clip(out[::-1] * 255 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGB").save(path_png)


def shade_m88(P, N, refs, depth):
    top, side, f34, r34 = refs["top"], refs["side"], refs["front34"], refs["rear34"]
    k = 3.0
    nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]
    # --- projections
    tpx = 191.5 + P[:, 0] / ST; tpy = 395.0 - P[:, 1] / ST
    c_top = sample(top, tpx, tpy)
    spx = 420.0 - P[:, 1] / SS; spy = 390.0 - P[:, 2] / SS
    c_side = sample(side, spx, spy)
    # front-3/4 view (camera front-right: hull +X edge at image left). Two rectified planes.
    Hf_plate = homography([(1.62, 1.37), (-1.62, 1.37), (-1.62, 2.29), (1.62, 2.29)],
                          [(300, 350), (600, 335), (588, 200), (300, 216)])
    Hf_blade = homography([(1.94, 0.02), (-1.94, 0.02), (-1.94, 1.12), (1.94, 1.12)],
                          [(312, 476), (664, 445), (646, 350), (300, 382)])
    fx, fy = apply_h(Hf_plate, P[:, 0], P[:, 2])
    bx_, by_ = apply_h(Hf_blade, P[:, 0], P[:, 2])
    is_blade = (P[:, 1] > 3.2) & (P[:, 2] < 1.25)
    c_front = np.where(is_blade[:, None], sample(f34, bx_, by_), sample(f34, fx, fy))
    # rear-3/4 view (camera rear-left: hull -X edge at image left)
    Hr = homography([(-1.62, 0.95), (1.62, 0.95), (1.62, 2.14), (-1.62, 2.14)],
                    [(262, 385), (602, 368), (598, 195), (258, 200)])
    rx, ry = apply_h(Hr, P[:, 0], P[:, 2])
    c_rear = sample(r34, rx, ry)
    # --- visibility (depth tests)
    tol = 0.06
    v_top = visible(depth["top"], P, tol + 0.03 * np.sqrt(np.clip(1 - nz ** 2, 0, 1)) / np.maximum(nz, 0.25))
    v_l = visible(depth["left"], P, tol); v_r = visible(depth["right"], P, tol)
    v_f = visible(depth["front"], P, tol); v_b = visible(depth["rear"], P, tol)
    v_side = np.where(nx < 0, v_l, v_r)
    w_t = np.clip(nz, 0, 1) ** k
    w_s = np.abs(nx) ** k
    w_f = np.clip(ny, 0, 1) ** k
    w_r = np.clip(-ny, 0, 1) ** k
    w_b = np.clip(-nz, 0, 1) ** k
    under = np.array([0.10, 0.10, 0.075])
    num = (c_top * (w_t * v_top)[:, None] + c_side * (w_s * v_side)[:, None]
           + c_front * (w_f * v_f)[:, None] + c_rear * (w_r * v_b)[:, None] + under * w_b[:, None] * 0.5)
    den = w_t * v_top + w_s * v_side + w_f * v_f + w_r * v_b + w_b * 0.5
    # occluded in every view: unoccluded blend, darkened (cavity), so it stays in palette
    num0 = (c_top * w_t[:, None] + c_side * w_s[:, None] + c_front * w_f[:, None] + c_rear * w_r[:, None]
            + under * w_b[:, None])
    den0 = w_t + w_s + w_f + w_r + w_b
    col = np.where((den > 0.02)[:, None], num / np.maximum(den, 1e-6)[:, None],
                   0.6 * num0 / np.maximum(den0, 1e-6)[:, None])
    # --- light procedural grime: mud towards the ground, a little mottling everywhere
    nse = value_noise(P, 0.9, seed=3)
    low = np.clip((1.15 - P[:, 2]) / 1.15, 0, 1) ** 1.5 * (0.25 + 0.35 * nse)
    mud = np.array([0.33, 0.29, 0.21])
    col = col * (1 - low[:, None]) + mud * low[:, None] * (0.6 + 0.4 * col.mean(1, keepdims=True) / 0.3)
    col *= (0.93 + 0.12 * value_noise(P, 0.35, seed=7))[:, None]
    return np.clip(col, 0, 1)


def texture_atlas(objs, refs, shade_fn, size, ao_size, ao_strength, depth_cells, bounds, out_png, ao_objs=None, depth_objs=None):
    """Rasterise atlas texels, project concept art, bake/multiply AO, save PNG. Returns path."""
    P, Nn, U, I = world_tris(objs, with_uv=True)
    allP = world_tris(depth_objs or [o for o in bpy.context.scene.objects if o.type == "MESH"])[0]
    (x0, y0, z0), (x1, y1, z1) = bounds
    c = depth_cells
    depth = {
        "top": depth_map(allP, (0, 1), 2, (x0, y0), (x1, y1), c, +1),
        "left": depth_map(allP, (1, 2), 0, (y0, z0), (y1, z1), c, -1),
        "right": depth_map(allP, (1, 2), 0, (y0, z0), (y1, z1), c, +1),
        "front": depth_map(allP, (0, 2), 1, (x0, z0), (x1, z1), c, +1),
        "rear": depth_map(allP, (0, 2), 1, (x0, z0), (x1, z1), c, -1),
    }
    pos, nor, oid, msk = uv_raster(P, Nn, U, I, size)
    Pm, Nm = pos[msk].astype(np.float64), nor[msk].astype(np.float64)
    col = np.zeros((size, size, 3), np.float32)
    col[msk] = shade_fn(Pm, Nm, refs, depth)
    if ao_strength > 0:
        ao = bake_ao(ao_objs or objs, ao_size, samples=16, distance=0.9)
        ao = np.asarray(Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR),
                        np.float32) / 255.0
        col *= (1 - ao_strength + ao_strength * ao)[..., None]
    col = fill_nearest(col, msk)
    save_png(col, out_png)
    return out_png, float(msk.mean())


def preview_set(prefix, prev_dir, length, width, height, rts_dist, close_dist, close_az=-38, lens=50):
    """front / side / rear / top orthographic (slight elevation), RTS 52deg 3/4 and a close 3/4."""
    cam = setup_preview_scene()
    out = []
    zc = height / 2
    fr = max(width, height / 0.75) * 1.45           # ortho_scale = visible width for a 4:3 frame
    sd = max(length, height / 0.75) * 1.12
    views = [("front", 0, 6, (0, 0, zc), fr, None, (800, 600)),
             ("side", -90, 6, (0, 0, zc), sd, None, (800, 600)),
             ("rear", 180, 6, (0, 0, zc), fr, None, (800, 600)),
             ("top", 0, 90, (0, 0, zc), max(length, width / 0.75) * 1.08, (0, 1, 0), (600, 800)),
             ("rts", 45, 52, (0, 0, zc * 0.6), None, None, (800, 600)),
             ("close34", close_az, 18, (0, 0, zc * 0.8), None, None, (800, 600))]
    for name, az, el, tgt, ortho, up, res in views:
        dist = {"rts": rts_dist, "close34": close_dist}.get(name, 60)
        if ortho:
            aim(cam, tgt, az, el, dist, ortho=ortho, roll_up=up)
        else:
            aim(cam, tgt, az, el, dist, lens=lens)
        p = os.path.join(prev_dir, f"{prefix}_{name}.png")
        render(p, res)
        out.append((p, name))
    return cam, out


def main():
    out, prev = parse_args("m88")
    reset_scene()
    base = os.path.join(REPO, "godot", "assets", "us", "vehicles", "m88")
    refs = {k: load_ref(os.path.join(base, f"m88_{k}.png"), erode=3) for k in ("top", "side", "front34", "rear34")}
    for k in ("top", "front34", "rear34"):
        gain_to(refs[k], refs["side"]["mean"], strength=0.85)
    atlas_mat = image_material("SA_M88", None, rough=0.78)
    track_mat = image_material("SA_TrackScroll", None, rough=0.9, metal=0.1)
    objs = build_m88(atlas_mat)
    left = ["Hull", "MG"] + [f"WheelL{i}" for i in range(len(WHEEL_Y))] + ["IdlerL", "SprocketL"]
    atlas_objs = [objs[n] for n in left]
    smart_uv(atlas_objs, margin=0.003)
    right = []
    for n in left[2:]:
        rn = n.replace("WheelL", "WheelR").replace("IdlerL", "IdlerR").replace("SprocketL", "SprocketR")
        objs[rn] = mirror_copy_x(objs[n], rn); right.append(objs[rn])
    tracks, m_per_v, total, n_links = build_tracks(track_mat)
    objs.update(tracks)

    albedo = os.path.join(out, "m88_albedo.png")
    _, cover = texture_atlas(atlas_objs, refs, shade_m88, 2048, 1024, 0.55, 0.02,
                             ((-2.3, -4.7, -0.1), (2.3, 4.7, 4.3)), albedo, ao_objs=atlas_objs + right)
    trk = os.path.join(out, "m88_track.png")
    make_track_texture(refs["top"], refs["side"], m_per_v, trk)
    img_a = load_image(albedo, "m88_albedo"); img_t = load_image(trk, "m88_track")
    for m, img in ((atlas_mat, img_a), (track_mat, img_t)):
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])

    order = ["Hull", "MG", "TrackL", "TrackR"] + sorted(n for n in objs if n.startswith("Wheel")) + \
            ["IdlerL", "IdlerR", "SprocketL", "SprocketR"]
    export = [objs[n] for n in order]
    glb = os.path.join(out, "m88.glb")
    export_glb(export, glb)
    # report
    tl = objs["TrackL"].data
    vs = [(tl.vertices[l.vertex_index].co.y, tl.uv_layers.active.data[l.index].uv.y) for l in tl.loops
          if tl.vertices[l.vertex_index].co.z < 0.01]
    vs.sort()
    print(f"M88 tris total {tri_count(export)}  hull {tri_count([objs['Hull']])}  tracks {tri_count(list(tracks.values()))}")
    print(f"M88 track loop {total:.3f} m, links {n_links}, metres per V {m_per_v:.4f}; ground run blender-V rear->front "
          f"{vs[0][1]:.3f} -> {vs[-1][1]:.3f}")
    print(f"M88 atlas coverage {cover:.3f}")
    for o in export:
        print(f"  {o.name:10s} tris {tri_count([o]):6d} origin {tuple(round(v, 3) for v in o.location)}")
    print("M88 GLB", glb)
    if prev:
        L = 8.3
        cam, shots = preview_set("pilot3d_m88", prev, L, 4.0, 3.8, rts_dist=17, close_dist=12.5)
        # scale shot: 1.8 m human-scale box beside the vehicle
        bpy.ops.mesh.primitive_cube_add(size=1, location=(2.75, 1.2, 0.9))
        hb = bpy.context.active_object; hb.scale = (0.45, 0.3, 1.8)
        hm = bpy.data.materials.new("HumanBox"); hm.use_nodes = True
        hm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.25, 0.1, 1)
        hb.data.materials.append(hm)
        aim(cam, (0.8, 0, 1.3), 62, 12, 13, lens=50)
        sp = os.path.join(prev, "pilot3d_m88_scale.png"); render(sp)
        shots.append((sp, "scale (1.8 m box)"))
        contact_sheet(shots, os.path.join(prev, "pilot3d_m88_sheet.png"), cols=4, cell=(480, 360),
                      title="Steel Accord pilot 3D - M88 recovery vehicle (Dozer) - Cycles CPU preview")
        print("M88 previews in", prev)


if __name__ == "__main__":
    main()
