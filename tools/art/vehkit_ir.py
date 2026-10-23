"""Steel Accord - shared kit for the Iranian ground-vehicle wave 1 (bpy 5.x).

Builds on tools/art/vehkit.py (imported, not modified) and so on the library half of veh_m88_3d.py.
Same node / axis / material conventions as the U.S. M2 roster (docs/M2_VEHICLES.md):
  forward = Blender +Y (Godot -Z), up = +Z, metres, root origin = ground contact under the hull centre,
  vehicle left = -X; Turret (yaw axis) > Gun (trunnion) > Muzzle; wheels / sprockets / idlers with hub
  origins spinning about local X; TrackL/TrackR with SA_TrackScroll (whole number of tiles per loop);
  SA_<Id> albedo atlas (2048^2, embedded) and SA_Team grey 0.62 panels.

Difference to the U.S. pipeline: the Iranian concept panels are single perspective renders, so nothing is
projected from them. Instead every part carries a *paint tag* (an integer face attribute written while the
geometry is built) and every atlas texel is painted procedurally from its world position, normal, tag and
object: a three-tone desert camouflage (3D noise, hard-edged), plate seams and bolt rows, hatches, small
national-colour stripe decals (green / white / red, no emblem, no text), rubber, glass, metal; then a
Cycles AO bake and a Cycles bevel-normal "edge" bake add contact shading and worn convex edges.
Deterministic: fixed hashes, no RNG state, no network.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import vehkit as vk  # noqa: E402
from vehkit import PI, lathe, set_origin, parent_to, empty  # noqa: E402,F401
from veh_m88_3d import Part, tri_count, smart_uv, _tri_pixels, uv_raster, fill_nearest, save_png, \
    load_image, image_material, bake_ao, aim, render, contact_sheet, reset_scene  # noqa: E402,F401

REPO = vk.REPO

# ============================================================================ paint tags
TAGS = {"camo": 1, "skirt": 2, "metal": 3, "rubber": 4, "glass": 5, "lens": 6, "grille": 7, "steel": 8,
        "dark": 9, "era": 10, "barrel": 11, "canvas": 12, "olive": 13, "plain": 14, "redlens": 15, "chain": 16}
TAG_NAMES = {v: k for k, v in TAGS.items()}
LAYER = "satag"


class TPart(Part):
    """Part whose faces carry a paint tag (FACE int attribute 'satag'). Use .t('tag') to switch the tag for the
    primitives that follow."""

    def __init__(self, name, tag="camo"):
        super().__init__(name)
        self.layer = self.bm.faces.layers.int.new(LAYER)
        self.tag = tag

    def t(self, tag):
        assert tag in TAGS, tag
        self.tag = tag
        return self

    def _stamp(self):
        v = TAGS[self.tag]
        L = self.layer
        for f in self.bm.faces:
            if f[L] == 0:
                f[L] = v

    def box(self, *a, **k):
        super().box(*a, **k); self._stamp()

    def beam(self, *a, **k):
        super().beam(*a, **k); self._stamp()

    def cyl(self, *a, **k):
        super().cyl(*a, **k); self._stamp()

    def rod(self, *a, **k):
        super().rod(*a, **k); self._stamp()

    def side(self, *a, **k):
        super().side(*a, **k); self._stamp()

    def plan(self, *a, **k):
        super().plan(*a, **k); self._stamp()

    def rings(self, *a, **k):
        super().rings(*a, **k); self._stamp()

    # ---- extra primitives
    def obox(self, c, size, fwd, up=(0, 0, 1)):
        """Oriented box: local Y along `fwd`, local Z as close to `up` as possible."""
        f = Vector(fwd).normalized()
        x = f.cross(Vector(up))
        if x.length < 1e-6:
            x = f.cross(Vector((1, 0, 0)))
        x.normalize()
        z = x.cross(f)
        R = Matrix((x, f, z)).transposed().to_4x4()
        M = Matrix.Translation(c) @ R @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._stamp()

    def slab(self, bottom_xy, z0, top_xy, z1):
        """Closed prism between a bottom outline at z0 and a top outline at z1 (same vertex count)."""
        self.rings([[(x, y, z0) for x, y in bottom_xy], [(x, y, z1) for x, y in top_xy]], caps=True)

    def loft(self, sections, caps=True):
        """sections: [(y, [(x, z), ...]), ...] closed outlines with equal vertex counts."""
        self.rings([[(x, y, z) for x, z in outline] for y, outline in sections], caps=caps)

    def tube(self, c, r, length, axis="y", seg=10, r2=None):
        rot = {"x": (0, PI / 2, 0), "y": (PI / 2, 0, 0), "z": (0, 0, 0)}[axis]
        self.cyl(c, r, length, rot, seg=seg, r2=r2)


def sect(hw, z0, z1, ch=0.0, top_hw=None, bot_hw=None):
    """8-vertex closed section (x, z): bottom half-width bot_hw (default hw-ch), widest hw between
    z0+ch and z1-ch, top half-width top_hw (default hw-ch)."""
    b = hw - ch if bot_hw is None else bot_hw
    t = hw - ch if top_hw is None else top_hw
    return [(-b, z0), (b, z0), (hw, z0 + ch), (hw, z1 - ch), (t, z1), (-t, z1), (-hw, z1 - ch), (-hw, z0 + ch)]


def build(part, mat, bevel=0.0, angle=35, smooth=33, location=None):
    o = part.build(mat, bevel=bevel, angle=angle, smooth=smooth, location=location)
    clean_mesh(o)
    return o


def clean_mesh(o):
    """Remove degenerate faces (zero normals) and make normals consistent."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    bad = [f for f in bm.faces if f.calc_area() < 1e-9]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    o.data.update()


