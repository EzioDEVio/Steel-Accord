"""Steel Accord - shared kit for the Iranian aircraft (wave 1), bpy 5.x.

Builds on tools/art/airkit.py (imported read-only; the U.S. scripts and outputs are not touched).
Differences from the U.S. pipeline:

  * no concept projection. The Iran concept panels are 3/4 perspective renders, so geometry is authored
    from real-world dimensions (metres) and the albedo atlas is PAINTED procedurally in world space:
      - camouflage: sand / brown / green (desert) or two-tone grey, from deterministic warped 3D noise,
        thresholded by quantile so each colour has a controlled coverage; optional anisotropy for the
        banded transport scheme; optional light underside
      - panel lines (stations along Y, chord lines on wings, longitudinal lines on fuselage sides)
      - decals projected along an axis inside a slab: roundels (green / white / red concentric),
        fin flashes (green / white / red horizontal stripes, no emblem, no text), window polygons
      - zones (radome, nozzle, walkway...) and per-part flat colours (gear, glass, stores, dark intakes)
      - Cycles AO bake multiplied in, light grime; no text or calligraphy anywhere
  * finish_ir() can keep some textured parts as separate top-level nodes that share the atlas
    (F-14 WingL / WingR with the pivot at the glove; AH-1J Gun barrel group)
  * QA: per-island signed-volume check of face orientation (outward normals) for every exported mesh

Conventions (same as M3): metres; forward = Blender +Y (Godot -Z); up = +Z; root origin = ground contact
under the fuselage midpoint; all nodes top-level; materials SA_<ID>, SA_<ID>_Blade / _Prop, SA_Team.
"""
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import airkit as K  # noqa: E402
import numpy as np  # noqa: E402
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

L = K.L
PI = math.pi
REPO = K.REPO
OUT3D = K.OUT3D
SCREENS = K.SCREENS

# ----------------------------------------------------------------------------------------------- palette
# sRGB albedo values (as written to the PNG)
SAND = (0.74, 0.63, 0.44)
BROWN = (0.50, 0.38, 0.24)
GREEN = (0.37, 0.39, 0.27)
UNDER_GREY = (0.68, 0.69, 0.67)
GREY_A = (0.61, 0.64, 0.67)
GREY_B = (0.47, 0.51, 0.55)
LIGHT_GREY = (0.78, 0.79, 0.78)
RADOME_BLACK = (0.09, 0.09, 0.09)
GEAR = (0.16, 0.16, 0.16)
STORE_GREY = (0.72, 0.73, 0.72)
GLASS = (0.17, 0.21, 0.25)
METAL = (0.30, 0.29, 0.27)
NOZZLE = (0.24, 0.22, 0.20)
FLAG_G = (0.10, 0.52, 0.24)
FLAG_W = (0.93, 0.93, 0.90)
FLAG_R = (0.80, 0.11, 0.11)

SCHEMES = {
    # name: (base, c1, c2, coverage c1, coverage c2)
    "desert": (SAND, BROWN, GREEN, 0.32, 0.30),
    "desert2": (SAND, GREEN, BROWN, 0.40, 0.18),       # transports: sand + olive bands, little brown
    "grey": (GREY_A, GREY_B, GREY_B, 0.28, 0.0),
    "light": (LIGHT_GREY, (0.70, 0.71, 0.70), (0.70, 0.71, 0.70), 0.18, 0.0),
}


def smooth_noise(P, scale, seed=0, octaves=3, dirs=4, decay=2.3):
    """Deterministic low-frequency 3D noise (summed sines, few octaves, steep decay) in about -1..1.
    Large soft blobs suitable for hand-sprayed camouflage. No RNG state is touched (local RandomState)."""
    rng = np.random.RandomState(1000 + seed)
    acc = np.zeros(len(P)); norm = 0.0
    for k in range(octaves):
        a = 1.0 / decay ** k
        for _ in range(dirs):
            d = rng.normal(size=3); d /= np.linalg.norm(d)
            f = (1.9 ** k) / scale
            acc += a * np.sin(P @ d * f * 2 * PI + rng.uniform(0, 2 * PI))
            norm += a
    return acc / (norm * 0.45)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def in_poly(u, v, poly):
    """Vectorised even-odd point-in-polygon test."""
    inside = np.zeros(len(u), bool)
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        c = ((yi > v) != (yj > v)) & (u < (xj - xi) * (v - yi) / ((yj - yi) if yj != yi else 1e-12) + xi)
        inside ^= c
        j = i
    return inside


