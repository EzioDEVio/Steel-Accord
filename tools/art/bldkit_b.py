"""Steel Accord - structure kit B (shared pipeline for the M1 structures: airfield, drop zone, radar, defense tower,
HESCO segment, parachute crate prop). Generalises the approved pilot pipeline of bld_supply_depot_3d.py
(which is left untouched):

  * every primitive is tagged with a *source surface* = tileable numpy texture mapped by a world-planar 'tile' UV
    (or a preset UV, e.g. along the arc of a hangar roof);
  * optional per-structure *plan* surface: one large painted ground texture in world XY (runway, markings, pad targets);
  * one non-overlapping 'atlas' UV over all opaque parts; Cycles bakes DIFFUSE colour + AO; numpy composites
    colour x AO into one JPEG; every part then uses one Principled BSDF with that atlas (+ a double-sided variant);
  * SA_Team stays a plain white material; status / beacon / flood / runway lights are separate small mesh objects,
    each with its own emissive material SA_Light_<name>; empties mark gameplay points;
  * GLB export, then previews are rendered from the *re-imported* GLB with Cycles CPU.

Conventions (same as the depot): metres, origin = centre of the footprint at ground level, front = Blender -Y
(= Godot +Z). Deterministic: fixed noise seeds, fixed bake seed, fixed creation order.
Run every generator with `python3 -I`; the generators add this folder to sys.path themselves.
"""
import bpy, bmesh, math, sys, os, tempfile
import numpy as np
from mathutils import Matrix, Euler, Vector
from PIL import Image

PI = math.pi
V = Vector


# ====================================================================== args
class Args:
    def __init__(self, argv):
        argv = list(argv)

        def opt(name):
            if name in argv:
                i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
            return None
        self.previews = opt("--previews")
        self.concept = opt("--concept")
        self.only = opt("--only")
        self.skip_build = "--previews-only" in argv
        if self.skip_build:
            argv.remove("--previews-only")
        self.out = argv[0] if argv else "."
        os.makedirs(self.out, exist_ok=True)


# ====================================================================== tileable source textures
N = 512
UU = ((np.arange(N) + 0.5) / N)[None, :].repeat(N, 0)
VV = ((np.arange(N) + 0.5) / N)[:, None].repeat(N, 1)
_NOISE = {}


def noise(sx, sy, seed):
    """Tileable gaussian-filtered noise (N x N), unit std; sx/sy ~ feature size in px."""
    key = (sx, sy, seed)
    if key not in _NOISE:
        w = np.random.default_rng(seed).standard_normal((N, N))
        fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.fftfreq(N)[None, :]
        r = np.real(np.fft.ifft2(np.fft.fft2(w) * np.exp(-((fx * sx) ** 2 + (fy * sy) ** 2))))
        _NOISE[key] = (r / (r.std() + 1e-9)).astype(np.float32)
    return _NOISE[key]


def frac(a):
    return a - np.floor(a)


def col(r, g, b):
    return np.array([r, g, b], np.float32) / 255.0


def shade(base, k):
    return base[None, None, :] * k[..., None]


def lines(coord, count, width):
    return (frac(coord * count) < width).astype(np.float32)


def t_conc():          # tan cast concrete (S = 4 m)
    k = 1 + 0.025 * noise(70, 70, 1) + 0.03 * noise(3, 3, 2) - 0.04 * np.clip(noise(2, 90, 3), 0, None)
    k *= 1 - 0.12 * lines(VV, 3, 0.006)
    k *= 1 - 0.06 * lines(UU, 2, 0.004)
    return shade(col(176, 162, 140), k)


def t_gconc():         # grey cast concrete with form-tie dots + streaks (S = 4 m)
    k = 1 + 0.03 * noise(60, 60, 101) + 0.035 * noise(3, 3, 102) - 0.06 * np.clip(noise(2, 80, 103), 0, None)
    k *= 1 - 0.14 * lines(VV, 2, 0.006)
    k *= 1 - 0.08 * lines(UU, 2, 0.004)
    fu, fv = frac(UU * 4 + 0.125), frac(VV * 4 + 0.125)
    k *= 1 - 0.25 * (((fu - 0.5) ** 2 + (fv - 0.5) ** 2) < 0.0012)
    return shade(col(150, 147, 140), k)


def t_slab():
    k = 1 + 0.025 * noise(90, 90, 4) + 0.03 * noise(3, 3, 5) - 0.05 * np.clip(noise(25, 25, 6) - 1.2, 0, None)
    k *= 1 - 0.35 * np.maximum(lines(UU, 2, 0.004), lines(VV, 2, 0.004))
    return shade(col(156, 146, 131), k)


def t_roof():          # olive standing seam (ribs repeat along u)
    f = frac(UU * 8)
    k = np.where(f < 0.1, 1.22, np.where(f < 0.2, 0.74, 1.0 - 0.08 * (f - 0.2)))
    k = k * (1 + 0.02 * noise(80, 80, 7) + 0.025 * noise(2, 2, 8) - 0.05 * np.clip(noise(2, 70, 9), 0, None))
    k *= 1 - 0.18 * lines(VV, 1, 0.004)
    return shade(col(102, 103, 82), k)


def t_clad():
    f = frac(UU * 10)
    k = np.where(f < 0.25, 1.16, np.where((f > 0.5) & (f < 0.68), 0.76, 1.0))
    k = k * (1 + 0.025 * noise(80, 80, 10) + 0.02 * noise(2, 2, 11) - 0.06 * np.clip(noise(2, 60, 12), 0, None))
    return shade(col(90, 92, 72), k)


def t_door():
    f = frac(VV * 14)
    k = np.where(f < 0.14, 0.62, np.where(f < 0.3, 1.14, 1.0)) * (1 + 0.04 * noise(40, 40, 13) + 0.02 * noise(2, 2, 14))
    return shade(col(146, 146, 140), k)


def t_odoor():         # olive roll-up / hangar door slats
    f = frac(VV * 14)
    k = np.where(f < 0.14, 0.66, np.where(f < 0.3, 1.12, 1.0)) * (1 + 0.04 * noise(40, 40, 113) + 0.02 * noise(2, 2, 114))
    return shade(col(92, 96, 70), k)


def t_container():
    s = np.sin(UU * 2 * PI * 10)
    k = (1 + 0.14 * np.tanh(3 * s)) * (1 + 0.03 * noise(50, 50, 15) + 0.02 * noise(2, 2, 16))
    k *= 1 - 0.1 * np.clip(noise(2, 50, 17), 0, None)
    return shade(col(78, 84, 62), k)


def t_tarp():
    k = 1 + 0.07 * noise(30, 6, 18) + 0.05 * noise(6, 30, 19) + 0.02 * noise(2, 2, 20)
    k *= 1 - 0.15 * lines(UU + 0.25, 2, 0.006)
    return shade(col(176, 153, 115), k)


