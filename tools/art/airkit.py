"""Steel Accord - shared kit for the M3 U.S. aircraft roster (bpy 5.x).

Generalises the approved CH-47 pilot pipeline (tools/art/air_ch47_3d.py / veh_m88_3d.py; their files and
outputs are not changed, the library half of veh_m88_3d is imported read-only):

  * reference views: sheet-quadrant extraction (connected alpha components of one 2x2 turnaround cell),
    rotation/flip to the canonical orientation (side view nose LEFT, top view nose UP)
  * view frames: side view = one uniform scale (defines world length Y and height Z); top view = its own
    across-scale (X) and a piecewise-linear Y rectification through landmarks (concept views disagree)
  * builders: superellipse fuselage loft, NACA-section lifting surfaces (wings, stabilisers, canted fins),
    bodies of revolution on any axis (nacelles, tanks, missiles, bombs, barrels), landing gear,
    rotors / propellers with real thin blades (hub origin, spin axis = a local axis), team panels, empties
  * texture: depth-tested projection of the top view (up-facing texels) and side view (+-X facing texels),
    blurred top colour on the underside, per-object overrides (flat colours for gear / glass etc.),
    Cycles AO bake multiplied in, one albedo atlas
  * QA: silhouette fit overlay of the model on the concept views, cheap Cycles contact sheet

Conventions: metres; forward = Blender +Y (Godot -Z); up = +Z; root origin = ground contact (gear bottom)
under the fuselage midpoint; aircraft left = -X. All exported objects are top-level nodes.
"""
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFile, ImageFilter  # noqa: E402
from scipy import ndimage  # noqa: E402

ImageFile.LOAD_TRUNCATED_IMAGES = True

PI = math.pi
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
HOME = os.path.abspath(os.path.join(REPO, ".."))
INC_A = os.path.join(HOME, "incoming", "a", "individual_views")
INC_AIR = os.path.join(HOME, "incoming_air")
INC_X = os.path.join(INC_AIR, "US_Aircraft_Game_Assets_Expanded_1")
INC_F35 = os.path.join(HOME, "incoming_f35")
INC_LIFT = os.path.join(HOME, "incoming_airlift", "aircraft_image_assets")
SPRITES = os.path.join(REPO, "godot", "assets", "aircraft")
ROTOR_PNG = os.path.join(REPO, "godot", "assets", "us", "rotors")
OUT3D = os.path.join(REPO, "godot", "assets", "units3d")
SCREENS = os.path.join(REPO, "docs", "screens")


# ============================================================================ reference images (no bpy)
def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA"))


def sheet_cell(path, cell, dil=6, min_frac=0.01):
    """Return the full sheet RGBA with alpha kept only on the connected components that belong to one
    cell of a 2x2 turnaround sheet. cell = 'tl' | 'tr' | 'bl' | 'br'. A component belongs to the cell
    in which its (alpha-weighted) centroid lies; parts may extend across the visual cell boundary."""
    a = load_rgba(path).copy()
    H, W = a.shape[:2]
    m = a[..., 3] > 24
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=dil))
    lab = lab * m
    keep = np.zeros_like(m)
    cx_want = 0 if cell[1] == "l" else 1
    cy_want = 0 if cell[0] == "t" else 1
    tot = m.sum()
    for k in range(1, n + 1):
        mk = lab == k
        s = mk.sum()
        if s < min_frac * tot / 4:
            continue
        ys, xs = np.nonzero(mk)
        if int(xs.mean() >= W / 2) == cx_want and int(ys.mean() >= H / 2) == cy_want:
            keep |= mk
    a[..., 3] = np.where(keep, a[..., 3], 0)
    return a


def orient(a, rot=0, flip=False):
    """rot: multiples of 90 deg counter-clockwise (np.rot90); flip: mirror left-right (after rot)."""
    if rot:
        a = np.rot90(a, rot)
    if flip:
        a = a[:, ::-1]
    return np.ascontiguousarray(a)


