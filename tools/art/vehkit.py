"""Steel Accord - shared vehicle kit for the M2 U.S. ground-vehicle roster (bpy 5.x).

Generalises the approved M88 pilot pipeline (tools/art/veh_m88_3d.py, whose library half is imported
unchanged, so the M88 output is not affected):
  * concept-view frames: side view (nose left after optional flip) and top view (nose up) -> metres
  * fitted 3/4-view cameras: the front-3/4 and rear-3/4 concept views are registered with an affine
    camera fitted by least squares to a handful of hand-picked landmarks (world point <-> image pixel),
    so every texel facing that camera can be projected (depth tested along the camera axis) instead of
    only one hand-rectified plane per view
  * tracked running gear: wheels / idler / sprocket / return rollers + belt ribbons (V along the belt,
    integer number of texture tiles per loop, material SA_TrackScroll)
  * wheeled running gear: lathe tyres with hub origin, optional SteerFL/SteerFR empties
  * Turret / Gun / Muzzle hierarchy helpers, SA_Team panels, atlas texturing with object-aware shading
  * cheap Cycles preview sheet (front, side, rear, top, RTS 52 deg, close 3/4)

Conventions: forward = Blender +Y (Godot -Z), up = +Z, metres, root origin = ground contact under the
vehicle centre, vehicle left = -X.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Euler, Vector
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import veh_m88_3d as m88k  # noqa: E402  (library half only; main() is not run)
from veh_m88_3d import (Part, mirror_copy_x, tri_count, smart_uv, world_tris, _tri_pixels, depth_map,  # noqa: E402,F401
                        visible, uv_raster, fill_nearest, gain_to, sample, value_noise, image_material,
                        bake_ao, save_png, load_image, aim, render, contact_sheet, reset_scene, homography,
                        apply_h)

PI = math.pi
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
VEH_REF = os.path.join(REPO, "godot", "assets", "us", "vehicles")
MANIFEST = os.path.join(REPO, "content", "manifest", "us_packs.json")


# ============================================================================ args
def parse_args(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    opts = {"out": None, "prev": os.path.join(REPO, "docs", "screens"), "do_prev": True, "quick": False, "pos": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--previews":
            opts["prev"] = argv[i + 1]; i += 2; continue
        if a == "--no-previews":
            opts["do_prev"] = False; i += 1; continue
        if a == "--quick":                      # one RTS preview only (iteration aid)
            opts["quick"] = True; i += 1; continue
        if a == "--out":
            opts["out"] = argv[i + 1]; i += 2; continue
        opts["pos"].append(a); i += 1
    return opts


# ============================================================================ Part extensions
def lathe(part, c, profile, seg=20, axis="x"):
    """Revolve a (axial, radius) profile about an axis through c. Closed rings; caps on both ends."""
    c = Vector(c)
    rings = []
    for ax, r in profile:
        ring = []
        for k in range(seg):
            a = 2 * PI * k / seg
            if axis == "x":
                ring.append(c + Vector((ax, r * math.cos(a), r * math.sin(a))))
            elif axis == "y":
                ring.append(c + Vector((r * math.cos(a), ax, r * math.sin(a))))
            else:
                ring.append(c + Vector((r * math.cos(a), r * math.sin(a), ax)))
        rings.append([tuple(p) for p in ring])
    part.rings(rings, caps=True)


def loft_sections(part, sections, caps=True):
    """sections: list of (y, [(x,z), ...]) closed outlines with equal vertex counts."""
    part.rings([[(x, y, z) for x, z in outline] for y, outline in sections], caps=caps)


def rect_section(hw, z0, z1, chamfer=0.0, top_hw=None):
    """8-vertex section: bottom half-width hw, top half-width top_hw (default hw), chamfered corners."""
    t = hw if top_hw is None else top_hw
    c = chamfer
    return [(-hw + c, z0), (hw - c, z0), (hw, z0 + c), (t, z1 - c), (t - c, z1), (-t + c, z1), (-t, z1 - c), (-hw, z0 + c)]


def set_origin(obj, pivot):
    """Move the object origin to world `pivot` without moving the geometry (object must be unrotated)."""
    pivot = Vector(pivot)
    d = pivot - obj.location
    obj.data.transform(Matrix.Translation(-d))
    obj.location = pivot
    return obj


def parent_to(child, parent):
    """Parent with identity inverse; local location = world offset (no rotations are used)."""
    wl = child.location.copy()
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.location = wl - parent_world(parent)
    return child


def parent_world(o):
    p = Vector((0, 0, 0))
    while o is not None:
        p += o.location
        o = o.parent
    return p


def empty(name, world_loc, parent=None, size=0.2):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"; e.empty_display_size = size
    bpy.context.scene.collection.objects.link(e)
    e.location = Vector(world_loc)
    if parent is not None:
        parent_to(e, parent)
    return e


def team_material():
    m = bpy.data.materials.get("SA_Team")
    if m is None:
        m = bpy.data.materials.new("SA_Team")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1)
        b.inputs["Roughness"].default_value = 0.6
    return m


def join_team(target, team_obj):
    """Join a team-colour object (material SA_Team) into `target` as an extra material slot."""
    tm = team_material()
    team_obj.data.materials.clear(); team_obj.data.materials.append(tm)
    if not team_obj.data.uv_layers:
        team_obj.data.uv_layers.new(name=target.data.uv_layers.active.name if target.data.uv_layers else "UVMap")
    # keep the world placement: bake team geometry into target-local space
    M = target.matrix_world.inverted() @ team_obj.matrix_world
    team_obj.data.transform(M)
    team_obj.matrix_world = target.matrix_world.copy()
    bpy.ops.object.select_all(action="DESELECT")
    team_obj.select_set(True); target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    return target


# ============================================================================ references
def manifest_entry(vid):
    import json
    with open(MANIFEST) as f:
        return json.load(f)["vehicles"][vid]


def load_ref(path, erode=2, flip=False):
    im = Image.open(path).convert("RGBA")
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    a = np.asarray(im, dtype=np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3]
    m = al > 0.5
    m_full = m.copy()
    if erode:
        m = ndimage.binary_erosion(m, iterations=erode)
    rgb = fill_nearest(rgb, m)
    return {"rgb": rgb, "a": m, "a_full": m_full, "mean": rgb[m].mean(0), "path": path, "flip": flip}


def load_refs(vid, erode=3):
    me = manifest_entry(vid)
    refs = {}
    for k in ("top", "side", "front34", "rear34"):
        flip = (k == "side" and me.get("side", {}).get("faces") == "right")
        refs[k] = load_ref(os.path.join(VEH_REF, vid, f"{vid}_{k}.png"), erode=erode, flip=flip)
    for k in ("top", "front34", "rear34"):
        gain_to(refs[k], refs["side"]["mean"], strength=0.85)
    return refs, me


class SideFrame:
    """Side view (nose left after flip). S(px,py) -> (y,z)."""

    def __init__(self, scale, px_centre, py_ground):
        self.s, self.pc, self.pg = scale, px_centre, py_ground

    def __call__(self, px, py):
        return ((self.pc - px) * self.s, (self.pg - py) * self.s)

    def y(self, px):
        return (self.pc - px) * self.s

    def z(self, py):
        return (self.pg - py) * self.s

    def px(self, y):
        return self.pc - y / self.s

    def py(self, z):
        return self.pg - z / self.s


class TopFrame:
    """Top view (nose up). T(px,py) -> (x,y). Optional `ymap` = [(py, y), ...] piecewise-linear
    rectification for concept top views whose proportions disagree with the side view."""

    def __init__(self, scale, px_centre, py_centre, sx=1.0, ymap=None):
        self.s, self.pc, self.py0, self.sx = scale, px_centre, py_centre, sx
        self.ymap = None
        if ymap:
            ym = sorted(ymap)
            self.ymap = (np.array([a for a, b in ym], float), np.array([b for a, b in ym], float))

    def __call__(self, px, py):
        return (self.x(px), self.y(py))

    def x(self, px):
        return (px - self.pc) * self.s * self.sx

    def y(self, py):
        if self.ymap is None:
            return (self.py0 - py) * self.s
        P, Y = self.ymap
        return float(np.interp(py, P, Y, left=Y[0] + (P[0] - py) * self.s, right=Y[-1] - (py - P[-1]) * self.s))

    def py_of(self, y):
        """vectorised inverse of y()"""
        y = np.asarray(y, float)
        if self.ymap is None:
            return self.py0 - y / self.s
        P, Y = self.ymap                     # Y decreasing with P increasing
        out = np.interp(-y, -Y, P)
        out = np.where(y > Y[0], P[0] - (y - Y[0]) / self.s, out)
        out = np.where(y < Y[-1], P[-1] + (Y[-1] - y) / self.s, out)
        return out

    def pxpy(self, x, y):
        return self.pc + x / (self.s * self.sx), float(self.py_of(y))


# ============================================================================ 3/4 view cameras
class PerspCam:
    """Pinhole camera looking at `target` from azimuth/elevation (deg, az from +Y towards +X) at `dist` m.
    Image coords: u = s*dist*xc/zc + tx, v = -s*dist*yc/zc + ty (s ~ pixels per metre at the target)."""

    def __init__(self, target, az, el, dist, s, tx, ty, roll=0.0, name=""):
        self.target = np.array(target, float)
        self.p = [az, el, dist, s, tx, ty, roll]
        self.name = name
        self._basis()

    def _basis(self):
        az, el, dist, s, tx, ty, roll = self.p
        a, e = math.radians(az), math.radians(el)
        d = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
        self.pos = self.target + d * dist
        f = -d
        r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
        u = np.cross(r, f)
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        self.r, self.u = cr * r + sr * u, -sr * r + cr * u
        self.f = f
        self.v = d                                     # towards the camera (for normal weighting)

    def set(self, p):
        self.p = list(p); self._basis(); return self

    def cam(self, P):
        Q = P - self.pos
        return Q @ self.r, Q @ self.u, Q @ self.f

    def project(self, P):
        az, el, dist, s, tx, ty, roll = self.p
        xc, yc, zc = self.cam(P)
        zc = np.maximum(zc, 1e-3)
        return np.stack([s * dist * xc / zc + tx, -s * dist * yc / zc + ty], -1)

    def view_dirs(self, P):
        d = self.pos - P
        return d / np.linalg.norm(d, axis=1, keepdims=True)

    def report(self):
        az, el, dist, s, tx, ty, roll = self.p
        return (f"{self.name}: az {az:.1f} el {el:.1f} dist {dist:.1f} m  scale {s:.1f} px/m  roll {roll:.1f}"
                f"  silhouette IoU {getattr(self, 'iou', float('nan')):.3f}")


def _poly_mask(uv_tris, W, H, ds):
    from PIL import ImageDraw
    im = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(im)
    T = uv_tris / ds
    for t in T:
        d.polygon([(t[0, 0], t[0, 1]), (t[1, 0], t[1, 1]), (t[2, 0], t[2, 1])], fill=1)
    return np.asarray(im, bool)


def silhouette_iou(cam, tris, ref_mask, ds=2):
    H, W = ref_mask.shape[0] // ds, ref_mask.shape[1] // ds
    uv = cam.project(tris.reshape(-1, 3)).reshape(-1, 3, 2)
    m = _poly_mask(uv, W, H, ds)
    r = ref_mask[:H * ds:ds, :W * ds:ds]
    inter = (m & r).sum(); uni = (m | r).sum()
    return inter / max(uni, 1), m


def fit_cam(tris, ref, az0, target, name, ds=2, el_range=(5, 45), az_span=30, verbose=True):
    """Fit a PerspCam to the concept silhouette (alpha) of `ref` by grid search + Nelder-Mead on IoU."""
    from scipy.optimize import minimize
    mask = ref["a_full"]
    H, W = mask.shape
    ys, xs = np.nonzero(mask)
    bb = (xs.min(), ys.min(), xs.max(), ys.max())
    big = tris.reshape(-1, 3)
    # cull tiny triangles for speed during the search
    area = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    sel = tris[area > np.percentile(area, 35)] if len(tris) > 4000 else tris

    def bbox_fit(az, el, dist, roll=0.0):
        c = PerspCam(target, az, el, dist, 1.0, 0, 0, roll)
        uv = c.project(big)
        w = uv[:, 0].max() - uv[:, 0].min(); h = uv[:, 1].max() - uv[:, 1].min()
        s = 0.5 * ((bb[2] - bb[0]) / w + (bb[3] - bb[1]) / h)
        c.set([az, el, dist, s, 0, 0, roll])
        uv = c.project(big)
        tx = (bb[0] + bb[2]) / 2 - (uv[:, 0].min() + uv[:, 0].max()) / 2
        ty = (bb[1] + bb[3]) / 2 - (uv[:, 1].min() + uv[:, 1].max()) / 2
        return c.set([az, el, dist, s, tx, ty, roll])

    best = (-1, None)
    for az in np.arange(az0 - az_span, az0 + az_span + 0.1, 6):
        for el in np.arange(el_range[0], el_range[1] + 0.1, 5):
            for dist in (14.0, 30.0, 80.0):
                c = bbox_fit(az, el, dist)
                iou, _ = silhouette_iou(c, sel, mask, ds * 2)
                if iou > best[0]:
                    best = (iou, c.p[:])
    p0 = np.array(best[1], float)
    scl = np.array([3.0, 3.0, max(p0[2] * 0.3, 2.0), p0[3] * 0.04, 8.0, 8.0, 2.0])

    def f(q):
        p = p0 + q * scl
        if p[2] < 6 or p[2] > 250 or p[1] < -5 or p[1] > 70:
            return 1.0
        c = PerspCam(target, *p)
        return 1.0 - silhouette_iou(c, sel, mask, ds)[0]

    simplex = np.vstack([np.zeros(7), np.eye(7)])
    r = minimize(f, np.zeros(7), method="Nelder-Mead", options={"maxfev": 260, "xatol": 0.02, "fatol": 1e-4,
                                                                 "initial_simplex": simplex})
    p = p0 + r.x * scl
    cam = PerspCam(target, *p, name=name)
    cam.iou = silhouette_iou(cam, tris, mask, 1)[0]
    if verbose:
        print("  fit", cam.report(), f"(grid best {best[0]:.3f})")
    return cam


def cam_depth(allP, cam, shape):
    """Image-space z-buffer (closest zc) of all triangles in the concept view's pixel grid."""
    H, W = shape
    flat = allP.reshape(-1, 3)
    uv = cam.project(flat).reshape(-1, 3, 2)
    zc = cam.cam(flat)[2].reshape(-1, 3)
    D = np.full((H, W), np.inf)
    for t in range(len(allP)):
        r = _tri_pixels(uv[t, 0], uv[t, 1], uv[t, 2], W, H)
        if r is None:
            continue
        ys, xs, w0, w1, w2 = r
        z = w0 * zc[t, 0] + w1 * zc[t, 1] + w2 * zc[t, 2]
        D[ys, xs] = np.minimum(D[ys, xs], z)
    D = ndimage.minimum_filter(D, size=3)
    return {"D": D, "cam": cam}