def t_crate():
    k = 1 + 0.05 * noise(20, 4, 21) + 0.02 * noise(2, 2, 22)
    k *= 1 - 0.25 * lines(VV, 8, 0.03)
    k *= 1 - 0.55 * lines(UU, 2, 0.02)
    img = shade(col(98, 101, 66), k)
    fu, fv = frac(UU * 2), frac(VV * 2)
    st = (fu > 0.3) & (fu < 0.7) & (fv > 0.45) & (fv < 0.55)
    img[st] = col(190, 178, 120)
    return img


def t_tcrate():        # tan plywood crate with darker edge battens
    k = 1 + 0.06 * noise(4, 30, 121) + 0.025 * noise(2, 2, 122)
    edge = np.maximum(lines(UU, 2, 0.07), lines(VV, 2, 0.07))
    k *= 1 - 0.22 * edge
    k *= 1 - 0.3 * lines(UU + 0.5, 2, 0.012)
    return shade(col(170, 134, 88), k)


def t_pallet():
    k = (1 + 0.08 * noise(3, 40, 23) + 0.03 * noise(2, 2, 24)) * (1 - 0.5 * lines(UU, 6, 0.06))
    return shade(col(138, 112, 76), k)


def t_wood():          # rough timber posts / beams
    k = (1 + 0.1 * noise(2, 40, 131) + 0.04 * noise(2, 2, 132)) * (1 - 0.25 * lines(UU, 5, 0.03))
    return shade(col(128, 100, 66), k)


def t_hazard():
    yel = (frac((UU + VV) * 4) < 0.5)
    img = np.where(yel[..., None], col(216, 172, 34)[None, None], col(32, 31, 28)[None, None])
    return img * (1 + 0.06 * noise(10, 10, 25))[..., None] * (1 - 0.15 * np.clip(noise(4, 4, 26) - 1.0, 0, None))[..., None]


def t_flat(rgb, amp, seed, size=40):
    def f():
        return shade(col(*rgb), 1 + amp * noise(size, size, seed) + 0.5 * amp * noise(2, 2, seed + 1))
    return f


def t_hvac():
    k = (1 + 0.03 * noise(40, 40, 27)) * (1 - 0.3 * np.maximum(lines(UU, 4, 0.01), lines(VV, 2, 0.01)))
    k *= 1 - 0.2 * lines(VV * 1.0, 24, 0.25) * (frac(UU * 4) > 0.5)
    return shade(col(170, 168, 162), k)


def t_cabinet():       # olive equipment cabinet: panel seams, vent grille strip
    k = (1 + 0.035 * noise(40, 40, 141) + 0.02 * noise(2, 2, 142)) * (1 - 0.35 * np.maximum(lines(UU, 2, 0.012), lines(VV, 1, 0.012)))
    k *= 1 - 0.25 * ((frac(VV * 1) > 0.72) & (frac(VV * 1) < 0.9) & (frac(UU * 2) > 0.15) & (frac(UU * 2) < 0.85)) * lines(VV, 40, 0.4)
    return shade(col(84, 92, 64), k)


def t_glass():
    frame = np.maximum(lines(UU, 4, 0.05), lines(VV, 2, 0.06))
    g = shade(col(58, 70, 88), 1 + 0.25 * (UU - VV) + 0.04 * noise(30, 30, 28))
    return np.where(frame[..., None] > 0, col(150, 152, 150)[None, None], g)


def t_cab():           # tower-cab glazing: teal tint, mullions every 1 m, sky reflection gradient
    frame = np.maximum(lines(UU, 4, 0.04), lines(VV, 1, 0.05))
    g = shade(col(52, 86, 92), 0.8 + 0.45 * VV + 0.05 * noise(30, 30, 151))
    return np.where(frame[..., None] > 0, col(74, 78, 70)[None, None], g)


def t_jersey():
    k = 1 + 0.05 * noise(50, 50, 29) + 0.03 * noise(2, 2, 30) - 0.05 * np.clip(noise(3, 3, 31) - 1.5, 0, None)
    return shade(col(150, 140, 123), k)


def t_hesco():         # geotextile liner behind welded-wire mesh (S = 1 m: 13 squares, vertical coils at edges)
    k = 1 + 0.06 * noise(6, 30, 161) + 0.05 * noise(30, 6, 162) + 0.03 * noise(2, 2, 163)
    k *= 1 - 0.12 * np.clip(noise(3, 40, 164), 0, None) * (VV < 0.4)        # dirt splash low on the cloth
    img = shade(col(150, 132, 100), k)
    wire = np.maximum(lines(UU, 13, 0.09), lines(VV, 13, 0.09))
    return np.where(wire[..., None] > 0, col(98, 98, 92)[None, None], img)


def t_earth():         # lumpy earth / gravel fill
    k = 1 + 0.12 * noise(6, 6, 171) + 0.08 * noise(2, 2, 172) + 0.06 * noise(20, 20, 173)
    dots = (noise(1.5, 1.5, 174) > 1.6).astype(np.float32)
    img = shade(col(150, 124, 92), k)
    return img * (1 - 0.25 * dots)[..., None] + 0.12 * (noise(1.5, 1.5, 175) > 1.9)[..., None]


def t_sand():          # sandbags: tan woven, darker seams
    k = 1 + 0.05 * noise(2, 2, 181) + 0.05 * noise(20, 20, 182)
    k *= 1 - 0.08 * lines(UU, 60, 0.5) * 0.5
    return shade(col(176, 152, 108), k)


def t_canvas_o():      # olive parachute / cargo canvas
    k = 1 + 0.06 * noise(20, 20, 191) + 0.03 * noise(2, 2, 192) + 0.05 * noise(60, 8, 193)
    return shade(col(98, 106, 70), k)


def t_canvas_t():      # sand parachute gore
    k = 1 + 0.06 * noise(20, 20, 195) + 0.03 * noise(2, 2, 196) + 0.05 * noise(60, 8, 197)
    return shade(col(168, 156, 120), k)


def t_camonet():       # bundled parachute / camo net: blotchy greens
    a = noise(16, 16, 201); b = noise(6, 6, 202)
    c1, c2, c3 = col(66, 84, 52), col(92, 104, 64), col(48, 58, 40)
    img = np.where((a > 0.4)[..., None], c2[None, None], np.where((b > 0.8)[..., None], c3[None, None], c1[None, None]))
    return img * (1 + 0.06 * noise(2, 2, 203))[..., None] * (1 - 0.18 * lines(UU + VV, 6, 0.04))[..., None]


def t_dish():          # olive dish face: concentric / radial panel seams come from geometry, here plates + grime
    k = (1 + 0.04 * noise(30, 30, 211) + 0.025 * noise(2, 2, 212) - 0.05 * np.clip(noise(4, 50, 213), 0, None))
    k *= 1 - 0.3 * np.maximum(lines(UU, 3, 0.012), lines(VV, 3, 0.012))
    return shade(col(90, 95, 68), k)


def t_strap():         # cargo webbing
    k = (1 + 0.04 * noise(2, 30, 221)) * (1 - 0.2 * lines(VV, 20, 0.3))
    return shade(col(150, 138, 70), k)