def ref_from_rgba(a, erode=2, keep_largest=False, path=""):
    """Like veh_m88_3d.load_ref but from an RGBA array; returns dict(rgb, a, mean, shape)."""
    f = a.astype(np.float32) / 255.0
    rgb, al = f[..., :3], f[..., 3]
    m = al > 0.5
    if keep_largest:
        lab, n = ndimage.label(m)
        if n > 1:
            sizes = ndimage.sum(m, lab, range(1, n + 1))
            m = lab == (1 + int(np.argmax(sizes)))
    raw = m.copy()
    if erode:
        m = ndimage.binary_erosion(m, iterations=erode)
    from veh_m88_3d import fill_nearest
    rgb = fill_nearest(rgb, m)
    return {"rgb": rgb, "a": m, "raw": raw, "mean": rgb[m].mean(0), "path": path}


def blurred(ref, sigma):
    r = dict(ref)
    r["rgb"] = np.stack([ndimage.gaussian_filter(ref["rgb"][..., c], sigma) for c in range(3)], -1)
    return r


def save_rgba(a, path):
    Image.fromarray(a, "RGBA").save(path)


# ============================================================================ frames
def _interp_ext(x, xp, fp):
    """np.interp with linear extrapolation; xp ascending."""
    x = np.asarray(x, float)
    y = np.interp(x, xp, fp)
    lo = x < xp[0]; hi = x > xp[-1]
    if np.any(lo):
        y = np.where(lo, fp[0] + (x - xp[0]) * (fp[1] - fp[0]) / (xp[1] - xp[0]), y)
    if np.any(hi):
        y = np.where(hi, fp[-1] + (x - xp[-1]) * (fp[-1] - fp[-2]) / (xp[-1] - xp[-2]), y)
    return y


class SideFrame:
    """Side view, nose LEFT. y = (cx - px) * s, z = (gy - py) * s."""

    def __init__(self, s, cx, gy):
        self.s, self.cx, self.gy = s, cx, gy

    def __call__(self, px, py):
        return ((self.cx - px) * self.s, (self.gy - py) * self.s)

    def y(self, px):
        return (self.cx - np.asarray(px, float)) * self.s

    def z(self, py):
        return (self.gy - np.asarray(py, float)) * self.s

    def px(self, y):
        return self.cx - np.asarray(y, float) / self.s

    def py(self, z):
        return self.gy - np.asarray(z, float) / self.s


class TopFrame:
    """Top view, nose UP. x = (px - cx) * sx; y from py by piecewise-linear landmarks [(py, y), ...]."""

    def __init__(self, sx, cx, marks):
        self.sx, self.cx = sx, cx
        marks = sorted(marks, key=lambda m: m[1])         # ascending world y (tail first)
        self.my = np.array([m[1] for m in marks], float)
        self.mp = np.array([m[0] for m in marks], float)

    def __call__(self, px, py):
        return (float(self.x(px)), float(self.y(py)))

    def x(self, px):
        return (np.asarray(px, float) - self.cx) * self.sx

    def y(self, py):
        order = np.argsort(self.mp)
        return _interp_ext(py, self.mp[order], self.my[order])

    def px(self, x):
        return self.cx + np.asarray(x, float) / self.sx

    def py(self, y):
        return _interp_ext(y, self.my, self.mp)


def polyline_fn(pts):
    """pts [(u, v), ...] -> f(u) by linear interpolation (sorted by u, clamped)."""
    pts = sorted(pts)
    u = np.array([p[0] for p in pts], float); v = np.array([p[1] for p in pts], float)
    return lambda q: np.interp(q, u, v)


# ============================================================================ bpy part
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import veh_m88_3d as L  # noqa: E402  (library half only)
from veh_m88_3d import Part  # noqa: E402,F401


def superellipse_ring(y, xc, half_w, zc, half_h, n, seg, z_top_scale=1.0):
    ring = []
    for k in range(seg):
        a = 2 * PI * k / seg
        c, s = math.cos(a), math.sin(a)
        x = xc + half_w * math.copysign(abs(c) ** (2 / n), c)
        hh = half_h * (z_top_scale if s > 0 else 1.0)
        z = zc + hh * math.copysign(abs(s) ** (2 / n), s)
        ring.append((x, y, z))
    return ring


def fuselage(P, ys, ztop, zbot, hw, n=2.6, seg=32, xc=0.0, min_hw=0.04, min_h=0.04):
    """Loft superellipse sections. ztop/zbot/hw/n: callables of world y (or constants for n)."""
    rings = []
    for y in ys:
        zt, zb = float(ztop(y)), float(zbot(y))
        h = max((zt - zb) / 2, min_h)
        nn = float(n(y)) if callable(n) else n
        rings.append(superellipse_ring(y, xc, max(float(hw(y)), min_hw), (zt + zb) / 2, h, nn, seg))
    P.rings(rings)