def join(target, others):
    vk.join_objs(target, others)
    return target


# ============================================================================ geometry helpers
def flag_slots():
    return []


def hatch(part, c, r, h=0.05, seg=16, hinge=True):
    """Round hatch: low disc + rim + hinge block (camo)."""
    x, y, z = c
    part.cyl((x, y, z + h / 2), r, h, seg=seg)
    part.cyl((x, y, z + h + 0.012), r * 0.82, 0.025, seg=seg)
    if hinge:
        part.box((x, y - r * 0.95, z + h * 0.8), (r * 0.6, 0.08, 0.06))


def smoke_launchers(part, c, n, yaw, pitch=0.5, r=0.045, length=0.24, dz=0.0, spacing=0.11, rows=1):
    """A row of n smoke-grenade tubes centred at c, pointing along yaw (deg from +Y towards +X), pitched up."""
    a = math.radians(yaw)
    fwd = Vector((math.sin(a) * math.cos(pitch), math.cos(a) * math.cos(pitch), math.sin(pitch)))
    lat = Vector((math.cos(a), -math.sin(a), 0))
    for rr in range(rows):
        for k in range(n):
            p = Vector(c) + lat * (k - (n - 1) / 2) * spacing + Vector((0, 0, rr * spacing * 0.9 + dz))
            part.t("dark").rod(p - fwd * length * 0.5, p + fwd * length * 0.5, r, seg=8)
    part.t("camo")


def antenna(part, base, height, r=0.012):
    x, y, z = base
    part.t("metal").cyl((x, y, z + 0.04), 0.045, 0.08, seg=8)
    part.cyl((x, y, z + height / 2), r, height, seg=4)
    part.t("camo")


def light_cluster(part, c, facing=1, w=0.18, h=0.12, n=2, guard=True):
    """Headlight pair box with lenses facing +Y (facing=1) or -Y (-1)."""
    x, y, z = c
    part.t("camo").box((x, y, z), (w, 0.10, h))
    for k in range(n):
        lx = x + (k - (n - 1) / 2) * (w / n)
        part.t("lens").tube((lx, y + facing * 0.055, z), min(w / n, h) * 0.36, 0.02, "y", seg=10)
    if guard:
        part.t("metal").box((x, y + facing * 0.09, z + h * 0.62), (w + 0.04, 0.02, 0.02))
    part.t("camo")


# ============================================================================ noise / painting
def _hash3(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) \
        ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF)


def vnoise(P, scale, seed=0):
    """Trilinear value noise in 0..1 on a hashed integer lattice (deterministic)."""
    Q = P / scale + seed * 17.13
    i = np.floor(Q).astype(np.int64)
    f = Q - i
    f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, scale, seed=0, octaves=4, gain=0.5):
    acc, amp, tot = 0, 1.0, 0
    for k in range(octaves):
        acc = acc + amp * vnoise(P, scale / (2.03 ** k), seed + 31 * k)
        tot += amp; amp *= gain
    return acc / tot


PAL = {
    "sand": np.array([0.745, 0.650, 0.480]),
    "olive": np.array([0.470, 0.440, 0.300]),
    "brown": np.array([0.370, 0.295, 0.210]),
    "dust": np.array([0.700, 0.620, 0.480]),
    "metal": np.array([0.200, 0.195, 0.180]),
    "rubber": np.array([0.085, 0.082, 0.078]),
    "glass": np.array([0.090, 0.120, 0.140]),
    "lens": np.array([0.880, 0.880, 0.830]),
    "redlens": np.array([0.700, 0.150, 0.100]),
    "steel": np.array([0.560, 0.540, 0.500]),
    "canvas": np.array([0.560, 0.500, 0.380]),
    "seam": np.array([0.250, 0.210, 0.160]),
    "green": np.array([0.090, 0.480, 0.220]),
    "white": np.array([0.930, 0.930, 0.910]),
    "red": np.array([0.800, 0.110, 0.120]),
}


def camo(P, cfg):
    """Three-tone hard-edged desert camouflage evaluated in world space. A skewed domain gives slanted, angular
    bands like the concept panels."""
    S = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.55, 1.0]])     # shear: blotches slant along the hull
    Q = P @ S.T * np.array([1.0, 0.75, 1.15])
    n1 = fbm(Q, cfg.get("camo_scale", 1.6), seed=cfg.get("seed", 1), octaves=3)
    n2 = fbm(Q + 11.7, cfg.get("camo_scale", 1.6) * 0.8, seed=cfg.get("seed", 1) + 7, octaves=3)
    col = np.tile(PAL["sand"], (len(P), 1))
    m_ol = n1 > cfg.get("olive_t", 0.585)
    m_br = (n2 > cfg.get("brown_t", 0.60)) & ~m_ol
    col[m_ol] = PAL["olive"]
    col[m_br] = PAL["brown"]
    return col