def t_grate():         # steel floor grating / drain
    k = (1 - 0.55 * np.maximum(lines(UU, 30, 0.35), lines(VV, 8, 0.12))) * (1 + 0.05 * noise(10, 10, 231))
    return shade(col(96, 96, 92), k)


def t_louvre():        # vent louvre panel
    k = (1 - 0.5 * lines(VV, 10, 0.45)) * (1 + 0.04 * noise(20, 20, 241))
    return shade(col(100, 102, 96), k)


SURF = {  # name: (texture fn, world size of one tile in metres)
    "conc": (t_conc, 4.0), "gconc": (t_gconc, 4.0), "slab": (t_slab, 6.0), "roof": (t_roof, 4.0),
    "clad": (t_clad, 3.0), "door": (t_door, 2.0), "odoor": (t_odoor, 2.0), "cont": (t_container, 3.0),
    "tarp": (t_tarp, 2.0), "crate": (t_crate, 1.2), "tcrate": (t_tcrate, 1.0), "pallet": (t_pallet, 1.2),
    "wood": (t_wood, 2.0), "hazard": (t_hazard, 1.6), "hvac": (t_hvac, 2.0), "cabinet": (t_cabinet, 1.6),
    "glass": (t_glass, 2.0), "cab": (t_cab, 4.0), "jersey": (t_jersey, 3.0), "hesco": (t_hesco, 1.0),
    "earth": (t_earth, 2.0), "sand": (t_sand, 1.0), "canvas_o": (t_canvas_o, 3.0), "canvas_t": (t_canvas_t, 3.0),
    "camonet": (t_camonet, 2.5), "dish": (t_dish, 3.0), "strap": (t_strap, 1.0), "grate": (t_grate, 1.0),
    "louvre": (t_louvre, 1.0),
    "metal": (t_flat((84, 86, 84), 0.05, 40), 2.0), "dark": (t_flat((30, 30, 28), 0.05, 42), 1.0),
    "yellow": (t_flat((214, 172, 42), 0.05, 44), 2.0), "lamp": (t_flat((255, 238, 186), 0.02, 46), 1.0),
    "rubber": (t_flat((26, 26, 25), 0.05, 48), 1.0), "olive": (t_flat((86, 92, 60), 0.06, 50), 2.0),
    "lolive": (t_flat((112, 116, 84), 0.05, 54), 2.0), "white": (t_flat((206, 206, 200), 0.03, 56), 2.0),
    "red": (t_flat((150, 36, 30), 0.05, 58), 1.0), "blue": (t_flat((40, 70, 150), 0.05, 60), 1.0),
    "steel": (t_flat((128, 130, 128), 0.05, 62), 2.0), "tan": (t_flat((168, 150, 112), 0.05, 64), 2.0),
    "team": (t_flat((235, 235, 235), 0.0, 52), 1.0),
}
DOUBLE_SIDED = {"canvas_o", "canvas_t"}     # faces of these surfaces get the double-sided atlas material


# ====================================================================== plan canvas (world-XY painted ground)
class Canvas:
    """Painted ground texture covering [x0,x1]x[y0,y1] (metres) at `ppm` px/m. Rows are bottom-up (row 0 = y0)."""

    def __init__(self, x0, x1, y0, y1, ppm):
        self.x0, self.x1, self.y0, self.y1, self.ppm = x0, x1, y0, y1, ppm
        self.W = int(round((x1 - x0) * ppm)); self.H = int(round((y1 - y0) * ppm))
        self.img = np.zeros((self.H, self.W, 3), np.float32)

    def _reg(self, bx0, bx1, by0, by1):
        p = self.ppm
        i0 = max(0, int(math.floor((by0 - self.y0) * p)) - 1); i1 = min(self.H, int(math.ceil((by1 - self.y0) * p)) + 1)
        j0 = max(0, int(math.floor((bx0 - self.x0) * p)) - 1); j1 = min(self.W, int(math.ceil((bx1 - self.x0) * p)) + 1)
        if i1 <= i0 or j1 <= j0:
            return None
        Y = self.y0 + (np.arange(i0, i1)[:, None] + 0.5) / p
        X = self.x0 + (np.arange(j0, j1)[None, :] + 0.5) / p
        X, Y = np.broadcast_arrays(X, Y)
        return (slice(i0, i1), slice(j0, j1)), X, Y

    @staticmethod
    def tsample(arr, X, Y, S):
        """Sample a tileable N x N array at world coords with tile size S (bilinear-free nearest; noise is smooth)."""
        n = arr.shape[0]
        i = (np.floor(Y / S * n).astype(np.int64)) % n; j = (np.floor(X / S * n).astype(np.int64)) % n
        return arr[i, j]

    def fill(self, bbox, fn):
        """fn(X, Y) -> (h, w, 3) colour, written over bbox."""
        r = self._reg(*bbox)
        if r is None:
            return
        sl, X, Y = r
        self.img[sl] = fn(X, Y)

    def paint(self, bbox, cover_fn, rgb, alpha=1.0, wear=0.25, seed=300):
        """cover_fn(X, Y) -> signed distance (metres, <0 inside). Antialiased; `wear` scuffs the paint."""
        r = self._reg(*bbox)
        if r is None:
            return
        sl, X, Y = r
        d = cover_fn(X, Y)
        a = np.clip(0.5 - d * self.ppm, 0, 1) * alpha
        if wear:
            w = self.tsample(noise(4, 4, seed), X, Y, 6.0) + 0.5 * self.tsample(noise(1.5, 1.5, seed + 1), X, Y, 3.0)
            a = a * np.clip(1 - wear * np.clip(w - 0.6, 0, None), 0, 1)
        c = np.asarray(rgb, np.float32) / 255.0 if max(rgb) > 1.0 else np.asarray(rgb, np.float32)
        base = self.img[sl]
        k = (base.mean(-1, keepdims=True) / 0.55) ** 0.5             # paint picks up the substrate's variation
        self.img[sl] = base * (1 - a[..., None]) + np.clip(c * (0.75 + 0.25 * k), 0, 1) * a[..., None]

    # --- shapes (signed distance helpers)
    def rect(self, x0, x1, y0, y1, rgb, **kw):
        cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0) / 2, abs(y1 - y0) / 2
        self.paint((cx - hx, cx + hx, cy - hy, cy + hy),
                   lambda X, Y: np.maximum(np.abs(X - cx) - hx, np.abs(Y - cy) - hy), rgb, **kw)

    def orect(self, cx, cy, L, W, ang, rgb, **kw):
        """Rectangle of length L along angle `ang` (radians) and width W."""
        ca, sa = math.cos(ang), math.sin(ang)
        R = (abs(L * ca) + abs(W * sa)) / 2 + 0.1, (abs(L * sa) + abs(W * ca)) / 2 + 0.1

        def d(X, Y):
            u = (X - cx) * ca + (Y - cy) * sa; v = -(X - cx) * sa + (Y - cy) * ca
            return np.maximum(np.abs(u) - L / 2, np.abs(v) - W / 2)
        self.paint((cx - R[0], cx + R[0], cy - R[1], cy + R[1]), d, rgb, **kw)

    def line(self, p0, p1, w, rgb, **kw):
        (x0, y0), (x1, y1) = p0, p1
        self.orect((x0 + x1) / 2, (y0 + y1) / 2, math.hypot(x1 - x0, y1 - y0) + w * 0.0, w, math.atan2(y1 - y0, x1 - x0), rgb, **kw)

    def ring(self, cx, cy, r0, r1, rgb, gaps=(), **kw):
        """Annulus; gaps = list of (centre_angle_deg, half_width_deg) left unpainted."""
        def d(X, Y):
            r = np.hypot(X - cx, Y - cy)
            dd = np.maximum(r0 - r, r - r1)
            if gaps:
                ang = np.degrees(np.arctan2(Y - cy, X - cx))
                for ga, gw in gaps:
                    da = np.abs((ang - ga + 180) % 360 - 180)
                    dd = np.maximum(dd, (gw - da) * np.radians(1) * r)
            return dd
        self.paint((cx - r1, cx + r1, cy - r1, cy + r1), d, rgb, **kw)

    def disc(self, cx, cy, r, rgb, **kw):
        self.paint((cx - r, cx + r, cy - r, cy + r), lambda X, Y: np.hypot(X - cx, Y - cy) - r, rgb, **kw)

    def arc(self, cx, cy, r, a0, a1, w, rgb, **kw):
        """Stroke of width w along a circular arc from a0 to a1 (deg, ccw)."""
        mid, half = (a0 + a1) / 2, (a1 - a0) / 2

        def d(X, Y):
            rr = np.hypot(X - cx, Y - cy)
            ang = np.degrees(np.arctan2(Y - cy, X - cx))
            da = np.abs((ang - mid + 180) % 360 - 180)
            return np.maximum(np.abs(rr - r) - w / 2, (da - half) * np.radians(1) * rr)
        self.paint((cx - r - w, cx + r + w, cy - r - w, cy + r + w), d, rgb, **kw)

    SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
           "7": "abc", "8": "abcdefg", "9": "abcdfg"}

    def digit(self, ch, cx, cy, h, rgb, ang=0.0, **kw):
        """Seven-segment style numeral of height h centred at (cx, cy); `ang` rotates it (0 = upright, reading +Y up)."""
        w, t = h * 0.55, h * 0.14
        segs = {"a": ((-w / 2, h / 2), (w / 2, h / 2)), "g": ((-w / 2, 0), (w / 2, 0)), "d": ((-w / 2, -h / 2), (w / 2, -h / 2)),
                "f": ((-w / 2, 0), (-w / 2, h / 2)), "b": ((w / 2, 0), (w / 2, h / 2)),
                "e": ((-w / 2, -h / 2), (-w / 2, 0)), "c": ((w / 2, -h / 2), (w / 2, 0))}
        ca, sa = math.cos(ang), math.sin(ang)
        for s in self.SEG[ch]:
            (ax, ay), (bx, by) = segs[s]
            ax, ay = cx + ax * ca - ay * sa, cy + ax * sa + ay * ca
            bx, by = cx + bx * ca - by * sa, cy + bx * sa + by * ca
            L = math.hypot(bx - ax, by - ay) + t
            self.orect((ax + bx) / 2, (ay + by) / 2, L, t, math.atan2(by - ay, bx - ax), rgb, **kw)