_AX = {"x": (0, (1, 2)), "y": (1, (0, 2)), "z": (2, (0, 1))}


class Decal:
    """Projected along `axis`; coordinates in the other two axes (x: (y, z); y: (x, z); z: (x, y)).
    side: +1 / -1 normal sign required, 0 = either. slab(P) -> bool mask limits depth. objs: keys or None."""

    def __init__(self, axis, side=0, slab=None, objs=None, min_n=0.3):
        self.axis, self.side, self.slab, self.objs, self.min_n = axis, side, slab, objs, min_n

    def mask(self, P, N, O, keyidx):
        a, _ = _AX[self.axis]
        n = N[:, a]
        m = (np.abs(n) > self.min_n) if self.side == 0 else (n * self.side > self.min_n)
        if self.slab is not None:
            m &= self.slab(P)
        if self.objs is not None:
            mo = np.zeros(len(P), bool)
            for k in self.objs:
                if k in keyidx:
                    mo |= O == keyidx[k]
            m &= mo
        return m

    def uv(self, P):
        _, (i, j) = _AX[self.axis]
        return P[:, i], P[:, j]


class Roundel(Decal):
    def __init__(self, center, r, axis, **kw):
        super().__init__(axis, **kw)
        self.c, self.r = center, r

    def paint(self, col, P, N, O, keyidx):
        m = self.mask(P, N, O, keyidx)
        if not m.any():
            return
        u, v = self.uv(P[m])
        d = np.hypot(u - self.c[0], v - self.c[1]) / self.r
        c = col[m]
        for rr, cc in ((1.0, FLAG_G), (0.68, FLAG_W), (0.36, FLAG_R)):
            c = np.where((d <= rr)[:, None], np.array(cc), c)
        col[m] = c


class Poly(Decal):
    def __init__(self, pts, rgb, axis, **kw):
        super().__init__(axis, **kw)
        self.pts, self.rgb = pts, rgb

    def paint(self, col, P, N, O, keyidx):
        m = self.mask(P, N, O, keyidx)
        if not m.any():
            return
        u, v = self.uv(P[m])
        ins = in_poly(u, v, self.pts)
        c = col[m]
        c[ins] = np.array(self.rgb)
        col[m] = c


class Circle(Decal):
    def __init__(self, center, r, rgb, axis, **kw):
        super().__init__(axis, **kw)
        self.c, self.r, self.rgb = center, r, rgb

    def paint(self, col, P, N, O, keyidx):
        m = self.mask(P, N, O, keyidx)
        if not m.any():
            return
        u, v = self.uv(P[m])
        ins = np.hypot(u - self.c[0], v - self.c[1]) <= self.r
        c = col[m]
        c[ins] = np.array(self.rgb)
        col[m] = c


def fin_flash(y_le0, y_te0, z0, z1, sweep_le, sweep_te, slab, objs=("air",), side=0):
    """Green / white / red horizontal-stripe flash on a fin (axis x). Bottom edge y_le0..y_te0 at z0,
    top at z1; the leading and trailing edges shift by sweep_* metres per metre of height (negative =
    swept back)."""
    out = []
    h = (z1 - z0) / 3.0
    for k, rgb in enumerate((FLAG_R, FLAG_W, FLAG_G)):           # bottom red, middle white, top green
        za, zb = z0 + k * h, z0 + (k + 1) * h
        pts = [(y_le0 + sweep_le * (za - z0), za), (y_te0 + sweep_te * (za - z0), za),
               (y_te0 + sweep_te * (zb - z0), zb), (y_le0 + sweep_le * (zb - z0), zb)]
        out.append(Poly(pts, rgb, "x", side=side, slab=slab, objs=objs))
    return out