def cam_visible(dm, P, tol):
    cam = dm["cam"]; D = dm["D"]
    H, W = D.shape
    uv = cam.project(P)
    zc = cam.cam(P)[2]
    x = uv[:, 0].astype(int); y = uv[:, 1].astype(int)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    out = np.zeros(len(P), bool)
    out[ok] = zc[ok] <= D[y[ok], x[ok]] + tol
    return out


def overlay(ref, model_mask, path):
    """QA image: concept alpha (red), model silhouette (cyan), overlap (white-ish)."""
    r = ref["a_full"]
    H, W = r.shape
    m = np.zeros_like(r)
    mh, mw = model_mask.shape
    m[:min(H, mh), :min(W, mw)] = model_mask[:min(H, mh), :min(W, mw)]
    img = (ref["rgb"] * 0.35 * 255).astype(np.uint8)
    img[r & ~m] = (230, 60, 60); img[m & ~r] = (60, 200, 230)
    img[m & r] = (np.asarray(img[m & r], float) * 0.4 + 140).astype(np.uint8)
    Image.fromarray(img).save(path)


def ortho_mask(tris, view, frame, shape):
    """Model silhouette in a concept ortho view: view 'side' (SideFrame) or 'top' (TopFrame)."""
    H, W = shape
    flat = tris.reshape(-1, 3)
    if view == "side":
        u = frame.pc - flat[:, 1] / frame.s; v = frame.pg - flat[:, 2] / frame.s
    else:
        u = frame.pc + flat[:, 0] / (frame.s * frame.sx); v = frame.py_of(flat[:, 1])
    uv = np.stack([u, v], -1).reshape(-1, 3, 2)
    return _poly_mask(uv, W, H, 1)