def ground_concrete(rgb=(160, 156, 146), joint=5.0, seed=310, stains=0.06):
    """fn(X, Y) for Canvas.fill: concrete panels with joints every `joint` m and soft stains."""
    def f(X, Y):
        T = Canvas.tsample
        k = 1 + 0.03 * T(noise(3, 3, seed), X, Y, 2.0) + 0.04 * T(noise(40, 40, seed + 1), X, Y, 30.0)
        k -= stains * np.clip(T(noise(25, 25, seed + 2), X, Y, 24.0) - 0.8, 0, None)
        k -= 0.05 * np.clip(T(noise(8, 8, seed + 3), X, Y, 9.0) - 1.4, 0, None)
        # per-panel tone shift
        pi = np.floor(X / joint); pj = np.floor(Y / joint)
        k *= 1 + 0.025 * np.sin(pi * 12.9898 + pj * 78.233) * np.cos(pi * 4.1 - pj * 2.7)
        jx = np.abs(frac(X / joint + 0.5) - 0.5) * joint; jy = np.abs(frac(Y / joint + 0.5) - 0.5) * joint
        k *= 1 - 0.32 * np.clip(1.5 - np.minimum(jx, jy) * 60, 0, 1)
        return (np.asarray(rgb, np.float32) / 255)[None, None] * k[..., None]
    return f


def ground_asphalt(rgb=(74, 75, 76), seed=330):
    def f(X, Y):
        T = Canvas.tsample
        k = 1 + 0.05 * T(noise(1.5, 1.5, seed), X, Y, 1.0) + 0.04 * T(noise(30, 30, seed + 1), X, Y, 25.0)
        k -= 0.06 * np.clip(T(noise(20, 4, seed + 2), X, Y, 20.0) - 0.7, 0, None)          # tyre streaks
        k += 0.05 * np.clip(T(noise(6, 6, seed + 3), X, Y, 8.0) - 1.2, 0, None)           # crack-seal patches
        return (np.asarray(rgb, np.float32) / 255)[None, None] * k[..., None]
    return f


