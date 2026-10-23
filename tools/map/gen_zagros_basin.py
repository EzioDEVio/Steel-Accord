"""Steel Accord - map generator for "Zagros Basin" (fictional sector, synthetic terrain).

Run:   python3 -I tools/map/gen_zagros_basin.py [--out godot/maps/zagros_basin] [--screens docs/screens]
                [--dem <file.tif|.tiff|.hgt|.png> [--dem-weight 1.0] [--dem-crop fx0,fz0,fx1,fz1] [--dem-relief 62]]
                [--no-plots]

Writes (all deterministic, fixed seeds):
  <out>/height.r16          601 x 601 little-endian uint16, row 0 = z -600, column 0 = x -600, 2 m spacing;
                            metres = value / 65535 * map.json height_scale
  <out>/height_preview.png  8-bit greyscale (humans only)
  <out>/splat.png           RGBA8 601 x 601: R rock, G gravel/scree, B scrub, A dry riverbed; sand = 1 - sum
  <out>/splat.png.import    Godot import settings (lossless, no mipmaps, NO fix_alpha_border - see doc)
  <out>/map.json            layout + gameplay data (schema in docs/MAP_ZAGROS_BASIN.md)
  <out>/fairness_report.json / fairness_report.txt   path distances + route connectivity checks
  <screens>/map_zagros_{overview,height,splat,routes}.png   top-down plots
  <scratch>/zagros_albedo.png (via --albedo <path>)   colour map for the Blender RTS render

The terrain is SYNTHETIC: no elevation data was available when this was authored. It imitates the broad Zagros
fold-belt character (NW-SE anticline ridges with layered limestone benches, a dry alluvial basin, fans and wadis).
--dem replaces the broad procedural shape (basin + ridge profile) with a resampled real DEM; all gameplay carving
(passes, trails, start/build flattening, roads) and the 180-degree symmetrisation are still applied afterwards, and
the route/fairness checks report whether the authored layout still works on that DEM.

Coordinates: map/Godot world x (east) and z (south), metres, -600..+600. Start A (team 0) south, start B (team 1)
north; everything gameplay-relevant is point-symmetric about the origin: (x, z) -> (-x, -z).
"""
import argparse, json, math, os, sys
from math import pi as PI
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from PIL import Image

# ====================================================================== constants
N = 601
STEP = 2.0
HALF = 600.0
HEIGHT_SCALE = 80.0
TH = math.radians(35.0)                       # ridge axes rotated 35 deg from +X (x east, z south => NW-SE)
UX, UZ = math.cos(TH), math.sin(TH)           # along-strike unit vector u
NX, NZ = -math.sin(TH), math.cos(TH)          # across-strike unit vector n (points from basin towards start A)
START_A = (0.0, 470.0)
START_B = (-START_A[0], -START_A[1])
START_R = 100.0                               # flat radius around each start (=> ~200 m across)
START_SKIRT = 45.0

MOVEMENT = {
    "infantry": {"max_slope_deg": 38.0,
                 "cost": {"sand": 1.0, "gravel": 1.1, "rock": 1.6, "riverbed": 1.2, "scrub": 1.1, "road": 0.9}},
    "wheeled": {"max_slope_deg": 18.0,
                "cost": {"sand": 1.35, "gravel": 1.2, "rock": 4.0, "riverbed": 1.5, "scrub": 1.4, "road": 0.55}},
    "tracked": {"max_slope_deg": 28.0,
                "cost": {"sand": 1.1, "gravel": 1.0, "rock": 2.2, "riverbed": 1.25, "scrub": 1.1, "road": 0.8}},
}
BUILDING_MAX_SLOPE = 8.0
# Limestone bench shaping of the anticline flanks (build/terrace) and the down-dip gullies. Tuned so the benches span
# several 2 m grid cells: the old 6.5/7 m steps with 38 % hard-edged risers and 9/16 m gully noise crossed into a
# regular field of triangular facets on the 2 m grid (docs/TERRAIN_TILING.md). Risers stay > 38 deg so the ridges
# still block every class except at the passes and the infantry goat trail (checked by verify()).
TERRACE_STEP = (12.0, 13.0)        # step height per bench, inner / outer ridge (m)
TERRACE_RISER = 0.55               # riser share of each step (smootherstep profile, rounded edges)
TERRACE_MIX = 0.6                  # share of the terraced profile vs the smooth ridge profile
GULLY_LAM = (16.0, 26.0)           # along-strike feature size of the two gully noise layers (m)

xs = -HALF + STEP * np.arange(N)
X, Z = np.meshgrid(xs, xs)                    # X[row=z index, col=x index]
T = X * UX + Z * UZ                           # along-strike coordinate
S = X * NX + Z * NZ                           # across-strike coordinate (A side > 0)
A_ = np.abs(S)                                # distance from the basin axis
TP = T * np.sign(S + 1e-9)                    # along-strike coordinate in the local side's frame (B = A rotated)


# Garrisonable civilian buildings (B2): a contested hospital in the middle of the basin, and a civic centre and an
# apartment block by each village, plus a mirrored pair of apartment blocks in the basin. Point-symmetric pairs.
# (Village houses listed under "props" are also turned into garrisonable houses by the game.)
CIVIC = [
    {"type": "civ_hospital", "pos": [0.0, 0.0]},
    {"type": "civ_center", "pos": [-195.0, 330.0]}, {"type": "civ_center", "pos": [195.0, -330.0]},
    {"type": "civ_apartment", "pos": [-285.0, 280.0]}, {"type": "civ_apartment", "pos": [285.0, -280.0]},
    {"type": "civ_apartment", "pos": [110.0, 120.0]}, {"type": "civ_apartment", "pos": [-110.0, -120.0]},
]


def w2tp(x, z):
    return x * UX + z * UZ, x * NX + z * NZ


def tp2w(t, s):
    return t * UX + s * NX, t * UZ + s * NZ


def mirror(p):
    return (-p[0], -p[1])


def mirror_poly(pts):
    return [(-x, -z) for x, z in pts]


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def symmetrize(a):
    """Exact 180-degree rotational symmetry on the grid: sample (i, j) <-> (N-1-i, N-1-j)."""
    return 0.5 * (a + a[::-1, ::-1])


# ====================================================================== noise
def aniso_noise(seed, lam_t, lam_s, pad=1024):
    """Gaussian-filtered white noise, unit std; feature sizes lam_t along strike and lam_s across (metres)."""
    w = np.random.default_rng(seed).standard_normal((pad, pad))
    f = np.fft.fftfreq(pad, d=STEP)
    fx = f[None, :]; fz = f[:, None]
    ft = fx * UX + fz * UZ; fs = fx * NX + fz * NZ
    r = np.real(np.fft.ifft2(np.fft.fft2(w) * np.exp(-((ft * lam_t) ** 2 + (fs * lam_s) ** 2) * 2.0)))
    r = r[:N, :N]
    return r / (r.std() + 1e-12)


# ====================================================================== polylines
def catmull(pts, spacing=6.0):
    """Centripetal-ish Catmull-Rom through control points, resampled to ~`spacing` metres."""
    P = np.asarray(pts, float)
    if len(P) < 3:
        dense = P
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
        out = []
        for i in range(1, len(Q) - 2):
            p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
            seg = np.linalg.norm(p2 - p1)
            n = max(2, int(seg / 1.0))
            for k in range(n):
                t = k / n
                t2, t3 = t * t, t * t * t
                out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        out.append(P[-1])
        dense = np.asarray(out)
    return resample(dense, spacing)


def resample(P, spacing):
    P = np.asarray(P, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    n = max(2, int(round(d[-1] / spacing)) + 1)
    s = np.linspace(0, d[-1], n)
    return np.c_[np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])]


def arclen(P):
    return np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.asarray(P), axis=0), axis=1))]


def poly_dist(P, pad):
    """Distance from every grid sample to polyline P (within `pad` m), and arc-length parameter of the nearest point."""
    P = np.asarray(P, float)
    L = arclen(P)
    dist = np.full((N, N), np.inf); par = np.zeros((N, N))
    for k in range(len(P) - 1):
        a, b = P[k], P[k + 1]
        x0, x1 = min(a[0], b[0]) - pad, max(a[0], b[0]) + pad
        z0, z1 = min(a[1], b[1]) - pad, max(a[1], b[1]) + pad
        j0 = max(0, int((x0 + HALF) / STEP)); j1 = min(N, int((x1 + HALF) / STEP) + 2)
        i0 = max(0, int((z0 + HALF) / STEP)); i1 = min(N, int((z1 + HALF) / STEP) + 2)
        if j1 <= j0 or i1 <= i0:
            continue
        px = X[i0:i1, j0:j1]; pz = Z[i0:i1, j0:j1]
        d = b - a; ll = max(1e-9, d @ d)
        t = np.clip(((px - a[0]) * d[0] + (pz - a[1]) * d[1]) / ll, 0, 1)
        dd = np.hypot(px - a[0] - t * d[0], pz - a[1] - t * d[1])
        sub = dist[i0:i1, j0:j1]
        m = dd < sub
        sub[m] = dd[m]
        par[i0:i1, j0:j1][m] = (L[k] + t * math.sqrt(ll))[m]
    return dist, par