def slab_absx(lo, hi):
    return lambda P: (np.abs(P[:, 0]) >= lo) & (np.abs(P[:, 0]) <= hi)


def slab_x(x0, th, cant_deg=0.0, z0=0.0):
    k = math.tan(math.radians(cant_deg))
    return lambda P: np.abs(P[:, 0] - (x0 + k * (P[:, 2] - z0))) <= th


def slab_z(lo, hi):
    return lambda P: (P[:, 2] >= lo) & (P[:, 2] <= hi)


def both(*fs):
    return lambda P: np.logical_and.reduce([f(P) for f in fs])


# ----------------------------------------------------------------------------------------------- painter
class Painter:
    """shade(P, N, O, depth) -> RGB for texture_atlas.
    keys: list of object keys in atlas order. flat: {key: rgb}. glass: {key: [frame y positions]}.
    zones: [(fn(P, N) -> mask, rgb, keys|None)]. decals: list of Decal. panel: dict(dy, dx, lon_z, keys)."""

    def __init__(self, keys, scheme="desert", camo_scale=3.0, aniso=(1, 1, 1), under=None, under_keys=None,
                 flat=None, glass=None, zones=(), decals=(), panel=None, grime=0.12, seed=0, camo_keys=None,
                 frame_w=0.06):
        self.keys = list(keys)
        self.keyidx = {k: i for i, k in enumerate(self.keys)}
        self.scheme = SCHEMES[scheme] if isinstance(scheme, str) else scheme
        self.camo_scale, self.aniso = camo_scale, np.array(aniso, float)
        self.under, self.under_keys = under, under_keys
        self.flat, self.glass = flat or {}, glass or {}
        self.zones, self.decals, self.panel = list(zones), list(decals), panel
        self.grime, self.seed, self.camo_keys, self.frame_w = grime, seed, camo_keys, frame_w

    def _om(self, O, keys):
        m = np.zeros(len(O), bool)
        for k in keys:
            if k in self.keyidx:
                m |= O == self.keyidx[k]
        return m

    def camo(self, P):
        base, c1, c2, f1, f2 = self.scheme
        Q = P * self.aniso[None]
        s = self.camo_scale
        w = np.stack([smooth_noise(Q, s * 1.3, seed=self.seed + 31 + a) for a in range(3)], -1) * (0.35 * s)
        Qw = Q + w
        n1 = smooth_noise(Qw, s, seed=self.seed + 11)
        n2 = smooth_noise(Qw, s * 0.9, seed=self.seed + 23)
        col = np.tile(np.array(base, float), (len(P), 1))
        e = 0.02
        if f1 > 0:
            t1 = np.quantile(n1, 1 - f1)
            a1 = smoothstep(t1 - e, t1 + e, n1)
        else:
            a1 = np.zeros(len(P))
        if f2 > 0:
            t2 = np.quantile(n2, 1 - f2 / max(1e-3, 1 - f1))
            a2 = smoothstep(t2 - e, t2 + e, n2) * (1 - a1)
        else:
            a2 = np.zeros(len(P))
        col = col * (1 - a1 - a2)[:, None] + np.array(c1) * a1[:, None] + np.array(c2) * a2[:, None]
        return col

    def __call__(self, P, N, O, depth):
        nz = N[:, 2]
        col = self.camo(P)
        if self.under is not None:
            um = np.ones(len(P), bool) if self.under_keys is None else self._om(O, self.under_keys)
            a = smoothstep(-0.25, -0.55, nz) * um
            col = col * (1 - a)[:, None] + np.array(self.under) * a[:, None]
        # panel lines
        if self.panel:
            pk = self.panel.get("keys")
            pm = np.ones(len(P), bool) if pk is None else self._om(O, pk)
            w = self.panel.get("w", 0.014)
            line = np.zeros(len(P), bool)
            dy = self.panel.get("dy")
            if dy:
                f = np.abs(((P[:, 1] + self.panel.get("y0", 0.0)) / dy + 0.5) % 1.0 - 0.5) * dy
                line |= f < w * 0.5
            dx = self.panel.get("dx")
            if dx:
                f = np.abs((P[:, 0] / dx + 0.5) % 1.0 - 0.5) * dx
                line |= (f < w * 0.5) & (np.abs(nz) > 0.6)
            for zl in self.panel.get("lon_z", ()):
                line |= (np.abs(P[:, 2] - zl) < w * 0.5) & (np.abs(N[:, 0]) > 0.5)
            k = self.panel.get("k", 0.80)
            col[line & pm] *= k
        # zones
        for fn, rgb, keys in self.zones:
            m = fn(P, N)
            if keys is not None:
                m &= self._om(O, keys)
            col[m] = np.array(rgb)
        # decals
        for d in self.decals:
            d.paint(col, P, N, O, self.keyidx)
        # flat parts
        for k, rgb in self.flat.items():
            m = self._om(O, [k])
            if m.any():
                col[m] = np.array(rgb) * (0.93 + 0.12 * L.value_noise(P[m], 0.4, seed=4))[:, None] if m.sum() > 8 else rgb
        # glass with frames (frames painted in the base colour)
        for k, frames in self.glass.items():
            m = self._om(O, [k])
            if not m.any():
                continue
            g = np.tile(np.array(GLASS), (m.sum(), 1))
            sheen = np.clip(N[m, 2], 0, 1) ** 2 * 0.10
            g = g + sheen[:, None]
            yy = P[m, 1]
            fr = np.zeros(m.sum(), bool)
            for yf in frames:
                fr |= np.abs(yy - yf) < self.frame_w * 0.5
            g[fr] = np.array(self.scheme[0]) * 0.85
            col[m] = g
        # weathering
        col *= (0.95 + 0.08 * L.value_noise(P, 0.9, seed=5))[:, None]
        if self.grime:
            g = np.clip((1.0 - P[:, 2]) / 1.0, 0, 1) * self.grime * L.value_noise(P, 0.5, seed=9)
            col = col * (1 - g[:, None]) + np.array([0.28, 0.25, 0.2]) * g[:, None]
        return np.clip(col, 0, 1)