def airfoil_ring(npts=6):
    """Closed airfoil outline (chord fraction xc, half-thickness factor) for a unit NACA 00xx.
    Returns list of (xc, sign) points: upper TE->LE, lower LE->TE (no duplicate LE)."""
    xs = [1.0, 0.75, 0.45, 0.2, 0.06, 0.0][:npts] if npts <= 6 else list(np.linspace(1, 0, npts))
    up = [(x, 1) for x in xs]
    lo = [(x, -1) for x in reversed(xs[:-1])]
    return up + lo


def naca_t(x, t):
    x = min(max(x, 0.0), 1.0)
    return 5 * t * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4) + 0.004 * t


def surface(P, sections, caps=True, npts=6):
    """Lifting surface lofted through sections [(le, te, t_ratio, nrm), ...] (world Vectors / tuples).
    nrm = thickness direction (unit). Works for wings (nrm ~ +Z), fins (nrm ~ +-X), canted fins."""
    prof = airfoil_ring(npts)
    rings = []
    for le, te, t, nrm in sections:
        le, te, nrm = Vector(le), Vector(te), Vector(nrm).normalized()
        ch = (te - le).length
        ring = []
        for x, sg in prof:
            p = le + (te - le) * x + nrm * (sg * naca_t(x, t) * ch)
            ring.append(tuple(p))
        rings.append(ring)
    P.rings(rings, caps=caps)


def wing_sections(top, side, pts, z_root, dihedral_deg=0.0, t_root=0.12, t_tip=0.08, mirror_x=1, sweep_z=None):
    """pts: [(px, le_py, te_py), ...] measured on the TOP view for the right wing (px > cx), root first.
    Returns sections for surface(). z of each section = z_root + |x - x_root| * tan(dihedral)."""
    out = []
    x0 = float(top.x(pts[0][0]))
    xs = [float(top.x(p[0])) for p in pts]
    span = max(abs(xs[-1] - x0), 1e-6)
    for (px, lpy, tpy), x in zip(pts, xs):
        f = abs(x - x0) / span
        z = z_root + abs(x - x0) * math.tan(math.radians(dihedral_deg))
        t = t_root + (t_tip - t_root) * f
        le = (mirror_x * x, float(top.y(lpy)), z)
        te = (mirror_x * x, float(top.y(tpy)), z)
        out.append((le, te, t, (0, 0, 1)))
    return out


def mirror_sections(secs):
    return [((-le[0], le[1], le[2]), (-te[0], te[1], te[2]), t, (-n[0], n[1], n[2])) for le, te, t, n in secs][::-1]


def fin_sections(side, pts, x=0.0, cant_deg=0.0, t_root=0.08, t_tip=0.06, side_sign=1):
    """Vertical/canted fin from SIDE-view measurements pts [(le_px, te_px, py), ...] root first.
    The fin root is at lateral offset x; cant leans the fin outward (side_sign +1 = towards +X)."""
    out = []
    z0 = float(side.z(pts[0][2]))
    hmax = max(abs(float(side.z(p[2])) - z0) for p in pts) or 1.0
    ca, sa = math.cos(math.radians(cant_deg)), math.sin(math.radians(cant_deg))
    for lpx, tpx, py in pts:
        h = float(side.z(py)) - z0
        f = abs(h) / hmax
        # canted: height h along the fin span direction (sa*side_sign, 0, ca) measured as vertical rise
        span = h / max(ca, 1e-3)
        off = Vector((side_sign * sa * span, 0, ca * span))
        base = Vector((x, 0, z0))
        le = base + off + Vector((0, float(side.y(lpx)), 0))
        te = base + off + Vector((0, float(side.y(tpx)), 0))
        nrm = Vector((ca * side_sign, 0, -sa))
        t = t_root + (t_tip - t_root) * f
        out.append((tuple(le), tuple(te), t, tuple(nrm)))
    return out