def sample_h(h, P):
    """Bilinear height at world points P (n x 2)."""
    P = np.asarray(P, float)
    fx = (P[:, 0] + HALF) / STEP; fz = (P[:, 1] + HALF) / STEP
    return ndi.map_coordinates(h, [fz, fx], order=1, mode="nearest")


def corridor(h, P, prof_s, prof_h, half_w, wall_cut, wall_fill, pad):
    """Force the terrain to follow profile prof_h(arc length) on a floor of half width half_w along polyline P, with
    cut walls of slope wall_cut and fill embankments of slope wall_fill (rise/run) beyond the floor."""
    d, s = poly_dist(P, pad)
    m = d < pad
    p = np.interp(s[m], prof_s, prof_h)
    e = np.maximum(0.0, d[m] - half_w)
    hm = h[m]
    hm = np.minimum(hm, p + wall_cut * e)
    hm = np.maximum(hm, p - wall_fill * e)
    h[m] = hm
    return d


# ====================================================================== DEM input (optional)
def load_dem(path, crop=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".hgt":
        raw = np.fromfile(path, ">i2")
        n = int(round(math.sqrt(raw.size)))
        a = raw.reshape(n, n).astype(np.float64)
        a[a < -1000] = np.nan                                    # SRTM voids
    elif ext in (".tif", ".tiff"):
        try:
            import tifffile
            a = tifffile.imread(path).astype(np.float64)
        except Exception:
            a = np.asarray(Image.open(path), np.float64)
        if a.ndim == 3:
            a = a[..., 0]
    else:                                                        # 16-bit (or 8-bit) greyscale PNG
        a = np.asarray(Image.open(path), np.float64)
        if a.ndim == 3:
            a = a[..., 0]
    if np.isnan(a).any():                                        # fill voids with nearest valid value
        idx = ndi.distance_transform_edt(np.isnan(a), return_distances=False, return_indices=True)
        a = a[tuple(idx)]
    if crop:
        fx0, fz0, fx1, fz1 = crop
        H, W = a.shape
        a = a[int(fz0 * H):int(fz1 * H), int(fx0 * W):int(fx1 * W)]
    # north-up raster: row 0 = north = z -600, which is already our row order
    rr = np.linspace(0, a.shape[0] - 1, N); cc = np.linspace(0, a.shape[1] - 1, N)
    return ndi.map_coordinates(a, np.meshgrid(rr, cc, indexing="ij"), order=1, mode="nearest")


# ====================================================================== layout (A side; B side by mirror)
def ridge_center(tp):
    return 212.0 + 10.0 * np.sin(tp / 160.0 + 0.7)


def pass_axis(t_p, skew, a0=96.0, a1=332.0, n=24):
    """Polyline across the inner ridge (A side), from the basin end (a0) to the valley end (a1)."""
    ar = float(ridge_center(t_p))
    a = np.linspace(a0, a1, n)
    t = t_p + skew * (a - ar)
    x, z = tp2w(t, a)
    return np.c_[x, z], a, ar


# passes: (name, t at the ridge axis, skew dt/da of the pass axis, half gap between the anticline noses, nose length)
PASSES_A = [("west", -212.0, 0.30, 22.0, 75.0),
            ("central", 147.0, 0.70, 30.0, 80.0),
            ("east", 522.0, -0.50, 22.0, 75.0)]
PASS_FLOOR = {"west": (20.0, 5.0), "central": (26.0, 2.0), "east": (20.0, 4.0)}   # road floor half width, saddle rise
HILL_A = (-75.0, 88.0)                        # (tp, a) of the basin whaleback hill


def ECHELON(tp):
    """En-echelon offset: alternate anticline segments sit slightly basin-ward / valley-ward."""
    return ((tp > -212.0) & (tp < 147.0)) | (tp > 522.0)
GOAT_A = ("goat_trail", -30.0, 1.25)          # infantry-only diagonal trail over the inner ridge


def floor_fn(a):
    """Valley/basin floor height as a function of distance from the basin axis (before ridges)."""
    return np.interp(a, [0, 60, 130, 200, 285, 340, 470, 515, 700, 900],
                     [2.0, 2.4, 4.6, 8.0, 11.5, 12.6, 14.0, 18.0, 26.0, 30.0])


# ====================================================================== build
def build(args):
    rng = np.random.default_rng(20261022)
    # ------------------------------------------------------------ broad shape
    def sym_noise(seed, lt, ls):
        n = symmetrize(aniso_noise(seed, lt, ls))
        return n / (n.std() + 1e-12)
    n_axis = sym_noise(1, 150.0, 900.0)                          # slow wander of the ridge axes
    n_h = sym_noise(2, 120.0, 400.0)
    ar = ridge_center(TP) + 7.0 * n_axis + np.where(ECHELON(TP), 9.0, -9.0)
    H1 = 56.0 + 6.0 * np.sin(TP / 230.0 + 1.1) + 4.0 * n_h
    d1 = np.where(A_ < ar, (ar - A_) / 60.0, (A_ - ar) / 74.0)
    p1 = np.clip(1 - d1 ** 2, 0, None) ** 1.25
    nose = np.ones((N, N))
    for name, tpp, skew, ghw, ln in PASSES_A:                     # anticline noses plunge into each pass gap
        axis_t = tpp + skew * (A_ - ar)
        x = np.abs(TP - axis_t) - ghw - 70.0 * np.clip(d1, 0, 1) ** 2      # gap widens towards the flanks
        u = np.clip(x / ln, 0, 1)
        nose *= np.sqrt(u * (2 - u))
    r1 = H1 * p1 * nose
    ao = 612.0 + 10.0 * np.sin(TP / 140.0) + 8.0 * n_axis
    H2 = 60.0 + 7.0 * np.sin(TP / 190.0 + 2.0) + 4.0 * n_h
    d2 = np.abs(A_ - ao) / 98.0
    r2 = H2 * np.clip(1 - d2 ** 2, 0, None) ** 1.25
    # low whaleback hill in the basin (A side), crowned by the old compound ruins
    ht, ha = HILL_A
    q = np.sqrt(((TP - ht) / 85.0) ** 2 + ((A_ - ha) / 46.0) ** 2)
    r3 = 10.0 * np.clip(1 - q ** 2, 0, None) ** 2.0

    def terrace(r, step, riser=TERRACE_RISER, mix=TERRACE_MIX, jitter=None):
        # Limestone benches: a gently sloping tread, then a riser over the last `riser` fraction of each step with a
        # smootherstep profile (zero slope AND curvature where it meets the treads), so bench edges are rounded and each
        # riser spans several 2 m grid cells. Narrow hard-edged risers (the old 6.5-7 m steps, riser = 38 % of a step)
        # aliased into a regular field of triangular facets on the 2 m grid. See docs/TERRAIN_TILING.md.
        rr = r if jitter is None else r + jitter
        k = rr / step; f = np.floor(k); fr = k - f
        u = np.clip((fr - (1.0 - riser)) / riser, 0.0, 1.0)
        tr = (f + u * u * u * (u * (u * 6.0 - 15.0) + 10.0)) * step
        return np.maximum(0, r * (1 - mix) + (tr - (0 if jitter is None else jitter)) * mix)

    jit = 2.2 * sym_noise(3, 40.0, 40.0) * smoothstep(3, 15, r1 + r2)
    gmod = smoothstep(-0.8, 1.2, sym_noise(4, 60.0, 60.0))
    gul = np.clip(sym_noise(11, GULLY_LAM[0], 50.0), 0, None) * (0.4 + 0.6 * gmod)   # gullies run down-dip (across strike)
    gul2 = np.clip(sym_noise(12, GULLY_LAM[1], 90.0), 0, None)
    ridges = terrace(r1, TERRACE_STEP[0], jitter=jit) + terrace(r2, TERRACE_STEP[1], jitter=jit) + r3
    ridges -= (r1 + r2) * (0.07 * gul + 0.05 * gul2) * smoothstep(4, 20, r1 + r2)
    base = floor_fn(A_) + 1.2 * sym_noise(13, 160.0, 160.0) + 0.5 * sym_noise(14, 45.0, 60.0)

    if args.dem:
        dem = load_dem(args.dem, args.dem_crop)
        lo, hi = np.percentile(dem, 2), np.percentile(dem, 99.5)
        demn = np.clip((dem - lo) / max(1e-6, hi - lo), 0, 1.2) * args.dem_relief + 2.0
        w = float(args.dem_weight)
        h = (base + ridges) * (1 - w) + demn * w
        print(f"DEM {args.dem}: range {lo:.1f}..{hi:.1f} m -> 2..{2 + args.dem_relief:.0f} game m, weight {w}")
    else:
        h = base + ridges
    h = symmetrize(h)

    # ------------------------------------------------------------ alluvial fans (A side + mirror)
    fans = []
    pass_polys = {}
    for name, tpp, skew, _, _ in PASSES_A:
        hw, rise = PASS_FLOOR[name]
        P, a, arp = pass_axis(tpp, skew)
        pass_polys[name] = (P, a, arp, hw, rise)
        fans.append((P[0], 115.0, 3.2))                          # basin mouth
        fans.append((P[-1], 70.0, 1.6))                          # valley mouth
    for tpp in (-400.0, -110.0, 330.0, 700.0):                   # gully fans along the inner ridge foot
        fx, fz = tp2w(tpp, 128.0)
        fans.append(((fx, fz), 80.0, 2.0))
    fan_mask = np.zeros((N, N))
    for (cx, cz), R, H in fans:
        for (px, pz) in ((cx, cz), mirror((cx, cz))):
            r = np.hypot(X - px, Z - pz)
            f = np.clip(1 - r / R, 0, None) ** 1.6
            h += H * f
            fan_mask = np.maximum(fan_mask, f)

    # ------------------------------------------------------------ wadis
    tt = np.arange(-1000.0, 1000.1, 8.0)
    sw = 18.0 * np.sin(tt / 97.0) + 8.0 * np.sin(tt / 43.0)        # odd in t => point-symmetric trunk
    trunk = np.stack(tp2w(tt, sw), 1)
    tribs_A = []
    for name in ("west", "central", "east"):
        P = pass_polys[name][0]
        st = P[2]
        tw, sw0 = w2tp(*st)
        ctrl = [tuple(st)] + [tp2w(tw - 20 * k * (1 if name != "east" else -1) + 6 * math.sin(k), sw0 - 28 * k) for k in range(1, 5)]
        ctrl = [c for c in ctrl if w2tp(*c)[1] > 8] + [tp2w(w2tp(*ctrl[-1])[0] - 12, 0.0)]
        tribs_A.append(catmull(ctrl, 8.0))
    for tpp in (-400.0, -110.0, 330.0):
        ctrl = [tp2w(tpp + 8 * k * math.sin(k * 1.3), 150.0 - 30 * k) for k in range(6)]
        tribs_A.append(catmull(ctrl, 8.0))
    wadis = [(trunk, 11.0, 2.3)] + [(P, 6.0, 1.4) for P in tribs_A] + [(np.asarray(mirror_poly(P)), 6.0, 1.4) for P in tribs_A]
    river = np.zeros((N, N))
    for P, hw, depth in wadis:
        d, _ = poly_dist(P, hw + 14.0)
        bed = 1 - smoothstep(hw * 0.55, hw + 9.0, d)             # 0..1 channel shape (wide gentle banks)
        h -= depth * bed
        river = np.maximum(river, 1 - smoothstep(hw * 0.5, hw * 1.05, d))

    # ------------------------------------------------------------ passes (cut/fill a floored notch through the ridge)
    pass_all = {}
    for name, (P, a, arp, hw, rise) in pass_polys.items():
        prof = floor_fn(a) + rise * np.exp(-((a - arp) / 55.0) ** 2) + 0.6
        prof[0] = sample_h(h, P[:1])[0]; prof[-1] = sample_h(h, P[-1:])[0]
        prof = ndi.gaussian_filter1d(prof, 2.0, mode="nearest")
        s = arclen(P)
        for PP in (P, np.asarray(mirror_poly(P))):
            corridor(h, PP, s, prof, hw, 1.1, 0.3, hw + 40.0)
        pass_all[name] = P
    # goat trail (infantry only): diagonal ramp at ~31 deg, narrow floor, steep walls
    gname, gt, gskew = GOAT_A
    arg = float(ridge_center(gt))
    ga = np.linspace(arg - 92, arg + 100, 60)
    gP = np.stack(tp2w(gt + gskew * (ga - arg), ga), 1)
    gs = arclen(gP)
    crest_s = np.interp(arg, ga, gs)
    gh0 = sample_h(h, gP)
    top = float(gh0.max()) - 9.0
    grade = math.tan(math.radians(31.5))
    ends = np.interp(gs, [gs[0], gs[-1]], [gh0[0], gh0[-1]])
    gprof = np.maximum(top - grade * np.abs(gs - crest_s), ends)
    for PP in (gP, np.asarray(mirror_poly(gP))):
        corridor(h, PP, gs, gprof, 4.5, 2.4, 2.4, 40.0)

    # ------------------------------------------------------------ flattening: starts, pads, sites
    flat_info = {}
    flat_ops = []                                                # replayed after the roads with the same targets

    def op_disc(c, R, skirt, key, tgt=None):
        for k, p in enumerate((c, mirror(c))):
            r = np.hypot(X - p[0], Z - p[1])
            t = float(np.median(h[r < R])) if tgt is None else tgt[k]
            w = 1 - smoothstep(R, R + skirt, r)
            h[:] = h * (1 - w) + t * w
            flat_info[f"{key}{'' if k == 0 else '_mirror'}"] = round(t, 2)
            if tgt is None:
                flat_ops.append((op_disc, (p, R, skirt, key, None), t))

    def op_rect(c, size, skirt, key, tgt=None, margin=5.0):
        for k, p in enumerate((c, mirror(c))):
            dd = np.hypot(np.maximum(0, np.abs(X - p[0]) - size[0] / 2 - margin),
                          np.maximum(0, np.abs(Z - p[1]) - size[1] / 2 - margin))
            t = float(np.median(h[dd <= 0])) if tgt is None else tgt[k]
            w = 1 - smoothstep(0, skirt, dd)
            h[:] = h * (1 - w) + t * w
            flat_info[f"{key}{'' if k == 0 else '_mirror'}"] = round(t, 2)

    def flatten_all(targets=None):
        ops = [("disc", START_A, (START_R + 4.0, START_SKIRT), "start")]
        ops += [("rect", c, (sz, 18.0), f"pad{i}") for i, (c, sz) in enumerate(BUILD_PADS_A)]
        ops += [("disc", c, (16.0, 12.0), f"pile{i}") for i, c in enumerate([c for c, _ in PILES_A] + PILES_C_HALF + [(0.0, 0.0)])]
        ops += [("disc", c, (15.0, 12.0), f"derrick{i}") for i, c in enumerate(DERRICKS_A + DERRICKS_C_HALF)]
        ops += [("disc", VILLAGE_A, (46.0, 22.0), "village")]
        for kind, c, prm, key in ops:
            tg = None if targets is None else (targets[key], targets[key + "_mirror"])
            if kind == "disc":
                op_disc(c, prm[0], prm[1], key, tg)
            else:
                op_rect(c, prm[0], prm[1], key, tg)
        return dict(flat_info)

    targets = flatten_all()
    h = symmetrize(h)

    # ------------------------------------------------------------ roads: smoothed, grade-limited profile + shoulders
    roads = road_polylines(pass_all, gP)
    for rd in roads:
        P = rd["P"]
        s = arclen(P)
        prof = sample_h(h, P)
        prof = ndi.gaussian_filter1d(prof, 4.0, mode="nearest")
        g = math.tan(math.radians(9.0))
        for _ in range(3):                                       # grade limit, both directions
            for i in range(1, len(prof)):
                prof[i] = np.clip(prof[i], prof[i - 1] - g * (s[i] - s[i - 1]), prof[i - 1] + g * (s[i] - s[i - 1]))
            for i in range(len(prof) - 2, -1, -1):
                prof[i] = np.clip(prof[i], prof[i + 1] - g * (s[i + 1] - s[i]), prof[i + 1] + g * (s[i + 1] - s[i]))
        corridor(h, P, s, prof, rd["width"] * 0.5 + 1.5, 0.45, 0.35, rd["width"] * 0.5 + 30.0)
    flatten_all(targets)                                         # roads must not disturb starts / pads / sites
    h = symmetrize(h)

    # ------------------------------------------------------------ asymmetric cosmetic detail on cliffs only
    sl = slope_deg(h)
    cliff = smoothstep(44.0, 55.0, ndi.gaussian_filter(sl, 1.0))
    h += 0.7 * cliff * aniso_noise(99, 10.0, 10.0)
    h = np.clip(h, 0.05, HEIGHT_SCALE - 0.05)
    return dict(h=h, river=river, fan=fan_mask, passes=pass_all, goat=gP, roads=roads, flat=flat_info,
                wadis=wadis, ridge_r=r1 + r2)


# ====================================================================== sites (A side; mirrored to B)
#  coordinates picked from the layout plots; see docs/MAP_ZAGROS_BASIN.md
BUILD_PADS_A = [((-170.0, 395.0), (64.0, 52.0)),            # west valley pad (towards the far pass)
                ((158.0, 540.0), (56.0, 44.0)),             # east pad (towards the near pass)
                ((-60.0, 330.0), (52.0, 44.0)),             # forward pad below the central pass mouth
                ((-218.0, -45.0), (60.0, 50.0)),            # contested: basin, west of centre (B mirror east)
                ((160.0, 150.0), (52.0, 48.0))]             # contested: basin mouth of A's central pass
PILES_A = [((-95.0, 430.0), 20000), ((90.0, 400.0), 20000)]
PILES_C_HALF = [(-330.0, -215.0)]                           # + mirror; plus the centre pile (0, 0)
DERRICKS_A = [(108.0, 468.0)]
DERRICKS_C_HALF = [(-470.0, -330.0)]
VILLAGE_A = (-235.0, 300.0)


def road_polylines(pass_all, goat):
    """Road centre lines (world). Main roads connect both starts via the three routes; each is symmetric as a set."""
    PW, PC, PE = pass_all["west"], pass_all["central"], pass_all["east"]
    # central road: A -> central pass -> centre -> mirror
    half = [START_A, (6.0, 405.0)] + [tuple(p) for p in PC[::-1][2:-2:3]] + [(22.0, 120.0), (14.0, 60.0), (0.0, 0.0)]
    central = half + mirror_poly(half[::-1])[1:]
    # west road: A -> west along the valley -> west pass -> basin -> B's west pass (= mirror of A's east pass) -> B
    pe_b = np.asarray(mirror_poly(PE))
    west = ([START_A, (-70.0, 445.0), (-150.0, 400.0), VILLAGE_A, (-290.0, 245.0)] + [tuple(p) for p in PW[::-1][1:-1:3]] +
            [(-290.0, -110.0), (-350.0, -260.0)] + [tuple(p) for p in pe_b[1::3]] + [(-95.0, -492.0), START_B])
    east = mirror_poly(west)
    # basin road along strike (odd lateral offset => symmetric), reaching both contested derricks
    tt = np.arange(-760.0, 760.1, 40.0)
    ss = 34.0 * np.sin(tt / 150.0)
    basin = [tp2w(t, s) for t, s in zip(tt, ss)]
    basin = [(x, z) for x, z in basin if abs(x) <= 596 and abs(z) <= 596]
    out = []
    for name, pts, w in (("central", central, 9.0), ("west", west, 7.0), ("east", east, 7.0), ("basin", basin, 6.0)):
        out.append(dict(name=name, P=catmull(pts, 6.0), width=w))
    return out


# ====================================================================== analysis helpers
def slope_deg(h):
    """Slope exactly as terrain_map.gd computes it: normal from central differences over +-1 sample (clamped edges)."""
    hp = np.pad(h, 1, mode="edge")
    hx = hp[1:-1, 2:] - hp[1:-1, :-2]
    hz = hp[2:, 1:-1] - hp[:-2, 1:-1]
    return np.degrees(np.arctan(np.hypot(hx, hz) / (2 * STEP)))


def road_mask(roads):
    """Same falloff as terrain_map.gd _bake_roads (full inside 0.35 w, zero beyond 0.6 w)."""
    m = np.zeros((N, N))
    for rd in roads:
        P = np.asarray(rd["points"], float); w = rd["width_m"]
        d, _ = poly_dist(P, w)
        m = np.maximum(m, np.clip(1 - (d - w * 0.35) / (w * 0.25), 0, 1))
    return m


def grid_index(p):
    return int(round((p[1] + HALF) / STEP)), int(round((p[0] + HALF) / STEP))


def build_graph(passable, cost):
    """8-connected graph; edge weight = length * mean cell cost; both cells must be passable."""
    idx = np.arange(N * N).reshape(N, N)
    rows, cols, wts = [], [], []
    for di, dj in ((0, 1), (1, 0), (1, 1), (1, -1)):
        L = STEP * math.hypot(di, dj)
        a = (slice(0, N - di), slice(max(0, -dj), N - max(0, dj)))
        b = (slice(di, N), slice(max(0, dj), N + min(0, dj)))
        ok = passable[a] & passable[b]
        if di == 1 and dj != 0:                                  # no corner cutting through blocked cells
            ok &= passable[(slice(0, N - 1), b[1])] & passable[(slice(1, N), a[1])]
        ia = idx[a][ok]; ib = idx[b][ok]
        w = L * 0.5 * (cost[a][ok] + cost[b][ok])
        rows += [ia, ib]; cols += [ib, ia]; wts += [w, w]
    return csr_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(N * N, N * N))