# ----------------------------------------------------------------------------------------------- geometry helpers
def set_origin(o, p):
    """Move the object origin to world point p without moving the geometry (identity rotation kept)."""
    p = Vector(p)
    d = p - o.location
    o.data.transform(Matrix.Translation(-d))
    o.location = p
    return o


def fn(pts):
    """[(y, v), ...] in metres -> f(y) (linear, clamped)."""
    return K.polyline_fn(pts)


def wing(P, root_le, root_te, tip_le, tip_te, t_root=0.06, t_tip=0.04, mid=None, mirror=True, z_fn=None):
    """Straight-tapered lifting surface from (x, y, z) LE/TE points of root and tip (right side, +X).
    mid: optional list of intermediate (le, te, t). mirror: build both sides as one surface."""
    secs = [(root_le, root_te, t_root, (0, 0, 1))]
    for le, te, t in (mid or []):
        secs.append((le, te, t, (0, 0, 1)))
    secs.append((tip_le, tip_te, t_tip, (0, 0, 1)))
    if mirror:
        K.surface(P, K.mirror_sections(secs[1:]) + secs)
    else:
        K.surface(P, secs)


def fin(P, root_le, root_te, tip_le, tip_te, t_root=0.06, t_tip=0.05, x=0.0, cant_deg=0.0, side_sign=1):
    """Vertical/canted fin. root_* / tip_* = (y, z). Cant leans the tip outward towards side_sign."""
    ca, sa = math.cos(math.radians(cant_deg)), math.sin(math.radians(cant_deg))
    nrm = (ca * side_sign, 0, -sa)
    z0 = root_le[1]
    out = []
    for (yl, zl), (yt, zt), t in ((root_le, root_te, t_root), (tip_le, tip_te, t_tip)):
        h = zl - z0
        dx = side_sign * sa / max(ca, 1e-3) * h
        out.append(((x + dx, yl, zl), (x + dx, yt, zt), t, nrm))
    K.surface(P, out)