def body_rev(P, p0, p1, radii, seg=16, squash=1.0, up=(0, 0, 1)):
    """Body of revolution from p0 to p1; radii [(t 0..1, r), ...]. squash scales the 'up' semi-axis."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0)
    Ln = ax.length
    ax.normalize()
    u = Vector(up)
    if abs(u.dot(ax)) > 0.95:
        u = Vector((1, 0, 0))
    e1 = u.cross(ax).normalized()           # lateral
    e2 = ax.cross(e1).normalized()          # ~up
    rings = []
    for t, r in radii:
        c = p0 + ax * (Ln * t)
        r = max(r, 0.004)
        ring = []
        for k in range(seg):
            a = 2 * PI * k / seg
            ring.append(tuple(c + e1 * (r * math.cos(a)) + e2 * (r * squash * math.sin(a))))
        rings.append(ring)
    P.rings(rings)


def missile(P, nose, length, r, fins=True, seg=10):
    """Simple missile along -Y from its nose point (pointing +Y)."""
    n = Vector(nose)
    tail = n - Vector((0, length, 0))
    body_rev(P, tail, n, [(0, r * 0.9), (0.02, r), (0.85, r), (0.95, r * 0.6), (1.0, r * 0.12)], seg=seg)
    if fins:
        for k in range(4):
            a = PI / 4 + k * PI / 2
            d = Vector((math.cos(a), 0, math.sin(a)))
            P.beam(tail + Vector((0, 0.05, 0)) + d * r, tail + Vector((0, 0.05, 0)) + d * (r * 2.6), 0.18, 0.012,
                   up=(0, 1, 0))


def bomb(P, nose, length, r, seg=12):
    n = Vector(nose)
    tail = n - Vector((0, length, 0))
    body_rev(P, tail, n, [(0, r * 0.35), (0.12, r * 0.75), (0.3, r), (0.72, r), (0.92, r * 0.7), (1.0, r * 0.15)],
             seg=seg)
    for k in range(4):
        a = PI / 4 + k * PI / 2
        d = Vector((math.cos(a), 0, math.sin(a)))
        P.beam(tail + Vector((0, 0.06, 0)) + d * (r * 0.3), tail + Vector((0, 0.06, 0)) + d * (r * 1.05), length * 0.16,
               0.012, up=(0, 1, 0))


def pylon(P, top_center, length, depth, width=0.1):
    c = Vector(top_center)
    P.box((c.x, c.y, c.z - depth / 2), (width, length, depth))


def gear_leg(P, wheel_c, r, width, strut_top, twin=False, seg=14, axle_x=None):
    """Wheel(s) at wheel_c (centre; bottom at z = wheel_c.z - r) + oleo strut up to strut_top."""
    wc = Vector(wheel_c)
    xs = [wc.x - width * 0.75, wc.x + width * 0.75] if twin else [wc.x]
    for x in xs:
        P.cyl((x, wc.y, wc.z), r, width, (0, PI / 2, 0), seg=seg)
        P.cyl((x, wc.y, wc.z), r * 0.5, width * 1.15, (0, PI / 2, 0), seg=8)
    top = Vector(strut_top)
    P.rod(Vector((wc.x, wc.y, wc.z)), top, max(r * 0.22, 0.05), seg=8)
    if twin:
        P.box((wc.x, wc.y, wc.z), (width * 2.2, 0.08, 0.08))


def empty(name, loc, rot=(0, 0, 0), size=0.3):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"; e.empty_display_size = size
    bpy.context.scene.collection.objects.link(e)
    e.location = Vector(loc)
    e.rotation_euler = rot
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


def join(objs, name=None):
    """Join objects into objs[0] (all transforms identity-located at the origin expected)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = objs[0]
    if name:
        o.name = name; o.data.name = name
    return o


def join_team(target, team_obj):
    tm = team_material()
    team_obj.data.materials.clear(); team_obj.data.materials.append(tm)
    if not team_obj.data.uv_layers:
        team_obj.data.uv_layers.new(name=target.data.uv_layers.active.name if target.data.uv_layers else "UVMap")
    for d in team_obj.data.uv_layers.active.data:
        d.uv = (0.5, 0.5)
    M = target.matrix_world.inverted() @ team_obj.matrix_world
    team_obj.data.transform(M)
    team_obj.matrix_world = target.matrix_world.copy()
    return join([target, team_obj])