# ====================================================================== kit
class Kit:
    def __init__(self, name, prefix, atlas=2048, ao_res=1024, ao_dist=4.0):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.name, self.prefix = name, prefix
        self.ATLAS, self.AO_RES, self.ao_dist = atlas, ao_res, ao_dist
        self.TMP = tempfile.mkdtemp(prefix=name + "_")
        self.mats = {}
        self.plan = None
        self.parts = []            # built atlas objects
        self.lights = []
        self.empties = []
        self.fences = []           # chain-link quads
        self.extra = []            # other export objects

    # ------------------------------------------------------------ images / materials
    def np_to_image(self, name, arr, alpha=None, colorspace="sRGB"):
        a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
        if alpha is not None:
            a8 = np.concatenate([a8, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)[..., None]], 2)
        path = os.path.join(self.TMP, name + ".png")
        Image.fromarray(a8[::-1]).save(path)
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = colorspace
        return img

    def mat(self, sname):
        if sname in self.mats:
            return self.mats[sname]
        m = bpy.data.materials.new("SA_Team" if sname == "team" else "SRC_" + sname)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.85
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.interpolation = "Cubic"
        if sname == "plan":
            tex.image = self.np_to_image(self.name + "_plan", self.plan.img); tex.interpolation = "Linear"
        else:
            tex.image = self.np_to_image("tile_" + sname, SURF[sname][0]())
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "tile"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        self.mats[sname] = m
        return m

    def set_plan(self, x0, x1, y0, y1, ppm):
        self.plan = Canvas(x0, x1, y0, y1, ppm)
        return self.plan

    def part(self, name, pivot=None):
        return Part(self, name, pivot)

    # ------------------------------------------------------------ lights / empties / fence
    def light(self, name, prims):
        """prims: list of ('box', centre, size, rot) | ('cyl', centre, r, depth, rot, seg) | ('sph', centre, r).
        Creates one mesh object `name` with its own emissive material SA_Light_<name> (white, strength 1)."""
        bm = bmesh.new()
        for p in prims:
            if p[0] == "box":
                _, c, s = p[:3]; rot = p[3] if len(p) > 3 else (0, 0, 0)
                M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*s, 1))
                bmesh.ops.create_cube(bm, size=1.0, matrix=M)
            elif p[0] == "cyl":
                _, c, r, d = p[:4]; rot = p[4] if len(p) > 4 else (0, 0, 0); seg = p[5] if len(p) > 5 else 8
                M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
                bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d, matrix=M)
            elif p[0] == "sph":
                _, c, r = p[:3]
                bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=r, matrix=Matrix.Translation(c))
        ctr = sum((v.co for v in bm.verts), V()) / max(1, len(bm.verts))
        bmesh.ops.translate(bm, verts=bm.verts, vec=-ctr)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); self.scene.collection.objects.link(o)
        o.location = ctr                     # origin at the lamp itself
        m = bpy.data.materials.new("SA_Light_" + name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Strength"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.4
        me.materials.append(m)
        for p in me.polygons:
            p.use_smooth = False
        self.lights.append(o)
        return o

    def empty(self, name, loc, parent=None):
        o = bpy.data.objects.new(name, None); o.empty_display_type = "PLAIN_AXES"; o.empty_display_size = 0.5
        self.scene.collection.objects.link(o)
        if parent is not None:
            o.parent = parent
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.location = V(loc) - parent.location
        else:
            o.location = V(loc)
        self.empties.append(o)
        return o

    def fence(self, p0, p1, z0, z1):
        self.fences.append((p0, p1, z0, z1))

    # ------------------------------------------------------------ finish: atlas, bake, composite, export
    def finish(self, out_dir, glb_name, ground_size=None):
        scene = self.scene
        objs = self.parts
        tex_name = self.name
        # fence object
        fence = None
        if self.fences:
            fbm = bmesh.new(); fuv = fbm.loops.layers.uv.new("UVMap")
            for (x0, y0), (x1, y1), z0, z1 in self.fences:
                L = math.hypot(x1 - x0, y1 - y0)
                vs = [fbm.verts.new(p) for p in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1))]
                f = fbm.faces.new(vs)
                for lp, uv in zip(f.loops, ((0, 0), (L, 0), (L, z1 - z0), (0, z1 - z0))):
                    lp[fuv].uv = uv
            fme = bpy.data.meshes.new("Fence"); fbm.to_mesh(fme); fbm.free()
            fence = bpy.data.objects.new("Fence", fme); scene.collection.objects.link(fence)
            fm = bpy.data.materials.new(self.prefix + "_Fence"); fm.use_nodes = True; fm.use_backface_culling = False
            fb = fm.node_tree.nodes["Principled BSDF"]; fb.inputs["Roughness"].default_value = 0.6
            fb.inputs["Metallic"].default_value = 0.3
            n = 256
            u = (np.arange(n) + 0.5)[None, :].repeat(n, 0); v = (np.arange(n) + 0.5)[:, None].repeat(n, 1)
            per = 32.0
            d1 = np.abs(frac((u + v) / per) - 0.5) * per; d2 = np.abs(frac((u - v) / per) - 0.5) * per
            a = np.clip(1.9 - np.minimum(d1, d2), 0, 1)
            ftex = fm.node_tree.nodes.new("ShaderNodeTexImage")
            ftex.image = self.np_to_image(tex_name + "_chainlink", np.full((n, n, 3), 0.62, np.float32), a)
            fm.node_tree.links.new(ftex.outputs["Color"], fb.inputs["Base Color"])
            fm.node_tree.links.new(ftex.outputs["Alpha"], fb.inputs["Alpha"])
            fme.materials.append(fm)

        # atlas UVs over all opaque parts
        for o in objs:
            o.data.uv_layers.new(name="atlas")
            o.data.uv_layers.active = o.data.uv_layers["atlas"]
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0015, area_weight=0.0)
        bpy.ops.uv.pack_islands(rotate=True, margin=0.0015, shape_method="AABB")
        bpy.ops.object.mode_set(mode="OBJECT")

        # bake colour then AO
        scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.seed = 7
        scene.render.bake.margin = 8
        col_img = bpy.data.images.new("bake_col", self.ATLAS, self.ATLAS)
        ao_img = bpy.data.images.new("bake_ao", self.AO_RES, self.AO_RES); ao_img.colorspace_settings.name = "Non-Color"
        src_mats = {m for o in objs for m in o.data.materials}
        targets = {}
        for m in sorted(src_mats, key=lambda m: m.name):
            n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = col_img
            m.node_tree.nodes.active = n; targets[m] = n
        hidden = ([fence] if fence else []) + self.lights
        for o in hidden:
            o.hide_render = True

        def sel():
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
        sel()
        scene.cycles.samples = 8
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=8, use_clear=True)
        for m, n in targets.items():
            n.image = ao_img
        world = bpy.data.worlds.new("bakeworld"); scene.world = world
        world.light_settings.distance = self.ao_dist
        gs = ground_size or 80
        bpy.ops.mesh.primitive_plane_add(size=gs, location=(0, 0, -0.001)); ground = bpy.context.active_object
        sel()
        scene.cycles.samples = 24
        bpy.ops.object.bake(type="AO", margin=8, use_clear=True)
        bpy.data.objects.remove(ground)
        for o in hidden:
            o.hide_render = False

        def img_np(img):
            a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
            return a.reshape(img.size[1], img.size[0], 4)[..., :3]
        c = img_np(col_img)
        ao = img_np(ao_img)[..., 0]
        ao = np.asarray(Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8)).resize((self.ATLAS, self.ATLAS), Image.BILINEAR), np.float32) / 255
        lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        lin *= (0.28 + 0.72 * ao ** 1.1)[..., None]
        srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
        out8 = (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]
        atlas_path = os.path.join(self.TMP, tex_name + "_albedo.jpg")
        Image.fromarray(out8).save(atlas_path, quality=90, optimize=True)

        # final materials
        atlas_img = bpy.data.images.load(atlas_path)

        def final_mat(nm, cull):
            m = bpy.data.materials.new(nm); m.use_nodes = True; m.use_backface_culling = cull
            bs = m.node_tree.nodes["Principled BSDF"]
            bs.inputs["Roughness"].default_value = 0.82; bs.inputs["Metallic"].default_value = 0.0
            at = m.node_tree.nodes.new("ShaderNodeTexImage"); at.image = atlas_img
            m.node_tree.links.new(at.outputs["Color"], bs.inputs["Base Color"])
            return m
        fin = final_mat(self.prefix + "_" + self.name.title().replace("_", ""), True)
        fin2 = final_mat(self.prefix + "_" + self.name.title().replace("_", "") + "_2S", False)
        team = self.mats.get("team")
        if team is not None:
            team.use_backface_culling = True
            for n in [n for n in team.node_tree.nodes if n.type in ("TEX_IMAGE", "UVMAP")]:
                team.node_tree.nodes.remove(n)
            team.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)

        for o in objs:
            me = o.data
            idx = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("material_index", idx)
            kind = np.array([0 if m.name not in ("SA_Team",) and m.name[4:] not in DOUBLE_SIDED else
                             (2 if m.name == "SA_Team" else 1) for m in me.materials], np.int32)
            k = kind[idx]
            used = sorted(set(k.tolist()))
            slots = [{0: fin, 1: fin2, 2: team}[u] for u in used]
            remap = {u: i for i, u in enumerate(used)}
            me.materials.clear()
            for s in slots:
                me.materials.append(s)
            me.polygons.foreach_set("material_index", np.array([remap[v] for v in k.tolist()], np.int32))
            me.uv_layers.remove(me.uv_layers["tile"])
            me.uv_layers["atlas"].name = "UVMap"
        if fence is not None:                    # join the fence into Props (or the first part)
            host = next((o for o in objs if o.name == "Props"), objs[0])
            bpy.ops.object.select_all(action="DESELECT")
            host.select_set(True); fence.select_set(True); bpy.context.view_layer.objects.active = host
            hn = host.name
            bpy.ops.object.join()
            host = bpy.context.active_object; host.name = hn; host.data.name = hn
            self.parts = objs = [host if o.name == hn else o for o in objs]

        ntris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
        ltris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in self.lights)
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs + self.lights + self.empties + self.extra:
            o.select_set(True)
        glb = os.path.join(out_dir, glb_name)
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True, use_selection=True,
                                  export_image_format="AUTO")
        print(self.name.upper(), "OK tris", ntris, "lights", len(self.lights), "light tris", ltris,
              "total", sum(ntris.values()) + ltris, "glb bytes", os.path.getsize(glb))
        return glb


