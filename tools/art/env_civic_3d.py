"""Steel Accord - neutral civilian buildings that infantry can garrison (original designs, code-built in Blender bpy 5.x).

Generic modern Middle-East / Mediterranean town style: light sand, beige and off-white plaster, faded colour
accents. No real-world logos, brands, writing or flags. The hospital is marked ONLY with a plain white "H" (on a green
panel, and in a white circle on the rooftop helipad); no red cross / crescent / crystal or any protected emblem.

Run:  python3 -I env_civic_3d.py <out_root> [--only id,id] [--sheet <contact_sheet.png>] [--previews-only]
Out:  <out_root>/<id>/<id>.glb for id in civ_house_a, civ_house_b, civ_apartment, civ_center, civ_hospital
      Each GLB: one mesh node `<id>` (atlas material CV_<Id>, 1024 px baked colour x AO; `<id>`_2S double-sided
      variant only where dish shells need it) + empties `Door`, `Port1..PortN` (+ `Heal` on the hospital).
Conventions (same as bldkit_b / the existing structures and props): metres; origin = centre of the footprint at
ground level; the main entrance faces Blender -Y = glTF/Godot +Z. Walls continue 0.5 m below the origin so the
buildings sit on uneven terrain without gaps. Everything (incl. canopies) stays inside the stated footprint; only
the `Door` empty lies just outside it. Deterministic: fixed noise seeds, fixed creation order.
Pipeline: tools/art/bldkit_b.py (+ prop_zb_common.py surfaces/normal patch); this file only adds surfaces, a few
facade helpers and the five layouts, plus the review contact sheet.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C
K = C.K
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Euler, Vector as V

PI = math.pi
SUB = -0.5
n_ = K.noise; col = K.col; shade = K.shade; lines = K.lines; frac = K.frac; UU = K.UU; VV = K.VV
IDS = ["civ_house_a", "civ_house_b", "civ_apartment", "civ_center", "civ_hospital"]
FOOT = {"civ_house_a": (10, 9), "civ_house_b": (12, 10), "civ_apartment": (18, 12), "civ_center": (22, 16),
        "civ_hospital": (24, 18)}


# ====================================================================== surfaces
def t_plas(rgb, seed, streak=0.07, patch=0.05):
    """Painted render / plaster: fine trowel noise, rain streaks from the top, faint repaired patches (S = 3 m)."""
    def f():
        k = 1 + 0.025 * n_(40, 40, seed) + 0.025 * n_(3, 3, seed + 1) - streak * np.clip(n_(2, 60, seed + 2), 0, None)
        p = np.clip(n_(45, 35, seed + 3) - 1.0, 0, None)
        k = k * (1 - patch * p)
        return shade(col(*rgb), k)
    return f


def t_ashlar():        # sand limestone cladding, 0.6 x 0.3 m blocks (S = 2.4 m: 4 x 8)
    row = np.floor(VV * 8)
    off = (row % 2) * 0.125
    j = np.maximum(lines(VV, 8, 0.05), lines(UU + off, 4, 0.025))
    tone = 1 + 0.045 * np.sin(row * 17.3 + np.floor((UU + off) * 4) * 61.7)
    k = (1 + 0.04 * n_(12, 12, 711) + 0.03 * n_(2, 2, 712)) * tone * (1 - 0.2 * j)
    return shade(col(200, 180, 146), k)


def t_roofc():         # pale cement roof screed, 1 m tiles, dark water stains (S = 4 m)
    k = 1 + 0.03 * n_(60, 60, 721) + 0.03 * n_(3, 3, 722) - 0.1 * np.clip(n_(40, 40, 723) - 0.9, 0, None)
    k *= 1 - 0.12 * np.maximum(lines(UU, 4, 0.01), lines(VV, 4, 0.01))
    return shade(col(178, 170, 156), k)


def t_pave():          # concrete pavers 0.5 m (S = 2 m)
    k = 1 + 0.03 * n_(30, 30, 731) + 0.03 * n_(2, 2, 732)
    tone = 1 + 0.035 * np.sin(np.floor(UU * 4) * 12.1 + np.floor(VV * 4) * 47.3)
    k *= tone * (1 - 0.25 * np.maximum(lines(UU, 4, 0.02), lines(VV, 4, 0.02)))
    return shade(col(170, 162, 146), k)


def t_asph():          # worn asphalt drive (S = 4 m)
    k = 1 + 0.06 * n_(2, 2, 741) + 0.04 * n_(20, 20, 742)
    return shade(col(78, 78, 76), k)


def t_wglass():        # window glass seen from outside: dark blue-grey, slight sky sheen (S = 2 m)
    k = 1 + 0.05 * n_(60, 20, 751) + 0.12 * (VV - 0.5)
    return shade(col(56, 66, 76), k)


def t_ribbon():        # hospital ribbon glazing: mullions every 1.5 m (S = 3 m, 2 mullions per tile)
    m = lines(UU, 2, 0.025)
    g = shade(col(66, 82, 92), 1 + 0.08 * (VV - 0.5) + 0.04 * n_(60, 20, 752))
    return np.where(m[..., None] > 0, col(196, 198, 194)[None, None], g)


def t_shutter(rgb, seed):   # louvred wooden / steel shutters (S = 1 m, 12 slats)
    def f():
        fr = frac(VV * 12)
        k = np.where(fr < 0.2, 0.72, 1.0 + 0.1 * fr) * (1 + 0.04 * n_(20, 4, seed) - 0.08 * np.clip(n_(3, 3, seed + 1) - 1.2, 0, None))
        return shade(col(*rgb), k)
    return f


def t_awning(rgb, seed):    # faded canvas awning with seams (S = 2 m)
    def f():
        k = (1 + 0.05 * n_(30, 6, seed) + 0.03 * n_(2, 2, seed + 1)) * (1 - 0.12 * lines(UU, 4, 0.01))
        return shade(col(*rgb), k)
    return f


def t_tankb():         # black polyethylene roof tank with moulded ribs (S = 1 m)
    k = (1 + 0.15 * (frac(VV * 6) < 0.15)) * (1 + 0.05 * n_(10, 10, 761))
    return shade(col(36, 36, 36), k)


def t_tankw():
    k = (1 - 0.12 * (frac(VV * 6) < 0.12)) * (1 + 0.03 * n_(10, 10, 762) - 0.06 * np.clip(n_(2, 30, 763), 0, None))
    return shade(col(214, 212, 204), k)


K.SURF.update({
    "plas_sand": (t_plas((214, 192, 156), 801), 3.0), "plas_beige": (t_plas((198, 180, 150), 811), 3.0),
    "plas_white": (t_plas((226, 220, 206), 821, streak=0.06), 3.0), "plas_dark": (t_plas((168, 150, 120), 831, 0.04), 3.0),
    "plas_ochre": (t_plas((206, 168, 112), 841), 3.0), "plas_rose": (t_plas((206, 170, 150), 851), 3.0),
    "trim": (t_plas((232, 228, 216), 861, streak=0.03, patch=0.0), 3.0),
    "ashlar": (t_ashlar, 2.4), "roofc": (t_roofc, 4.0), "pave": (t_pave, 2.0), "asph": (t_asph, 4.0),
    "wglass": (t_wglass, 2.0), "ribbon": (t_ribbon, 3.0),
    "shut_g": (t_shutter((92, 128, 104), 871), 1.0), "shut_b": (t_shutter((84, 118, 142), 873), 1.0),
    "shut_o": (t_shutter((176, 132, 74), 875), 1.0),
    "awn_t": (t_awning((86, 136, 132), 881), 2.0), "awn_s": (t_awning((196, 170, 120), 883), 2.0),
    "awn_r": (t_awning((168, 112, 84), 885), 2.0),
    "acc_teal": (K.t_flat((70, 132, 128), 0.04, 891), 2.0), "acc_blue": (K.t_flat((122, 150, 168), 0.04, 893), 2.0),
    "acc_terra": (K.t_flat((172, 108, 78), 0.04, 895), 2.0),
    "sign_green": (K.t_flat((24, 120, 84), 0.02, 897), 2.0), "sign_w": (K.t_flat((240, 240, 236), 0.0, 899), 2.0),
    "tank_b": (t_tankb, 1.0), "tank_w": (t_tankw, 1.0), "tank_bl": (K.t_flat((70, 110, 160), 0.04, 901), 1.0),
    "padg": (K.t_flat((86, 90, 90), 0.05, 903), 3.0), "dishw": (K.t_flat((220, 220, 214), 0.02, 905), 1.0),
    "bark2": (K.t_flat((98, 84, 66), 0.06, 907), 1.0),
})
K.DOUBLE_SIDED.update({"dishw"})


# ====================================================================== facade helpers
class Face:
    """Wall plane of a block. axis 'y': plane y = c, u = x; axis 'x': plane x = c, u = y. sg = outward sign."""

    def __init__(self, axis, c, sg):
        self.ax, self.c, self.sg = axis, c, sg

    def span(self, P, m, u0, u1, n0, n1, z0, z1, bottom=False):
        a, b = sorted((self.c + self.sg * n0, self.c + self.sg * n1))
        u0, u1 = sorted((u0, u1))
        if self.ax == "y":
            P.span(m, u0, u1, a, b, z0, z1, bottom=bottom)
        else:
            P.span(m, a, b, u0, u1, z0, z1, bottom=bottom)

    def pt(self, u, n, z):
        return (u, self.c + self.sg * n, z) if self.ax == "y" else (self.c + self.sg * n, u, z)


def faces(x0, x1, y0, y1):
    return {"front": Face("y", y0, -1), "back": Face("y", y1, 1), "left": Face("x", x0, -1), "right": Face("x", x1, 1)}


def block(P, wall, roof, x0, x1, y0, y1, z1, z0=SUB):
    """Four outward wall quads + a roof quad (no hidden faces -> no wasted atlas space)."""
    P.quad(wall, [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)])
    P.quad(wall, [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)])
    P.quad(wall, [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)])
    P.quad(wall, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)])
    if roof:
        P.quad(roof, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])


def ring(P, m, x0, x1, y0, y1, z0, z1, o=0.06):
    """Thin band around a block (floor slab edges, plinths, cornices), only on the outside."""
    P.span(m, x0 - o, x1 + o, y0 - o, y0, z0, z1)
    P.span(m, x0 - o, x1 + o, y1, y1 + o, z0, z1)
    P.span(m, x0 - o, x0, y0, y1, z0, z1)
    P.span(m, x1, x1 + o, y0, y1, z0, z1)


def parapet(P, m, x0, x1, y0, y1, z, h=0.6, t=0.22, cap="trim", sides="fblr"):
    """Low roof parapet on top of the block edge (z = roof level) with a coping cap."""
    # side runs stop at the front/back runs so no two boxes overlap (overlaps trap AO -> black specks)
    rects = {"f": (x0, x1, y0, y0 + t), "b": (x0, x1, y1 - t, y1), "l": (x0, x0 + t, y0 + t, y1 - t),
             "r": (x1 - t, x1, y0 + t, y1 - t)}
    for s in sides:
        a0, a1, b0, b1 = rects[s]
        P.span(m, a0, a1, b0, b1, z, z + h)
        if s in "fb":
            P.span(cap, a0 - 0.04, a1 + 0.04, b0 - 0.04, b1 + 0.04, z + h, z + h + 0.07)
        else:
            P.span(cap, a0 - 0.04, a1 + 0.04, b0 + 0.04, b1 - 0.04, z + h, z + h + 0.07)


def window(P, f, u, z0, w, h, glass="wglass", frame="trim", shutter=None, sill=True, bars=0, hood=False, n0=0.0):
    """n0: wall-surface offset (use the thickness of a cladding band the window sits on)."""
    f.span(P, frame, u - w / 2 - 0.1, u + w / 2 + 0.1, n0, n0 + 0.05, z0 - 0.1, z0 + h + 0.1)
    f.span(P, glass, u - w / 2, u + w / 2, n0 + 0.05, n0 + 0.06, z0, z0 + h)
    if sill:
        f.span(P, frame, u - w / 2 - 0.16, u + w / 2 + 0.16, n0, n0 + 0.15, z0 - 0.17, z0 - 0.08)
    if shutter:
        f.span(P, shutter, u - w - 0.12, u - w / 2 - 0.12, n0, n0 + 0.05, z0, z0 + h)
        f.span(P, shutter, u + w / 2 + 0.12, u + w + 0.12, n0, n0 + 0.05, z0, z0 + h)
    for k in range(bars):
        uu = u - w / 2 + (k + 1) * w / (bars + 1)
        f.span(P, "metal", uu - 0.018, uu + 0.018, n0 + 0.07, n0 + 0.1, z0, z0 + h)
    if hood:
        f.span(P, frame, u - w / 2 - 0.2, u + w / 2 + 0.2, n0, n0 + 0.3, z0 + h + 0.12, z0 + h + 0.24)


def door(P, f, u, w, h, leaf="door", frame="trim", step=True, hood=0.0, z0=0.0, n0=0.0):
    f.span(P, frame, u - w / 2 - 0.12, u + w / 2 + 0.12, n0, n0 + 0.06, z0, z0 + h + 0.12)
    f.span(P, leaf, u - w / 2, u + w / 2, n0 + 0.06, n0 + 0.08, z0 + (0.15 if step else 0), z0 + h)
    if step:
        f.span(P, frame, u - w / 2 - 0.3, u + w / 2 + 0.3, n0, n0 + 0.5, z0 - 0.1, z0 + 0.15)
    if hood:
        f.span(P, frame, u - w / 2 - 0.35, u + w / 2 + 0.35, n0, n0 + hood, z0 + h + 0.25, z0 + h + 0.38)


def balcony(P, f, u0, u1, z, depth, rail="plas_white", metal=False, slab="trim"):
    """Cantilever balcony slab at floor level z, with a solid balustrade or a metal railing."""
    f.span(P, slab, u0, u1, 0, depth, z - 0.18, z + 0.02)
    if metal:
        f.span(P, "metal", u0, u1, depth - 0.06, depth, z + 0.95, z + 1.0)
        f.span(P, "metal", u0, u0 + 0.05, 0, depth, z + 0.95, z + 1.0)
        f.span(P, "metal", u1 - 0.05, u1, 0, depth, z + 0.95, z + 1.0)
        n = max(2, int((u1 - u0) / 0.45))
        for k in range(n + 1):
            uu = u0 + 0.03 + k * (u1 - u0 - 0.06) / n
            f.span(P, "metal", uu - 0.02, uu + 0.02, depth - 0.05, depth - 0.01, z + 0.02, z + 0.95)
        for s in (u0 + 0.025, u1 - 0.025):
            for nn in (depth * 0.5,):
                f.span(P, "metal", s - 0.02, s + 0.02, nn - 0.02, nn + 0.02, z + 0.02, z + 0.95)
    else:
        f.span(P, rail, u0, u1, depth - 0.12, depth, z + 0.02, z + 1.0)
        f.span(P, rail, u0, u0 + 0.12, 0, depth - 0.12, z + 0.02, z + 1.0)
        f.span(P, rail, u1 - 0.12, u1, 0, depth - 0.12, z + 0.02, z + 1.0)
        f.span(P, "trim", u0 - 0.03, u1 + 0.03, depth - 0.15, depth + 0.03, z + 1.0, z + 1.06)


def awning(P, f, u0, u1, z, depth, m, drop=0.45):
    """Sloped fabric awning (closed thin prism) projecting from a wall."""
    pts = [(0.0, z), (depth, z - drop), (depth, z - drop - 0.06), (0.0, z - 0.06)]
    if f.ax == "y":
        P.prism(m, [(f.c + f.sg * n, zz) for n, zz in pts], "x", u0, u1)
    else:
        P.prism(m, [(f.c + f.sg * n, zz) for n, zz in pts], "y", u0, u1)


def tank(P, x, y, z, r=0.5, h=1.0, m="tank_w", stand=0.6):
    if stand:
        for dx in (-1, 1):
            for dy in (-1, 1):
                P.span("metal", x + dx * r * 0.7 - 0.03, x + dx * r * 0.7 + 0.03, y + dy * r * 0.7 - 0.03,
                       y + dy * r * 0.7 + 0.03, z, z + stand)
        P.span("metal", x - r * 0.8, x + r * 0.8, y - r * 0.8, y + r * 0.8, z + stand - 0.06, z + stand)
    P.cyl(m, (x, y, z + stand + h / 2), r, h, seg=12)
    P.cyl(m, (x, y, z + stand + h + 0.05), r * 0.35, 0.1, seg=8)


def solar_heater(P, x, y, z, ang=0.0):
    """Thermosiphon solar water heater: tilted collector + horizontal tank on a frame (faces -Y before rotation)."""
    R = Euler((0, 0, ang)).to_matrix()

    def T(p):
        q = R @ V(p)
        return (x + q.x, y + q.y, z + q.z)
    P.box("ribbon", T((0, 0, 0.55)), (1.8, 1.6, 0.06), rot=(-0.6, 0, ang))
    P.cyl("tank_w", T((0, 0.75, 1.15)), 0.24, 1.8, rot=(0, PI / 2, ang), seg=10)
    for sx in (-0.8, 0.8):
        P.strut("metal", T((sx, 0.7, 0.0)), T((sx, 0.7, 1.0)), 0.025, seg=4)
        P.strut("metal", T((sx, -0.6, 0.0)), T((sx, -0.6, 0.15)), 0.025, seg=4)


def dish(P, x, y, z, r=0.45, ang=0.0, mast=0.7):
    """Small satellite dish on a short mast, aimed horizontally at `ang` (rad, 0 = -Y) and tilted up ~35 deg."""
    P.strut("metal", (x, y, z), (x, y, z + mast), 0.03, seg=5)
    M = Matrix.Translation((x, y, z + mast)) @ Euler((0, 0, ang)).to_matrix().to_4x4() @ \
        Euler((-math.radians(90 - 35), 0, 0)).to_matrix().to_4x4()
    P.lathe("dishw", [(0.0, 0.0), (r * 0.5, 0.03), (r, 0.12)], M=M, seg=12)
    tip = M @ V((0, 0, r * 0.9))
    P.strut("metal", tuple(M @ V((0, -r * 0.8, 0.1))), tuple(tip), 0.012, seg=4)
    P.box("dark", tuple(tip), (0.07, 0.07, 0.1))


def ac_unit(P, f, u, z, n0=0.0):
    """Split air-conditioner outdoor unit hung on a wall (or standing on a roof when f is None)."""
    f.span(P, "hvac", u - 0.42, u + 0.42, n0, n0 + 0.3, z, z + 0.58)
    f.span(P, "dark", u - 0.3 + 0.12, u + 0.3 - 0.02, n0 + 0.3, n0 + 0.32, z + 0.08, z + 0.5)
    if n0 == 0.0:
        f.span(P, "metal", u - 0.38, u - 0.34, 0, 0.34, z - 0.12, z)
        f.span(P, "metal", u + 0.34, u + 0.38, 0, 0.34, z - 0.12, z)


def roof_ac(P, x, y, z, ang_face="y-"):
    P.span("metal", x - 0.5, x + 0.5, y - 0.22, y + 0.22, z, z + 0.08)
    P.span("hvac", x - 0.42, x + 0.42, y - 0.16, y + 0.16, z + 0.08, z + 0.66)
    P.span("dark", x - 0.2, x + 0.34, y - 0.18, y - 0.16, z + 0.16, z + 0.58)


def antenna(P, x, y, z, h=2.2):
    P.strut("metal", (x, y, z), (x, y, z + h), 0.025, seg=4)
    for k, w in enumerate((0.7, 0.55, 0.4)):
        zz = z + h - 0.15 - k * 0.3
        P.strut("metal", (x - w / 2, y, zz), (x + w / 2, y, zz), 0.012, seg=3)


def spout(P, f, u, z):
    f.span(P, "metal", u - 0.05, u + 0.05, 0, 0.35, z - 0.08, z)


def tree(P, x, y, h=4.0, r=1.6, seed=0):
    C.trunk(P, "bark2", (x, y, -0.2), (x + 0.2, y + 0.1, h * 0.6), 0.14, 0.09, seg=7, rings=4, bend=(0.2, 0.1), seed=seed)
    for k, (dx, dy, dz, rr) in enumerate(((0, 0, 0.75, 1.0), (0.6, 0.3, 0.6, 0.7), (-0.5, -0.4, 0.55, 0.7), (0.1, -0.6, 0.9, 0.6))):
        C.blob(P, "shrub", (x + 0.2 + dx * r * 0.6, y + 0.1 + dy * r * 0.6, h * dz + 0.6), r * rr * 0.75, seed + k, squash=0.75, subdiv=1)


def planter(P, x0, x1, y0, y1, seed=0):
    P.span("trim", x0, x1, y0, y1, 0.0, 0.55)
    P.span("earth", x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 0.1, 0.55, 0.58)
    n = max(1, int((x1 - x0 + y1 - y0) / 1.6))
    for k in range(n):
        t = (k + 0.5) / n
        cx = x0 + (x1 - x0) * (t if x1 - x0 >= y1 - y0 else 0.5)
        cy = y0 + (y1 - y0) * (t if y1 - y0 > x1 - x0 else 0.5)
        C.blob(P, "shrub", (cx, cy, 0.85), 0.45, seed + k, squash=0.7, subdiv=1)


def ring_marking(P, m, cx, cy, z, r0, r1, seg=40):
    """Flat painted annulus (upward normals) - helipad circle."""
    bm = P.bm(m)
    inner = [bm.verts.new((cx + r0 * math.cos(2 * PI * k / seg), cy + r0 * math.sin(2 * PI * k / seg), z)) for k in range(seg)]
    outer = [bm.verts.new((cx + r1 * math.cos(2 * PI * k / seg), cy + r1 * math.sin(2 * PI * k / seg), z)) for k in range(seg)]
    for k in range(seg):
        k1 = (k + 1) % seg
        bm.faces.new((inner[k], outer[k], outer[k1], inner[k1]))


def h_glyph(f, P, m, u, z, size, n0, n1):
    """Plain block letter 'H' (two posts + bar) on a wall-facing face; size = letter height."""
    s = size; w = s * 0.18
    f.span(P, m, u - s * 0.36, u - s * 0.36 + w, n0, n1, z - s / 2, z + s / 2)
    f.span(P, m, u + s * 0.36 - w, u + s * 0.36, n0, n1, z - s / 2, z + s / 2)
    f.span(P, m, u - s * 0.36 + w - 0.01, u + s * 0.36 - w + 0.01, n0, n1, z - w / 2, z + w / 2)


def h_sign(P, f, u, zc, size, n0=0.0, frame=True):
    """Green square panel with a white 'H' on face f (outward). Medical sign - deliberately NOT a protected emblem."""
    hs = size / 2
    if frame:
        f.span(P, "metal", u - hs - 0.06, u + hs + 0.06, n0, n0 + 0.1, zc - hs - 0.06, zc + hs + 0.06)
    f.span(P, "sign_green", u - hs, u + hs, n0 + 0.1, n0 + 0.14, zc - hs, zc + hs)
    h_glyph(f, P, "sign_w", u, zc, size * 0.62, n0 + 0.14, n0 + 0.16)


class Ports:
    def __init__(self, kit):
        self.kit, self.n = kit, 0

    def add(self, p):
        self.n += 1
        self.kit.empty(f"Port{self.n}", p)

    def at(self, f, u, z, out=0.3):
        self.add(f.pt(u, out, z))


# ====================================================================== buildings
def civ_house_a(kit, P):
    """10 x 9 m single-storey house: sand plaster, low parapet, door with hood, 4 windows, roof water tank."""
    X0, X1, Y0, Y1, H = -4.6, 4.6, -2.9, 4.1, 3.3
    block(P, "plas_sand", "roofc", X0, X1, Y0, Y1, H)
    ring(P, "plas_dark", X0, X1, Y0, Y1, SUB, 0.45, o=0.04)
    ring(P, "trim", X0, X1, Y0, Y1, H - 0.2, H, o=0.05)
    parapet(P, "plas_sand", X0, X1, Y0, Y1, H, h=0.55)
    F = faces(X0, X1, Y0, Y1)
    door(P, F["front"], -0.9, 1.0, 2.2, leaf="doorb", hood=0.7)
    window(P, F["front"], -3.1, 1.0, 1.2, 1.3, shutter="shut_g")
    window(P, F["front"], 2.4, 1.0, 1.4, 1.3, shutter="shut_g")
    window(P, F["right"], 0.8, 1.1, 1.0, 1.2, bars=3)
    window(P, F["left"], 1.6, 1.1, 1.0, 1.2, bars=3)
    window(P, F["back"], -2.0, 1.4, 0.8, 0.9, bars=2)
    window(P, F["back"], 2.6, 1.4, 0.8, 0.9, bars=2)
    ac_unit(P, F["right"], -1.6, 2.2)
    for u in (-4.0, 4.0):
        spout(P, F["back"], u, H + 0.05)
    spout(P, F["left"], -1.0, H + 0.05)
    # front terrace + path
    P.span("pave", X0 + 0.4, 1.4, -4.3, Y0, -0.1, 0.12)
    P.span("trim", X0 + 0.3, 1.5, -4.4, -4.3, -0.1, 0.18)
    P.span("trim", X0 + 0.3, X0 + 0.4, -4.3, Y0, -0.1, 0.18)
    P.span("trim", 1.4, 1.5, -4.3, Y0, -0.1, 0.18)
    planter(P, -4.1, -2.8, -4.2, -3.6, seed=11)
    # roof: tank on stand, solar-less house: AC unit, antenna, roof hatch
    tank(P, -3.2, 3.0, H, r=0.55, h=1.1, m="tank_b", stand=0.8)
    tank(P, -2.0, 3.2, H, r=0.42, h=0.9, m="tank_w", stand=0.8)
    roof_ac(P, 2.4, 2.8, H)
    antenna(P, 3.6, 3.6, H, 2.4)
    P.span("trim", 0.2, 1.2, 0.6, 1.6, H, H + 0.35)
    P.span("metal", 0.25, 1.15, 0.65, 1.55, H + 0.35, H + 0.4)
    D = (-0.9, -5.1, 0.0)
    ports = [(F["front"], -3.1, 1.65), (F["front"], 2.4, 1.65), (F["right"], 0.8, 1.7), (F["left"], 1.6, 1.7),
             (F["back"], -2.0, 1.85), (F["back"], 2.6, 1.85)]
    roof = [(X0 + 0.5, Y0 + 0.3, H + 0.85), (X1 - 0.5, Y1 - 0.3, H + 0.85)]
    return D, ports, roof, None


def civ_house_b(kit, P):
    """12 x 10 m two-storey house: beige plaster, roof stair hut, walled courtyard on the east side, front balcony."""
    X0, X1, Y0, Y1 = -6.0, 2.6, -3.9, 5.0
    F1, H = 3.2, 6.4
    block(P, "plas_beige", "roofc", X0, X1, Y0, Y1, H)
    ring(P, "plas_dark", X0, X1, Y0, Y1, SUB, 0.45, o=0.04)
    ring(P, "trim", X0, X1, Y0, Y1, F1 - 0.12, F1 + 0.08, o=0.06)
    ring(P, "acc_terra", X0, X1, Y0, Y1, H - 0.25, H, o=0.04)
    parapet(P, "plas_beige", X0, X1, Y0, Y1, H, h=0.65)
    F = faces(X0, X1, Y0, Y1)
    # front: ground door + 2 windows; upper balcony (French door + window) and one more window
    door(P, F["front"], 0.9, 1.1, 2.3, leaf="doorb", hood=0.8)
    window(P, F["front"], -4.6, 1.0, 1.2, 1.3, bars=3)
    window(P, F["front"], -2.2, 1.0, 1.2, 1.3, bars=3)
    balcony(P, F["front"], -5.2, -0.6, F1, 1.0, metal=True)
    door(P, F["front"], -3.9, 0.9, 2.2, leaf="wglass", step=False, z0=F1 + 0.02)
    window(P, F["front"], -1.8, F1 + 1.0, 1.0, 1.3, shutter="shut_o")
    window(P, F["front"], 1.4, F1 + 1.0, 1.2, 1.3, shutter="shut_o")
    awning(P, F["front"], -5.2, -0.6, F1 + 2.75, 1.05, "awn_s")
    # left (west) side
    for u in (-1.8, 2.6):
        window(P, F["left"], u, 1.1, 1.0, 1.2, bars=3)
        window(P, F["left"], u, F1 + 1.1, 1.0, 1.2, shutter="shut_o")
    # rear
    for u in (-4.0, -0.5):
        window(P, F["back"], u, 1.3, 0.9, 1.0, bars=2)
        window(P, F["back"], u, F1 + 1.1, 1.0, 1.2, shutter="shut_o")
    # courtyard side (east): door into the courtyard + windows
    door(P, F["right"], 2.8, 0.9, 2.2, leaf="door")
    window(P, F["right"], -1.2, 1.1, 1.0, 1.2, bars=3)
    window(P, F["right"], -1.2, F1 + 1.1, 1.0, 1.2, shutter="shut_o")
    window(P, F["right"], 2.8, F1 + 1.1, 1.0, 1.2, shutter="shut_o")
    ac_unit(P, F["back"], 1.4, F1 + 1.2)
    ac_unit(P, F["left"], 0.4, F1 + 2.2)
    spout(P, F["back"], -5.5, H + 0.05); spout(P, F["right"], 4.6, H + 0.05)
    # roof stair hut (door faces the roof's open side, -Y), tanks, solar heater, dish
    SX0, SX1, SY0, SY1, SH = -5.6, -3.0, 2.2, 4.6, H + 2.5
    block(P, "plas_beige", "roofc", SX0, SX1, SY0, SY1, SH, z0=H)
    ring(P, "trim", SX0, SX1, SY0, SY1, SH - 0.15, SH + 0.05, o=0.06)
    door(P, Face("y", SY0, -1), -4.3, 0.9, 2.05, leaf="door", step=False, z0=H, hood=0.5)
    window(P, Face("x", SX1, 1), 3.4, H + 1.2, 0.6, 0.6, sill=False)
    tank(P, -5.0, 3.6, SH, r=0.5, h=1.0, m="tank_w", stand=0.0)
    tank(P, -3.7, 3.6, SH, r=0.45, h=0.9, m="tank_b", stand=0.0)
    solar_heater(P, -0.6, 3.4, H)
    dish(P, 1.6, -2.8, H, r=0.42, ang=0.0)
    roof_ac(P, 1.2, 1.2, H)
    # courtyard: walls with coping, gate, paving, tree, bench
    CX0, CX1, CY0, CY1, WH, T = X1, 6.0, -5.0, 5.0, 2.2, 0.25
    for (a0, a1, b0, b1) in ((CX1 - T, CX1, CY0, CY1), (CX0, CX1, CY1 - T, CY1), (CX0, 3.5, CY0, CY0 + T),
                             (5.2, CX1, CY0, CY0 + T), (CX0, CX0 + T, CY0, Y0)):
        P.span("plas_beige", a0, a1, b0, b1, SUB, WH)
        P.span("trim", a0 - 0.04, a1 + 0.04, b0 - 0.04, b1 + 0.04, WH, WH + 0.08)
    for x in (3.5, 5.2):
        P.span("plas_dark", x - 0.18, x + 0.18, CY0 - 0.05, CY0 + 0.3, SUB, WH + 0.35)
        P.span("trim", x - 0.22, x + 0.22, CY0 - 0.09, CY0 + 0.34, WH + 0.35, WH + 0.43)
    P.span("shut_g", 3.68, 5.02, CY0 + 0.08, CY0 + 0.14, 0.05, 2.1, bottom=True)          # closed steel gate
    P.span("pave", CX0, CX1 - T, CY0 + T, CY1 - T, -0.1, 0.04)
    tree(P, 4.9, 3.4, h=4.2, r=1.7, seed=21)
    P.span("woodold", 4.9, 5.6, -1.6, 0.4, 0.0, 0.45)
    P.span("trim", -5.8, -4.2, -4.9, Y0, -0.1, 0.12)
    D = (4.35, -5.6, 0.0)                               # outside the courtyard gate
    ports = [(F["front"], -2.2, 1.65), (F["front"], -3.9, F1 + 1.2), (F["front"], 1.4, F1 + 1.65),
             (F["left"], -1.8, F1 + 1.7), (F["left"], 2.6, 1.7), (F["back"], -4.0, F1 + 1.7), (F["back"], -0.5, 1.8),
             (F["right"], -1.2, F1 + 1.7)]
    roof = [(X0 + 0.5, Y0 + 0.3, H + 0.95), (X1 - 0.4, Y1 - 0.3, H + 0.95)]
    return D, ports, roof, None


def civ_apartment(kit, P):
    """18 x 12 m four-storey apartment block: shops on the ground floor, balconies, busy roof."""
    X0, X1, Y0, Y1 = -8.8, 8.8, -4.8, 5.8
    LV = [0.0, 3.6, 6.7, 9.8]; H = 12.9
    block(P, "plas_white", "roofc", X0, X1, Y0, Y1, H)
    P.span("plas_beige", X0 - 0.04, X1 + 0.04, Y0 - 0.04, Y0, SUB, LV[1])                 # ground floor band, front
    P.span("plas_beige", X0 - 0.04, X0, Y0, Y1, SUB, LV[1])
    P.span("plas_beige", X1, X1 + 0.04, Y0, Y1, SUB, LV[1])
    P.span("plas_beige", X0 - 0.04, X1 + 0.04, Y1, Y1 + 0.04, SUB, LV[1])
    for z in LV[1:]:
        ring(P, "trim", X0, X1, Y0, Y1, z - 0.12, z + 0.08, o=0.08)
    ring(P, "acc_blue", X0, X1, Y0, Y1, H - 0.3, H, o=0.06)
    parapet(P, "plas_white", X0, X1, Y0, Y1, H, h=0.8)
    F = faces(X0, X1, Y0, Y1)
    f = F["front"]
    # ground floor: three shop fronts with roller shutters + blank colour fascias (no text), central entrance
    for (u0, u1, fas) in ((-8.2, -5.0, "acc_teal"), (-4.4, -1.4, "acc_terra"), (2.2, 5.4, "acc_blue"), (5.9, 8.2, "awn_s")):
        f.span(P, "trim", u0 - 0.12, u1 + 0.12, 0.04, 0.1, 0.0, 3.0)
        f.span(P, "door", u0, u1, 0.1, 0.12, 0.05, 2.7)
        f.span(P, fas, u0, u1, 0.1, 0.16, 2.75, 3.25)
    door(P, f, 0.4, 1.4, 2.6, leaf="glass", hood=1.1, n0=0.04)
    awning(P, f, -8.2, -5.0, 3.45, 1.0, "awn_t")
    # upper floors front: two balconies per floor + stairwell slot windows + end windows
    rail = ["plas_white", "acc_blue", "plas_white"]
    for i, z in enumerate(LV[1:]):
        for (u0, u1) in ((-7.0, -2.6), (2.6, 7.0)):
            balcony(P, f, u0, u1, z, 1.15, rail=rail[i], metal=(i == 1))
            door(P, f, (u0 + u1) / 2 - 0.9, 0.9, 2.2, leaf="wglass", step=False, z0=z + 0.02)
            window(P, f, (u0 + u1) / 2 + 0.8, z + 0.9, 1.2, 1.3, sill=False)
        window(P, f, 0.4, z + 1.6, 0.6, 1.0, sill=False)
        window(P, f, -8.1, z + 0.9, 0.8, 1.3, shutter=None, bars=2)
        window(P, f, 8.1, z + 0.9, 0.8, 1.3, shutter=None, bars=2)
    awning(P, f, 2.6, 7.0, LV[3] + 2.7, 1.2, "awn_r")
    awning(P, f, -7.0, -2.6, LV[2] + 2.7, 1.2, "awn_s")
    # rear: 5 windows per floor (bars on the ground floor), service door
    for z in LV:
        for u in (-7.0, -3.6, 0.0, 3.6, 7.0):
            if z == 0 and u == 0.0:
                door(P, F["back"], u, 1.0, 2.2, leaf="door", n0=0.04)
                continue
            window(P, F["back"], u, z + 1.0, 1.2, 1.3, bars=(3 if z == 0 else 0),
                   shutter=("shut_b" if (z > 0 and (u + z) % 2 < 1) else None), n0=(0.04 if z == 0 else 0.0))
    for u in (-5.2, 1.8, 5.4):
        ac_unit(P, F["back"], u, LV[2] + 2.2)
    ac_unit(P, F["back"], -1.8, LV[3] + 2.2)
    # sides: 2 windows per floor
    for side in ("left", "right"):
        for z in LV:
            for u in (-2.0, 2.8):
                window(P, F[side], u, z + 1.0, 1.0, 1.3, bars=(3 if z == 0 else 0),
                       shutter=("shut_b" if z > 0 else None), n0=(0.04 if z == 0 else 0.0))
        ac_unit(P, F[side], 0.4, LV[1] + 2.2)
    # roof: stair / lift hut, tanks on a steel rack, solar heaters, dishes, AC units, antenna
    SX0, SX1, SY0, SY1, SH = -1.6, 1.8, 1.6, 4.8, H + 2.7
    block(P, "plas_white", "roofc", SX0, SX1, SY0, SY1, SH, z0=H)
    ring(P, "acc_blue", SX0, SX1, SY0, SY1, SH - 0.2, SH, o=0.05)
    door(P, Face("y", SY0, -1), 0.0, 0.9, 2.1, leaf="door", step=False, z0=H, hood=0.5)
    P.span("metal", -7.6, -2.6, 3.4, 4.9, H, H + 0.7)
    for k, (x, m) in enumerate(((-7.0, "tank_w"), (-5.8, "tank_b"), (-4.6, "tank_w"), (-3.4, "tank_bl"))):
        tank(P, x, 4.15, H + 0.7, r=0.5, h=1.0, m=m, stand=0.0)
    tank(P, 3.0, 4.6, H, r=0.55, h=1.1, m="tank_b", stand=0.5)
    tank(P, 4.3, 4.6, H, r=0.55, h=1.1, m="tank_w", stand=0.5)
    solar_heater(P, 6.4, 3.6, H)
    solar_heater(P, -6.2, 0.6, H)
    dish(P, -3.2, -3.8, H, r=0.5, ang=0.3)
    dish(P, 3.6, -3.9, H, r=0.45, ang=-0.2)
    dish(P, 7.8, -0.5, H, r=0.4, ang=0.1)
    for (x, y) in ((-1.0, -1.2), (0.4, -1.2), (2.6, 0.8), (5.0, -2.0)):
        roof_ac(P, x, y, H)
    antenna(P, 1.2, 4.2, SH, 2.6)
    D = (0.4, -5.6, 0.0)
    ports = [(f, -4.8, LV[1] + 1.4, 0.9), (f, 4.8, LV[2] + 1.4, 0.9), (f, -4.8, LV[3] + 1.4, 0.9),
             (F["back"], -7.0, LV[2] + 1.65), (F["back"], 0.0, LV[1] + 1.65), (F["back"], 7.0, LV[3] + 1.65),
             (F["left"], -2.0, LV[1] + 1.65), (F["left"], 2.8, LV[3] + 1.65),
             (F["right"], 2.8, LV[1] + 1.65), (F["right"], -2.0, LV[3] + 1.65)]
    roof = [(X0 + 0.5, Y0 + 0.3, H + 1.2), (X1 - 0.5, Y1 - 0.3, H + 1.2)]
    return D, ports, roof, None


def civ_center(kit, P):
    """22 x 16 m community centre: two storeys, stone-clad ground floor, glazed entrance with a canopy,
    a bare flagpole (no flag) and a monument sign board with an abstract emblem only (no text)."""
    X0, X1, Y0, Y1 = -10.2, 10.2, -3.2, 7.6
    F1, H = 4.2, 8.0
    block(P, "plas_white", "roofc", X0, X1, Y0, Y1, H)
    ring(P, "ashlar", X0, X1, Y0, Y1, SUB, F1, o=0.06)
    ring(P, "trim", X0, X1, Y0, Y1, F1 - 0.05, F1 + 0.25, o=0.12)
    ring(P, "acc_teal", X0, X1, Y0, Y1, H - 0.35, H, o=0.05)
    parapet(P, "plas_white", X0, X1, Y0, Y1, H, h=0.6)
    F = faces(X0, X1, Y0, Y1)
    f = F["front"]
    # entrance bay: full-height glazed projection
    EX0, EX1, EY0 = -3.6, 3.6, -4.3
    block(P, "glass", "roofc", EX0, EX1, EY0, Y0, H + 0.6)
    for x in (EX0, EX1):
        P.span("trim", x - 0.2, x + 0.2, EY0 - 0.1, Y0, SUB, H + 0.8)
    P.span("trim", EX0 - 0.2, EX1 + 0.2, EY0 - 0.15, Y0, H + 0.6, H + 0.95)
    P.span("trim", EX0, EX1, EY0 - 0.08, EY0, F1 - 0.15, F1 + 0.15)
    door(P, Face("y", EY0, -1), 0.0, 2.6, 2.6, leaf="wglass", step=False)
    # canopy on four columns
    CY0 = -6.6
    P.span("trim", -5.0, 5.0, CY0, EY0, 3.5, 3.85)
    P.span("acc_teal", -5.05, 5.05, CY0 - 0.05, CY0 + 0.1, 3.45, 3.9)
    for x in (-4.6, 4.6):
        P.cyl("trim", (x, CY0 + 0.4, 1.75), 0.18, 3.5, seg=10)
    # blank fascia sign above the canopy (abstract emblem only)
    ef = Face("y", EY0, -1)
    ef.span(P, "acc_teal", -2.6, 2.6, 0.0, 0.12, 5.0, 6.4)
    P.cyl("sign_w", (-1.8, EY0 - 0.14, 5.7), 0.45, 0.06, rot=(PI / 2, 0, 0), seg=16)
    ef.span(P, "sign_w", -1.0, 2.2, 0.12, 0.15, 5.85, 6.0)
    ef.span(P, "sign_w", -1.0, 1.2, 0.12, 0.15, 5.45, 5.6)
    # front windows: tall ground floor + upper with sun-shade fins
    for u in (-8.6, -6.6, -4.8, 4.8, 6.6, 8.6):
        window(P, f, u, 0.9, 1.3, 2.4, frame="trim", n0=0.06)
        window(P, f, u, F1 + 1.0, 1.3, 1.8, frame="trim", sill=False, hood=True)
    for side in ("left", "right"):
        for u in (-1.2, 2.2, 5.6):
            window(P, F[side], u, 0.9, 1.3, 2.4, n0=0.06)
            window(P, F[side], u, F1 + 1.0, 1.3, 1.8, sill=False, hood=True)
    for u in (-8.0, -4.8, -1.6, 4.8, 8.0):
        window(P, F["back"], u, 1.0, 1.3, 1.8, bars=3, n0=0.06)
        window(P, F["back"], u, F1 + 1.0, 1.3, 1.8, sill=False, hood=True)
    door(P, F["back"], 1.6, 1.8, 2.4, leaf="door", hood=0.9, n0=0.06)
    # forecourt: paving, planters, benches, flagpole (bare), monument sign
    P.span("pave", -10.6, 10.6, -7.8, Y0, -0.1, 0.06)
    P.span("trim", -10.7, 10.7, -7.95, -7.8, -0.1, 0.16)
    planter(P, -9.6, -6.4, -6.9, -6.1, seed=31)
    planter(P, 6.4, 9.6, -2.9, -2.1, seed=35)
    for x in (-5.6, 5.6):
        P.span("woodold", x - 0.9, x + 0.9, -5.6, -5.2, 0.4, 0.48)
        for s in (-0.7, 0.7):
            P.span("metal", x + s - 0.04, x + s + 0.04, -5.55, -5.25, 0.0, 0.4)
    fx, fy = -7.8, -4.4
    P.span("ashlar", fx - 0.6, fx + 0.6, fy - 0.6, fy + 0.6, -0.1, 0.45)
    P.cyl("steel", (fx, fy, 0.45 + 4.8), 0.09, 9.6, seg=10, r2=0.05)
    P.cyl("steel", (fx, fy, 10.1), 0.11, 0.18, seg=10)
    P.strut("metal", (fx + 0.07, fy, 1.2), (fx + 0.07, fy, 9.9), 0.006, seg=3)       # halyard, no flag
    P.span("metal", fx + 0.08, fx + 0.14, fy - 0.03, fy + 0.03, 1.1, 1.3)
    sx, sy = 7.6, -6.2
    P.span("ashlar", sx - 1.8, sx + 1.8, sy - 0.3, sy + 0.3, -0.1, 0.6)
    P.span("acc_teal", sx - 1.6, sx + 1.6, sy - 0.12, sy + 0.12, 0.6, 1.9)
    P.span("trim", sx - 1.65, sx + 1.65, sy - 0.15, sy + 0.15, 1.9, 1.98)
    sf = Face("y", sy - 0.12, -1)
    P.cyl("sign_w", (sx - 1.0, sy - 0.14, 1.25), 0.38, 0.04, rot=(PI / 2, 0, 0), seg=16)
    P.cyl("acc_teal", (sx - 1.0, sy - 0.17, 1.25), 0.22, 0.04, rot=(PI / 2, 0, 0), seg=16)
    sf.span(P, "sign_w", sx - 0.4, sx + 1.3, 0.0, 0.03, 1.4, 1.52)
    sf.span(P, "sign_w", sx - 0.4, sx + 0.8, 0.0, 0.03, 1.0, 1.12)
    # roof: stair hut, large AC units, skylight, dish
    SX0, SX1, SY0, SY1, SH = 5.0, 8.2, 4.0, 7.0, H + 2.6
    block(P, "plas_white", "roofc", SX0, SX1, SY0, SY1, SH, z0=H)
    ring(P, "acc_teal", SX0, SX1, SY0, SY1, SH - 0.2, SH, o=0.05)
    door(P, Face("x", SX0, -1), 5.5, 0.9, 2.1, leaf="door", step=False, z0=H, hood=0.4)
    for (x, y) in ((-7.6, 4.6), (-5.4, 4.6), (-3.2, 4.6)):
        P.span("metal", x - 0.9, x + 0.9, y - 0.7, y + 0.7, H, H + 0.15)
        P.span("hvac", x - 0.8, x + 0.8, y - 0.6, y + 0.6, H + 0.15, H + 1.15)
        P.cyl("dark", (x, y, H + 1.17), 0.45, 0.04, seg=12)
    P.frustum("glass", -1.0, 2.6, 1.0, 4.6, H, H + 0.9, 0.5)
    dish(P, 8.6, 1.0, H, r=0.5, ang=-0.4)
    antenna(P, 7.4, 6.4, SH, 2.0)
    D = (0.0, -7.4, 0.0)
    ports = [(f, -8.6, F1 + 1.9), (f, -4.8, F1 + 1.9), (f, 6.6, F1 + 1.9), (f, 8.6, 2.1),
             (F["left"], -1.2, F1 + 1.9), (F["left"], 5.6, 2.1), (F["right"], 2.2, F1 + 1.9), (F["right"], -1.2, 2.1),
             (F["back"], -4.8, F1 + 1.9), (F["back"], 4.8, F1 + 1.9)]
    roof = [(X0 + 0.5, Y0 + 0.3, H + 0.9), (X1 - 0.5, Y1 - 0.3, H + 0.9)]
    return D, ports, roof, None


def civ_hospital(kit, P):
    """24 x 18 m three-storey hospital: ribbon windows, ambulance-bay canopy at the entrance, rooftop helipad with a
    white 'H' in a circle, white 'H' on green panels. No red cross / crescent / crystal anywhere."""
    X0, X1, Y0, Y1 = -11.8, 11.8, -4.0, 8.8
    LV = [0.0, 3.9, 7.5]; H = 11.1
    block(P, "plas_white", "roofc", X0, X1, Y0, Y1, H)
    ring(P, "plas_dark", X0, X1, Y0, Y1, SUB, 0.5, o=0.04)
    ring(P, "acc_blue", X0, X1, Y0, Y1, H - 0.45, H, o=0.06)
    parapet(P, "plas_white", X0, X1, Y0, Y1, H, h=0.7)
    F = faces(X0, X1, Y0, Y1)
    f = F["front"]

    def ribbon_band(face, u0, u1, z, hgt=1.5):
        face.span(P, "acc_blue", u0 - 0.15, u1 + 0.15, 0, 0.08, z - 0.45, z + hgt + 0.25)
        face.span(P, "ribbon", u0, u1, 0.08, 0.1, z, z + hgt)
        face.span(P, "trim", u0 - 0.2, u1 + 0.2, 0, 0.35, z + hgt + 0.25, z + hgt + 0.35)    # sun-shade ledge
    # stair core (front left) with a vertical slot window
    SCX0, SCX1 = -11.8, -8.6
    P.span("plas_beige", SCX0 - 0.02, SCX1, Y0 - 0.5, Y0, SUB, H + 1.0)
    P.span("trim", SCX0 - 0.06, SCX1 + 0.04, Y0 - 0.56, Y0, H + 1.0, H + 1.1)
    Face("y", Y0 - 0.5, -1).span(P, "wglass", -10.6, -9.8, 0.0, 0.03, 1.0, H - 3.2)
    # front: ground floor partly glazed lobby, upper floors ribbon windows
    for z in LV[1:]:
        ribbon_band(f, -8.0, 11.2, z + 0.95)
    ribbon_band(f, 6.0, 11.2, 0.95, hgt=1.6)
    ribbon_band(f, -8.0, -5.6, 0.95, hgt=1.6)
    for side in ("left", "right", "back"):
        u0, u1 = ((Y0 + 0.6, Y1 - 0.6) if side != "back" else (X0 + 0.6, X1 - 0.6))
        for z in LV:
            if side == "back" and z == 0:
                ribbon_band(F[side], u0, -2.0, z + 0.95)
                ribbon_band(F[side], 2.0, u1, z + 0.95)
            else:
                ribbon_band(F[side], u0, u1, z + 0.95)
    door(P, F["back"], 0.0, 2.6, 2.6, leaf="door", hood=1.0, n0=0.0)
    # entrance lobby: glazed box under the canopy
    LX0, LX1, LY0 = -5.0, 5.0, -5.4
    block(P, "glass", "roofc", LX0, LX1, LY0, Y0, 3.6)
    ring(P, "trim", LX0, LX1, LY0, Y0, 3.4, 3.7, o=0.08)
    P.span("trim", LX0 - 0.2, LX0, LY0 - 0.1, Y0, SUB, 3.7); P.span("trim", LX1, LX1 + 0.2, LY0 - 0.1, Y0, SUB, 3.7)
    door(P, Face("y", LY0, -1), 0.0, 2.8, 2.6, leaf="wglass", step=False)
    # ambulance bay canopy: slab cantilevered from the facade on two front columns; drive + drop-off kerb
    CY0 = -8.8
    P.span("trim", -7.0, 7.0, CY0, Y0, 4.4, 4.85)
    P.span("acc_blue", -7.05, 7.05, CY0 - 0.06, CY0 + 0.12, 4.35, 4.95)
    for x in (-6.4, 6.4):
        P.span("trim", x - 0.25, x + 0.25, CY0 + 0.3, CY0 + 0.8, -0.1, 4.4)
    for x in (-5.0, 0.0, 5.0):
        P.span("lamp", x - 0.6, x + 0.6, -7.0, -6.8, 4.36, 4.4, bottom=True)
    P.span("asph", -7.6, 7.6, -9.0, LY0, -0.1, 0.02)
    P.span("pave", -5.0, 5.0, -6.2, LY0, -0.1, 0.14)
    P.span("trim", -5.0, 5.0, -6.3, -6.2, -0.1, 0.16)
    P.span("pave", -11.9, -7.6, -9.0, Y0, -0.1, 0.06); P.span("pave", 7.6, 11.9, -9.0, Y0, -0.1, 0.06)
    for x in (-7.7, 7.7):
        P.span("trim", x - 0.1, x + 0.1, -9.0, Y0, -0.1, 0.16)
    for x in (-3.6, -1.2, 1.2, 3.6):                                                    # bollards
        P.cyl("metal", (x, -6.05, 0.5), 0.08, 0.7, seg=8)
    # medical marking: white H on green panels (canopy front, sign pylon, parapet sign)
    cf = Face("y", CY0 - 0.06, -1)
    h_sign(P, cf, 0.0, 5.6, 1.5, n0=-0.0, frame=True)
    px, py = 9.4, -7.6
    for dx in (-0.85, 0.85):
        P.span("metal", px + dx - 0.07, px + dx + 0.07, py - 0.07, py + 0.07, 0.0, 2.2)
    P.span("ashlar", px - 1.2, px + 1.2, py - 0.3, py + 0.3, -0.1, 0.35)
    h_sign(P, Face("y", py - 0.07, -1), px, 3.0, 1.7, n0=-0.07)
    h_sign(P, Face("y", py + 0.07, 1), px, 3.0, 1.7, n0=-0.07, frame=False)
    h_sign(P, f, -10.2, H - 1.8, 1.4, n0=0.5)                                          # on the stair core
    # roof: plant room, tanks, AC units, lift overrun; helipad on steel legs with an access stair
    PX0, PX1, PY0, PY1, PH = -11.0, -4.0, 3.4, 8.0, H + 2.6
    block(P, "plas_white", "roofc", PX0, PX1, PY0, PY1, PH, z0=H)
    ring(P, "acc_blue", PX0, PX1, PY0, PY1, PH - 0.25, PH, o=0.05)
    pf = Face("y", PY0, -1)
    for u in (-10.0, -8.4, -6.8):
        pf.span(P, "louvre", u - 0.6, u + 0.6, 0.0, 0.05, H + 0.6, H + 2.0)
    door(P, pf, -5.2, 1.0, 2.2, leaf="door", step=False, z0=H)
    for k, x in enumerate((-10.4, -9.0, -7.6)):
        tank(P, x, 1.6, H, r=0.6, h=1.3, m=("tank_w" if k != 1 else "tank_bl"), stand=0.4)
    for (x, y) in ((-10.0, -2.6), (-8.6, -2.6), (-7.2, -2.6), (-5.8, -2.6)):
        roof_ac(P, x, y, H)
    P.span("metal", -4.6, -2.2, -0.4, 1.8, H, H + 1.8)                                  # lift overrun
    dish(P, -3.0, -3.2, H, r=0.45, ang=0.2)
    HX, HY, HZ, HS = 4.6, 2.4, H + 1.2, 5.4
    for dx in (-HS + 0.8, 0.0, HS - 0.8):
        for dy in (-HS + 0.8, 0.0, HS - 0.8):
            P.span("metal", HX + dx - 0.12, HX + dx + 0.12, HY + dy - 0.12, HY + dy + 0.12, H, HZ - 0.25)
    P.span("metal", HX - HS + 0.4, HX + HS - 0.4, HY - HS + 0.4, HY + HS - 0.4, HZ - 0.3, HZ - 0.2)
    P.span("padg", HX - HS, HX + HS, HY - HS, HY + HS, HZ - 0.2, HZ)
    ring(P, "metal", HX - HS, HX + HS, HY - HS, HY + HS, HZ - 0.25, HZ + 0.05, o=0.08)
    ring_marking(P, "sign_w", HX, HY, HZ + 0.01, 3.9, 4.4, seg=40)
    hb = 3.0; hw = 0.62; hz = HZ + 0.012                                                 # 'H' (letter reads from the front)
    P.span("sign_w", HX - 1.1 - hw / 2, HX - 1.1 + hw / 2, HY - hb / 2, HY + hb / 2, hz - 0.01, hz)
    P.span("sign_w", HX + 1.1 - hw / 2, HX + 1.1 + hw / 2, HY - hb / 2, HY + hb / 2, hz - 0.01, hz)
    P.span("sign_w", HX - 1.1, HX + 1.1, HY - hw / 2, HY + hw / 2, hz - 0.01, hz)
    for k in range(8):                                                                    # perimeter lights
        a = 2 * PI * k / 8 + PI / 8
        P.cyl("lamp", (HX + (HS - 0.25) * math.cos(a) / max(abs(math.cos(a)), abs(math.sin(a))),
                       HY + (HS - 0.25) * math.sin(a) / max(abs(math.cos(a)), abs(math.sin(a))), HZ + 0.06), 0.09, 0.12, seg=6)
    # safety-net shelf on three sides, access stair from the roof on the west side
    NZ = HZ - 0.32
    P.span("grate", HX - HS, HX + HS + 0.6, HY - HS - 0.6, HY - HS, NZ, NZ + 0.05)
    P.span("grate", HX - HS, HX + HS + 0.6, HY + HS, HY + HS + 0.6, NZ, NZ + 0.05)
    P.span("grate", HX + HS, HX + HS + 0.6, HY - HS, HY + HS, NZ, NZ + 0.05)
    for k in range(6):
        z1 = H + 0.2 * (k + 1)
        x0 = HX - HS - 2.2 + k * 0.36
        P.span("grate", x0, x0 + 0.36, HY - 0.6, HY + 0.6, z1 - 0.06, z1)
        P.span("metal", x0, x0 + 0.36, HY - 0.66, HY - 0.6, H, z1)
        P.span("metal", x0, x0 + 0.36, HY + 0.6, HY + 0.66, H, z1)
    D = (0.0, -5.9, 0.0)
    heal = (0.0, -7.0, 0.0)
    ports = [(f, -6.8, LV[1] + 1.7, 0.4), (f, 2.0, LV[1] + 1.7, 0.4), (f, 9.0, LV[2] + 1.7, 0.4),
             (f, -4.0, LV[2] + 1.7, 0.4), (F["left"], 0.0, LV[1] + 1.7, 0.4), (F["left"], 5.6, LV[2] + 1.7, 0.4),
             (F["right"], 4.4, LV[1] + 1.7, 0.4), (F["right"], -1.2, LV[2] + 1.7, 0.4),
             (F["back"], -6.0, LV[1] + 1.7, 0.4), (F["back"], 6.0, LV[2] + 1.7, 0.4)]
    roof = [(X1 - 0.5, Y0 + 0.3, H + 1.0), (X0 + 4.0, Y1 - 0.3, H + 1.0)]
    return D, ports, roof, heal


BUILD = {"civ_house_a": civ_house_a, "civ_house_b": civ_house_b, "civ_apartment": civ_apartment,
         "civ_center": civ_center, "civ_hospital": civ_hospital}
PREFIX = {"civ_house_a": "CVA", "civ_house_b": "CVB", "civ_apartment": "CVP", "civ_center": "CVC", "civ_hospital": "CVH"}


def make(bid, root):
    out = os.path.join(root, bid)
    os.makedirs(out, exist_ok=True)
    kit = K.Kit(bid, PREFIX[bid], atlas=1024, ao_res=512, ao_dist=3.0)
    P = kit.part(bid)
    D, ports, roof, heal = BUILD[bid](kit, P)
    P.build()
    kit.empty("Door", D)
    pr = Ports(kit)
    for p in ports:
        f, u, z = p[:3]
        pr.at(f, u, z, out=(p[3] if len(p) > 3 else 0.3))
    for p in roof:
        pr.add(p)
    if heal is not None:
        kit.empty("Heal", heal)
    W, Dp = FOOT[bid]
    return kit.finish(out, bid + ".glb", ground_size=max(W, Dp) * 3)


# ====================================================================== review renders + contact sheet
def gltf_to_godot(p):
    return (round(p[0], 2), round(p[2], 2), round(-p[1], 2))


def inspect(glb):
    """Re-import the GLB; return (tris, {empty: blender xyz}, bbox, mesh names, material names)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    tris, emp, names, mats = 0, {}, [], set()
    lo = V((1e9, 1e9, 1e9)); hi = V((-1e9, -1e9, -1e9))
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            names.append(o.name)
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
            mats |= {m.name for m in o.data.materials if m}
            for v in o.data.vertices:
                w = o.matrix_world @ v.co
                lo = V((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z))); hi = V((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
        elif o.type == "EMPTY":
            emp[o.name] = tuple(o.matrix_world.translation)
        else:
            names.append(f"{o.name}<{o.type}>")
    return tris, emp, (tuple(lo), tuple(hi)), names, sorted(mats)


def render_views(glb, bid, tmp):
    from PIL import Image
    W, Dp = FOOT[bid]
    span = max(W, Dp)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=glb)
    hmax = max((o.matrix_world @ V(b)).z for o in scene.objects if o.type == "MESH" for b in o.bound_box)
    markers = []
    mk = {}
    for nm, rgb in (("port", (1.0, 0.15, 0.1)), ("door", (0.1, 1.0, 0.2)), ("heal", (0.1, 0.8, 1.0))):
        m = bpy.data.materials.new("mk_" + nm); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = 3.0
        mk[nm] = m
    for o in list(scene.objects):
        if o.type == "EMPTY" and (o.name.startswith("Port") or o.name in ("Door", "Heal")):
            kind = "port" if o.name.startswith("Port") else o.name.lower()
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.35 if kind == "port" else 0.6,
                                                 location=o.matrix_world.translation)
            s = bpy.context.active_object; s.data.materials.append(mk[kind]); markers.append(s)
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 12
    scene.cycles.use_denoising = True; scene.cycles.max_bounces = 3
    scene.render.resolution_x, scene.render.resolution_y = 640, 400
    scene.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.42, 0.45, 0.5, 1); bg.inputs["Strength"].default_value = 0.7
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.0; sun.angle = math.radians(3)
    so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
    so.rotation_euler = Euler((math.radians(40), 0, math.radians(-35)))
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.17, 0.12, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.002)); bpy.context.active_object.data.materials.append(gm)
    cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam; cam_d.clip_end = 2000
    shots = [("front 3/4 + empties", -35, 28, span * 1.75 + hmax * 0.8, None, True),
             ("RTS view 70 m / 50 deg", -35, 50, 70.0, None, False),
             ("rear 3/4 + empties", 145, 32, span * 1.75 + hmax * 0.8, None, True),
             ("top + empties", 0, 89.9, 120, span * 1.3, True)]
    tiles = []
    for i, (lab, az, el, dist, ortho, show_mk) in enumerate(shots):
        for s in markers:
            s.hide_render = not show_mk
        tgt = V((0, 0, hmax * 0.3 if ortho is None else 0))
        a, e = math.radians(az), math.radians(el)
        d = V((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = tgt + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam_d.type = "ORTHO"; cam_d.ortho_scale = ortho
        else:
            cam_d.type = "PERSP"; cam_d.sensor_fit = "VERTICAL"; cam_d.angle_y = math.radians(40)   # game camera fov 40
        p = os.path.join(tmp, f"{bid}_{i}.png")
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append((lab, Image.open(p).convert("RGB")))
    return tiles


def contact_sheet(root, sheet, ids, info):
    from PIL import Image, ImageDraw
    import tempfile
    tmp = tempfile.mkdtemp(prefix="civic_sheet_")
    rows = []
    for bid in ids:
        rows.append((bid, render_views(os.path.join(root, bid, bid + ".glb"), bid, tmp)))
    TW, TH, LH = 640, 400, 22
    img = Image.new("RGB", (TW * 4, len(rows) * (TH + LH) + 30), (24, 24, 26))
    dr = ImageDraw.Draw(img)
    dr.text((8, 8), "Steel Accord - civic garrison buildings (env_civic_3d.py). Markers: red = PortN, green = Door, "
            "cyan = Heal. Front = Godot +Z (Blender -Y). Persp views use the game camera FOV (40 deg vertical).",
            fill=(230, 230, 230))
    for r, (bid, tiles) in enumerate(rows):
        y = 30 + r * (TH + LH)
        W, Dp = FOOT[bid]
        dr.text((8, y + 4), f"{bid}  {W} x {Dp} m   tris {info[bid]['tris']}   ports {info[bid]['ports']}", fill=(240, 220, 150))
        for c, (lab, t) in enumerate(tiles):
            img.paste(t, (c * TW, y + LH))
            dr.text((c * TW + 6, y + LH + 4), lab, fill=(255, 255, 255))
    img.save(sheet)
    for fn in os.listdir(tmp):
        os.remove(os.path.join(tmp, fn))
    os.rmdir(tmp)
    print("contact sheet", sheet)


# ====================================================================== main
def main(argv):
    argv = list(argv)

    def opt(name):
        if name in argv:
            i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
        return None
    only = opt("--only"); sheet = opt("--sheet")
    skip = "--previews-only" in argv
    if skip:
        argv.remove("--previews-only")
    root = argv[0] if argv else "."
    ids = [i for i in IDS if not only or i in only.split(",")]
    if not skip:
        for bid in ids:
            make(bid, root)
    info = {}
    for bid in ids:
        glb = os.path.join(root, bid, bid + ".glb")
        tris, emp, (lo, hi), names, mats = inspect(glb)
        ports = sorted([k for k in emp if k.startswith("Port")], key=lambda s: int(s[4:]))
        info[bid] = {"tris": tris, "ports": len(ports)}
        print(f"== {bid}: tris {tris}  meshes {names}  materials {mats}")
        print(f"   bbox blender x[{lo[0]:.2f},{hi[0]:.2f}] y[{lo[1]:.2f},{hi[1]:.2f}] z[{lo[2]:.2f},{hi[2]:.2f}]")
        for k in ["Door", "Heal"] + ports:
            if k in emp:
                print(f"   {k:6s} godot {gltf_to_godot(emp[k])}")
    if sheet:
        contact_sheet(root, sheet, ids, info)


if __name__ == "__main__":
    main(sys.argv[1:])