# ============================================================================ rotors / propellers
_AXIS_ROT = {
    "z": Matrix.Identity(3),                                        # main rotor: disc XY, shaft Z
    "x": Matrix(((0, 0, 1), (0, 1, 0), (-1, 0, 0))),                # tail rotor: local z -> world x
    "y": Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0))),                # propeller: local z -> world y
}


def rotor(name, hub, n_blades, radius, chord, mat, root_r=None, axis="z", twist=(8, -4), coning=2.0,
          phase=0.0, hub_r=None, mast=0.0, taper=0.15, thick=0.07, flip_pitch=False, paddle=False,
          tex_v=(0.06, 0.98), nseg=6, sign_x=1.0):
    """Hub + n real thin blades as ONE object with origin at `hub`, built in a local frame where the
    blades lie in the XY plane spinning about Z, then rotated so local Z maps to world `axis`
    (object rotation stays identity, so the spin axis is the object's local x / y / z).
    UVs: U across chord, V along span (tex_v range); the hub uses texel (0.5, 0.02)."""
    R3 = _AXIS_ROT[axis]
    if axis == "x" and sign_x < 0:
        R3 = Matrix(((0, 0, -1), (0, 1, 0), (1, 0, 0)))
    root_r = root_r if root_r is not None else radius * 0.09
    hub_r = hub_r if hub_r is not None else max(radius * 0.035, 0.08)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")

    def add_faces(V, us, vs):
        nr = len(V[0])
        for i in range(len(V) - 1):
            for j in range(nr):
                f = bm.faces.new((V[i][j], V[i][(j + 1) % nr], V[i + 1][(j + 1) % nr], V[i + 1][j]))
                uvs = [(us[j], vs[i]), (us[(j + 1) % nr] if j + 1 < nr else 1.0, vs[i]),
                       (us[(j + 1) % nr] if j + 1 < nr else 1.0, vs[i + 1]), (us[j], vs[i + 1])]
                for lp, uv in zip(f.loops, uvs):
                    lp[uvl].uv = uv
        f0 = bm.faces.new(V[-1])
        for lp in f0.loops:
            lp[uvl].uv = (0.5, vs[-1])

    def tr(p):
        v = R3 @ Vector(p)
        return (v.x, v.y, v.z)

    # hub (cylinder about local z)
    def cyl(z0, z1, r, seg=12):
        V = [[bm.verts.new(tr((r * math.cos(2 * PI * k / seg), r * math.sin(2 * PI * k / seg), z))) for k in range(seg)]
             for z in (z0, z1)]
        add_faces(V, [0.5] * seg, [0.02, 0.02])
        f = bm.faces.new(V[0][::-1])
        for lp in f.loops:
            lp[uvl].uv = (0.5, 0.02)
    cyl(-hub_r * 0.6, hub_r * 0.6, hub_r, 14)
    cyl(hub_r * 0.6, hub_r * 1.0, hub_r * 0.55, 10)
    if mast:
        cyl(-mast, -hub_r * 0.6, hub_r * 0.5, 10)
    prof = [(-0.5, 0), (-0.25, 0.5), (0.5, 0.12), (0.5, -0.12), (-0.25, -0.5)]
    us = [0.0, 0.25, 0.5, 0.75, 1.0]
    for b in range(n_blades):
        a = 2 * PI * b / n_blades + phase
        d = Vector((math.cos(a), math.sin(a), 0))
        p = Vector((-math.sin(a), math.cos(a), 0))
        # grip
        g0, g1 = d * hub_r * 0.7, d * root_r
        V = []
        for gp in (g0, g1):
            V.append([bm.verts.new(tr(gp + p * (u * chord * 0.45) + Vector((0, 0, v * thick * 2.2)))) for u, v in
                      ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5))])
        add_faces(V, [0.5] * 4, [0.02, 0.02])
        rings = []
        ts = np.linspace(0, 1, nseg)
        for t in ts:
            r = root_r + t * (radius - root_r)
            c = chord * (1 - taper * t)
            if paddle:                                         # propeller blade: wide mid, narrow root/tip
                c = chord * (0.55 + 0.75 * math.sin(PI * min(1.0, 0.15 + 0.85 * t)) ** 0.8) * (1 - 0.35 * t)
            th = thick * (1 - 0.45 * t)
            tw = math.radians(twist[0] + (twist[1] - twist[0]) * t) * (-1 if flip_pitch else 1)
            cz = math.sin(math.radians(coning)) * r
            ring = []
            for u, v in prof:
                cc, zz = u * c, v * th
                c2 = cc * math.cos(tw) - zz * math.sin(tw); z2 = cc * math.sin(tw) + zz * math.cos(tw)
                q = d * r + p * c2
                ring.append(bm.verts.new(tr((q.x, q.y, cz + z2))))
            rings.append(ring)
        add_faces(rings, us, [tex_v[0] + (tex_v[1] - tex_v[0]) * t for t in ts])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.location = Vector(hub)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def blade_texture(ref, root_px, tip_px, width_px, path_png, size=(64, 512), hub_col=(0.07, 0.07, 0.065),
                  root_frac=0.05, fallback=None):
    """Blade albedo strip sampled along a blade drawn in a concept view; U = chord, V = span."""
    root, tip = np.array(root_px, float), np.array(tip_px, float)
    d = (tip - root) / np.linalg.norm(tip - root); p = np.array([-d[1], d[0]])
    Wt, Ht = size
    v = (np.arange(Ht) + 0.5) / Ht; u = (np.arange(Wt) + 0.5) / Wt
    V_, U_ = np.meshgrid(v, u, indexing="ij")
    pts = root[None, None] + (tip - root)[None, None] * V_[..., None] + p[None, None] * ((U_ - 0.5) * width_px)[..., None]
    col = L.sample(ref, pts[..., 0].ravel(), pts[..., 1].ravel()).reshape(Ht, Wt, 3)
    if fallback is not None:
        col = 0.5 * col + 0.5 * np.array(fallback)
    col[: int(root_frac * Ht)] = np.array(hub_col)
    L.save_png(col, path_png)
    return path_png