# ====================================================================== geometry accumulator
class Part:
    """Accumulates primitives per (surface, bevel) into bmeshes; build() makes one joined object.
    A part with `pivot` gets its object origin at that point (mesh is built in world space, then shifted)."""

    def __init__(self, kit, name, pivot=None):
        self.kit, self.name, self.pivot, self.bms = kit, name, pivot, {}

    def bm(self, m, bev=False):
        key = (m, bev)
        if key not in self.bms:
            b = bmesh.new()
            b.loops.layers.uv.new("tile")
            b.faces.layers.int.new("preset")
            self.bms[key] = b
        return self.bms[key]

    @staticmethod
    def _drop_bottom(bm, verts):
        faces = {f for v in verts for f in v.link_faces}
        dead = []
        for f in faces:
            f.normal_update()
            if f.normal.z < -0.999:
                dead.append(f)
        bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")

    def box(self, m, c, size, rot=(0, 0, 0), bottom=False, bev=False):
        bm = self.bm(m, bev)
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
        if not bottom:
            self._drop_bottom(bm, r["verts"])

    def span(self, m, x0, x1, y0, y1, z0, z1, bottom=False, bev=False):
        self.box(m, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)),
                 bottom=bottom, bev=bev)

    def cyl(self, m, c, r, depth, rot=(0, 0, 0), seg=10, r2=None, bottom=False):
        bm = self.bm(m)
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                                    radius2=r if r2 is None else r2, depth=depth, matrix=M)
        if not bottom:
            self._drop_bottom(bm, res["verts"])

    def strut(self, m, a, b, r, seg=6):
        a, b = V(a), V(b)
        d = b - a
        M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r,
                              depth=d.length, matrix=M)

    def prism(self, m, pts, axis, a0, a1, bev=False, arc_uv=False, caps=True, M=None):
        """Extrude a closed 2D profile. axis 'x': pts are (y, z) extruded over x; axis 'y': pts are (x, z).
        arc_uv: side faces get u = extrusion coordinate, v = profile arc length (ribs follow the profile)."""
        bm = self.bm(m, bev)
        T = (lambda p: M @ V(p)) if M is not None else (lambda p: p)
        if axis == "x":
            A = [bm.verts.new(T((a0, p, q))) for p, q in pts]; B = [bm.verts.new(T((a1, p, q))) for p, q in pts]
        else:
            A = [bm.verts.new(T((p, a0, q))) for p, q in pts]; B = [bm.verts.new(T((p, a1, q))) for p, q in pts]
        n = len(A)
        fs = [bm.faces.new(A[::-1]), bm.faces.new(B)] if caps else []
        side = []
        for i in range(n):
            side.append(bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i])))
        fs += side
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        if arc_uv:
            uv = bm.loops.layers.uv["tile"]; pre = bm.faces.layers.int["preset"]
            S = SURF[m][1]
            acc = [0.0]
            for i in range(n):
                p, q = pts[i], pts[(i + 1) % n]
                acc.append(acc[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
            for i, f in enumerate(side):
                lut = {A[i]: (a0, acc[i]), A[(i + 1) % n]: (a0, acc[i + 1]), B[(i + 1) % n]: (a1, acc[i + 1]), B[i]: (a1, acc[i])}
                for lp in f.loops:
                    u, v = lut[lp.vert]
                    lp[uv].uv = (u / S, v / S)
                f[pre] = 1
        self._drop_bottom(bm, A + B)

    def frustum(self, m, x0, x1, y0, y1, z0, z1, inset, bev=False, top=True):
        bm = self.bm(m, bev)
        A = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
        B = [bm.verts.new(p) for p in ((x0 + inset, y0 + inset, z1), (x1 - inset, y0 + inset, z1),
                                       (x1 - inset, y1 - inset, z1), (x0 + inset, y1 - inset, z1))]
        if top:
            bm.faces.new(B)
        for i in range(4):
            bm.faces.new((A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]))

    def quad(self, m, pts):
        """Single polygon from a list of 3D points (ccw seen from the side it should face)."""
        bm = self.bm(m)
        bm.faces.new([bm.verts.new(p) for p in pts])

    def loft(self, m, rings, cap0=False, cap1=True, closed=True, bev=False, jitter=None):
        """Rings = list of equal-length lists of 3D points; quads between consecutive rings.
        jitter: optional (rng, amount_xy, amount_z, first_ring) -> deterministic lumpy displacement."""
        bm = self.bm(m, bev)
        if jitter is not None:
            rng, axy, az, r0 = jitter
            rings = [[(x + (rng.uniform(-axy, axy) if i >= r0 else 0), y + (rng.uniform(-axy, axy) if i >= r0 else 0),
                       z + (rng.uniform(-az, az) if i >= r0 else 0)) for (x, y, z) in ring] for i, ring in enumerate(rings)]
        R = [[bm.verts.new(p) for p in ring] for ring in rings]
        n = len(R[0]); fs = []
        for a, b in zip(R[:-1], R[1:]):
            for i in range(n if closed else n - 1):
                fs.append(bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])))
        if cap0:
            fs.append(bm.faces.new(R[0][::-1]))
        if cap1:
            fs.append(bm.faces.new(R[-1]))
        return fs

    def lathe(self, m, prof, M=Matrix.Identity(4), seg=16, a0=0.0, a1=2 * PI, closed_prof=False):
        """Revolve profile [(r, z), ...] about local Z (then transform by M). r == 0 points collapse to one vertex.
        closed_prof: also connect last profile point back to the first (thin shells)."""
        bm = self.bm(m)
        full = abs(a1 - a0 - 2 * PI) < 1e-6
        na = seg if full else seg + 1
        cols = []
        for j in range(na):
            a = a0 + (a1 - a0) * j / seg
            ca, sa = math.cos(a), math.sin(a)
            cols.append(a)
        P = []
        for (r, z) in prof:
            if r < 1e-6:
                v = bm.verts.new(M @ V((0, 0, z)))
                P.append([v] * na)
            else:
                P.append([bm.verts.new(M @ V((r * math.cos(a), r * math.sin(a), z))) for a in cols])
        npf = len(P)
        pairs = list(zip(range(npf - 1), range(1, npf)))
        if closed_prof:
            pairs.append((npf - 1, 0))
        for i0, i1 in pairs:
            for j in range(seg):
                j1 = (j + 1) % na if full else j + 1
                vs = [P[i0][j], P[i0][j1], P[i1][j1], P[i1][j]]
                uniq = []
                for v in vs:
                    if v not in uniq:
                        uniq.append(v)
                if len(uniq) >= 3:
                    try:
                        bm.faces.new(uniq)
                    except ValueError:
                        pass

    def build(self):
        kit = self.kit
        objs = []
        for (sname, bev), bm in sorted(self.bms.items()):
            bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces])
            uv = bm.loops.layers.uv["tile"]; pre = bm.faces.layers.int["preset"]
            if sname == "plan":
                pl = kit.plan
                for f in bm.faces:
                    for lp in f.loops:
                        p = lp.vert.co
                        lp[uv].uv = ((p.x - pl.x0) / (pl.x1 - pl.x0), (p.y - pl.y0) / (pl.y1 - pl.y0))
            else:
                S = SURF[sname][1]
                for f in bm.faces:
                    if f[pre]:
                        continue
                    n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
                    for lp in f.loops:
                        p = lp.vert.co
                        u, v = ((p.x, p.y) if ax == 2 else (p.y, p.z) if ax == 0 else (p.x, p.z))
                        lp[uv].uv = (u / S, v / S)
            me = bpy.data.meshes.new(f"{self.name}_{sname}{'_b' if bev else ''}")
            bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(me.name, me); kit.scene.collection.objects.link(o)
            me.materials.append(kit.mat(sname))
            if bev:
                b = o.modifiers.new("bv", "BEVEL")
                b.width = 0.035; b.segments = 1; b.limit_method = "ANGLE"; b.angle_limit = math.radians(40)
                b.harden_normals = True; b.use_clamp_overlap = True
            objs.append(o)
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            bpy.context.view_layer.objects.active = o
            for md in list(o.modifiers):
                bpy.ops.object.modifier_apply(modifier=md.name)
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        j = bpy.context.active_object; j.name = self.name; j.data.name = self.name
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
        if self.pivot is not None:
            pv = V(self.pivot)
            j.data.transform(Matrix.Translation(-pv))
            j.location = pv
        kit.parts.append(j)
        return j