def nozzle(P, x, y_exit, z, r_out, length, r_in_frac=0.86, seg=20):
    """Engine nozzle tube from y_exit + length (front) back to y_exit (exit); returns dark-disc position."""
    K.body_rev(P, (x, y_exit, z), (x, y_exit + length, z),
               [(0, r_out * 0.92), (0.15, r_out), (1, r_out * 1.02)], seg=seg)
    return (x, y_exit + 0.03, z), r_out * r_in_frac


# ----------------------------------------------------------------------------------------------- QA
def orientation_report(objs):
    """For every connected island of every mesh: signed volume (outward normals => positive).
    Returns (n_islands, n_negative, list of (obj, island tris, volume)) for negative closed islands."""
    tot = neg = 0
    bad = []
    for o in objs:
        if o.type != "MESH":
            continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        seen = set()
        for f in bm.faces:
            if f.index in seen:
                continue
            stack = [f]; isl = []
            seen.add(f.index)
            while stack:
                g = stack.pop(); isl.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen:
                            seen.add(h.index); stack.append(h)
            vol = 0.0
            for g in isl:
                vs = [v.co for v in g.verts]
                for i in range(1, len(vs) - 1):
                    vol += vs[0].dot(vs[i].cross(vs[i + 1]))
            vol /= 6.0
            tot += 1
            if vol < -1e-7:
                neg += 1
                bad.append((o.name, len(isl), vol))
        bm.free()
    return tot, neg, bad


# ----------------------------------------------------------------------------------------------- pipeline
def parse_args(aid):
    argv = sys.argv[1:]
    o = {"out": os.path.join(OUT3D, aid), "prev": True, "quick": False,
         "sheet": os.path.join(SCREENS, f"{aid}_sheet.png")}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-previews":
            o["prev"] = False
        elif a == "--quick":
            o["quick"] = True
        elif a == "--sheet":
            o["sheet"] = argv[i + 1]; i += 1
        else:
            o["out"] = a
        i += 1
    os.makedirs(o["out"], exist_ok=True)
    return o


def preview_sheet(aid, title, length, span, height, out_png, quick=False, res=(640, 400), samples=20, close_az=-40,
                  ground_col=(0.30, 0.29, 0.26), close_el=16, close_k=1.2):
    """front / side / rear / top (ortho) + RTS 52 deg + close 3/4 (Cycles CPU, denoised)."""
    cam = L.setup_preview_scene(ground=True, ground_col=ground_col, size=max(length, span) * 4)
    sc = bpy.context.scene
    sc.cycles.samples = 6 if quick else samples
    tmp = tempfile.mkdtemp(prefix=f"ir_{aid}_")
    zc = height / 2
    asp = res[0] / res[1]
    fr = max(span, height * asp) * 1.12
    sd = max(length, height * asp) * 1.10
    tp = max(length, span * asp) * 1.06
    diag = math.sqrt(length ** 2 + span ** 2)
    views = [("front", 0, 5, (0, 0, zc), fr, None), ("side", -90, 5, (0, 0, zc), sd, None),
             ("rear", 180, 5, (0, 0, zc), fr, None), ("top", 0, 90, (0, 0, zc), tp, (1, 0, 0)),
             ("rts 52 deg", 45, 52, (0, 0, zc * 0.5), None, None),
             ("close 3/4", close_az, close_el, (0, 0, zc * 0.8), None, None)]
    if quick:
        views = [views[1], views[3], views[5]]
        res = (480, 300)
    shots = []
    for name, az, el, tgt, ortho, up in views:
        if ortho:
            L.aim(cam, tgt, az, el, diag * 3 + 50, ortho=ortho, roll_up=up)
        else:
            dist = diag * (1.75 if name.startswith("rts") else close_k)
            L.aim(cam, tgt, az, el, dist, lens=50)
        cam.data.clip_end = diag * 10 + 200
        p = os.path.join(tmp, name.replace(" ", "_").replace("/", "") + ".png")
        L.render(p, res)
        shots.append((p, name))
    L.contact_sheet(shots, out_png, cols=3, cell=res, title=title)
    return out_png