def flat_texture(rgb, path_png, size=(16, 64), tip=None, tip_frac=0.06):
    col = np.ones((size[1], size[0], 3)) * np.array(rgb)
    if tip is not None:
        col[int((1 - tip_frac) * size[1]):] = np.array(tip)
    col[: int(0.05 * size[1])] = np.array((0.07, 0.07, 0.065))
    L.save_png(col, path_png)
    return path_png


# ============================================================================ atlas texturing
class Shade:
    """Generic aircraft projection shader.
    refs: {'top': ref (nose-up), 'side': ref (nose-left)}, frames: top TopFrame, side SideFrame.
    modes: per object index -> None (projection) | ('flat', rgb) | ('side', ) | ('top', ) | ('mul', k)"""

    def __init__(self, refs, top, side, modes=None, under_k=0.62, k=3.0, grime=0.18, under_rgb=None,
                 top_tol=0.08, side_tol=0.08):
        self.refs, self.top, self.side = refs, top, side
        self.modes = modes or {}
        self.under_k, self.k, self.grime = under_k, k, grime
        self.under_rgb = under_rgb
        self.top_tol, self.side_tol = top_tol, side_tol
        self.top_blur = blurred(refs["top"], 6)

    def __call__(self, P, N, O, depth):
        top, side, k = self.refs["top"], self.refs["side"], self.k
        nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]
        tpx, tpy = self.top.px(P[:, 0]), self.top.py(P[:, 1])
        c_top = L.sample(top, tpx, tpy)
        c_und = L.sample(self.top_blur, tpx, tpy) * self.under_k
        if self.under_rgb is not None:
            c_und = 0.5 * c_und + 0.5 * np.array(self.under_rgb)
        spx, spy = self.side.px(P[:, 1]), self.side.py(P[:, 2])
        c_side = L.sample(side, spx, spy)
        v_top = L.visible(depth["top"], P, self.top_tol + 0.04 * np.sqrt(np.clip(1 - nz ** 2, 0, 1)) / np.maximum(nz, 0.25))
        v_side = np.where(nx < 0, L.visible(depth["left"], P, self.side_tol), L.visible(depth["right"], P, self.side_tol))
        only_side = np.zeros(len(P), bool); only_top = np.zeros(len(P), bool)
        for oi, md in self.modes.items():
            if md and md[0] == "side":
                only_side |= O == oi
            if md and md[0] == "top":
                only_top |= O == oi
        w_t = np.clip(nz, 0, 1) ** k * v_top * (~only_side)
        w_s = np.abs(nx) ** k * v_side * (~only_top)
        w_y = np.abs(ny) ** k * (~only_top)
        w_b = np.clip(-nz, 0, 1) ** k
        num = c_top * w_t[:, None] + c_side * (w_s + w_y)[:, None] + c_und * w_b[:, None]
        den = w_t + w_s + w_y + w_b
        num0 = c_top * (np.clip(nz, 0, 1) ** k)[:, None] + c_side * (np.abs(nx) ** k)[:, None] + c_und * w_b[:, None]
        den0 = np.clip(nz, 0, 1) ** k + np.abs(nx) ** k + w_b
        col = np.where((den > 0.02)[:, None], num / np.maximum(den, 1e-6)[:, None],
                       0.75 * num0 / np.maximum(den0, 1e-6)[:, None])
        for oi, md in self.modes.items():
            if md and md[0] == "flat":
                m = O == oi
                col[m] = np.array(md[1]) * (0.9 + 0.2 * L.value_noise(P[m], 0.4, seed=4))[:, None] if m.sum() > 8 else md[1]
            if md and md[0] == "mul":
                col[O == oi] *= md[1]
        col *= (0.95 + 0.08 * L.value_noise(P, 0.9, seed=5))[:, None]
        if self.grime:
            g = np.clip((1.0 - P[:, 2]) / 1.0, 0, 1) * self.grime * L.value_noise(P, 0.5, seed=9)
            col = col * (1 - g[:, None]) + np.array([0.28, 0.25, 0.2]) * g[:, None]
        return np.clip(col, 0, 1)