def trace(pred, src, dst):
    path = []
    k = dst
    while k >= 0 and k != src:
        path.append(k); k = pred[k]
    if k != src:
        return None
    path.append(src)
    path = np.array(path[::-1])
    return np.c_[xs[path % N], xs[path // N]]


# ====================================================================== main
def main():
    ap = argparse.ArgumentParser()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ap.add_argument("--out", default=os.path.join(root, "godot", "maps", "zagros_basin"))
    ap.add_argument("--screens", default=os.path.join(root, "docs", "screens"))
    ap.add_argument("--albedo", default=None, help="also write a colour map PNG for the Blender RTS render")
    ap.add_argument("--dem", default=None)
    ap.add_argument("--dem-weight", type=float, default=1.0)
    ap.add_argument("--dem-relief", type=float, default=62.0)
    ap.add_argument("--dem-crop", type=lambda s: [float(v) for v in s.split(",")], default=None)
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    R = build(args)
    h = R["h"]
    sl = slope_deg(h)

    # ------------------------------------------------------------ splat
    river = R["river"]; fan = R["fan"]
    curv = ndi.laplace(ndi.gaussian_filter(h, 2.0))
    bench = smoothstep(10.0, 28.0, R["ridge_r"]) * (0.45 + 0.35 * smoothstep(-0.5, 1.0, aniso_noise(23, 12.0, 12.0)))
    rock = np.clip(smoothstep(27.0, 42.0, sl) + 0.5 * smoothstep(0.15, 0.6, -curv) * smoothstep(14, 26, sl) + bench, 0, 1)
    talus = np.clip(ndi.gaussian_filter(rock, 5.0) * 1.6 - rock, 0, 1)
    gravel = np.clip(0.75 * smoothstep(9.0, 24.0, sl) + 0.7 * talus + 0.55 * fan + 0.5 * (smoothstep(0.0, 1.0, ndi.gaussian_filter(river, 3.0)) - river), 0, 1)
    gravel *= (1 - rock)
    moist = np.clip(ndi.gaussian_filter(river, 9.0) * 3.0, 0, 1)
    # north-facing (towards -z) slopes hold a little more scrub
    hz = np.gradient(h, axis=0)
    north = smoothstep(0.02, 0.4, hz)                            # h rising towards +z => slope faces -z (north)
    patch = smoothstep(0.1, 1.2, aniso_noise(21, 22.0, 22.0)) * 0.8 + smoothstep(0.6, 1.8, aniso_noise(22, 6.0, 6.0)) * 0.4
    scrub = np.clip((0.25 + 0.6 * moist + 0.25 * north) * patch, 0, 0.85) * (1 - smoothstep(18, 32, sl))
    bed = np.clip(river, 0, 1)
    # flattened sites read as compacted gravel, no scrub
    sites = np.zeros((N, N))
    for c in [START_A, START_B]:
        sites = np.maximum(sites, 1 - smoothstep(START_R - 10, START_R + 10, np.hypot(X - c[0], Z - c[1])))
    scrub *= (1 - 0.85 * sites)
    gravel = np.maximum(gravel, 0.35 * sites)
    bed *= (1 - 0.7 * sites)
    W = np.stack([rock, gravel * (1 - rock), scrub * (1 - rock), bed * (1 - rock)], -1)
    tot = W.sum(-1, keepdims=True)
    W = np.where(tot > 1, W / tot, W)
    W = np.stack([symmetrize(W[..., c]) for c in range(4)], -1)   # symmetric movement costs (per channel!)
    W8 = (np.clip(W, 0, 1) * 255 + 0.5).astype(np.uint8)
    Wq = W8.astype(np.float64) / 255.0

    # ------------------------------------------------------------ write heightfield
    q = np.clip(np.round(h / HEIGHT_SCALE * 65535), 0, 65535).astype("<u2")
    q.tofile(os.path.join(args.out, "height.r16"))
    hq = q.astype(np.float64) / 65535 * HEIGHT_SCALE
    slq = slope_deg(hq)
    Image.fromarray((hq / hq.max() * 255).astype(np.uint8)).save(os.path.join(args.out, "height_preview.png"))
    Image.fromarray(W8, "RGBA").save(os.path.join(args.out, "splat.png"))
    write_import(os.path.join(args.out, "splat.png.import"))

    # ------------------------------------------------------------ gameplay data
    def r1(v):
        return round(float(v), 1)

    starts = [dict(team=0, pos=[r1(START_A[0]), r1(START_A[1])], facing_deg=0.0),
              dict(team=1, pos=[r1(START_B[0]), r1(START_B[1])], facing_deg=180.0)]
    pads = []
    for c, sz in BUILD_PADS_A:
        for k, p in enumerate((c, mirror(c))):
            pads.append(dict(center=[r1(p[0]), r1(p[1])], size=[r1(sz[0]), r1(sz[1])],
                             owner_hint=(0 if k == 0 else 1) if math.hypot(*np.subtract(c, START_A)) < 300 else -1))
    piles = []
    for c, cash in PILES_A:
        for k, p in enumerate((c, mirror(c))):
            piles.append(dict(id=f"pile_{'a' if k == 0 else 'b'}{len([q for q in piles if q['id'].startswith('pile_' + ('a' if k == 0 else 'b'))])}",
                              pos=[r1(p[0]), r1(p[1])], cash=cash, contested=False))
    piles.append(dict(id="pile_c0", pos=[0.0, 0.0], cash=30000, contested=True))
    for i, c in enumerate(PILES_C_HALF):
        for k, p in enumerate((c, mirror(c))):
            piles.append(dict(id=f"pile_c{1 + 2 * i + k}", pos=[r1(p[0]), r1(p[1])], cash=30000, contested=True))
    derricks = []
    for c in DERRICKS_A:
        for k, p in enumerate((c, mirror(c))):
            derricks.append(dict(id=f"derrick_{'a' if k == 0 else 'b'}0", pos=[r1(p[0]), r1(p[1])], income=100,
                                 every_s=10, capture_s=8, radius_m=12, contested=False))
    for i, c in enumerate(DERRICKS_C_HALF):
        for k, p in enumerate((c, mirror(c))):
            derricks.append(dict(id=f"derrick_c{2 * i + k}", pos=[r1(p[0]), r1(p[1])], income=100, every_s=10,
                                 capture_s=8, radius_m=12, contested=True))
    roads = [dict(name=rd["name"], width_m=rd["width"], points=[[r1(x), r1(z)] for x, z in resample(rd["P"], 14.0)])
             for rd in R["roads"]]
    rmask = road_mask(roads)
    props = scatter_props(hq, slq, Wq, rmask, R, pads, piles, derricks)

    mapj = {
        "name": "Zagros Basin",
        "id": "zagros_basin",
        "version": 1,
        "size_m": [1200, 1200],
        "grid": {"samples": N, "spacing_m": STEP, "origin": [-HALF, -HALF],
                 "height_file": "height.r16", "height_format": "u16le, row-major, row 0 = z -600, col 0 = x -600",
                 "splat_file": "splat.png", "splat_channels": {"r": "rock", "g": "gravel", "b": "scrub", "a": "riverbed",
                                                               "remainder": "sand"}},
        "height_scale": HEIGHT_SCALE,
        "water_level": None,
        "players": 2,
        "symmetry": "point (x, z) -> (-x, -z)",
        "starts": starts,
        "start_flat_radius_m": START_R,
        "build_pads": pads,
        "supply_piles": piles,
        "oil_derricks": derricks,
        "roads": roads,
        "props": props,
        "civic": CIVIC,
        "prop_types": PROP_TYPES,
        "movement": MOVEMENT,
        "building_max_slope_deg": BUILDING_MAX_SLOPE,
        "notes": ("Fictional sector inspired by the character of Zagros foothills and a dry basin. SYNTHETIC terrain "
                  "(procedural; no real elevation data). All settlements, roads, supply sites and derricks are invented. "
                  "1200 x 1200 game metres represent ~5 km; vertical relief is exaggerated for the RTS camera. "
                  "facing_deg / yaw_deg are Godot rotation_degrees.y (0 = facing -Z, 90 = facing -X). Movement cost per "
                  "cell = sum(splat weight x material cost) (sand = remainder), blended to the road cost by the road mask; "
                  "a cell is impassable for a class when its slope exceeds max_slope_deg. See docs/MAP_ZAGROS_BASIN.md."),
    }
    with open(os.path.join(args.out, "map.json"), "w") as f:
        json.dump(mapj, f, indent=1)

    # ------------------------------------------------------------ verification
    rep = verify(hq, slq, Wq, rmask, mapj, R)
    rep["flatness"] = flat_checks(hq, slq, mapj)
    with open(os.path.join(args.out, "fairness_report.json"), "w") as f:
        json.dump(rep, f, indent=1)
    txt = report_text(rep)
    with open(os.path.join(args.out, "fairness_report.txt"), "w") as f:
        f.write(txt)
    print(txt)
    if args.albedo:
        write_albedo(args.albedo, hq, slq, Wq, rmask, roads=mapj["roads"])
    if not args.no_plots:
        plots(args.screens, hq, slq, Wq, rmask, mapj, R, rep)


# ====================================================================== props
PROP_TYPES = {
    "village_house": {"glb": "res://assets/units3d/props/village_house.glb", "footprint_m": [8.4, 8.4], "blocks": True},
    "ruin": {"glb": "res://assets/units3d/props/ruin.glb", "footprint_m": [11.0, 10.0], "blocks": True},
    "rock_cluster": {"glb": "res://assets/units3d/props/rock_cluster.glb", "footprint_m": [6.0, 5.0], "blocks": True},
    "date_palm": {"glb": "res://assets/units3d/props/date_palm.glb", "footprint_m": [1.0, 1.0], "blocks": False},
    "scrub": {"glb": "res://assets/units3d/props/scrub.glb", "footprint_m": [1.6, 1.6], "blocks": False},
    "pylon": {"glb": "res://assets/units3d/props/pylon.glb", "footprint_m": [5.0, 5.0], "blocks": True},
    "wall": {"glb": None, "footprint_m": [6.0, 0.6], "blocks": True,
             "note": "reserved; no asset yet, not placed on this map"},
}


def scatter_props(h, sl, W, rmask, R, pads, piles, derricks):
    rng = np.random.default_rng(7)
    keep_out = np.zeros((N, N), bool)
    keep_out |= rmask > 0.05
    keep_out |= ndi.binary_dilation(rmask > 0.05, iterations=3)
    for c in (START_A, START_B):
        keep_out |= np.hypot(X - c[0], Z - c[1]) < START_R + 25
    for p in pads:
        cx, cz = p["center"]; w, d = p["size"]
        keep_out |= (np.abs(X - cx) < w / 2 + 10) & (np.abs(Z - cz) < d / 2 + 10)
    for s in piles + derricks:
        keep_out |= np.hypot(X - s["pos"][0], Z - s["pos"][1]) < 30
    for P in list(R["passes"].values()):
        for PP in (P, np.asarray(mirror_poly(P))):
            d, _ = poly_dist(PP, 40.0)
            keep_out |= d < 18.0
    for PP in (R["goat"], np.asarray(mirror_poly(R["goat"]))):
        d, _ = poly_dist(PP, 12.0)
        keep_out |= d < 7.0
    props = []
    occupied = []

    def free(x, z, r):
        for (ox, oz, orr) in occupied:
            if (ox - x) ** 2 + (oz - z) ** 2 < (r + orr) ** 2:
                return False
        return True

    def add(t, x, z, yaw, sc, r):
        """Adds the prop and its point mirror (A half only)."""
        for (px, pz, py) in ((x, z, yaw), (-x, -z, (yaw + 180.0) % 360.0)):
            props.append(dict(type=t, pos=[round(px, 1), round(pz, 1)], yaw_deg=round(py, 1), scale=round(sc, 2)))
            occupied.append((px, pz, r))

    def cell(x, z):
        i, j = grid_index((x, z))
        return min(max(i, 0), N - 1), min(max(j, 0), N - 1)

    # village: houses along the west valley road around VILLAGE_A, oriented to the road
    vx, vz = VILLAGE_A
    road_dir = math.degrees(math.atan2(330.0 - 300.0, -150.0 - (-235.0)))
    lay = [(-26, -14), (-8, -20), (12, -17), (-22, 12), (0, 16), (20, 12), (34, -4)]
    for k, (du, dv) in enumerate(lay):
        a = math.radians(-35.0)
        x = vx + du * math.cos(a) - dv * math.sin(a); z = vz + du * math.sin(a) + dv * math.cos(a)
        yaw = (-(-35.0) + (180 if dv > 0 else 0) + rng.uniform(-6, 6)) % 360
        add("village_house", x, z, yaw, rng.uniform(0.95, 1.08), 5.5)
    for k in range(9):                                            # palms around the village well / wadi
        ang = rng.uniform(0, 2 * math.pi); rr = rng.uniform(28, 52)
        x, z = vx + rr * math.cos(ang), vz + rr * math.sin(ang)
        i, j = cell(x, z)
        if not keep_out[i, j] and free(x, z, 2.0):
            add("date_palm", x, z, rng.uniform(0, 360), rng.uniform(0.85, 1.15), 2.0)
    # ruins: an old walled compound near the centre (A half: south-west of the centre pile)
    for (x, z, yaw) in ((-104.0, 24.0, 25.0), (-126.0, 38.0, 115.0), (-96.0, 46.0, 300.0)):
        add("ruin", x, z, yaw, 1.0, 7.0)
    # ruins at the west basin crossing
    for (x, z, yaw) in ((-262.0, -170.0, 40.0), (-245.0, -150.0, 210.0)):
        add("ruin", x, z, yaw, 0.9, 7.0)
    # pylon line across the basin (straight line through the origin => symmetric set)
    for t in (60.0, 180.0, 300.0, 420.0, 540.0, 660.0):
        x, z = tp2w(t, 0.09 * t - 46.0)
        if abs(x) > 590 or abs(z) > 590:
            continue
        i, j = cell(x, z)
        if keep_out[i, j]:
            x, z = tp2w(t + 18.0, 0.09 * t - 46.0)
        add("pylon", x, z, (-35.0 + 90.0) % 360, 1.0, 4.0)       # cross arms perpendicular to the line
    # also pylons on the B half of the same line are produced by the mirror (t < 0)

    # date palms along the trunk wadi near the centre and the basin fans
    half = S > 0
    cand = np.argwhere(half & (R["river"] < 0.2) & (ndi.gaussian_filter(R["river"], 4.0) > 0.12) & (sl < 15) & ~keep_out & (A_ < 120))
    rng.shuffle(cand)
    n = 0
    for i, j in cand:
        if n >= 26:
            break
        x, z = xs[j] + rng.uniform(-0.9, 0.9), xs[i] + rng.uniform(-0.9, 0.9)
        if free(x, z, 9.0):
            add("date_palm", x, z, rng.uniform(0, 360), rng.uniform(0.8, 1.15), 2.0); n += 1
    # rock clusters: talus at cliff feet, crests, fans
    talus = ndi.gaussian_filter(W[..., 0], 4.0)
    cand = np.argwhere(half & ~keep_out & (sl < 34) & (talus > 0.25) & (W[..., 0] < 0.5))
    rng.shuffle(cand)
    n = 0
    for i, j in cand:
        if n >= 70:
            break
        x, z = xs[j], xs[i]
        if free(x, z, 9.0):
            add("rock_cluster", x, z, rng.uniform(0, 360), rng.uniform(0.7, 1.5), 4.0); n += 1
    cand = np.argwhere(half & ~keep_out & (sl < 12) & (A_ < 300) & (W[..., 0] < 0.1))
    rng.shuffle(cand)
    n = 0
    for i, j in cand:
        if n >= 18:
            break
        x, z = xs[j], xs[i]
        if free(x, z, 30.0):
            add("rock_cluster", x, z, rng.uniform(0, 360), rng.uniform(0.6, 1.0), 4.0); n += 1
    # scrub: weighted by the splat scrub channel
    pr = W[..., 2] * (~keep_out) * half * (sl < 26)
    flat = pr.ravel() / pr.sum()
    picks = rng.choice(N * N, size=1400, replace=False, p=flat)
    n = 0
    for k in picks:
        if n >= 330:
            break
        i, j = divmod(int(k), N)
        x, z = xs[j] + rng.uniform(-1, 1), xs[i] + rng.uniform(-1, 1)
        if free(x, z, 3.0):
            add("scrub", x, z, rng.uniform(0, 360), rng.uniform(0.7, 1.4), 1.0); n += 1
    return props


# ====================================================================== verification
def class_cost(W, rmask, cls):
    c = MOVEMENT[cls]["cost"]
    sand = np.clip(1 - W.sum(-1), 0, 1)
    mat = W[..., 0] * c["rock"] + W[..., 1] * c["gravel"] + W[..., 2] * c["scrub"] + W[..., 3] * c["riverbed"] + sand * c["sand"]
    return mat * (1 - rmask) + c["road"] * rmask


def verify(h, sl, W, rmask, mapj, R):
    rep = {"classes": {}, "routes": {}, "fairness": {}, "barriers": {}}
    sA = grid_index(START_A); sB = grid_index(START_B)
    iA = sA[0] * N + sA[1]; iB = sB[0] * N + sB[1]
    # pass block discs (crest point of each pass, A side + mirror)
    crest = {}
    for name, P in R["passes"].items():
        a = np.array([w2tp(*p)[1] for p in P])
        k = int(np.argmin(np.abs(a - ridge_center(w2tp(*P[len(P) // 2])[0]))))
        crest[name + "_A"] = tuple(P[k]); crest[name + "_B"] = mirror(tuple(P[k]))
    ga = R["goat"][len(R["goat"]) // 2]
    crest["goat_A"] = tuple(ga); crest["goat_B"] = mirror(tuple(ga))
    rep["pass_crests"] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in crest.items()}

    def block(names, r=105.0):
        m = np.zeros((N, N), bool)
        for nm in names:
            c = crest[nm]
            m |= np.hypot(X - c[0], Z - c[1]) < (r if not nm.startswith("goat") else 60.0)
        return m
    # route = the passes it uses (world west / centre / east); B's world-west pass is the mirror of A's east pass
    routes = {"west": ["west_A", "east_B"], "central": ["central_A", "central_B"], "east": ["east_A", "west_B"]}
    allp = [k for k in crest]
    rep["route_paths"] = {}
    for cls, spec in MOVEMENT.items():
        passable = sl <= spec["max_slope_deg"]
        cost = class_cost(W, rmask, cls)
        frac = float(passable.mean())
        G = build_graph(passable, cost)
        dist, pred = dijkstra(G, indices=[iA, iB], return_predecessors=True)
        rep["classes"][cls] = {"passable_fraction": round(frac, 4), "A_to_B_cost": round(float(dist[0, iB]), 1)}
        # fairness: own sites and contested sites
        fair = {}
        for kind, items in (("supply_piles", mapj["supply_piles"]), ("oil_derricks", mapj["oil_derricks"])):
            for it in items:
                g = grid_index(it["pos"]); gi = g[0] * N + g[1]
                fair[it["id"]] = (round(float(dist[0, gi]), 1), round(float(dist[1, gi]), 1))
        rep["fairness"][cls] = fair
        rep["routes"][cls] = {}
        for rname, used in routes.items():
            blk = block([p for p in allp if p not in used])
            G2 = build_graph(passable & ~blk, cost)
            d2, p2 = dijkstra(G2, indices=[iA], return_predecessors=True)
            ok = bool(np.isfinite(d2[0, iB]))
            path = trace(p2[0], iA, iB) if ok else None
            L = float(np.sum(np.hypot(*np.diff(path, axis=0).T))) if ok else None
            rep["routes"][cls][rname] = {"connected": ok, "cost": round(float(d2[0, iB]), 1) if ok else None,
                                          "length_m": round(L, 1) if ok else None}
            if ok:
                rep["route_paths"][f"{cls}:{rname}"] = path[::4].round(1).tolist()
        # barrier tests: all passes blocked (goat trails open), and everything blocked
        bl1 = block([p for p in allp if not p.startswith("goat")])
        G3 = build_graph(passable & ~bl1, cost)
        d3 = dijkstra(G3, indices=[iA])
        bl2 = block(allp)
        G4 = build_graph(passable & ~bl2, cost)
        d4 = dijkstra(G4, indices=[iA])
        rep["barriers"][cls] = {"passes_blocked_goat_open_connected": bool(np.isfinite(d3[0, iB])),
                                "all_blocked_connected": bool(np.isfinite(d4[0, iB]))}
    rep["max_slope_deg"] = round(float(sl.max()), 1)
    rep["cells_over_38deg"] = int((sl > 38).sum())
    rep["cells_over_45deg"] = int((sl > 45).sum())
    return rep


def flat_checks(h, sl, mapj):
    out = {}
    for st in mapj["starts"]:
        x, z = st["pos"]
        m = np.hypot(X - x, Z - z) < START_R
        out[f"start_team{st['team']}"] = {"height_range_m": round(float(h[m].max() - h[m].min()), 2),
                                          "max_slope_deg": round(float(sl[m].max()), 2),
                                          "mean_h": round(float(h[m].mean()), 2)}
    for k, p in enumerate(mapj["build_pads"]):
        (x, z), (w, d) = p["center"], p["size"]
        m = (np.abs(X - x) <= w / 2) & (np.abs(Z - z) <= d / 2)
        out[f"pad{k}"] = {"center": p["center"], "height_range_m": round(float(h[m].max() - h[m].min()), 2),
                          "max_slope_deg": round(float(sl[m].max()), 2)}
    rm = road_mask(mapj["roads"]) > 0.9
    out["roads_max_slope_deg"] = round(float(sl[rm].max()), 2)
    out["roads_p99_slope_deg"] = round(float(np.percentile(sl[rm], 99)), 2)
    return out


CONTESTED_MIRROR = {"pile_c1": "pile_c2", "pile_c2": "pile_c1", "derrick_c0": "derrick_c1", "derrick_c1": "derrick_c0"}


def fairness_max_diff(rep):
    worst = 0.0
    for cls, fair in rep["fairness"].items():
        for k, (a, _) in fair.items():
            km = k.replace("_a", "_b") if k.startswith(("pile_a", "derrick_a")) else CONTESTED_MIRROR.get(k, k)
            if km in fair and not k.startswith(("pile_b", "derrick_b")):
                b = fair[km][1]
                worst = max(worst, 100 * abs(a - b) / max(a, b, 1e-9))
    return worst


def report_text(rep):
    L = ["Zagros Basin - verification report (generated by tools/map/gen_zagros_basin.py)", ""]
    L.append("FAIRNESS: path cost from start A (team 0) vs start B (team 1), per movement class.")
    L.append("  cost = metres x terrain/road multiplier; own sites compare A->own vs B->own; contested compare A vs B.")
    for cls, fair in rep["fairness"].items():
        L.append(f"  [{cls}]")
        ids = list(fair)
        done = set()
        for k in ids:
            if k in done:
                continue
            if k.startswith(("pile_a", "derrick_a")):
                kb = k.replace("_a", "_b")
                a = fair[k][0]; b = fair[kb][1]
                done |= {k, kb}
                L.append(f"    own   {k:12s}/{kb:12s}  A {a:8.1f}  B {b:8.1f}  diff {100 * abs(a - b) / max(a, b, 1e-9):5.2f} %")
            elif "_c" in k:
                km = CONTESTED_MIRROR.get(k, k)
                a = fair[k][0]; b = fair[km][1]
                done |= {k, km}
                L.append(f"    contested A->{k:11s} vs B->{km:11s}  A {a:8.1f}  B {b:8.1f}  diff {100 * abs(a - b) / max(a, b, 1e-9):5.2f} %")
    L.append(f"  worst A/B difference over all classes and sites: {fairness_max_diff(rep):.2f} % (limit 3 %)")
    L.append("")
    L.append("ROUTES: A->B with only that route's two passes open (others blocked by 105 m discs on the crests).")
    for cls, rr in rep["routes"].items():
        s = ", ".join(f"{k}: {'OK' if v['connected'] else 'BLOCKED'}" + (f" ({v['length_m']:.0f} m)" if v["connected"] else "")
                      for k, v in rr.items())
        L.append(f"  {cls:9s} {s}")
    L.append("")
    L.append("BARRIERS: A->B connectivity with every pass blocked (goat trails open) / with everything blocked.")
    for cls, b in rep["barriers"].items():
        L.append(f"  {cls:9s} passes blocked: {'connected' if b['passes_blocked_goat_open_connected'] else 'disconnected'}"
                 f";  all blocked: {'connected' if b['all_blocked_connected'] else 'disconnected'}")
    L.append("")
    L.append(f"Max slope {rep['max_slope_deg']} deg; cells > 38 deg: {rep['cells_over_38deg']}; > 45 deg: {rep['cells_over_45deg']}")
    for cls, c in rep["classes"].items():
        L.append(f"  {cls:9s} passable fraction {c['passable_fraction']:.3f}")
    L.append("")
    L.append("FLATNESS (starts: 100 m radius; pads: full rectangle):")
    for k, v in rep["flatness"].items():
        L.append(f"  {k}: {v}")
    return "\n".join(L) + "\n"


def write_import(path):
    with open(path, "w") as f:
        f.write("""[remap]

importer="texture"
type="CompressedTexture2D"

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=false
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
""")


# ====================================================================== colour map + plots
def colour_map(h, sl, W, rmask, ppc=1):
    """Approximate the in-game terrain shader colours (sand/rock/gravel/scrub/riverbed/asphalt) for previews."""
    n1 = aniso_noise(31, 30.0, 30.0); n2 = aniso_noise(32, 4.0, 4.0)
    k1 = smoothstep(-1.5, 1.5, n1)[..., None]; k2 = smoothstep(-1.5, 1.5, n2)[..., None]
    sand = (np.array([0.70, 0.60, 0.44]) * (1 - k1) + np.array([0.78, 0.68, 0.50]) * k1) * (0.92 + 0.12 * k2)
    rock = (np.array([0.46, 0.40, 0.34]) * (1 - k2) + np.array([0.58, 0.52, 0.45]) * k2)
    gravel = np.array([0.58, 0.54, 0.48]) * (0.9 + 0.15 * k2)
    scrub = np.array([0.50, 0.50, 0.32]) * (0.9 + 0.2 * k2)
    river = np.array([0.66, 0.62, 0.53]) * (0.95 + 0.1 * k1)
    asphalt = np.array([0.33, 0.31, 0.28])
    slope01 = 1 - np.cos(np.radians(sl))
    rock_w = np.clip(W[..., 0] + smoothstep(0.25, 0.55, slope01), 0, 1)[..., None]
    c = sand
    c = c * (1 - W[..., 1:2]) + gravel * W[..., 1:2]
    c = c * (1 - W[..., 2:3]) + scrub * W[..., 2:3]
    c = c * (1 - W[..., 3:4]) + river * W[..., 3:4]
    c = c * (1 - rock_w) + rock * rock_w
    r = smoothstep(0.1, 0.8, rmask)[..., None]
    c = c * (1 - r) + asphalt * r
    return np.clip(c, 0, 1)


def write_albedo(path, h, sl, W, rmask, roads=None, res=4096):
    """Preview colour map at `res` px: terrain colours upsampled from the 2 m grid + rock strata banding, with the
    roads re-rasterised at full resolution (for the Blender RTS render only; the game shades procedurally)."""
    from PIL import ImageDraw, ImageFilter
    c = colour_map(h, sl, W, np.zeros_like(rmask))
    # strata: light limestone benches / darker risers and bands, only where rock dominates
    rockw = smoothstep(0.1, 0.5, W[..., 0])
    band = 1 + (0.12 * np.sin(h * 2 * PI / 6.5) + 0.05 * np.sin(h * 2 * PI / 2.1)) * rockw
    band *= 1 - 0.22 * smoothstep(38, 60, sl) * rockw
    c = np.clip(c * band[..., None], 0, 1)
    img = Image.fromarray((c * 255).astype(np.uint8)).resize((res, res), Image.BICUBIC)
    a = np.asarray(img, np.float32) / 255
    rng = np.random.default_rng(5)
    g = ndi.gaussian_filter(rng.standard_normal((res, res)).astype(np.float32), 1.2) * 2.2
    a *= (1 + 0.05 * g[..., None])
    up = lambda arr: np.asarray(Image.fromarray(arr.astype(np.float32), "F").resize((res, res), Image.BILINEAR))
    scrub_u = up(W[..., 2]); grav_u = up(W[..., 1])
    dots = ndi.gaussian_filter(rng.standard_normal((res, res)).astype(np.float32), 1.0)
    sd = smoothstep(1.2, 1.6, dots * (0.6 + scrub_u * 1.4)) * (scrub_u > 0.08)
    a = a * (1 - 0.45 * sd[..., None]) + np.array([0.33, 0.35, 0.22], np.float32) * 0.45 * sd[..., None]
    pebble = smoothstep(1.5, 1.9, ndi.gaussian_filter(rng.standard_normal((res, res)).astype(np.float32), 0.7) * (0.7 + grav_u))
    a = a * (1 - 0.25 * pebble[..., None])
    del dots, g
    if roads:
        m = Image.new("L", (res, res), 0); dr = ImageDraw.Draw(m)
        ppm = res / (2 * HALF)
        for rd in roads:
            pts = [((x + HALF) * ppm, (z + HALF) * ppm) for x, z in catmull(rd["points"], 3.0)]
            dr.line(pts, fill=255, width=max(1, int(rd["width_m"] * 0.75 * ppm)), joint="curve")
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(ppm * 0.6)), np.float32)[..., None] / 255
        asph = np.array([0.36, 0.33, 0.30], np.float32)
        edge = np.array([0.62, 0.56, 0.47], np.float32)
        shoulder = np.asarray(Image.fromarray((m[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(ppm * 1.5)), np.float32)[..., None] / 255
        a = a * (1 - 0.5 * np.clip(shoulder * 2 - m, 0, 1)) + edge * 0.5 * np.clip(shoulder * 2 - m, 0, 1)
        a = a * (1 - m) + asph * m
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(path)
    print("albedo", path)


def hillshade(h, az=315, alt=40):
    gy, gx = np.gradient(h, STEP)
    slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    a, b = math.radians(az), math.radians(alt)
    return np.clip(np.sin(b) * np.cos(slope) + np.cos(b) * np.sin(slope) * np.cos(a - aspect), 0, 1)


def plots(outdir, h, sl, W, rmask, mapj, R, rep):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    os.makedirs(outdir, exist_ok=True)
    ext = [-HALF, HALF, HALF, -HALF]                              # x right, z down (north = top)
    hs = hillshade(h)

    def frame(ax, title):
        ax.set_xlim(-HALF, HALF); ax.set_ylim(HALF, -HALF)
        ax.set_title(title, fontsize=12, loc="left")
        ax.set_xlabel("x (m, east)"); ax.set_ylabel("z (m, south)")
        ax.set_aspect("equal")

    def sites(ax, labels=True, small=False):
        for rd in mapj["roads"]:
            P = np.asarray(rd["points"])
            ax.plot(P[:, 0], P[:, 1], color="#2b2622", lw=rd["width_m"] * (0.22 if small else 0.32), alpha=0.9, solid_capstyle="round")
        for p in mapj["build_pads"]:
            (x, z), (w, d) = p["center"], p["size"]
            ax.add_patch(Rectangle((x - w / 2, z - d / 2), w, d, fill=False, ec="#ffffff", lw=1.0, ls="--"))
        for st in mapj["starts"]:
            x, z = st["pos"]
            ax.add_patch(Circle((x, z), START_R, fill=False, ec="#ffffff", lw=1.4))
            ax.plot([x], [z], marker="*", ms=16, mec="k", mfc=("#3b82f6" if st["team"] == 0 else "#ef4444"))
            if labels:
                ax.text(x + 18, z + (40 if st["team"] == 0 else -30), f"Start {'A' if st['team'] == 0 else 'B'}", color="w",
                        fontsize=10, weight="bold", bbox=dict(fc="#00000088", ec="none", pad=1.5))
        for p in mapj["supply_piles"]:
            x, z = p["pos"]
            ax.plot([x], [z], marker="s", ms=8 if p["contested"] else 7, mec="k", mfc="#facc15")
            if labels:
                ax.text(x + 9, z - 9, f"{p['cash'] // 1000}k", fontsize=7, color="#fde68a",
                        bbox=dict(fc="#00000077", ec="none", pad=0.6))
        for d in mapj["oil_derricks"]:
            x, z = d["pos"]
            ax.plot([x], [z], marker="D", ms=8, mec="k", mfc="#a855f7")
        for p in mapj["props"]:
            if p["type"] in ("village_house", "ruin", "pylon"):
                x, z = p["pos"]
                ax.plot([x], [z], marker={"village_house": "s", "ruin": "x", "pylon": "+"}[p["type"]], ms=3.5,
                        color={"village_house": "#f5f5f4", "ruin": "#fca5a5", "pylon": "#e5e7eb"}[p["type"]], ls="none")

    # ---- height
    fig, ax = plt.subplots(figsize=(9.6, 9.6), dpi=110)
    im = ax.imshow(h, extent=ext, cmap="terrain", vmin=-8, vmax=72)
    ax.imshow(hs, extent=ext, cmap="gray", alpha=0.35)
    cs = ax.contour(xs, xs, h, levels=np.arange(5, 80, 5), colors="k", linewidths=0.35, alpha=0.6)
    ax.clabel(cs, levels=np.arange(10, 80, 20), fontsize=6, fmt="%d m")
    sites(ax, labels=False, small=True)
    frame(ax, "Zagros Basin - height (game metres, 5 m contours) - SYNTHETIC terrain")
    fig.colorbar(im, ax=ax, shrink=0.7, label="height (m)")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "map_zagros_height.png")); plt.close(fig)

    # ---- splat
    fig, axs = plt.subplots(2, 3, figsize=(13.5, 9.4), dpi=100)
    sand = np.clip(1 - W.sum(-1), 0, 1)
    for ax, (nm, arr, cm) in zip(axs.ravel(), (("rock (R)", W[..., 0], "Greys"), ("gravel / scree (G)", W[..., 1], "Oranges"),
                                               ("scrub (B)", W[..., 2], "Greens"), ("dry riverbed (A)", W[..., 3], "Blues"),
                                               ("sand (remainder)", sand, "YlOrBr"), ("slope (deg)", sl, "magma"))):
        im = ax.imshow(arr, extent=ext, cmap=cm, vmin=0, vmax=(1 if "slope" not in nm else 60))
        ax.set_title(nm, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.75)
    fig.suptitle("Zagros Basin - splat.png material weights (sand = 1 - R - G - B - A) and slope", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "map_zagros_splat.png")); plt.close(fig)

    # ---- overview
    col = colour_map(h, sl, W, rmask)
    shade = (0.55 + 0.6 * hs)[..., None]
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=110)
    ax.imshow(np.clip(col * shade, 0, 1), extent=ext)
    sites(ax)
    for p in mapj["props"]:
        x, z = p["pos"]
        if p["type"] == "date_palm":
            ax.plot([x], [z], marker="o", ms=2.5, color="#3f6212", ls="none")
        elif p["type"] == "rock_cluster":
            ax.plot([x], [z], marker="^", ms=2.5, color="#57534e", ls="none")
    for k, c in rep["pass_crests"].items():
        nm, side = k.split("_")
        if side == "B" and nm in ("west", "east"):
            nm = "east" if nm == "west" else "west"              # B's passes are mirrored: label by world side
        ax.text(c[0], c[1], {"west": "W pass", "central": "C pass", "east": "E pass", "goat": "trail"}[nm], fontsize=8,
                color="w", ha="center", va="center", bbox=dict(fc="#1f2937aa", ec="none", pad=1.0))
    vx, vz = VILLAGE_A
    for (x, z) in ((vx, vz), mirror((vx, vz))):
        ax.text(x, z + 40, "village", fontsize=8, color="w", ha="center", bbox=dict(fc="#00000066", ec="none", pad=0.8))
    from matplotlib.lines import Line2D
    leg = [Line2D([], [], marker="*", ms=12, mfc="#3b82f6", mec="k", ls="none", label="start A (team 0)"),
           Line2D([], [], marker="*", ms=12, mfc="#ef4444", mec="k", ls="none", label="start B (team 1)"),
           Line2D([], [], marker="s", ms=7, mfc="#facc15", mec="k", ls="none", label="supply pile"),
           Line2D([], [], marker="D", ms=7, mfc="#a855f7", mec="k", ls="none", label="oil derrick"),
           Line2D([], [], color="#2b2622", lw=2.5, label="road"),
           Line2D([], [], color="w", lw=1, ls="--", label="build pad"),
           Line2D([], [], marker="s", ms=4, color="#f5f5f4", ls="none", label="house"),
           Line2D([], [], marker="x", ms=4, color="#fca5a5", ls="none", label="ruin"),
           Line2D([], [], marker="+", ms=6, color="#e5e7eb", ls="none", label="pylon")]
    ax.legend(handles=leg, loc="lower left", fontsize=8, framealpha=0.75)
    frame(ax, "Zagros Basin - overview (1200 x 1200 m, ~5 km represented; north up)")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "map_zagros_overview.png")); plt.close(fig)

    # ---- routes
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=110)
    ax.imshow(hs, extent=ext, cmap="gray", vmin=-0.3, vmax=1.2)
    blocked = {}
    for cls, colr in (("wheeled", "#ef4444"), ("tracked", "#f59e0b"), ("infantry", "#22c55e")):
        imp = sl > MOVEMENT[cls]["max_slope_deg"]
        blocked[cls] = imp
    over = np.zeros((N, N, 4))
    over[blocked["wheeled"]] = (0.95, 0.35, 0.3, 0.30)
    over[blocked["tracked"]] = (0.95, 0.6, 0.1, 0.40)
    over[blocked["infantry"]] = (0.55, 0.0, 0.6, 0.65)
    ax.imshow(over, extent=ext)
    styles = {"wheeled": ("#dc2626", "-", 2.6), "tracked": ("#f59e0b", "--", 2.0), "infantry": ("#16a34a", ":", 2.0)}
    for key, path in rep["route_paths"].items():
        cls, rname = key.split(":")
        P = np.asarray(path)
        c, ls, lw = styles[cls]
        ax.plot(P[:, 0], P[:, 1], color=c, ls=ls, lw=lw, alpha=0.95)
    sites(ax, labels=True, small=True)
    leg = [Line2D([], [], color="#dc2626", lw=2.6, label="wheeled route (max 18 deg)"),
           Line2D([], [], color="#f59e0b", lw=2, ls="--", label="tracked route (max 28 deg)"),
           Line2D([], [], color="#16a34a", lw=2, ls=":", label="infantry route (max 38 deg)"),
           Rectangle((0, 0), 1, 1, fc=(0.95, 0.35, 0.3, 0.5), label="too steep: wheeled"),
           Rectangle((0, 0), 1, 1, fc=(0.95, 0.6, 0.1, 0.6), label="too steep: tracked"),
           Rectangle((0, 0), 1, 1, fc=(0.55, 0.0, 0.6, 0.75), label="too steep: infantry (> 38 deg)")]
    ax.legend(handles=leg, loc="lower left", fontsize=8, framealpha=0.8)
    s = "  ".join(f"{cls}: " + "/".join(("W" if k == "west" else "C" if k == "central" else "E") + ("+" if v["connected"] else "x")
                                        for k, v in rr.items()) for cls, rr in rep["routes"].items())
    frame(ax, "Zagros Basin - routes A->B per movement class (west / central / east, each forced through its passes)")
    ax.text(-590, -575, s, fontsize=8.5, color="w", bbox=dict(fc="#000000aa", ec="none"))
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "map_zagros_routes.png")); plt.close(fig)
    print("plots ->", outdir)


if __name__ == "__main__":
    main()