# ============================================================================ tracked running gear
class TrackSpec:
    def __init__(self, track_x, width, thick, wheel_r, wheel_ys, idler, sprocket, rollers=(), pitch=0.16,
                 links_per_tile=6, wheel_z=None, wheel_w=0.19, wheel_gap=0.13, idler_r_face=None,
                 sprocket_teeth=11, extra_circles=()):
        self.track_x, self.width, self.thick = track_x, width, thick
        self.wheel_r = wheel_r
        self.wheel_z = thick + wheel_r if wheel_z is None else wheel_z
        self.wheel_ys = list(wheel_ys)
        self.idler = idler            # (y, z, r)
        self.sprocket = sprocket      # (y, z, r)
        self.rollers = list(rollers)  # (y, z, r)
        self.pitch, self.lpt = pitch, links_per_tile
        self.wheel_w, self.wheel_gap = wheel_w, wheel_gap
        self.teeth = sprocket_teeth
        self.extra = list(extra_circles)

    def circles(self):
        return ([(y, self.wheel_z, self.wheel_r) for y in self.wheel_ys] + [self.idler, self.sprocket]
                + self.rollers + self.extra)


def build_running_gear(spec, mat, hull_part=None):
    """Left-side wheels / idler / sprocket as separate objects (hub origins); return rollers into hull_part."""
    objs = {}
    xl = -spec.track_x
    g = spec.wheel_gap
    for i, y in enumerate(spec.wheel_ys):
        W = Part(f"WheelL{i}")
        for dx in (-g, g):
            W.cyl((dx, 0, 0), spec.wheel_r, spec.wheel_w, (0, PI / 2, 0), seg=20)
        W.cyl((-g - spec.wheel_w / 2 - 0.03, 0, 0), spec.wheel_r * 0.36, 0.07, (0, PI / 2, 0), seg=10)
        objs[f"WheelL{i}"] = W.build(mat, bevel=0.0, smooth=40, location=(xl, y, spec.wheel_z))
    iy, iz, ir = spec.idler
    I_ = Part("IdlerL")
    for dx in (-g * 0.9, g * 0.9):
        I_.cyl((dx, 0, 0), ir, spec.wheel_w * 0.95, (0, PI / 2, 0), seg=20)
    I_.cyl((-g - spec.wheel_w / 2 - 0.02, 0, 0), ir * 0.35, 0.07, (0, PI / 2, 0), seg=10)
    objs["IdlerL"] = I_.build(mat, bevel=0.0, smooth=40, location=(xl, iy, iz))
    sy, sz, sr = spec.sprocket
    SP = Part("SprocketL")
    n = spec.teeth
    for dx in (-g * 0.85, g * 0.85):
        ro, ri = [], []
        for k in range(n * 4):
            a = 2 * PI * k / (n * 4)
            rr = sr + 0.035 if (k % 4) in (1, 2) else sr - 0.035
            ro.append((dx - 0.04, math.cos(a) * rr, math.sin(a) * rr))
            ri.append((dx + 0.04, math.cos(a) * rr, math.sin(a) * rr))
        SP.rings([ro, ri])
    SP.cyl((0, 0, 0), sr - 0.08, 2 * g + 0.1, (0, PI / 2, 0), seg=14)
    SP.cyl((-g - 0.12, 0, 0), sr * 0.4, 0.1, (0, PI / 2, 0), seg=10)
    objs["SprocketL"] = SP.build(mat, bevel=0.0, smooth=40, location=(xl, sy, sz))
    if hull_part is not None:
        for s in (-1, 1):
            for (y, z, r) in spec.rollers:
                hull_part.cyl((s * spec.track_x, y, z), r, 0.3, (0, PI / 2, 0), seg=10)
    return objs