def finish_ir(aid, o, mat, objs, empties, painter_kw, bounds, dims, title, separate=(), extra_export=(),
              ao=0.42, cell=0.03, blade=None, ao_dist=0.9, prev_kw=None, atlas=2048):
    """objs: {key: obj} textured parts (+ optional 'team'). separate: keys exported as their own nodes
    (sharing the atlas). extra_export: other objects (rotors, props) exported as is.
    blade: (mat, png, image name). Returns (body, export list)."""
    keys = [k for k in objs if k != "team"]
    tex_objs = [objs[k] for k in keys]
    L.smart_uv(tex_objs, margin=0.003)
    painter = Painter(keys, **painter_kw)
    albedo = os.path.join(o["out"], f"{aid}_albedo.png")
    _, cover = K.texture_atlas(tex_objs, painter, atlas, 1024, ao, cell, bounds, albedo,
                               depth_objs=tex_objs + ([objs["team"]] if "team" in objs else []), ao_dist=ao_dist)
    K.attach_texture(mat, albedo, f"{aid}_albedo")
    if blade:
        K.attach_texture(blade[0], blade[1], blade[2])
    body_parts = [objs[k] for k in keys if k not in separate]
    body = K.join(body_parts, "Body")
    if "team" in objs:
        body = K.join_team(body, objs["team"])
    body.name = "Body"; body.data.name = "Body"
    seps = []
    for k in separate:
        ob = objs[k]
        ob.name = k; ob.data.name = k
        seps.append(ob)
    ems = [K.empty(n, p) if not isinstance(p, dict) else K.empty(n, p["loc"], p.get("rot", (0, 0, 0)))
           for n, p in empties.items()]
    export = [body] + seps + list(extra_export) + ems
    glb = os.path.join(o["out"], f"{aid}.glb")
    K.export_glb(export, glb)
    tot, neg, bad = orientation_report([e for e in export if e.type == "MESH"])
    print(f"{aid.upper()} atlas coverage {cover:.3f}")
    print(K.report(export, body))
    print(f"{aid.upper()} normals: {tot} islands, {neg} inward" + (f" {bad[:6]}" if bad else ""))
    print(f"{aid.upper()} GLB", glb)
    if o["prev"]:
        preview_sheet(aid, title, dims[0], dims[1], dims[2], o["sheet"], quick=o["quick"], **(prev_kw or {}))
        print(f"{aid.upper()} sheet", o["sheet"])
    return body, export


def blade_png(out_dir, aid, rgb=(0.09, 0.09, 0.09), tip=(0.80, 0.68, 0.12), suffix="blade"):
    p = os.path.join(out_dir, f"{aid}_{suffix}.png")
    K.flat_texture(rgb, p, tip=tip)
    return p


def prop_png_redwhite(out_dir, aid, rgb=(0.075, 0.08, 0.085)):
    """Propeller strip: dark blade, white then red tip bands (V along span)."""
    col = np.ones((64, 16, 3)) * np.array(rgb)
    col[int(0.86 * 64):int(0.93 * 64)] = np.array(FLAG_W)
    col[int(0.93 * 64):] = np.array(FLAG_R)
    col[: int(0.05 * 64)] = np.array((0.07, 0.07, 0.065))
    p = os.path.join(out_dir, f"{aid}_prop.png")
    L.save_png(col, p)
    return p