# ====================================================================== reusable dressing
def ladder(P, p0, along, n_rungs, height, out, m="metal", half=0.22):
    p0 = V(p0); along = V(along); out = V(out)
    for s in (-half, half):
        a = p0 + along * s
        P.strut(m, a + out * 0.12, a + out * 0.12 + V((0, 0, height)), 0.025, seg=4)
    for k in range(n_rungs):
        z = 0.3 + k * (height - 0.4) / max(1, n_rungs - 1)
        P.strut(m, p0 + along * -half + out * 0.12 + V((0, 0, z)), p0 + along * half + out * 0.12 + V((0, 0, z)), 0.015, seg=4)


def railing(P, pts, z, h=1.05, post=1.6, m="metal", closed=False, r=0.025):
    """Posts + top and mid rails along a polyline at deck height z."""
    seq = list(pts) + ([pts[0]] if closed else [])
    for a, b in zip(seq[:-1], seq[1:]):
        a, b = V((*a, 0)), V((*b, 0))
        L = (b - a).length; n = max(1, int(math.ceil(L / post)))
        for k in range(n + (0 if closed else 1)):
            p = a + (b - a) * (k / n)
            P.strut(m, (p.x, p.y, z), (p.x, p.y, z + h), r * 1.2, seg=4)
        P.strut(m, (a.x, a.y, z + h), (b.x, b.y, z + h), r, seg=4)
        P.strut(m, (a.x, a.y, z + h * 0.5), (b.x, b.y, z + h * 0.5), r * 0.8, seg=4)
    if not closed:
        pass


def sandbag_row(P, a, b, z, layers=2, bag=(0.62, 0.34, 0.16), m="sand", stagger=True):
    """Stacked sandbags (bevelled boxes) along segment a-b, centred on it, starting at height z."""
    a, b = V((*a, 0)), V((*b, 0))
    d = b - a; L = d.length; ang = math.atan2(d.y, d.x)
    n = max(1, int(round(L / (bag[0] + 0.02))))
    s = L / n
    for l in range(layers):
        off = 0.5 * s if (stagger and l % 2) else 0.0
        cnt = n - (1 if off else 0)
        for k in range(cnt):
            t = (k + 0.5) * s + off
            p = a + d.normalized() * t
            P.box(m, (p.x, p.y, z + bag[2] * (l + 0.5)), (s - 0.03, bag[1], bag[2]), (0, 0, ang), bev=True)
    return z + layers * bag[2]


JERSEY = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.12, 0.3), (0.08, 0.81), (-0.08, 0.81), (-0.12, 0.3), (-0.3, 0.08)]


def jersey_run(P, a, b, fixed, axis, base, seglen=2.8, gap=0.12, prof=JERSEY, m="jersey"):
    L = abs(b - a); n = max(1, int(round(L / (seglen + gap)))); s = L / n
    for k in range(n):
        t0 = min(a, b) + k * s + gap / 2; t1 = t0 + s - gap
        P.prism(m, [(fixed + px, base + pz) for px, pz in prof], axis, t0, t1)


def pallet(P, cx, cy, base, sx=1.2, sy=1.0):
    P.span("pallet", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, base, base + 0.14)
    return base + 0.14


def ammo_pallet(P, cx, cy, base, layers=2, surf="crate", rot90=False):
    z = pallet(P, cx, cy, base)
    cw, cd, ch = (0.57, 0.47, 0.36) if not rot90 else (0.47, 0.57, 0.36)
    for l in range(layers):
        for i in (-1, 1):
            for j in (-1, 1):
                c = (cx + i * (cw / 2 + 0.01), cy + j * (cd / 2 + 0.01), z + l * (ch + 0.01) + ch / 2)
                P.box(surf, c, (cw, cd, ch))
    top = z + layers * (ch + 0.01)
    P.span("strap", cx - 0.6, cx + 0.6, cy - 0.04, cy + 0.04, base + 0.14, top + 0.015)
    P.span("strap", cx - 0.04, cx + 0.04, cy - 0.5, cy + 0.5, base + 0.14, top + 0.02)
    return top


