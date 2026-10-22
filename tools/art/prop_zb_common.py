"""Steel Accord - shared helpers for the Zagros Basin map props (prop_*.py). Imports bldkit_b and:

  * patches bldkit_b.orient_islands so face normals are updated BEFORE the planar 'tile' UV projection.
    (bldkit_b leaves faces of open islands made by Part.frustum / Part.quad / Part.loft with stale zero normals, so the
    projection axis falls back to X and the texture smears into stripes; bldkit_b itself is not modified here.)
  * adds the extra source surfaces used by the map props (mud plaster, mud brick, limestone, sandstone, palm bark,
    fronds, shrub foliage/twigs, galvanised steel, ...);
  * organic geometry helpers: displaced boulders, foliage blobs, bent ribbons (fronds), tapered trunks.
Deterministic: fixed seeds only.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import bmesh
import numpy as np
from mathutils import Matrix, Euler, Vector as V

_orig_orient = K.orient_islands


def _orient_with_normals(bm):
    bm.normal_update()
    _orig_orient(bm)
    bm.normal_update()


K.orient_islands = _orient_with_normals
PI = math.pi
n_ = K.noise; col = K.col; shade = K.shade; lines = K.lines; frac = K.frac; UU = K.UU; VV = K.VV


# ====================================================================== extra source surfaces
def t_mud():           # sun-bleached mud/straw plaster, streaky rain wash from the top (S = 3 m)
    k = 1 + 0.05 * n_(30, 30, 501) + 0.04 * n_(3, 3, 502) - 0.07 * np.clip(n_(2, 50, 503), 0, None)
    straw = (n_(1.2, 6, 504) > 2.0).astype(np.float32)
    k *= 1 + 0.08 * straw
    patch = np.clip(n_(40, 30, 505) - 0.9, 0, None)                  # repaired patches, slightly darker/redder
    img = shade(col(184, 156, 118), k)
    return img * (1 - 0.08 * patch[..., None]) + col(30, 10, 0)[None, None] * 0.06 * patch[..., None]


def t_mudbrick():      # exposed sun-dried bricks with mortar joints (S = 2 m: 6 courses, 5 bricks)
    row = np.floor(VV * 6)
    off = (row % 2) * 0.1
    jv = lines(VV, 6, 0.1); ju = lines(UU + off, 5, 0.05)
    k = (1 + 0.06 * n_(6, 6, 511) + 0.04 * n_(2, 2, 512)) * (1 - 0.22 * np.maximum(jv, ju))
    tone = 1 + 0.05 * np.sin(row * 12.9 + np.floor((UU + off) * 5) * 78.2)
    return shade(col(170, 138, 100), k * tone)


def t_lime():          # pale limestone with bedding lines (v = height) and pitting (S = 4 m)
    bed = 0.035 * np.sin(VV * 2 * PI * 5 + 2.0 * n_(60, 30, 521))
    k = 1 + bed + 0.08 * n_(30, 30, 523) + 0.05 * n_(8, 8, 527) + 0.04 * n_(2, 2, 524) - 0.12 * np.clip(n_(3, 3, 525) - 1.4, 0, None)
    stain = np.clip(n_(10, 50, 526) - 0.6, 0, None)[..., None]
    img = shade(col(164, 152, 132), k)
    return img * (1 - 0.18 * stain)


def t_sandstone():     # warmer reddish sandstone with cross-bedding (S = 4 m)
    bed = 0.04 * np.sin((VV + 0.15 * UU) * 2 * PI * 5 + 2.0 * n_(50, 30, 531))
    k = 1 + bed + 0.06 * n_(15, 15, 532) + 0.05 * n_(2, 2, 533)
    return shade(col(170, 128, 92), k)


def t_bark():          # date palm trunk: diamond leaf-base pattern (u around, v up; S = 1 m)
    a = frac(UU * 6 + VV * 3); b = frac(UU * 6 - VV * 3)
    ridge = np.minimum(np.abs(a - 0.5), np.abs(b - 0.5))
    k = (0.75 + 0.6 * np.clip(ridge * 3, 0, 1)) * (1 + 0.05 * n_(6, 6, 541) + 0.04 * n_(2, 2, 542))
    return shade(col(120, 96, 70), k)


def t_frond():         # palm frond: midrib along u + angled leaflets (S = 1 m, u along the frond)
    leaf = frac((UU * 1.0 + np.abs(VV - 0.5) * 1.2) * 14)
    k = np.where(leaf < 0.55, 1.08, 0.72) * (1 + 0.05 * n_(20, 4, 551))
    mid = (np.abs(VV - 0.5) < 0.04)
    img = shade(col(104, 112, 58), k)
    img[mid] = col(150, 140, 92)
    dry = np.clip(n_(60, 30, 552) - 0.8, 0, None)[..., None]          # some sun-dried leaflets
    return img * (1 - 0.4 * dry) + col(170, 146, 88)[None, None] * 0.4 * dry


def t_shrub():         # dusty grey-green shrub foliage (S = 1 m)
    k = 1 + 0.12 * n_(4, 4, 561) + 0.06 * n_(1.5, 1.5, 562)
    spots = (n_(2, 2, 563) > 1.0).astype(np.float32)[..., None]
    img = shade(col(118, 120, 84), k)
    return img * (1 - 0.25 * spots) + col(160, 146, 104)[None, None] * 0.25 * spots


def t_twig():
    k = 1 + 0.08 * n_(2, 20, 571)
    return shade(col(92, 76, 60), k)


def t_galv():          # weathered galvanised steel lattice (S = 2 m)
    k = 1 + 0.05 * n_(20, 20, 581) + 0.04 * n_(2, 2, 582) - 0.08 * np.clip(n_(4, 40, 583), 0, None)
    return shade(col(150, 152, 150), k)


def t_glassins():      # glazed ceramic insulator discs
    k = (1 - 0.3 * lines(VV, 8, 0.25)) * (1 + 0.04 * n_(10, 10, 591))
    return shade(col(104, 110, 104), k)


def t_rubble():        # mixed rubble / fallen mud brick (S = 2 m)
    k = 1 + 0.14 * n_(3, 3, 601) + 0.08 * n_(1.5, 1.5, 602) + 0.05 * n_(15, 15, 603)
    return shade(col(156, 130, 98), k)


def t_wood_old():      # grey sun-bleached timber (roof beams, doors)
    k = (1 + 0.1 * n_(2, 40, 611) + 0.04 * n_(2, 2, 612)) * (1 - 0.3 * lines(UU, 6, 0.04))
    return shade(col(120, 108, 92), k)


def t_door_blue():     # painted metal door, faded turquoise (S = 2 m)
    k = (1 + 0.04 * n_(20, 20, 621) - 0.15 * np.clip(n_(3, 3, 622) - 1.2, 0, None)) * (1 - 0.25 * lines(VV, 4, 0.02))
    return shade(col(64, 120, 122), k)


def t_plaster_w():     # lime-washed plaster (S = 3 m)
    k = 1 + 0.03 * n_(30, 30, 631) + 0.03 * n_(2, 2, 632) - 0.08 * np.clip(n_(2, 60, 633), 0, None)
    return shade(col(206, 196, 176), k)


def t_dates():
    k = 1 + 0.15 * n_(1.5, 1.5, 641)
    return shade(col(150, 82, 36), k)


K.SURF.update({
    "mud": (t_mud, 3.0), "mudbrick": (t_mudbrick, 2.0), "lime": (t_lime, 4.0), "sandstone": (t_sandstone, 4.0),
    "bark": (t_bark, 1.0), "frond": (t_frond, 1.0), "shrub": (t_shrub, 1.0), "twig": (t_twig, 1.0),
    "galv": (t_galv, 2.0), "insul": (t_glassins, 0.5), "rubble": (t_rubble, 2.0), "woodold": (t_wood_old, 2.0),
    "doorb": (t_door_blue, 2.0), "plaster": (t_plaster_w, 3.0), "dates": (t_dates, 0.5),
})
K.DOUBLE_SIDED.update({"frond"})


# ====================================================================== organic geometry
def _hash3(p, seed):
    return math.sin(p[0] * 12.9898 + p[1] * 78.233 + p[2] * 37.719 + seed * 4.37) * 43758.5453 % 1.0


def vnoise3(p, seed):
    """Smooth value noise in 3D (deterministic, pure python - only used on small vertex counts)."""
    ip = [math.floor(c) for c in p]; f = [c - i for c, i in zip(p, ip)]
    u = [t * t * (3 - 2 * t) for t in f]
    acc = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[0] if dx else 1 - u[0]) * (u[1] if dy else 1 - u[1]) * (u[2] if dz else 1 - u[2])
                acc += w * (_hash3((ip[0] + dx, ip[1] + dy, ip[2] + dz), seed) % 1.0)
    return acc * 2 - 1


def boulder(P, m, c, size, seed, rot_z=0.0, subdiv=2, facet=0.18, sink=0.12, flat_top=0.0, strata=0.0):
    """Displaced icosphere boulder (closed mesh) scaled to `size` (x, y, z), sunk `sink` m into the ground.
    facet: amplitude of the fractured-face displacement; strata: horizontal step amplitude (layered rock)."""
    bm = P.bm(m)
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    vs = res["verts"]
    R = Euler((0, 0, rot_z)).to_matrix()
    for v in vs:
        p = v.co.copy()
        d = 1.0 + 0.22 * vnoise3(p * 1.3, seed) + facet * vnoise3(p * 3.1, seed + 7)
        p = p * d
        if strata:
            z = p.z
            p.z = z + strata * (math.floor(z * 3.0) / 3.0 - z) * 0.6
        if flat_top and p.z > 1 - flat_top:
            p.z = 1 - flat_top + (p.z - (1 - flat_top)) * 0.25
        p = V((p.x * size[0], p.y * size[1], max(p.z, -0.6) * size[2]))
        p = R @ p
        v.co = V(c) + p + V((0, 0, size[2] * 0.62 - sink))
    return vs


def blob(P, m, c, r, seed, squash=0.8, subdiv=1, amp=0.25):
    bm = P.bm(m)
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in res["verts"]:
        p = v.co.copy()
        d = 1.0 + amp * vnoise3(p * 2.0, seed)
        v.co = V(c) + V((p.x * r * d, p.y * r * d, p.z * r * d * squash))


def ribbon(P, m, pts, widths, normal_up=True, keel=0.0):
    """Strip through 3D centre points with given half widths; the cross direction is horizontal (perpendicular to the
    local tangent). keel > 0 folds the strip into a shallow V (palm frond). Open surface -> use a double-sided surface."""
    bm = P.bm(m)
    rows = []
    for i, (p, w) in enumerate(zip(pts, widths)):
        p = V(p)
        t = (V(pts[min(i + 1, len(pts) - 1)]) - V(pts[max(i - 1, 0)])).normalized()
        side = t.cross(V((0, 0, 1)))
        if side.length < 1e-4:
            side = V((1, 0, 0))
        side.normalize()
        up = side.cross(t).normalized()
        rows.append([bm.verts.new(p - side * w + up * keel * w), bm.verts.new(p), bm.verts.new(p + side * w + up * keel * w)])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(2):
            f = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))


def trunk(P, m, base, top, r0, r1, seg=10, rings=8, bend=(0.0, 0.0), seed=0):
    """Tapered, gently bent trunk with presets UVs: u around, v up (metres), so bark textures wrap correctly."""
    bm = P.bm(m)
    uv = bm.loops.layers.uv["tile"]; pre = bm.faces.layers.int["preset"]
    base = V(base); top = V(top)
    S = K.SURF[m][1]
    ringsv = []
    for j in range(rings + 1):
        t = j / rings
        c = base.lerp(top, t) + V((bend[0] * math.sin(t * PI * 0.9), bend[1] * math.sin(t * PI * 0.9), 0))
        r = r0 + (r1 - r0) * t
        r *= 1 + 0.06 * math.sin(t * 23.0 + seed)
        ringsv.append([bm.verts.new(c + V((r * math.cos(2 * PI * k / seg), r * math.sin(2 * PI * k / seg), 0)))
                       for k in range(seg)])
    H = (top - base).length
    circ = 2 * PI * (r0 + r1) / 2
    for j in range(rings):
        for k in range(seg):
            k1 = (k + 1) % seg
            f = bm.faces.new((ringsv[j][k], ringsv[j][k1], ringsv[j + 1][k1], ringsv[j + 1][k]))
            f[pre] = 1
            for lp in f.loops:
                jj = j + (1 if lp.vert in ringsv[j + 1] else 0)
                kk = k if lp.vert in (ringsv[j][k], ringsv[j + 1][k]) else k + 1
                lp[uv].uv = (kk / seg * circ / S, jj / rings * H / S)
    bm.faces.new(ringsv[-1])                                       # top cap (hidden under the crown)
    return ringsv


def finish_and_preview(kit, args, glb_name, prefix, shots, ground=40):
    glb = os.path.join(args.out, glb_name)
    if not args.skip_build:
        kit_obj = kit() if callable(kit) else kit
        kit_obj.finish(args.out, glb_name, ground_size=ground)
    if args.previews:
        K.previews(glb, args.previews, prefix, shots, only=args.only)
    return glb