def mirror_gear(objs, names):
    out = {}
    for n in names:
        rn = n.replace("WheelL", "WheelR").replace("IdlerL", "IdlerR").replace("SprocketL", "SprocketR")
        out[rn] = mirror_copy_x(objs[n], rn)
    return out


def belt_path(spec, step=0.1):
    from scipy.spatial import ConvexHull
    pts = []
    for (cy, cz, r) in spec.circles():
        rr = r + spec.thick / 2
        for k in range(96):
            a = 2 * PI * k / 96
            pts.append((cy + rr * math.cos(a), cz + rr * math.sin(a)))
    pts = np.array(pts)
    poly = pts[ConvexHull(pts).vertices]
    seg = np.diff(np.vstack([poly, poly[:1]]), axis=0)
    L = np.linalg.norm(seg, axis=1); total = L.sum()
    n = int(round(total / step))
    cum = np.concatenate([[0], np.cumsum(L)])
    out = []
    for k in range(n):
        d = k * total / n
        i = np.searchsorted(cum, d, side="right") - 1
        t = (d - cum[i]) / max(L[i], 1e-9)
        out.append(poly[i] + seg[i] * t)
    return np.array(out), total


def build_tracks(spec, mat, step=0.1):
    path, total = belt_path(spec, step)
    n_links = spec.lpt * max(1, round(total / (spec.pitch * spec.lpt)))
    m_per_v = total / (n_links / spec.lpt)
    n = len(path)
    cen = path.mean(0)
    tang = np.roll(path, -1, 0) - np.roll(path, 1, 0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.stack([tang[:, 1], -tang[:, 0]], 1)
    flip = ((path - cen) * nrm).sum(1) < 0
    nrm[flip] *= -1
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    v_of = list(arc / m_per_v) + [total / m_per_v]
    objs = {}
    for s, name in ((-1, "TrackL"), (1, "TrackR")):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        x_in, x_out = s * (spec.track_x - spec.width / 2), s * (spec.track_x + spec.width / 2)
        h = spec.thick / 2
        corners = [(x_in, +h), (x_out, +h), (x_out, -h), (x_in, -h)]
        u_ranges = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.9), (0.9, 1.0)]
        ring = []
        for k in range(n + 1):
            i = k % n
            ring.append([bm.verts.new((cx, path[i, 0] + nrm[i, 0] * o, path[i, 1] + nrm[i, 1] * o)) for cx, o in corners])
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


def track_colours(ref, rect):
    x0, y0, x1, y1 = rect
    strip = ref["rgb"][y0:y1, x0:x1].reshape(-1, 3)
    lum = strip.mean(1)
    dark = np.median(strip[lum < np.percentile(lum, 30)], 0)
    lite = np.median(strip[lum > np.percentile(lum, 80)], 0)
    return dark, lite