def plane_coords(P, N):
    """2D coordinates in the plane of the dominant normal axis + axis index."""
    ax = np.argmax(np.abs(N), 1)
    u = np.where(ax == 0, P[:, 1], P[:, 0])
    v = np.where(ax == 2, P[:, 1], P[:, 2])
    return u, v, ax


def _line(d, w):
    """1 on a line of half-width w at distance d (soft 1-texel edge)."""
    return np.clip(1.5 - np.abs(d) / w, 0, 1)


def seam_mask(P, N, tags, cfg):
    """Plate seams: vertical seams at cfg['seams_y'] on side/top faces, horizontal seams at cfg['seams_z'] on
    sides, regular plate seams on 'skirt' faces; bolt dots along skirt seams."""
    m = np.zeros(len(P))
    nx, ny, nz = np.abs(N).T
    for y in cfg.get("seams_y", ()):
        m = np.maximum(m, _line(P[:, 1] - y, 0.008) * ((nx > 0.5) | (nz > 0.5)))
    for z in cfg.get("seams_z", ()):
        m = np.maximum(m, _line(P[:, 2] - z, 0.008) * (nx > 0.5))
    for x in cfg.get("seams_x", ()):
        m = np.maximum(m, _line(np.abs(P[:, 0]) - x, 0.008) * (nz > 0.5))
    sk = tags == TAGS["skirt"]
    if sk.any():
        pitch = cfg.get("skirt_pitch", 0.62)
        d = (P[sk, 1] - cfg.get("skirt_y0", 0.0)) / pitch
        dd = (d - np.round(d)) * pitch
        mm = _line(dd, 0.009)
        # bolt rows near top and bottom of each plate
        z = P[sk, 2]
        zt, zb = cfg.get("skirt_bolt_z", (None, None))
        bolts = 0
        for zz in (zt, zb):
            if zz is None:
                continue
            bp = 0.155
            e = (P[sk, 1] / bp - np.round(P[sk, 1] / bp)) * bp
            bolts = np.maximum(bolts, ((e ** 2 + (z - zz) ** 2) < 0.018 ** 2) * 1.0)
        m[sk] = np.maximum(m[sk], np.maximum(mm, bolts * 0.8))
    return m


def paint_wheel(Pm, Nm, hub, kind, cfg):
    """Rotation-invariant colours for a wheel-like object; hub = (y, z, r_outer, r_rim)."""
    hy, hz, r, r_rim = hub
    rho = np.sqrt((Pm[:, 1] - hy) ** 2 + (Pm[:, 2] - hz) ** 2)
    face = np.abs(Nm[:, 0]) > 0.5
    base = PAL["sand"] * 0.93 + PAL["olive"] * 0.07
    col = np.tile(base, (len(Pm), 1))
    dust = 0.85 + 0.15 * vnoise(np.stack([rho * 3, rho * 3, Pm[:, 0] * 2], 1), 0.15, seed=3)
    col *= dust[:, None]
    if kind == "road":
        tyre = rho > r - 0.065
        col[tyre] = PAL["rubber"] * 1.25
        col[(~face) & (rho > r * 0.7)] = PAL["rubber"] * 1.1          # tread surface
        ring = face & (np.abs(rho - r * 0.62) < 0.012)
        col[ring] = PAL["seam"]
        hubc = face & (rho < r * 0.30)
        col[hubc] = col[hubc] * 0.72
        # bolt circle
        ang = np.arctan2(Pm[:, 2] - hz, Pm[:, 1] - hy)
        k = 8
        e = (ang * k / (2 * PI) - np.round(ang * k / (2 * PI))) * 2 * PI / k * rho
        bolt = face & (np.abs(rho - r * 0.42) < 0.018) & (np.abs(e) < 0.018)
        col[bolt] = PAL["seam"] * 0.9
    elif kind == "tyre":
        tyre = rho > r_rim + 0.012
        col[tyre] = PAL["rubber"] * (1.0 + 0.25 * (~face[tyre]))[:, None]
        rimline = face & (np.abs(rho - r_rim) < 0.012)
        col[rimline] = PAL["seam"]
        hubc = face & (rho < r_rim * 0.45)
        col[hubc] = PAL["olive"] * 0.85
        ang = np.arctan2(Pm[:, 2] - hz, Pm[:, 1] - hy)
        k = 10
        e = (ang * k / (2 * PI) - np.round(ang * k / (2 * PI))) * 2 * PI / k * rho
        nut = face & (np.abs(rho - r_rim * 0.30) < 0.014) & (np.abs(e) < 0.014)
        col[nut] = PAL["metal"]
    elif kind == "sprocket":
        teeth = rho > r - 0.05
        col[teeth] = PAL["metal"] * 1.6
        hubc = face & (rho < r * 0.42)
        col[hubc] = col[hubc] * 0.75
    elif kind == "idler":
        rim = rho > r - 0.05
        col[rim] = PAL["metal"] * 1.5
        ring = face & (np.abs(rho - r * 0.55) < 0.012)
        col[ring] = PAL["seam"]
    return col