def texture_atlas(objs, shade, size, ao_size, ao_strength, cell, bounds, out_png, depth_objs=None, ao_dist=0.9):
    """Like veh_m88_3d.texture_atlas but the shader also receives the object index of each texel."""
    P, Nn, U, I = L.world_tris(objs, with_uv=True)
    allP = L.world_tris(depth_objs or objs)[0]
    (x0, y0, z0), (x1, y1, z1) = bounds
    depth = {
        "top": L.depth_map(allP, (0, 1), 2, (x0, y0), (x1, y1), cell, +1),
        "left": L.depth_map(allP, (1, 2), 0, (y0, z0), (y1, z1), cell, -1),
        "right": L.depth_map(allP, (1, 2), 0, (y0, z0), (y1, z1), cell, +1),
    }
    pos, nor, oid, msk = L.uv_raster(P, Nn, U, I, size)
    Pm, Nm = pos[msk].astype(np.float64), nor[msk].astype(np.float64)
    col = np.zeros((size, size, 3), np.float32)
    col[msk] = shade(Pm, Nm, oid[msk], depth)
    if ao_strength > 0:
        ao = L.bake_ao(objs, ao_size, samples=16, distance=ao_dist)
        ao = np.asarray(Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR),
                        np.float32) / 255.0
        col *= (1 - ao_strength + ao_strength * ao)[..., None]
    col = L.fill_nearest(col, msk)
    L.save_png(col, out_png)
    return out_png, float(msk.mean())


def attach_texture(mat, png, name):
    img = L.load_image(png, name)
    nt = mat.node_tree
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return img


# ============================================================================ QA
def fit_overlay(objs, side, top, side_rgba, top_rgba, out_png):
    """Outline the model's orthographic silhouette (red) over the concept side and top views."""
    P = L.world_tris(objs)[0]
    panels = []
    for fr, a, kind in ((side, side_rgba, "side"), (top, top_rgba, "top")):
        H, W = a.shape[:2]
        if kind == "side":
            u, v = fr.px(P[..., 1]), fr.py(P[..., 2])
        else:
            u, v = fr.px(P[..., 0]), fr.py(P[..., 1])
        Q = np.stack([u, v, np.zeros_like(u)], -1)
        dm = L.depth_map(Q, (0, 1), 2, (0, 0), (W, H), 1.0, +1)
        m = np.isfinite(dm["D"]) & (dm["D"] > -1e30)
        edge = m ^ ndimage.binary_erosion(m, iterations=1)
        bg = np.full((H, W, 3), 255, np.uint8)
        al = a[..., 3:4].astype(np.float32) / 255
        img = (a[..., :3] * al + bg * (1 - al)).astype(np.uint8)
        img[m & (a[..., 3] < 60)] = (np.array([255, 190, 190])).astype(np.uint8)   # model where concept is empty
        img[edge] = (230, 0, 0)
        cm = a[..., 3] > 60
        img[(cm ^ ndimage.binary_erosion(cm)) & ~m] = (0, 90, 255)                  # concept outline outside model
        ys, xs = np.nonzero(m | cm)
        pad = 12
        img = img[max(ys.min() - pad, 0):ys.max() + pad, max(xs.min() - pad, 0):xs.max() + pad]
        panels.append(Image.fromarray(img))
    Wt = sum(p.width for p in panels); Ht = max(p.height for p in panels)
    sheet = Image.new("RGB", (Wt, Ht), (255, 255, 255))
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0)); x += p.width
    sheet.save(out_png)
    return out_png