def make_track_texture(dark, lite, lpt, path_png, size=(256, 512), rubber_pads=True):
    Wt, Ht = size
    v = (np.arange(Ht) + 0.5) / Ht * lpt
    f = v % 1.0
    u = (np.arange(Wt) + 0.5) / Wt
    F, U_ = np.meshgrid(f, u, indexing="ij")
    out = np.zeros((Ht, Wt, 3), np.float32)
    ut = U_ / 0.5
    shoe = np.where((F > 0.06) & (F < 0.94), 1.0, 0.25)
    grouser = np.exp(-((F - 0.5) / 0.08) ** 2)
    tread = dark[None, None] * (0.75 + 0.5 * grouser[..., None]) * shoe[..., None]
    if rubber_pads:
        pad = ((np.abs(ut - 0.27) < 0.17) | (np.abs(ut - 0.73) < 0.17)) & (F > 0.15) & (F < 0.85)
        tread = np.where(pad[..., None], dark * 0.55, tread)
    edge = (ut < 0.06) | (ut > 0.94)
    tread = np.where(edge[..., None], lite * (0.8 + 0.3 * np.exp(-((F - 0.5) / 0.2) ** 2))[..., None], tread)
    m = U_ < 0.5; out[m] = tread[m]
    side = lite * 0.6 * (0.55 + 0.45 * np.exp(-((F - 0.5) / 0.22) ** 2))[..., None] * np.where((F > 0.05) & (F < 0.95), 1, 0.4)[..., None]
    m = ((U_ >= 0.5) & (U_ < 0.6)) | (U_ >= 0.9); out[m] = side[m]
    ui = (U_ - 0.6) / 0.3
    inner = dark * 0.85 * np.where((F > 0.06) & (F < 0.94), 1, 0.35)[..., None]
    horn = (np.abs(ui - 0.5) < 0.08) & (F > 0.3) & (F < 0.7)
    inner = np.where(horn[..., None], lite * 0.9, inner)
    m = (U_ >= 0.6) & (U_ < 0.9); out[m] = inner[m]
    rng = np.random.RandomState(11)
    out *= (0.92 + 0.16 * ndimage.gaussian_filter(rng.rand(Ht, Wt), 2.0))[..., None]
    a = np.clip(out[::-1] * 255 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGB").save(path_png)


# ============================================================================ wheeled running gear
def tyre_part(name, r, w, rim_r, hub_r=None, seg=22, outer=-1, rim_depth=0.06, lugs=True):
    """Tyre + rim + hub around the local X axis; outer side is `outer` (-1 = -X for left wheels)."""
    P = Part(name)
    hw = w / 2
    s = outer
    sh = min(0.06, r * 0.15)
    prof = [(-s * hw, rim_r), (-s * hw, r - sh), (-s * (hw - sh * 0.4), r - sh * 0.25), (-s * (hw - sh), r),
            (s * (hw - sh), r), (s * (hw - sh * 0.4), r - sh * 0.25), (s * hw, r - sh), (s * hw, rim_r)]
    lathe(P, (0, 0, 0), prof, seg=seg)
    # rim dish (recessed on the outer side) + hub
    P.cyl((s * (hw - rim_depth / 2 - 0.01), 0, 0), rim_r, w - 2 * rim_depth, (0, PI / 2, 0), seg=seg)
    hr = hub_r or rim_r * 0.45
    P.cyl((s * (hw - rim_depth * 0.6), 0, 0), hr, rim_depth * 1.2, (0, PI / 2, 0), seg=12)
    if lugs:
        for k in range(seg // 2):
            a = 2 * PI * (k + 0.5) / (seg // 2)
            c = Vector((0, math.cos(a) * (r - 0.006), math.sin(a) * (r - 0.006)))
            P.box(c, (w * 0.8, 0.07, 0.03), (a - PI / 2, 0, 0))
    return P


def build_wheels(specs, mat, steer=("FL", "FR")):
    """specs: list of (suffix, x, y, z, r, w, rim_r). Left wheels (x<0) authored, right = mirror copies
    sharing UVs. Steering wheels get SteerXX empties at the hub (yaw about local Y in Godot)."""
    objs = {}
    left = []
    for suf, x, y, z, r, w, rim in specs:
        if x < 0:
            o = tyre_part(f"Wheel{suf}", r, w, rim, outer=-1).build(mat, bevel=0.0, smooth=50, location=(x, y, z))
            objs[f"Wheel{suf}"] = o; left.append(f"Wheel{suf}")
    for suf, x, y, z, r, w, rim in specs:
        if x > 0:
            lsuf = suf[:-1] + "L"
            o = mirror_copy_x(objs[f"Wheel{lsuf}"], f"Wheel{suf}")
            o.location = (x, y, z)
            objs[f"Wheel{suf}"] = o
    steers = {}
    for suf in steer:
        w = objs.get(f"Wheel{suf}")
        if w is None:
            continue
        e = empty(f"Steer{suf}", w.location)
        parent_to(w, e)
        steers[f"Steer{suf}"] = e
    return objs, left, steers


# ============================================================================ texturing
def make_depth(allP, bounds, cell):
    (x0, y0, z0), (x1, y1, z1) = bounds
    d = {
        "top": depth_map(allP, (0, 1), 2, (x0, y0), (x1, y1), cell, +1),
        "left": depth_map(allP, (1, 2), 0, (y0, z0), (y1, z1), cell, -1),
        "right": depth_map(allP, (1, 2), 0, (y0, z0), (y1, z1), cell, +1),
        "front": depth_map(allP, (0, 2), 1, (x0, z0), (x1, z1), cell, +1),
        "rear": depth_map(allP, (0, 2), 1, (x0, z0), (x1, z1), cell, -1),
        "bottom": depth_map(allP, (0, 1), 2, (x0, y0), (x1, y1), cell, -1),
    }
    return d


class ShadeCfg:
    def __init__(self, side, top, cams=None, k=3.0, k34=4.0, w34=1.0, mud_h=1.0, mud=(0.33, 0.29, 0.21),
                 mud_amt=0.55, rubber_objs=(), rubber_col=(0.075, 0.072, 0.068), tyre_axis_r=None,
                 overrides=None, under=(0.10, 0.10, 0.075), side_weight=1.0, top_weight=1.0, hubs=None,
                 hub_period=40.0, hub_angle=-90.0):
        self.side, self.top = side, top
        self.cams = cams or {}
        self.k, self.k34, self.w34 = k, k34, w34
        self.mud_h, self.mud, self.mud_amt = mud_h, np.array(mud), mud_amt
        self.rubber_objs = set(rubber_objs)
        self.rubber_col = np.array(rubber_col)
        self.tyre_axis_r = tyre_axis_r or {}
        self.overrides = overrides or []      # callables (P, N, names_per_texel, col) -> col
        self.under = np.array(under)
        self.sw, self.tw = side_weight, top_weight
        # rotation-invariant wheels: name -> (hub_y, hub_z, r_tread or None). Texels of these objects are
        # re-sampled from the side view at the same radius but at an angle folded into the visible sector
        # around `hub_angle` (deg in the y-z plane, -90 = bottom), period `hub_period`, so a spinning wheel
        # never shows skirt / fender colours baked into its hidden half.
        self.hubs = hubs or {}
        self.hub_period, self.hub_angle = hub_period, hub_angle


def shade_generic(P, N, names, refs, depth, cfg):
    k = cfg.k
    nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]
    S, T = cfg.side, cfg.top
    c_top = sample(refs["top"], T.pc + P[:, 0] / (T.s * T.sx), T.py_of(P[:, 1]))
    c_side = sample(refs["side"], S.pc - P[:, 1] / S.s, S.pg - P[:, 2] / S.s)
    tol = 0.06
    v_top = visible(depth["top"], P, tol + 0.03 * np.sqrt(np.clip(1 - nz ** 2, 0, 1)) / np.maximum(nz, 0.25))
    v_l = visible(depth["left"], P, tol); v_r = visible(depth["right"], P, tol)
    v_side = np.where(nx < 0, v_l, v_r)
    w_t = np.clip(nz, 0, 1) ** k * v_top * cfg.tw
    w_s = np.abs(nx) ** k * v_side * cfg.sw
    w_b = np.clip(-nz, 0, 1) ** k
    num = c_top * w_t[:, None] + c_side * w_s[:, None] + cfg.under * (w_b * 0.5)[:, None]
    den = w_t + w_s + w_b * 0.5
    num0 = c_top * (np.clip(nz, 0, 1) ** k)[:, None] + c_side * (np.abs(nx) ** k)[:, None] + cfg.under * w_b[:, None]
    den0 = np.clip(nz, 0, 1) ** k + np.abs(nx) ** k + w_b
    fallback_fr = np.zeros(len(P))
    for key, cam in cfg.cams.items():
        ref = refs[key]
        uv = cam.project(P)
        H, W = ref["a"].shape
        xi = np.clip(uv[:, 0].astype(int), 0, W - 1); yi = np.clip(uv[:, 1].astype(int), 0, H - 1)
        inside = ref["a"][yi, xi] & (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
        c = sample(ref, uv[:, 0], uv[:, 1])
        ndv = np.clip((N * cam.view_dirs(P)).sum(1), 0, 1)
        vis = cam_visible(depth[key], P, 0.07)
        w = ndv ** cfg.k34 * vis * inside * cfg.w34
        # 3/4 views only take over faces that point mostly front / rear (+-Y) or are not covered by ortho views
        fr = np.clip(np.abs(ny) * 1.6 - 0.25, 0, 1)
        w = w * np.maximum(fr, 0.15)
        num += c * w[:, None]; den += w
        num0 += c * (ndv ** cfg.k34 * fr)[:, None]; den0 += ndv ** cfg.k34 * fr
        fallback_fr += w
    # faces facing front/rear that no camera covers: side view sampled at the face (streak) as M88 did
    w_fr = np.abs(ny) ** k * 0.35
    vf = visible(depth["front"], P, tol) | visible(depth["rear"], P, tol)
    num += c_side * (w_fr * vf * (fallback_fr < 0.05))[:, None] * 0.85
    den += w_fr * vf * (fallback_fr < 0.05)
    num0 += c_side * w_fr[:, None]; den0 += w_fr
    col = np.where((den > 0.02)[:, None], num / np.maximum(den, 1e-6)[:, None],
                   0.6 * num0 / np.maximum(den0, 1e-6)[:, None])
    if cfg.hubs:
        for name, (hy, hz, rt) in cfg.hubs.items():
            m = names == name
            if not m.any():
                continue
            dy = P[m, 1] - hy; dz = P[m, 2] - hz
            rho = np.sqrt(dy ** 2 + dz ** 2)
            th = np.degrees(np.arctan2(dz, dy))
            per = cfg.hub_period
            th2 = np.radians(cfg.hub_angle + ((th - cfg.hub_angle + per / 2) % per) - per / 2)
            py_ = S.pc - (hy + rho * np.cos(th2)) / S.s
            pz_ = S.pg - (hz + rho * np.sin(th2)) / S.s
            c = sample(refs["side"], py_, pz_)
            face = np.abs(N[m, 0]) > 0.5
            inner = N[m, 0] * (1 if True else 1) > 0          # left wheels: +X faces the hull
            c = np.where(inner[:, None], c * 0.55, c)
            cm = col[m]
            cm[face] = c[face]
            if rt is not None:
                tread = ~face
                cm[tread] = cfg.rubber_col * (0.9 + 0.2 * value_noise(P[m][tread], 0.1, seed=9))[:, None] + c[tread] * 0.25
            col[m] = cm
    # rubber on tyre treads
    if cfg.rubber_objs:
        is_rub = np.array([n in cfg.rubber_objs for n in names])
        tread = is_rub & (np.abs(nx) < 0.55)
        rub = cfg.rubber_col * (0.85 + 0.3 * value_noise(P, 0.15, seed=5))[:, None]
        col = np.where(tread[:, None], rub, col)
    for fn in cfg.overrides:
        col = fn(P, N, names, col)
    nse = value_noise(P, 0.9, seed=3)
    low = np.clip((cfg.mud_h - P[:, 2]) / cfg.mud_h, 0, 1) ** 1.5 * (0.2 + 0.3 * nse) * cfg.mud_amt / 0.55
    col = col * (1 - low[:, None]) + cfg.mud * low[:, None] * (0.6 + 0.4 * col.mean(1, keepdims=True) / 0.3)
    col *= (0.93 + 0.12 * value_noise(P, 0.35, seed=7))[:, None]
    return np.clip(col, 0, 1)


def texture_atlas(objs, refs, cfg, size, out_png, ao_objs=None, ao_size=1024, ao_strength=0.5, cell=0.02,
                  depth_objs=None, margin=0.4):
    bpy.context.view_layer.update()
    P, Nn, U, I = world_tris(objs, with_uv=True)
    dobjs = depth_objs or [o for o in bpy.context.scene.objects if o.type == "MESH"]
    allP = world_tris(dobjs)[0]
    lo = allP.reshape(-1, 3).min(0) - margin; hi = allP.reshape(-1, 3).max(0) + margin
    depth = make_depth(allP, (tuple(lo), tuple(hi)), cell)
    for k, cam in cfg.cams.items():
        depth[k] = cam_depth(allP, cam, refs[k]["a"].shape)
    pos, nor, oid, msk = uv_raster(P, Nn, U, I, size)
    Pm, Nm = pos[msk].astype(np.float64), nor[msk].astype(np.float64)
    names = np.array([objs[i].name for i in oid[msk]])
    col = np.zeros((size, size, 3), np.float32)
    col[msk] = shade_generic(Pm, Nm, names, refs, depth, cfg)
    if ao_strength > 0:
        ao = bake_ao(ao_objs or objs, ao_size, samples=16, distance=0.8)
        ao = np.asarray(Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR),
                        np.float32) / 255.0
        f = (1 - ao_strength + ao_strength * ao)
        if cfg.hubs:
            hub_ids = [i for i, o in enumerate(objs) if o.name in cfg.hubs]
            f = np.where(np.isin(oid, hub_ids), 1.0, f)
        col *= f[..., None]
    col = fill_nearest(col, msk)
    save_png(col, out_png)
    return out_png, float(msk.mean())


def attach_texture(mat, img):
    nt = mat.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])