def drum(P, x, y, base, m="olive"):
    P.cyl(m, (x, y, base + 0.45), 0.29, 0.9, seg=12)
    P.cyl("metal", (x, y, base + 0.91), 0.3, 0.03, seg=12, bottom=True)


def cabinet(P, cx, cy, base, sx, sy, h, face="-y"):
    """Olive equipment cabinet with plinth, roof lip and a door handle on `face`."""
    P.span("metal", cx - sx / 2 + 0.05, cx + sx / 2 - 0.05, cy - sy / 2 + 0.05, cy + sy / 2 - 0.05, base, base + 0.1)
    P.span("cabinet", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, base + 0.1, base + h, bev=True)
    P.span("olive", cx - sx / 2 - 0.05, cx + sx / 2 + 0.05, cy - sy / 2 - 0.05, cy + sy / 2 + 0.05, base + h, base + h + 0.06, bottom=True)
    if face == "-y":
        P.span("metal", cx + sx * 0.3, cx + sx * 0.3 + 0.04, cy - sy / 2 - 0.04, cy - sy / 2, base + h * 0.45, base + h * 0.6)
    elif face == "+x":
        P.span("metal", cx + sx / 2, cx + sx / 2 + 0.04, cy - sy * 0.3, cy - sy * 0.3 + 0.04, base + h * 0.45, base + h * 0.6)
    elif face == "-x":
        P.span("metal", cx - sx / 2 - 0.04, cx - sx / 2, cy - sy * 0.3, cy - sy * 0.3 + 0.04, base + h * 0.45, base + h * 0.6)


def flood_pole(kit, P, name, x, y, base, h=7.0, aim=None, heads=2):
    """Light pole with a cross-bar of flood heads aimed at `aim` (xy). Lenses become emissive object `name`."""
    P.span("conc", x - 0.25, x + 0.25, y - 0.25, y + 0.25, base, base + 0.35, bev=True)
    P.cyl("metal", (x, y, base + 0.35 + h / 2), 0.09, h, seg=8, r2=0.06)
    ax, ay = aim if aim is not None else (0.0, 0.0)
    yaw = math.atan2(ay - y, ax - x)
    zt = base + 0.35 + h
    P.box("metal", (x, y, zt + 0.1), (0.9 if heads > 1 else 0.3, 0.08, 0.08), (0, 0, yaw + PI / 2), bottom=True)
    prims = []
    offs = (-1, 1) if heads > 1 else (0,)
    for s in offs:
        hx = x + s * 0.38 * math.cos(yaw + PI / 2); hy = y + s * 0.38 * math.sin(yaw + PI / 2)
        P.box("metal", (hx, hy, zt), (0.38, 0.3, 0.3), (0, math.radians(30), yaw), bottom=True)
        prims.append(("box", (hx + 0.2 * math.cos(yaw), hy + 0.2 * math.sin(yaw), zt - 0.1), (0.05, 0.26, 0.26), (0, math.radians(30), yaw)))
    kit.light(name, prims)


# ====================================================================== previews
PREVIEW_TINT = {"Light_Status": (0.15, 1.0, 0.25, 1.6), "Light_Beacon": (1.0, 0.08, 0.04, 2.0),
                "Light_Flood": (1.0, 0.9, 0.7, 1.6), "Light_Runway": (1.0, 0.8, 0.3, 1.8)}


def previews(glb, outdir, prefix, shots, only=None, concept=None, res=(640, 400), samples=24, ground_rgb=(0.11, 0.10, 0.075)):
    """Render shots of the *exported* GLB. shots: list of dicts(name, az, el, dist, lens=50, ortho=None, target).
    Preview-only: light objects are tinted by group (status green, beacon red, flood warm, runway amber)."""
    os.makedirs(outdir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=glb)
    for o in scene.objects:
        if o.type == "MESH" and o.name.startswith("Light_"):
            for key, (r, g, b, s) in PREVIEW_TINT.items():
                if o.name.startswith(key):
                    m = o.active_material.copy(); o.active_material = m
                    bs = m.node_tree.nodes.get("Principled BSDF")
                    if bs:
                        bs.inputs["Emission Color"].default_value = (r, g, b, 1)
                        bs.inputs["Base Color"].default_value = (r, g, b, 1)
                        bs.inputs["Emission Strength"].default_value = s
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = samples
    scene.cycles.use_denoising = True; scene.cycles.max_bounces = 3
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.32, 0.33, 0.36, 1); bg.inputs["Strength"].default_value = 0.6
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.2; sun.angle = math.radians(3)
    so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
    so.rotation_euler = Euler((math.radians(42), 0, math.radians(-38)))
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*ground_rgb, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.002)); bpy.context.active_object.data.materials.append(gm)
    cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam
    cam_d.clip_end = 2000
    done = []
    for s in shots:
        name = s["name"]
        path = os.path.join(outdir, f"{prefix}_{name}.png")
        if only and name not in only.split(","):
            continue
        tgt = V(s.get("target", (0, 0, 2))); az, el = math.radians(s["az"]), math.radians(s["el"])
        d = V((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        cam.location = tgt + d * s["dist"]
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if s.get("ortho"):
            cam_d.type = "ORTHO"; cam_d.ortho_scale = s["ortho"]
        else:
            cam_d.type = "PERSP"; cam_d.lens = s.get("lens", 50)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done.append(path)
        print("rendered", path)
    if concept and (not only or "rts" in only.split(",")):
        a = Image.open(os.path.join(outdir, f"{prefix}_rts.png")).convert("RGB")
        b = Image.open(concept).convert("RGB")
        b = b.resize((int(b.width * a.height / b.height), a.height), Image.LANCZOS)
        sbs = Image.new("RGB", (a.width + b.width + 12, a.height), (20, 20, 20))
        sbs.paste(a, (0, 0)); sbs.paste(b, (a.width + 12, 0))
        sbs.save(os.path.join(outdir, f"{prefix}_vs_concept.png"))
        print("wrote side-by-side")
    return done


def std_shots(span, h, top_ortho=None, tz=None, dmul=1.0):
    """Default camera set scaled to a structure of footprint `span` metres and height `h`."""
    d = (span * 1.55 + h) * dmul
    tz = h * 0.35 if tz is None else tz
    return [dict(name="rts", az=-38, el=52, dist=d, target=(0, 0, tz)),
            dict(name="front", az=0, el=20, dist=d, target=(0, 0, tz)),
            dict(name="side", az=-90, el=14, dist=d, target=(0, 0, tz)),
            dict(name="top", az=0, el=89.9, dist=d + 40, ortho=top_ortho or span * 1.15, target=(0, 0, 0))]