def paint(P, N, tags, names, cfg):
    col = camo(P, cfg)
    t = tags
    # olive-only small parts, plain sand
    col[t == TAGS["olive"]] = PAL["olive"]
    col[t == TAGS["plain"]] = PAL["sand"] * 0.95
    # ERA blocks: camo but slightly darker, with a dark border driven by local face geometry (AO adds the gaps)
    era = t == TAGS["era"]
    col[era] *= 0.93
    # grille: dark slats running across X
    g = t == TAGS["grille"]
    if g.any():
        u = P[g, 1] / cfg.get("grille_pitch", 0.09)
        sl = np.abs(u - np.round(u)) < 0.22
        cg = col[g] * 0.8
        cg[sl] = PAL["metal"] * 0.8
        col[g] = cg
    for name in ("metal", "rubber", "glass", "lens", "redlens", "steel", "canvas"):
        m = t == TAGS[name]
        if m.any():
            col[m] = PAL[name]
    col[t == TAGS["dark"]] = PAL["metal"] * 0.75
    col[t == TAGS["chain"]] = PAL["metal"] * 1.3
    glass = t == TAGS["glass"]
    if glass.any():                                       # a faint sky reflection on up-facing glass
        col[glass] += np.clip(N[glass, 2], 0, 1)[:, None] * np.array([0.06, 0.08, 0.1])
    canv = t == TAGS["canvas"]
    if canv.any():
        col[canv] *= (0.85 + 0.25 * fbm(P[canv], 0.12, seed=21, octaves=2))[:, None]
    # plate seams + bolts on painted surfaces
    painted = np.isin(t, [TAGS["camo"], TAGS["skirt"], TAGS["era"], TAGS["olive"], TAGS["plain"], TAGS["barrel"]])
    sm = seam_mask(P, N, t, cfg) * painted
    col = col * (1 - sm[:, None] * 0.75) + PAL["seam"] * (sm[:, None] * 0.75)
    # decals (world space)
    for d in cfg.get("decals", []):
        col = decal(P, N, names, col, d)
    # wheels / sprockets / idlers / tyres
    for name, (hub, kind) in cfg.get("hubs", {}).items():
        m = names == name
        if m.any():
            col[m] = paint_wheel(P[m], N[m], hub, kind, cfg)
    # weathering: dust low on the hull, vertical streaks, broad value variation
    nse = fbm(P, 0.5, seed=5, octaves=3)
    mud_h = cfg.get("mud_h", 0.9)
    low = np.clip((mud_h - P[:, 2]) / mud_h, 0, 1) ** 1.4 * (0.35 + 0.45 * nse) * cfg.get("mud_amt", 0.6)
    col = col * (1 - low[:, None]) + PAL["dust"] * 0.8 * low[:, None]
    streak = fbm(P * np.array([6.0, 6.0, 0.35]), 1.0, seed=9, octaves=2)
    side = np.abs(N[:, 2]) < 0.6
    col *= (1 - 0.10 * side * np.clip(streak - 0.45, 0, 1) * 2)[:, None]
    col *= (0.94 + 0.10 * fbm(P, 0.25, seed=13, octaves=3))[:, None]
    top_dust = np.clip(N[:, 2], 0, 1) ** 2 * (0.12 + 0.12 * nse)
    col = col * (1 - top_dust[:, None]) + PAL["dust"] * top_dust[:, None]
    return np.clip(col, 0, 1)


def decal(P, N, names, col, d):
    """World-space decals.
    kind 'flag'  : green/white/red horizontal stripes on a face looking along d['axis'] ('+x','-x','+y','-y').
    kind 'ring'  : dark circular outline (hatch seam) on up-facing faces; c=(x,y,z), r, z tolerance.
    kind 'rect'  : dark rectangular outline (door / panel) on faces looking along axis; c=(u,v) in-plane.
    kind 'fill'  : solid colour on faces looking along axis inside rect (e.g. vision blocks, louvres)."""
    kind = d["kind"]
    obj = d.get("obj")
    sel = np.ones(len(P), bool) if obj is None else np.isin(names, obj if isinstance(obj, (list, tuple)) else [obj])
    if kind == "ring":
        cx, cy, cz = d["c"]
        rr = np.sqrt((P[:, 0] - cx) ** 2 + (P[:, 1] - cy) ** 2)
        m = sel & (N[:, 2] > 0.6) & (np.abs(P[:, 2] - cz) < d.get("ztol", 0.15))
        w = d.get("w", 0.012)
        ln = m & (np.abs(rr - d["r"]) < w)
        col[ln] = PAL["seam"]
        return col
    ax = {"+x": (0, 1), "-x": (0, -1), "+y": (1, 1), "-y": (1, -1), "+z": (2, 1)}[d["axis"]]
    i, s = ax
    facing = sel & (N[:, i] * s > 0.6)
    if "depth" in d:                           # only faces near a given plane coordinate
        facing &= np.abs(P[:, i] - d["depth"]) < d.get("dtol", 0.2)
    if i == 0:
        u, v = P[:, 1], P[:, 2]
    elif i == 1:
        u, v = P[:, 0], P[:, 2]
    else:
        u, v = P[:, 0], P[:, 1]
    cu, cv = d["c"]
    w, h = d["size"]
    inside = facing & (np.abs(u - cu) <= w / 2) & (np.abs(v - cv) <= h / 2)
    if kind == "flag":
        rel = (v - (cv - h / 2)) / h                    # 0 bottom .. 1 top
        c = np.where((rel > 2 / 3)[:, None], PAL["green"], np.where((rel > 1 / 3)[:, None], PAL["white"], PAL["red"]))
        border = inside & ((np.abs(np.abs(u - cu) - w / 2) < 0.012) | (np.abs(np.abs(v - cv) - h / 2) < 0.012))
        col[inside] = c[inside] * 0.92
        col[border] = PAL["seam"]
    elif kind == "rect":
        lw = d.get("w", 0.01)
        e = inside & ((np.abs(np.abs(u - cu) - w / 2) < lw) | (np.abs(np.abs(v - cv) - h / 2) < lw))
        col[e] = PAL["seam"]
    elif kind == "fill":
        col[inside] = np.array(d["col"]) if not isinstance(d["col"], str) else PAL[d["col"]]
    elif kind == "louvre":
        pitch = d.get("pitch", 0.08)
        q = (v if d.get("dir", "v") == "v" else u) / pitch
        sl = inside & (np.abs(q - np.round(q)) < 0.25)
        col[inside] = col[inside] * 0.85
        col[sl] = PAL["metal"] * 0.9
    return col