# ============================================================================ export / report
def export_glb(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True)


def all_descendants(roots):
    out = []
    for r in roots:
        out.append(r)
        out.extend(all_descendants(list(r.children)))
    return out


def report(vid, export, extra_lines=()):
    meshes = [o for o in export if o.type == "MESH"]
    lines = [f"{vid}: tris total {tri_count(meshes)}"]
    for o in export:
        wl = o.matrix_world.translation
        t = tri_count([o]) if o.type == "MESH" else 0
        par = o.parent.name if o.parent else "-"
        lines.append(f"  {o.name:12s} {o.type:5s} tris {t:6d} parent {par:10s} world {tuple(round(v, 3) for v in wl)}"
                     f" local {tuple(round(v, 3) for v in o.location)}")
    lines += list(extra_lines)
    txt = "\n".join(lines)
    print(txt)
    return txt


# ============================================================================ previews
def setup_preview_scene(samples=20):
    cam = m88k.setup_preview_scene()
    sc = bpy.context.scene
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    try:
        sc.render.threads_mode = "FIXED"; sc.render.threads = 2
    except Exception:
        pass
    return cam


def preview_sheet(vid, title, prev_dir, length, width, height, rts_dist, close_dist, close_az=-38, quick=False,
                  res=(640, 400), samples=20):
    cam = setup_preview_scene(samples)
    zc = height / 2
    ar = res[0] / res[1]
    fr = max(width, height * ar) * 1.35
    sd = max(length, height * ar) * 1.12
    views = [("front", 0, 6, (0, 0, zc), fr, None),
             ("side", -90, 6, (0, 0, zc), sd, None),
             ("rear", 180, 6, (0, 0, zc), fr, None),
             ("top", 0, 90, (0, 0, zc), max(length, width * ar) * 1.1, (-1, 0, 0)),
             ("rts", 45, 52, (0, 0, zc * 0.6), None, None),
             ("close34", close_az, 18, (0, 0, zc * 0.8), None, None)]
    if quick:
        views = [v for v in views if v[0] in ("rts",)]
    shots = []
    for name, az, el, tgt, ortho, up in views:
        dist = {"rts": rts_dist, "close34": close_dist}.get(name, 60)
        if ortho:
            aim(cam, tgt, az, el, dist, ortho=ortho, roll_up=up)
        else:
            aim(cam, tgt, az, el, dist, lens=50)
        p = os.path.join(prev_dir, f"m2_{vid}_{name}.png")
        render(p, res)
        shots.append((p, name))
    if not quick:
        contact_sheet(shots, os.path.join(prev_dir, f"m2_{vid}_sheet.png"), cols=3, cell=res, title=title)
        for p, _ in shots:            # keep only the sheet (deliverable); per-view files are intermediates
            try:
                os.remove(p)
            except OSError:
                pass
    return shots