def preview_sheet(aid, title, length, span, height, out_png, res=(640, 400), samples=20, close_az=-40,
                  extra=None, ground_col=(0.30, 0.29, 0.26)):
    """front / side / rear / top (ortho) + RTS 52 deg + close 3/4 Cycles renders -> one contact sheet."""
    cam = L.setup_preview_scene(ground=True, ground_col=ground_col, size=max(length, span) * 4)
    sc = bpy.context.scene
    sc.cycles.samples = samples
    tmp = tempfile.mkdtemp(prefix=f"m3_{aid}_")
    zc = height / 2
    asp = res[0] / res[1]
    fr = max(span, height * asp) * 1.12
    sd = max(length, height * asp) * 1.10
    tp = max(span, length * asp) * 1.06
    diag = math.sqrt(length ** 2 + span ** 2)
    views = [("front", 0, 5, (0, 0, zc), fr, None), ("side", -90, 5, (0, 0, zc), sd, None),
             ("rear", 180, 5, (0, 0, zc), fr, None), ("top", 0, 90, (0, 0, zc), tp, (1, 0, 0)),
             ("rts 52 deg", 45, 52, (0, 0, zc * 0.5), None, None), ("close 3/4", close_az, 16, (0, 0, zc * 0.8), None, None)]
    shots = []
    for name, az, el, tgt, ortho, up in views:
        if ortho:
            L.aim(cam, tgt, az, el, diag * 3 + 50, ortho=ortho, roll_up=up)
        else:
            dist = diag * (1.75 if name.startswith("rts") else 1.2)
            L.aim(cam, tgt, az, el, dist, lens=50)
        cam.data.clip_end = diag * 10 + 200
        p = os.path.join(tmp, name.replace(" ", "_").replace("/", "") + ".png")
        L.render(p, res)
        shots.append((p, name))
    if extra:
        shots += extra(cam, tmp)
    L.contact_sheet(shots, out_png, cols=3, cell=res, title=title)
    return out_png


def report(export, body):
    lines = [f"tris total {L.tri_count([o for o in export if o.type == 'MESH'])}"]
    for o in export:
        if o.type == "MESH":
            lines.append(f"  {o.name:12s} tris {L.tri_count([o]):6d} origin {tuple(round(v, 3) for v in o.location)}")
        else:
            lines.append(f"  {o.name:12s} empty      origin {tuple(round(v, 3) for v in o.location)}")
    from mathutils import Vector as V
    bb = np.array([list(body.matrix_world @ V(c)) for c in body.bound_box])
    lines.append(f"  Body bounds min {bb.min(0).round(2)} max {bb.max(0).round(2)}")
    return "\n".join(lines)


def export_glb(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = [o for o in objs if o.type == "MESH"][0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True)


def parse_args(aid):
    argv = sys.argv[1:]
    o = {"out": os.path.join(OUT3D, aid), "prev": True, "fit": True, "sheet": os.path.join(SCREENS, f"m3_{aid}_sheet.png"),
         "fit_png": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-previews":
            o["prev"] = False
        elif a == "--sheet":
            o["sheet"] = argv[i + 1]; i += 1
        elif a == "--fit":
            o["fit_png"] = argv[i + 1]; i += 1
        else:
            o["out"] = a
        i += 1
    os.makedirs(o["out"], exist_ok=True)
    return o