# ============================================================================ bakes
def world_tris_tags(objs):
    """World-space triangles (N,3,3), normals, uvs, object index and paint tag per triangle."""
    P, Nn, U, I, Tg = [], [], [], [], []
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
        li = np.empty(nt * 3, dtype=np.int64); me.loop_triangles.foreach_get("loops", li)
        uv = np.empty(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uv)
        U.append(uv.reshape(-1, 2)[li].reshape(-1, 3, 2))
        I.append(np.full(nt, k))
        pi = np.empty(nt, dtype=np.int64); me.loop_triangles.foreach_get("polygon_index", pi)
        at = me.attributes.get(LAYER)
        if at is not None and at.domain == "FACE":
            vals = np.empty(len(me.polygons), dtype=np.int32); at.data.foreach_get("value", vals)
            tg = vals[pi]
        else:
            tg = np.zeros(nt, np.int32)
        Tg.append(np.where(tg == 0, TAGS["camo"], tg))
    return np.concatenate(P), np.concatenate(Nn), np.concatenate(U), np.concatenate(I), np.concatenate(Tg)


def uv_raster_tags(P, Nn, U, I, Tg, size):
    S = size
    pos = np.zeros((S, S, 3), np.float32); nor = np.zeros((S, S, 3), np.float32)
    oid = np.full((S, S), -1, np.int32); tag = np.zeros((S, S), np.int32); msk = np.zeros((S, S), bool)
    UV = U * S
    for t in range(len(P)):
        r = _tri_pixels(UV[t, 0], UV[t, 1], UV[t, 2], S, S)
        if r is None:
            continue
        ys, xs, w0, w1, w2 = r
        pos[ys, xs] = (w0[:, None] * P[t, 0] + w1[:, None] * P[t, 1] + w2[:, None] * P[t, 2])
        nor[ys, xs] = Nn[t]
        oid[ys, xs] = I[t]
        tag[ys, xs] = Tg[t]
        msk[ys, xs] = True
    return pos, nor, oid, tag, msk