# ============================================================================ two-view component (visual hull)
def prism_side(name, pts_yz, x0, x1):
    p = Part(name); p.side(pts_yz, x0, x1); return p


def vhull(name, side_yz, plan_xy, z_range, x_range, mat=None, bevel=0.0, angle=35, plan_top=1.0):
    """Intersection of a side-profile prism (extruded across x_range) and a plan prism (z_range).
    Returns a Part-like built object (mesh object)."""
    a = Part(name + "_s"); a.side(side_yz, x_range[0], x_range[1])
    oa = a.build(None, bevel=0.0)
    b = Part(name + "_p"); b.plan(plan_xy, z_range[0], z_range[1], top=plan_top)
    ob = b.build(None, bevel=0.0)
    m = oa.modifiers.new("isect", "BOOLEAN"); m.operation = "INTERSECT"; m.object = ob; m.solver = "EXACT"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = oa; oa.select_set(True)
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(ob, do_unlink=True)
    oa.name = name; oa.data.name = name
    bm = bmesh.new(); bm.from_mesh(oa.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(oa.data); bm.free()
    if mat is not None:
        oa.data.materials.clear(); oa.data.materials.append(mat)
    if bevel:
        bv = oa.modifiers.new("bv", "BEVEL"); bv.width = bevel; bv.segments = 1
        bv.limit_method = "ANGLE"; bv.angle_limit = math.radians(angle); bv.use_clamp_overlap = True
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = oa; oa.select_set(True)
        bpy.ops.object.modifier_apply(modifier=bv.name)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = oa; oa.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(33))
    return oa