def bake_edges(objs, size, radius=0.025, samples=8):
    """Bevel-normal vs. true-normal bake -> edge mask (1 on rounded convex/concave edges)."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = samples
    img = bpy.data.images.new("edge_bake", size, size, alpha=False, float_buffer=False)
    tmp = bpy.data.materials.new("edge_bake_mat"); tmp.use_nodes = True
    nt = tmp.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    bev = nt.nodes.new("ShaderNodeBevel"); bev.inputs["Radius"].default_value = radius; bev.samples = 8
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    nt.links.new(bev.outputs["Normal"], dot.inputs[0]); nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    nt.links.new(dot.outputs["Value"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
    saved = []
    for o in objs:
        saved.append([s.material for s in o.material_slots])
        for s in o.material_slots:
            s.material = tmp
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type="EMIT", margin=8)
    a = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a)
    for o, mats in zip(objs, saved):
        for s, m in zip(o.material_slots, mats):
            s.material = m
    bpy.data.images.remove(img); bpy.data.materials.remove(tmp)
    d = a.reshape(size, size, 4)[..., 0]
    return np.clip((1.0 - d) * 6.0, 0, 1)


def texture_atlas_ir(uv_objs, cfg, size, out_png, ao_size=1024):
    bpy.context.view_layer.update()
    P, Nn, U, I, Tg = world_tris_tags(uv_objs)
    pos, nor, oid, tag, msk = uv_raster_tags(P, Nn, U, I, Tg, size)
    Pm, Nm = pos[msk].astype(np.float64), nor[msk].astype(np.float64)
    names = np.array([uv_objs[i].name for i in oid[msk]])
    col = np.zeros((size, size, 3), np.float32)
    col[msk] = paint(Pm, Nm, tag[msk], names, cfg)
    hub_ids = [i for i, o in enumerate(uv_objs) if o.name in cfg.get("hubs", {})]
    is_hub = np.isin(oid, hub_ids)
    ao = bake_ao(uv_objs, ao_size, samples=16, distance=0.7)
    ao = np.asarray(Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR),
                    np.float32) / 255.0
    ed = bake_edges(uv_objs, ao_size)
    ed = np.asarray(Image.fromarray((ed * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR), np.float32) / 255.0
    convex = ed * np.clip((ao - 0.78) / 0.15, 0, 1)                 # edges that are not in a crease
    f = 0.42 + 0.58 * ao
    f = np.where(is_hub, 0.75 + 0.25 * ao, f)
    col *= f[..., None]
    wear = convex * cfg.get("edge_wear", 0.55)
    col = col * (1 - wear[..., None]) + (PAL["sand"] * 1.12)[None, None] * wear[..., None]
    col = fill_nearest(col, msk)
    save_png(col, out_png)
    return out_png, float(msk.mean())


# ============================================================================ QA
def normals_check(objs):
    """Signed volume per connected component of each mesh: a closed shell with outward normals has
    volume > 0. Returns report lines (components with negative volume are flagged)."""
    lines, bad_total = [], 0
    for o in objs:
        if o.type != "MESH":
            continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        seen = set(); neg = 0; comps = 0; zero = 0
        for f in bm.faces:
            if f.normal.length < 0.5:
                zero += 1
        for f0 in bm.faces:
            if f0.index in seen:
                continue
            comps += 1
            stack = [f0]; seen.add(f0.index); vol = 0.0
            while stack:
                f = stack.pop()
                vs = [v.co for v in f.verts]
                for k in range(1, len(vs) - 1):
                    vol += vs[0].dot(vs[k].cross(vs[k + 1])) / 6.0
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index not in seen:
                            seen.add(g.index); stack.append(g)
            if vol < -1e-7:
                neg += 1
        bm.free()
        bad_total += neg + zero
        if neg or zero:
            lines.append(f"  normals: {o.name}: {neg} of {comps} components inward, {zero} zero-normal faces")
    lines.insert(0, f"normals check: {'OK' if bad_total == 0 else 'ISSUES'} (signed volume per component, "
                    f"zero-length normals)")
    return lines


def backface_qa(path_prefix, views, res=(480, 300)):
    """Workbench renders with back-face culling (inverted faces show as holes)."""
    sc = bpy.context.scene
    old = sc.render.engine
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.show_backface_culling = True
    sh.light = "STUDIO"; sh.color_type = "TEXTURE"
    cam = bpy.data.objects.get("PrevCam")
    if cam is None:
        cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
        sc.collection.objects.link(cam); sc.camera = cam
    out = []
    for name, (tgt, az, el, dist) in views.items():
        aim(cam, tgt, az, el, dist, lens=50)
        p = f"{path_prefix}_{name}.png"
        render(p, res)
        out.append((p, name))
    sc.render.engine = old
    return out


# ============================================================================ pipeline
class Ctx:
    def __init__(self, vid):
        self.vid = vid
        self.mat = image_material(f"SA_{vid.title().replace('_', '')}", None, rough=0.8)
        self.track_mat = image_material("SA_TrackScroll", None, rough=0.9, metal=0.1)
        self.objs = {}
        self.team = []
        self.notes = []


def preview_sheet_ir(vid, title, prev_dir, length, width, height, rts_dist, close_dist, close_az=-38, quick=False,
                     res=(640, 400), samples=20, sheet_name=None):
    cam = vk.setup_preview_scene(samples)
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
        views = [v for v in views if v[0] in ("rts", "close34")]
    shots = []
    for name, az, el, tgt, ortho, up in views:
        dist = {"rts": rts_dist, "close34": close_dist}.get(name, 60)
        if ortho:
            aim(cam, tgt, az, el, dist, ortho=ortho, roll_up=up)
        else:
            aim(cam, tgt, az, el, dist, lens=50)
        p = os.path.join(prev_dir, f"_{vid}_{name}.png")
        render(p, res)
        shots.append((p, name))
    sheet = os.path.join(prev_dir, sheet_name or f"{vid}_sheet.png")
    contact_sheet(shots, sheet, cols=3 if not quick else 2, cell=res, title=title)
    for p, _ in shots:
        try:
            os.remove(p)
        except OSError:
            pass
    return sheet


def track_texture(path, lpt):
    dark = np.array([0.20, 0.18, 0.15])
    lite = np.array([0.50, 0.46, 0.40])
    vk.make_track_texture(dark, lite, lpt, path, rubber_pads=False)


def strip_tags(objs):
    for o in objs:
        if o.type == "MESH":
            a = o.data.attributes.get(LAYER)
            if a is not None:
                o.data.attributes.remove(a)


def run(vid, build_fn, title, argv=None):
    """build_fn(ctx) -> dict(uv=[names], post_uv=callable(objs) or None, tracks=TrackSpec or None,
    roots=[names], hubs={name: (hub, kind)}, cfg={paint cfg}, preview={...}, extra=[lines])"""
    opts = vk.parse_args(argv)
    out = opts["out"] or os.path.join(REPO, "godot", "assets", "units3d", vid)
    os.makedirs(out, exist_ok=True)
    qa_dir = os.environ.get("VEH_QA_DIR") or os.path.join(out, "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    if qa_dir.startswith(out):
        open(os.path.join(qa_dir, ".gdignore"), "w").close()
    reset_scene()
    ctx = Ctx(vid)
    spec = build_fn(ctx)
    objs = ctx.objs
    uv_objs = [objs[n] for n in spec["uv"]]
    bpy.context.view_layer.update()
    smart_uv(uv_objs, margin=0.003)
    if spec.get("post_uv"):
        spec["post_uv"](objs)
    extra = list(spec.get("extra", []))
    m_per_v = None
    if spec.get("tracks") is not None:
        tracks, m_per_v, total, n_links = vk.build_tracks(spec["tracks"], ctx.track_mat)
        objs.update(tracks)
        extra.append(f"track loop {total:.3f} m, links {n_links}, link pitch {total / n_links:.4f} m, "
                     f"metres per V (track_m_per_v) {m_per_v:.4f} (tile = {spec['tracks'].lpt} links)")
    bpy.context.view_layer.update()
    cfg = dict(spec.get("cfg", {}))
    cfg["hubs"] = spec.get("hubs", {})
    albedo = os.path.join(out, f"{vid}_albedo.png")
    _, cover = texture_atlas_ir(uv_objs, cfg, 2048, albedo)
    extra.append(f"atlas coverage {cover:.3f}")
    vk.attach_texture(ctx.mat, load_image(albedo, f"{vid}_albedo"))
    if spec.get("tracks") is not None:
        trk = os.path.join(out, f"{vid}_track.png")
        track_texture(trk, spec["tracks"].lpt)
        vk.attach_texture(ctx.track_mat, load_image(trk, f"{vid}_track"))
    for tgt, part in ctx.team:
        o = part.build(None, bevel=0.0)
        vk.join_team(objs[tgt], o)
    roots = [objs[n] for n in spec["roots"]]
    export = vk.all_descendants(roots)
    strip_tags(export)
    extra += normals_check(export)
    glb = os.path.join(out, f"{vid}.glb")
    vk.export_glb(export, glb)
    txt = vk.report(vid, export, extra)
    with open(os.path.join(qa_dir, f"{vid}_report.txt"), "w") as f:
        f.write(txt + "\n")
    print("GLB", glb)
    if opts["do_prev"]:
        pv = spec["preview"]
        L, W, H = pv["length"], pv["width"], pv["height"]
        # back-face-culled workbench QA (holes = inverted normals)
        backface_qa(os.path.join(qa_dir, f"{vid}_backface"),
                    {"rts": ((0, 0, H * 0.3), 45, 52, pv["rts_dist"]),
                     "low_rear": ((0, 0, H * 0.4), -150, 10, pv["close_dist"])})
        prev_dir = qa_dir if opts["quick"] else opts["prev"]
        os.makedirs(prev_dir, exist_ok=True)
        sheet = preview_sheet_ir(vid, title, prev_dir, quick=opts["quick"], **pv)
        print("SHEET", sheet)
    return objs, m_per_v


# ============================================================================ T-72-family tracked chassis
T72 = dict(nose=3.45, rear=-3.45, belly=0.45, deck=1.42, sponson_z=1.10, half_lo=1.08, half_hi=1.72,
           glacis_y=2.05, track=vk.TrackSpec(
               track_x=1.40, width=0.58, thick=0.10, wheel_r=0.375,
               wheel_ys=[2.30, 1.47, 0.66, -0.16, -0.98, -1.95],
               idler=(3.02, 0.55, 0.27), sprocket=(-3.05, 0.62, 0.31),
               rollers=[(1.88, 0.885, 0.09), (0.26, 0.885, 0.09), (-1.36, 0.885, 0.09)],
               pitch=0.15, links_per_tile=6, wheel_w=0.19, wheel_gap=0.13, sprocket_teeth=12))


def t72_hull(H, C=T72, skirts="armour", deck_louvres=True, rear_log=False, drums=False, exhaust=True,
             front_lights=True):
    """Adds the T-72-family hull (lower hull, sponsons, glacis, fenders, skirts, rear plate details) to TPart H.
    skirts: 'armour' (thick boxy plates, Karrar) | 'rubber' (thin, T-72S) | 'plain' (engineer)."""
    n, r, b, d, sz = C["nose"], C["rear"], C["belly"], C["deck"], C["sponson_z"]
    gy = C["glacis_y"]
    lo, hi = C["half_lo"], C["half_hi"]
    H.t("camo")
    # lower hull between the tracks (closed side profile)
    # (kept below / inside the sponson shell so no faces are coplanar with it -> no z-fighting)
    H.side([(3.05, b), (n - 0.01, 0.92), (n - 0.01, 0.97), (n - 0.60, 1.15), (r + 0.02, 1.15), (r + 0.02, 0.72),
            (r + 0.28, b)], -lo, lo)
    # upper hull / sponsons over the tracks
    H.side([(n - 0.03, sz), (n, 0.98), (gy, d), (r + 0.12, d), (r, d - 0.12), (r, sz)], -hi, hi)
    # fender lips (thin plates over the track run), front mudguards turned up
    for s in (-1, 1):
        H.box((s * (hi - 0.02), (n + r) / 2, sz - 0.015), (0.04, n - r, 0.03))
        H.obox((s * 1.40, n + 0.05, 1.04), (0.60, 0.22, 0.03), (0, 0.35, 1.0))
    return H


def t72_skirts(H, C=T72, kind="armour", y0=2.25, y1=None):
    r = C["rear"]
    y1 = r + 0.12 if y1 is None else y1
    hi = C["half_hi"]
    for s in (-1, 1):
        if kind == "armour":
            # boxy composite side skirt: lower main plates + upper band, slightly thicker at the front
            H.t("skirt").box((s * (hi + 0.05), (y0 + y1) / 2, 1.02), (0.10, y0 - y1, 0.80))
            H.t("camo").box((s * (hi + 0.06), (y0 + y1) / 2, 1.43), (0.12, y0 - y1 + 0.02, 0.04))
            H.t("skirt").obox((s * (hi + 0.05), y0 + 0.42, 1.12), (0.10, 0.85, 0.60), (0, 1, 0.45))
        elif kind == "rubber":
            H.t("skirt").box((s * (hi + 0.02), (y0 + y1) / 2, 1.13), (0.035, y0 - y1, 0.58))
            H.t("rubber").obox((s * (hi + 0.02), y0 + 0.40, 1.15), (0.035, 0.80, 0.42), (0, 1, 0.35))
        else:
            H.t("skirt").box((s * (hi + 0.02), (y0 + y1) / 2, 1.10), (0.04, y0 - y1, 0.64))
            H.t("camo").obox((s * (hi + 0.02), y0 + 0.40, 1.14), (0.04, 0.80, 0.45), (0, 1, 0.35))
    H.t("camo")


def t72_details(H, C=T72, rear_log=False, drums=False, exhaust=True, lights=True, louvres=True, rear_boxes=True,
                fender_boxes=True):
    n, r, d = C["nose"], C["rear"], C["deck"]
    hi = C["half_hi"]
    # driver's hatch + vision block on the glacis line
    hatch(H, (0.0, 2.02, d), 0.30, h=0.05)
    H.t("glass").obox((0.0, 2.33, d - 0.03), (0.32, 0.04, 0.09), (0, 0.6, 1.0))
    H.t("camo")
    if lights:
        for s in (-1, 1):
            light_cluster(H, (s * 1.42, 3.05, 1.17), facing=1, w=0.22, h=0.13)
    # tow hooks front and rear
    for s in (-1, 1):
        H.t("metal").box((s * 0.65, n + 0.02, 0.86), (0.14, 0.10, 0.10))
        H.box((s * 0.75, r - 0.04, 0.95), (0.14, 0.10, 0.10))
        H.t("redlens").box((s * 1.45, r - 0.02, 1.30), (0.12, 0.04, 0.07))
    H.t("camo")
    if louvres:
        H.t("grille").box((0.0, -2.35, d + 0.02), (1.70, 1.30, 0.04))
        H.t("camo")
    if exhaust:
        H.t("dark").box((-hi + 0.15, -2.05, d - 0.02), (0.30, 0.55, 0.10))
        H.t("camo")
    if rear_log:
        H.t("canvas").tube((0.0, r - 0.10, d + 0.16), 0.13, 3.0, "x", seg=10)
        H.t("metal").box((-1.1, r - 0.10, d + 0.16), (0.06, 0.30, 0.30)); H.box((1.1, r - 0.10, d + 0.16), (0.06, 0.30, 0.30))
        H.t("camo")
    if drums:
        for s in (-1, 1):
            H.t("olive").tube((s * 0.62, r - 0.30, d + 0.30), 0.29, 0.86, "x", seg=14)
            H.t("metal").tube((s * 0.62, r - 0.30, d + 0.30), 0.30, 0.04, "x", seg=14)
        H.t("camo")
    if rear_boxes:
        for s in (-1, 1):
            H.box((s * 1.25, r - 0.10, d - 0.18), (0.55, 0.20, 0.30))
    # fender stowage boxes on the sponsons
    for s in ((-1, 1) if fender_boxes else ()):
        for k, y in enumerate((0.95, -0.35)):
            H.box((s * (hi - 0.22), y, d + 0.17), (0.40, 1.10, 0.34))


def t72_gear(ctx, C=T72):
    gear = vk.build_running_gear(C["track"], ctx.mat)
    ctx.objs.update(gear)
    return list(gear.keys())


def gear_hubs(ctx, left_names, C=T72):
    sp = C["track"]
    hubs = {}
    for nm in left_names:
        o = ctx.objs[nm]
        y, z = o.location.y, o.location.z
        if nm.startswith("Wheel"):
            hubs[nm] = ((y, z, sp.wheel_r, None), "road")
        elif nm.startswith("Idler"):
            hubs[nm] = ((y, z, sp.idler[2], None), "idler")
        else:
            hubs[nm] = ((y, z, sp.sprocket[2], None), "sprocket")
    return hubs


def gear_roots(n_wheels):
    return ([f"Wheel{s}{i}" for s in "LR" for i in range(n_wheels)] +
            ["IdlerL", "IdlerR", "SprocketL", "SprocketR", "TrackL", "TrackR"])


def gun_barrel(G, ty, tz, profile, seg=14):
    """Lathe a barrel along +Y from the trunnion; profile = [(dy, r), ...]."""
    lathe(G, (0, ty, tz), profile, seg=seg, axis="y")