def join_objs(target, others):
    bpy.ops.object.select_all(action="DESELECT")
    for o in others:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    return target


def finish_wheels(objs, left_names, steer=("FL", "FR")):
    """Post-UV: mirror left wheels to the right (sharing UVs), add Steer empties for steering wheels."""
    for n in left_names:
        rn = n[:-1] + "R" if n.endswith("L") else n.replace("L", "R")
        objs[rn] = mirror_copy_x(objs[n], rn)
    for suf in steer:
        w = objs.get(f"Wheel{suf}")
        if w is None:
            continue
        e = empty(f"Steer{suf}", w.location)
        parent_to(w, e)
        objs[f"Steer{suf}"] = e
    return objs


# ============================================================================ pipeline
class Ctx:
    def __init__(self, vid, side, top):
        self.vid = vid
        self.refs, self.me = load_refs(vid)
        self.S, self.T = side, top
        self.mat = image_material(f"SA_{vid.title().replace('_', '')}", None, rough=0.78)
        self.track_mat = image_material("SA_TrackScroll", None, rough=0.9, metal=0.1)
        self.objs = {}
        self.team = []         # (target_name, Part)
        self.notes = []


def run_vehicle(vid, side, top, build, title, qa_dir=None, argv=None):
    """build(ctx) -> dict(uv=[names], post_uv=callable(objs) or None, tracks=TrackSpec or None,
    track_rect=(x0,y0,x1,y1), roots=[names], cams={'front34': az0, 'rear34': az0}, preview={...},
    cfg={...ShadeCfg kwargs}, extra=[report lines])"""
    opts = parse_args(argv)
    out = opts["out"] or os.path.join(REPO, "godot", "assets", "units3d", vid)
    os.makedirs(out, exist_ok=True)
    qa_dir = qa_dir or os.environ.get("VEH_QA_DIR") or os.path.join(out, "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    if qa_dir.startswith(out):
        open(os.path.join(qa_dir, ".gdignore"), "w").close()
    reset_scene()
    ctx = Ctx(vid, side, top)
    spec = build(ctx)
    objs = ctx.objs
    uv_objs = [objs[n] for n in spec["uv"]]
    bpy.context.view_layer.update()
    smart_uv(uv_objs, margin=0.003)
    if spec.get("post_uv"):
        spec["post_uv"](objs)
    extra = list(spec.get("extra", []))
    tracks = None
    if spec.get("tracks") is not None:
        tracks, m_per_v, total, n_links = build_tracks(spec["tracks"], ctx.track_mat)
        objs.update(tracks)
        extra.append(f"track loop {total:.3f} m, links {n_links}, link pitch {total / n_links:.4f} m, "
                     f"metres per V {m_per_v:.4f} (tile = {spec['tracks'].lpt} links)")
    bpy.context.view_layer.update()
    meshes = [o for o in objs.values() if o.type == "MESH"]
    allP = world_tris(meshes)[0]
    # --- fit the 3/4 concept cameras to the silhouettes
    lo = allP.reshape(-1, 3).min(0); hi = allP.reshape(-1, 3).max(0)
    target = (lo + hi) / 2
    cams = {}
    for key, az0 in spec.get("cams", {}).items():
        cams[key] = fit_cam(allP, ctx.refs[key], az0, target, key)
        extra.append(cams[key].report())
    # --- QA overlays (silhouette agreement)
    os.makedirs(qa_dir, exist_ok=True)
    for key, frame in (("side", ctx.S), ("top", ctx.T)):
        m = ortho_mask(allP, key, frame, ctx.refs[key]["a_full"].shape)
        r = ctx.refs[key]["a_full"]
        iou = (m & r).sum() / max((m | r).sum(), 1)
        extra.append(f"{key} silhouette IoU {iou:.3f}")
        overlay(ctx.refs[key], m, os.path.join(qa_dir, f"{vid}_ov_{key}.png"))
    for key, cam in cams.items():
        _, m = silhouette_iou(cam, allP, ctx.refs[key]["a_full"], 1)
        overlay(ctx.refs[key], m, os.path.join(qa_dir, f"{vid}_ov_{key}.png"))
    # --- texture
    kw = dict(spec.get("cfg", {}))
    cfg = ShadeCfg(ctx.S, ctx.T, cams=cams, **kw)
    albedo = os.path.join(out, f"{vid}_albedo.png")
    ao_objs = [o for o in meshes if o.name not in ("TrackL", "TrackR")]
    _, cover = texture_atlas(uv_objs, ctx.refs, cfg, 2048, albedo, ao_objs=ao_objs, ao_strength=0.5)
    extra.append(f"atlas coverage {cover:.3f}")
    attach_texture(ctx.mat, load_image(albedo, f"{vid}_albedo"))
    if tracks:
        trk = os.path.join(out, f"{vid}_track.png")
        dark, lite = track_colours(ctx.refs["side"], spec["track_rect"])
        make_track_texture(dark, lite, spec["tracks"].lpt, trk)
        attach_texture(ctx.track_mat, load_image(trk, f"{vid}_track"))
    # --- team colour panels
    for tgt, part in ctx.team:
        o = part.build(None, bevel=0.0)
        join_team(objs[tgt], o)
    # --- export
    roots = [objs[n] for n in spec["roots"]]
    export = all_descendants(roots)
    glb = os.path.join(out, f"{vid}.glb")
    export_glb(export, glb)
    txt = report(vid, export, extra)
    with open(os.path.join(qa_dir, f"{vid}_report.txt"), "w") as f:
        f.write(txt + "\n")
    print("GLB", glb)
    if opts["do_prev"]:
        pv = spec["preview"]
        prev_dir = opts["prev"]
        if opts["quick"]:
            prev_dir = qa_dir
        os.makedirs(prev_dir, exist_ok=True)
        preview_sheet(vid, title, prev_dir, quick=opts["quick"], **pv)
    return objs
