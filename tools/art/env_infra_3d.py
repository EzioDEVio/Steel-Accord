"""Steel Accord - Zagros Basin infrastructure and landmark props (B3). Original designs, code-built in Blender bpy 5.x
with the shared structure kit (bldkit_b + prop_zb_common + the civic surfaces of env_civic_3d).

No real-world logos, brands, writing, flags or protected emblems: sign panels and fascias carry plain colour fields or
abstract shapes only; railway stock carries stripes only.

Run:  python3 -I env_infra_3d.py <out_dir> [--only id,id] [--sheet <png>]
Out:  <out_dir>/<id>.glb for id in IDS below. One mesh node `<id>` (1024 or 512 px baked colour x AO atlas material
      IF_<Id>) per prop; named empties where the game needs them (see each builder).
Conventions: metres; origin = footprint centre at ground level (rail stock: formation level, rail top at RT = 0.67 m);
long props (walls, fences, bridges, rail stock, platform, gantry crane, container stack) run along Godot Z (Blender Y);
directional props face Godot +Z (Blender -Y): the tunnel portal's face looks out of the mountain along +Z, the
locomotive's cab end is +Z. Geometry continues 0.5 m below ground where it stands on uneven terrain.
Deterministic: fixed seeds, fixed creation order.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env_civic_3d as CV            # civic surfaces + facade helpers (its main() only runs as a script)
C = CV.C
K = CV.K
import bpy
import numpy as np
from mathutils import Vector as V

PI = math.pi
n_ = K.noise; col = K.col; shade = K.shade; lines = K.lines; frac = K.frac; UU = K.UU; VV = K.VV
SUB = CV.SUB
RT = 0.67                            # rail head above the formation (ballast 0.35 + sleeper 0.15 + rail 0.17)


def t_cont(rgb, seed):
    """Shipping-container side: corrugation every 0.28 m along u, rust streaks, faded paint (S = 2.8 m)."""
    def f():
        s = np.sin(UU * 2 * PI * 10)
        k = (1 + 0.13 * np.tanh(3 * s)) * (1 + 0.03 * n_(50, 50, seed) + 0.02 * n_(2, 2, seed + 1))
        k *= 1 - 0.12 * np.clip(n_(2, 40, seed + 2), 0, None)
        img = shade(col(*rgb), k)
        rust = np.clip(n_(8, 30, seed + 3) - 1.1, 0, None)[..., None]
        return img * (1 - 0.3 * rust) + col(110, 60, 35)[None, None] * 0.3 * rust
    return f


K.SURF.update({
    "cont_red": (t_cont((150, 62, 46), 951), 2.8), "cont_blue": (t_cont((52, 92, 132), 953), 2.8),
    "cont_green": (t_cont((70, 112, 82), 955), 2.8), "cont_grey": (t_cont((150, 152, 148), 957), 2.8),
    "cont_tan": (t_cont((188, 160, 110), 959), 2.8), "boxcar": (t_cont((118, 64, 46), 961), 2.8),
    "loco_body": (K.t_flat((86, 104, 122), 0.04, 963), 2.0), "loco_cream": (K.t_flat((214, 204, 176), 0.03, 965), 2.0),
    "tank_dark": (K.t_flat((64, 66, 68), 0.05, 967), 2.0), "ballast": (K.t_flat((120, 116, 108), 0.12, 969, size=6), 1.0),
    "aviation_r": (K.t_flat((196, 60, 44), 0.03, 971), 2.0), "aviation_w": (K.t_flat((232, 230, 224), 0.02, 973), 2.0),
})

IDS = ["tunnel_portal", "loco", "tank_car", "boxcar", "flatcar", "rail_platform", "rail_bridge", "road_bridge",
       "water_tower", "fuel_station", "cell_tower", "radio_mast", "chimney", "silos", "fuel_tanks", "gantry_crane",
       "container_stack", "compound_wall", "fence"]
ATLAS = {"compound_wall": 256, "fence": 256, "rail_platform": 512, "container_stack": 512, "chimney": 512,
         "radio_mast": 512, "cell_tower": 512}


# ====================================================================== helpers
def arch_pts(cx, spring, r, flat=1.0, n=8):
    """Semicircular arch intrados points left -> right in (u, z)."""
    return [(cx - r * math.cos(PI * k / n), spring + r * flat * math.sin(PI * k / n)) for k in range(n + 1)]


def crown(P, m, pts, top, a0, a1):
    """Fill between an arch curve (list of (u, z)) and the level `top`, extruded over Y a0..a1 (axis 'y')."""
    for p0, p1 in zip(pts[:-1], pts[1:]):
        P.prism(m, [p0, p1, (p1[0], top), (p0[0], top)], "y", a0, a1)


def crown_x(P, m, pts, top, a0, a1):
    """Same, for an arch in a wall plane x = const: pts are (y, z), extruded over X a0..a1."""
    for p0, p1 in zip(pts[:-1], pts[1:]):
        P.prism(m, [p0, p1, (p1[0], top), (p0[0], top)], "x", a0, a1)


def bogie(P, y):
    P.span("dark", -1.15, 1.15, y - 1.35, y + 1.35, RT + 0.2, RT + 0.62)
    for dy in (-0.9, 0.9):
        for sx in (-1, 1):
            P.cyl("dark", (sx * 0.78, y + dy, RT + 0.46), 0.46, 0.14, rot=(0, PI / 2, 0), seg=12, bottom=True)
        P.strut("steel", (-0.85, y + dy, RT + 0.46), (0.85, y + dy, RT + 0.46), 0.07, seg=6)
    P.span("yellow", -1.2, -1.15, y - 0.4, y + 0.4, RT + 0.3, RT + 0.5)


def underframe(P, L, z0=1.15, z1=1.45, w=1.45):
    P.span("dark", -w, w, -L / 2, L / 2, z0, z1)
    for sg in (-1, 1):                                   # buffer beams, couplers
        y = sg * L / 2
        P.span("red", -w, w, y - 0.12 * (sg > 0), y + 0.12 * (sg < 0), z0 - 0.15, z1 + 0.1)
        P.cyl("steel", (0, y + sg * 0.3, z0 + 0.1), 0.18, 0.6, rot=(PI / 2, 0, 0), seg=8, bottom=True)
        for sx in (-1, 1):
            P.cyl("steel", (sx * 0.9, y + sg * 0.25, z0 + 0.15), 0.2, 0.5, rot=(PI / 2, 0, 0), seg=8, bottom=True)


# ====================================================================== rail
def tunnel_portal(kit, P):
    """Concrete headwall 18 m wide with a horseshoe opening (6.4 m wide, 7.8 m high), stepped wing walls, a cover slab
    and a dark recess 1.6 m inside the face (the tunnel is not traversable). Face plane y = 0 looks along -Y (out)."""
    HW, TOP, OW, SPRING, TH = 9.0, 10.8, 3.2, 4.6, 1.2
    P.span("gconc", -HW, -OW, 0.0, TH, SUB - 0.5, TOP)
    P.span("gconc", OW, HW, 0.0, TH, SUB - 0.5, TOP)
    arc = arch_pts(0.0, SPRING, OW)
    crown(P, "gconc", arc, TOP, 0.0, TH)
    # lining: side walls + soffit from the face to the dark recess
    D = 1.6
    P.quad("gconc", [(-OW, 0.0, 0.0), (-OW, D, 0.0), (-OW, D, SPRING), (-OW, 0.0, SPRING)])
    P.quad("gconc", [(OW, D, 0.0), (OW, 0.0, 0.0), (OW, 0.0, SPRING), (OW, D, SPRING)])
    for (u0, z0), (u1, z1) in zip(arc[:-1], arc[1:]):
        P.quad("gconc", [(u1, 0.0, z1), (u0, 0.0, z0), (u0, D, z0), (u1, D, z1)])
    P.span("dark", -OW, OW, D, D + 0.2, -0.2, SPRING + OW + 0.1, bottom=True)
    # arch ring (voussoir band) and pilaster strips on the face
    for (u0, z0), (u1, z1) in zip(arc[:-1], arc[1:]):
        P.prism("trim", [(u0 * 1.12, SPRING + (z0 - SPRING) * 1.12), (u1 * 1.12, SPRING + (z1 - SPRING) * 1.12), (u1, z1), (u0, z0)],
                "y", -0.12, 0.0)
    for x in (-HW + 0.6, -OW - 0.9, OW + 0.9, HW - 0.6):
        P.span("trim", x - 0.35, x + 0.35, -0.15, 0.0, SUB, TOP)
    P.span("trim", -HW - 0.2, HW + 0.2, -0.25, TH + 0.1, TOP, TOP + 0.35)          # coping
    P.span("gconc", -HW, HW, TH, 7.5, TOP - 0.6, TOP)                              # cover slab over the slot
    P.span("earth", -HW + 0.2, HW - 0.2, TH + 0.2, 7.5, TOP, TOP + 0.4)
    # stepped wing walls splaying out ~30 deg from the headwall ends
    for sg in (-1, 1):
        ang = sg * math.radians(-30.0)
        d = V((sg * math.cos(math.radians(30.0)), -math.sin(math.radians(30.0)), 0.0))
        for k, hgt in enumerate((9.2, 7.0, 4.8, 2.6)):
            c = V((sg * HW, 0.6, 0.0)) + d * (1.0 + k * 2.0)
            P.box("gconc", (c.x, c.y, (SUB - 0.5 + hgt) / 2), (2.05, 0.9, hgt - SUB + 0.5), rot=(0, 0, ang))
            P.box("trim", (c.x, c.y, hgt + 0.12), (2.1, 1.05, 0.24), rot=(0, 0, ang))
    # drainage channels either side of the track inside the opening
    for x in (-2.6, 2.6):
        P.span("dark", x - 0.2, x + 0.2, -1.5, D, -0.02, 0.06)
    return None


def loco(kit, P):
    """18 m diesel road-switcher: cab at the +Z end (Blender -Y), long hood, fuel tank, bogies, walkway handrails;
    faded blue-grey with a cream stripe and yellow end stripes (no lettering)."""
    L = 18.0
    for y in (-5.4, 5.4):
        bogie(P, y)
    underframe(P, L, z0=RT + 0.75, z1=RT + 1.15, w=1.5)
    Z0 = RT + 1.15
    P.span("tank_dark", -1.25, 1.25, -2.4, 2.4, RT + 0.45, RT + 0.75)            # fuel tank
    # cab (front, -Y)
    CY0, CY1, CH = -L / 2 + 0.6, -L / 2 + 3.8, Z0 + 3.0
    P.span("loco_body", -1.5, 1.5, CY0, CY1, Z0, CH)
    P.span("loco_body", -1.55, 1.55, CY0 - 0.05, CY1 + 0.05, CH, CH + 0.12)
    for x in (-0.7, 0.7):
        P.span("wglass", x - 0.55, x + 0.55, CY0 - 0.04, CY0, Z0 + 1.7, Z0 + 2.6)
    for sx in (-1, 1):
        P.span("wglass", sx * 1.5 - 0.02, sx * 1.5 + 0.02, CY0 + 0.6, CY1 - 0.4, Z0 + 1.6, Z0 + 2.5)
    # short nose ahead of the cab
    P.span("loco_body", -1.0, 1.0, -L / 2 + 0.15, CY0, Z0, Z0 + 1.5)
    for x in (-0.5, 0.5):
        P.cyl("lamp", (x, -L / 2 + 0.12, Z0 + 1.2), 0.12, 0.06, rot=(PI / 2, 0, 0), seg=8, bottom=True)
    # long hood with louvres and roof fans
    P.span("loco_body", -1.1, 1.1, CY1, L / 2 - 0.4, Z0, Z0 + 2.6)
    for sx in (-1, 1):
        P.span("loco_cream", sx * 1.1 - 0.02 * (sx < 0), sx * 1.1 + 0.02 * (sx > 0), CY1 + 0.2, L / 2 - 0.6, Z0 + 1.2, Z0 + 1.45)
        P.span("loco_cream", sx * 1.5 - 0.02 * (sx < 0), sx * 1.5 + 0.02 * (sx > 0), CY0 + 0.1, CY1 - 0.1, Z0 + 1.2, Z0 + 1.45)
        for y in np.arange(CY1 + 1.0, L / 2 - 1.0, 1.6):
            P.span("louvre", sx * 1.1 - 0.03 * (sx < 0), sx * 1.1 + 0.03 * (sx > 0), y - 0.55, y + 0.55, Z0 + 1.6, Z0 + 2.3)
    for y in (2.0, 4.6, 7.2):
        P.cyl("dark", (0, y, Z0 + 2.65), 0.62, 0.1, seg=12)
        P.cyl("metal", (0, y, Z0 + 2.7), 0.12, 0.08, seg=8)
    P.cyl("dark", (0, CY1 + 1.2, Z0 + 2.9), 0.16, 0.6, seg=8)                     # exhaust stack
    # walkway handrails along both sides, yellow end stripes
    for sx in (-1, 1):
        for y in np.linspace(CY1 + 0.2, L / 2 - 0.6, 6):
            P.strut("yellow", (sx * 1.45, y, Z0), (sx * 1.45, y, Z0 + 1.0), 0.025, seg=4)
        P.strut("yellow", (sx * 1.45, CY1 + 0.2, Z0 + 1.0), (sx * 1.45, L / 2 - 0.6, Z0 + 1.0), 0.025, seg=4)
    for y in (-L / 2 + 0.12, L / 2 - 0.1):
        for k in range(4):
            x = -1.2 + k * 0.8
            P.span("yellow", x, x + 0.4, y - 0.04, y + 0.04, RT + 0.8, RT + 1.1)
    return None


def tank_car(kit, P):
    """13 m tank wagon: dark grey barrel on a frame, top dome with a walkway and ladders (no markings)."""
    L = 13.0
    for y in (-4.4, 4.4):
        bogie(P, y)
    underframe(P, L, z0=RT + 0.75, z1=RT + 1.05)
    zc = RT + 1.05 + 1.45
    P.cyl("tank_dark", (0, 0, zc), 1.45, L - 1.4, rot=(PI / 2, 0, 0), seg=18, bottom=True)
    for sg in (-1, 1):
        P.lathe("tank_dark", [(1.45, 0.0), (1.2, 0.35), (0.0, 0.5)], M=K.Matrix.Translation((0, sg * (L - 1.4) / 2, zc)) @
                K.Euler((-sg * PI / 2, 0, 0)).to_matrix().to_4x4(), seg=18)
    P.cyl("tank_dark", (0, 0, zc + 1.45 + 0.2), 0.5, 0.5, seg=12)
    P.span("grate", -0.9, 0.9, -1.2, 1.2, zc + 1.3, zc + 1.36)
    for sx in (-1, 1):
        P.strut("metal", (sx * 0.9, -1.2, zc + 1.36), (sx * 0.9, 1.2, zc + 1.36), 0.02, seg=4)
        C.K.ladder(P, (sx * 1.5, 0.0, RT + 1.05), (0, 1, 0), 6, 2.6, (sx, 0, 0), m="metal")
    P.span("white", -1.47, 1.47, -0.3, 0.3, zc - 0.2, zc + 0.2)                     # pale band (no text)
    return None


def boxcar(kit, P):
    """15 m covered goods wagon: rust-brown corrugated box, curved roof, sliding doors on both sides."""
    L = 15.0
    for y in (-5.2, 5.2):
        bogie(P, y)
    underframe(P, L, z0=RT + 0.75, z1=RT + 1.05)
    Z0, H = RT + 1.05, RT + 4.0
    P.span("boxcar", -1.45, 1.45, -L / 2 + 0.2, L / 2 - 0.2, Z0, H)
    P.prism("cont_grey", [(-1.5, H), (1.5, H), (0.8, H + 0.32), (0.0, H + 0.42), (-0.8, H + 0.32)], "y",
            -L / 2 + 0.15, L / 2 - 0.15)
    for sx in (-1, 1):
        x = sx * 1.45
        P.span("cont_tan", x - 0.05 * (sx < 0), x + 0.05 * (sx > 0), -1.6, 1.6, Z0 + 0.1, H - 0.2)
        P.span("steel", x - 0.08 * (sx < 0), x + 0.08 * (sx > 0), -3.4, 3.4, H - 0.25, H - 0.15)
        for y in (-1.5, 1.5):
            P.span("dark", x - 0.07 * (sx < 0), x + 0.07 * (sx > 0), y - 0.04, y + 0.04, Z0 + 0.4, H - 0.4)
    return None


def flatcar(kit, P):
    """15 m flat wagon carrying two 20 ft containers (plain colours, no markings)."""
    L = 15.0
    for y in (-5.2, 5.2):
        bogie(P, y)
    underframe(P, L, z0=RT + 0.75, z1=RT + 1.1)
    P.span("woodold", -1.4, 1.4, -L / 2 + 0.1, L / 2 - 0.1, RT + 1.1, RT + 1.22)
    for y in np.linspace(-L / 2 + 0.6, L / 2 - 0.6, 6):
        for sx in (-1, 1):
            P.span("dark", sx * 1.4 - 0.08 * (sx > 0), sx * 1.4 + 0.08 * (sx < 0), y - 0.08, y + 0.08, RT + 1.22, RT + 1.6)
    for y, m in ((-3.35, "cont_blue"), (3.35, "cont_red")):
        container(P, 0.0, y, RT + 1.22, 6.06, m)
    return None


def container(P, x, y, z, L, m, w=2.44, h=2.59):
    """Container with its long axis along Y: corrugated walls, darker corner posts, door bars at the +Y end."""
    P.span(m, x - w / 2, x + w / 2, y - L / 2, y + L / 2, z, z + h)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.span("dark", x + sx * w / 2 - 0.12 * (sx > 0), x + sx * w / 2 + 0.12 * (sx < 0) - 0.0 * sx,
                   y + sy * L / 2 - 0.12 * (sy > 0), y + sy * L / 2 + 0.12 * (sy < 0), z, z + h)
    for k in range(4):
        xx = x - w / 2 + (k + 0.5) * w / 4
        P.strut("metal", (xx, y + L / 2 + 0.03, z + 0.15), (xx, y + L / 2 + 0.03, z + h - 0.15), 0.025, seg=4)


def rail_platform(kit, P):
    """40 m passenger platform (Y), 4 m wide, deck 1.1 m above the formation; yellow safety line on the track side
    (-X), lamp posts, benches and a small shelter."""
    X0, X1, L, Hd = -2.0, 2.0, 20.0, 1.1
    P.span("gconc", X0, X1, -L, L, SUB, Hd - 0.08)
    P.span("pave", X0, X1, -L, L, Hd - 0.08, Hd)
    P.span("trim", X0 - 0.05, X0 + 0.45, -L, L, Hd - 0.12, Hd + 0.01)
    P.span("yellow", X0 + 0.5, X0 + 0.62, -L, L, Hd, Hd + 0.005, bottom=False)
    for sg in (-1, 1):                                   # ramps at both ends
        P.prism("gconc", [(sg * L, SUB), (sg * (L + 3.5), SUB), (sg * L, Hd)] if sg > 0 else [(sg * (L + 3.5), SUB), (sg * L, SUB), (sg * L, Hd)],
                "x", X0 + 0.6, X1)
    for y in np.linspace(-L + 2, L - 2, 6):
        P.cyl("metal", (X1 - 0.5, y, Hd + 2.0), 0.06, 4.0, seg=6)
        P.span("metal", X1 - 1.2, X1 - 0.45, y - 0.08, y + 0.08, Hd + 3.9, Hd + 4.0)
        kit.light(f"Lamp{int(y + 30)}", [("box", (X1 - 1.05, y, Hd + 3.85), (0.4, 0.15, 0.08))])
    for y in (-9.0, 9.0):
        P.span("woodold", 0.4, 1.0, y - 1.0, y + 1.0, Hd + 0.45, Hd + 0.52)
        for d in (-0.85, 0.85):
            P.span("metal", 0.45, 0.95, y + d - 0.04, y + d + 0.04, Hd, Hd + 0.45)
    # shelter
    P.span("metal", 0.2, 1.9, -3.0, 3.0, Hd + 2.6, Hd + 2.72)
    P.span("glass", 1.8, 1.86, -3.0, 3.0, Hd + 0.2, Hd + 2.6)
    for y in (-2.9, 2.9):
        P.span("metal", 1.75, 1.9, y - 0.06, y + 0.06, Hd, Hd + 2.6)
    return None


def bridge(P, L, half, arches, spring, rise, para_h, deck_t=0.0):
    """Masonry arch bridge along Y: spandrel walls at x = +-half down to -4.5 m with arched openings (dark behind),
    parapets, end pillars and wing walls. Origin = deck surface (the road / rail formation) centre."""
    BOT = -4.5
    span_w = (L - 2.0) / arches
    centres = [-L / 2 + 1.0 + span_w * (i + 0.5) for i in range(arches)]
    r = span_w / 2 - 0.7
    for sx in (-1, 1):
        a0, a1 = (half - 0.7, half) if sx > 0 else (-half, -half + 0.7)
        # piers between the arches and at both ends
        edges = [-L / 2] + [c + s * r for c in centres for s in (-1, 1)] + [L / 2]
        for k in range(0, len(edges), 2):
            y0, y1 = edges[k], edges[k + 1]
            P.span("ashlar", a0, a1, y0, y1, BOT, deck_t)
        for c in centres:
            pts = [(c - r * math.cos(PI * k / 8), spring + rise * math.sin(PI * k / 8)) for k in range(9)]
            crown_x(P, "ashlar", pts, deck_t, a0, a1)
            band = [(c - (r + 0.35) * math.cos(PI * k / 8), spring + (rise + 0.35) * math.sin(PI * k / 8)) for k in range(9)]
            for (p0, q0), (p1, q1) in zip(zip(band[:-1], band[1:]), zip(pts[:-1], pts[1:])):
                xo = half + 0.05 if sx > 0 else -half - 0.05
                xi = half if sx > 0 else -half
                P.prism("trim", [q0, q1, p1, p0], "x", min(xo, xi), max(xo, xi))
        # cutwaters on the pier faces (below the springing)
        for c0, c1 in zip(centres[:-1], centres[1:]):
            ym = (c0 + c1) / 2
            P.box("ashlar", (sx * (half + 0.35), ym, (BOT + spring) / 2), (0.7, 0.7, spring - BOT), rot=(0, 0, PI / 4))
        # parapet with coping
        xp0, xp1 = (half - 0.5, half) if sx > 0 else (-half, -half + 0.5)
        P.span("ashlar", xp0, xp1, -L / 2, L / 2, deck_t, deck_t + para_h)
        P.span("trim", xp0 - 0.06, xp1 + 0.06, -L / 2, L / 2, deck_t + para_h, deck_t + para_h + 0.14)
        for sy in (-1, 1):                               # end pillars + short wing walls
            y = sy * (L / 2 - 0.4)
            P.span("ashlar", xp0 - 0.15, xp1 + 0.15, y - 0.4, y + 0.4, BOT, deck_t + para_h + 0.45)
            P.span("trim", xp0 - 0.2, xp1 + 0.2, y - 0.45, y + 0.45, deck_t + para_h + 0.45, deck_t + para_h + 0.6)
            P.span("ashlar", xp0, xp1, sy * L / 2, sy * (L / 2 + 3.0), BOT, deck_t + 0.3)
    # dark void behind the arches (the causeway fill is never seen through an opening)
    for sx in (-1, 1):
        x0, x1 = (half - 1.1, half - 0.7) if sx > 0 else (-half + 0.7, -half + 1.1)
        for c in centres:
            P.span("dark", x0, x1, c - r, c + r, BOT, spring + rise + 0.05)
    return None


def road_bridge(kit, P):
    """34 m three-arch masonry road bridge (9 m carriageway between parapets) over a dry riverbed."""
    bridge(P, 34.0, 5.2, 3, -2.9, 1.9, 1.0)
    for (a, b) in ((4.5, 4.7), (-4.7, -4.5)):            # kerbs on the deck edge
        P.span("trim", a, b, -17.0, 17.0, -0.05, 0.18)
    return None


def rail_bridge(kit, P):
    """24 m two-arch masonry rail bridge (single track) over a gully."""
    bridge(P, 24.0, 3.0, 2, -2.6, 2.4, 0.8, deck_t=0.0)
    return None


# ====================================================================== town + industry landmarks
def water_tower(kit, P):
    """16 m town water tower: four concrete legs with bracing rings, white steel tank with a conical roof, walkway,
    ladder."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.strut("gconc", (sx * 2.7, sy * 2.7, SUB), (sx * 1.9, sy * 1.9, 11.8), 0.32, seg=8)
            P.span("gconc", sx * 2.7 - 0.6, sx * 2.7 + 0.6, sy * 2.7 - 0.6, sy * 2.7 + 0.6, SUB, 0.35)
    for z in (4.0, 8.0):
        w = 2.7 - 0.8 * z / 11.8
        for (a, b) in (((-w, -w), (w, -w)), ((w, -w), (w, w)), ((w, w), (-w, w)), ((-w, w), (-w, -w))):
            P.strut("gconc", (a[0], a[1], z), (b[0], b[1], z), 0.18, seg=6)
    P.lathe("tank_w", [(0.0, 11.6), (2.2, 11.8), (3.7, 12.6), (3.7, 16.2), (3.2, 16.8), (0.6, 17.6), (0.0, 17.7)], seg=20)
    P.cyl("metal", (0, 0, 17.8), 0.3, 0.4, seg=8)
    P.cyl("grate", (0, 0, 12.55), 4.4, 0.1, seg=20, bottom=True)
    for k in range(16):
        a = 2 * PI * k / 16
        P.strut("metal", (4.35 * math.cos(a), 4.35 * math.sin(a), 12.6), (4.35 * math.cos(a), 4.35 * math.sin(a), 13.6), 0.025, seg=4)
    K.ladder(P, (0.0, -2.0, 0.4), (1, 0, 0), 20, 12.2, (0, -1, 0))
    P.strut("metal", (0.6, 0.6, 0.0), (0.6, 0.6, 12.0), 0.12, seg=8)                # down pipe
    return None


def fuel_station(kit, P):
    """20 x 14 m roadside fuel station: white canopy on four columns with a plain teal fascia (no brand), two pump
    islands, a small kiosk and a blank sign pylon."""
    P.span("pave", -10.0, 10.0, -7.0, 7.0, -0.1, 0.04)
    P.span("white", -7.5, 7.5, -4.2, 4.2, 4.9, 5.4)
    P.span("acc_teal", -7.6, 7.6, -4.3, 4.3, 5.4, 5.95)
    P.span("trim", -7.65, 7.65, -4.35, 4.35, 5.95, 6.05)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.span("white", sx * 4.0 - 0.25, sx * 4.0 + 0.25, sy * 1.6 - 0.25, sy * 1.6 + 0.25, 0.0, 4.9)
    for sy in (-1.6, 1.6):
        P.span("gconc", -5.5, 5.5, sy - 0.6, sy + 0.6, 0.0, 0.2)
        for x in (-2.0, 2.0):
            P.span("white", x - 0.45, x + 0.45, sy - 0.3, sy + 0.3, 0.2, 2.0)
            P.span("acc_teal", x - 0.46, x + 0.46, sy - 0.31, sy + 0.31, 1.6, 1.8)
            P.span("dark", x - 0.3, x + 0.3, sy - 0.32, sy - 0.3, 1.0, 1.4)
        for x in (-4.6, 4.6):
            P.cyl("yellow", (x, sy, 0.6), 0.12, 0.8, seg=8)
    # kiosk at the back (+Y), glazed front facing the forecourt
    KX0, KX1, KY0, KY1, KH = -5.0, 3.0, 4.8, 6.9, 3.3
    CV.block(P, "plas_white", "roofc", KX0, KX1, KY0, KY1, KH)
    CV.ring(P, "acc_teal", KX0, KX1, KY0, KY1, KH - 0.35, KH, o=0.05)
    f = CV.Face("y", KY0, -1)
    f.span(P, "glass", KX0 + 0.5, KX1 - 2.0, 0.0, 0.05, 0.3, 2.6)
    CV.door(P, f, KX1 - 1.0, 1.1, 2.2, leaf="glass", step=False)
    CV.roof_ac(P, -3.5, 6.0, KH)
    # sign pylon (abstract: colour fields only)
    P.span("ashlar", 7.2, 8.8, -6.4, -5.6, -0.1, 0.5)
    P.span("acc_teal", 7.4, 8.6, -6.2, -5.8, 0.5, 5.2)
    for k, z in enumerate((3.4, 2.4, 1.4)):
        P.span("sign_w", 7.55, 8.45, -6.24, -6.2, z, z + 0.6)
    P.cyl("metal", (-8.6, 5.6, 0.6), 0.25, 1.2, seg=8)                             # air pump
    return None


def lattice(P, pts_fn, levels, m, r):
    """Square/triangular lattice tower: pts_fn(z) -> corner list; members between consecutive levels."""
    for z0, z1 in zip(levels[:-1], levels[1:]):
        A = pts_fn(z0); B = pts_fn(z1); n = len(A)
        for i in range(n):
            P.strut(m, (*A[i], z0), (*B[i], z1), r, seg=4)
            P.strut(m, (*B[i], z1), (*B[(i + 1) % n], z1), r * 0.7, seg=4)
            P.strut(m, (*A[i], z0), (*B[(i + 1) % n], z1), r * 0.5, seg=4)


def cell_tower(kit, P):
    """28 m three-legged lattice phone mast: sector antenna panels, two link dishes, platform, equipment cabinets and
    a fenced compound."""
    def tri(z):
        w = 2.0 - 1.4 * z / 28.0
        return [(w * math.cos(a), w * math.sin(a)) for a in (PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3)]
    lattice(P, tri, [0.0, 3.5, 7.0, 10.5, 14.0, 17.5, 21.0, 24.5, 28.0], "galv", 0.07)
    for x, y in tri(0.0):
        P.span("gconc", x - 0.4, x + 0.4, y - 0.4, y + 0.4, SUB, 0.3)
    P.cyl("grate", (0, 0, 24.6), 1.6, 0.08, seg=12, bottom=True)
    for k in range(3):
        a = PI / 2 + 2 * PI * k / 3 + PI / 3
        for dz in (0.0,):
            for s in (-0.35, 0.35):
                c = (1.35 * math.cos(a) - s * math.sin(a), 1.35 * math.sin(a) + s * math.cos(a), 26.0)
                P.box("white", c, (0.3, 0.12, 1.5), rot=(0, 0, a + PI / 2))
    for k, (a, z) in enumerate(((0.3, 20.5), (2.4, 18.0))):
        M = K.Matrix.Translation((0.9 * math.cos(a), 0.9 * math.sin(a), z)) @ K.Euler((PI / 2, 0, a + PI / 2)).to_matrix().to_4x4()
        P.lathe("dishw", [(0.0, 0.0), (0.4, 0.06), (0.6, 0.2)], M=M, seg=12)
    for x in (-1.6, 1.2):
        P.span("cabinet", x - 0.5, x + 0.5, -2.2, -1.5, 0.0, 1.8)
    for (a, b) in (((-2.4, -2.4), (2.4, -2.4)), ((2.4, -2.4), (2.4, 2.4)), ((2.4, 2.4), (-2.4, 2.4)), ((-2.4, 2.4), (-2.4, -2.4))):
        kit.fence(a, b, 0.0, 2.0)
        P.strut("galv", (a[0], a[1], 0.0), (a[0], a[1], 2.1), 0.04, seg=4)
    kit.light("Beacon", [("sph", (0, 0, 28.3), 0.18)])
    return None


def radio_mast(kit, P):
    """40 m square lattice radio mast in red/white aviation bands, top beacon, small equipment hut."""
    def sq(z):
        w = 0.55
        return [(-w, -w), (w, -w), (w, w), (-w, w)]
    lv = list(np.arange(0.0, 40.01, 2.5))
    for i, (z0, z1) in enumerate(zip(lv[:-1], lv[1:])):
        lattice(P, sq, [z0, z1], "aviation_r" if (i // 2) % 2 == 0 else "aviation_w", 0.05)
    P.span("gconc", -1.0, 1.0, -1.0, 1.0, SUB, 0.3)
    for k in range(4):                                      # top antenna whips
        a = PI / 4 + k * PI / 2
        P.strut("metal", (0.5 * math.cos(a), 0.5 * math.sin(a), 40.0), (0.5 * math.cos(a), 0.5 * math.sin(a), 43.0), 0.03, seg=4)
    kit.light("Beacon", [("sph", (0, 0, 40.4), 0.2)])
    CV.block(P, "plas_white", "roofc", 1.2, 3.4, -1.4, 1.0, 2.6)
    CV.door(P, CV.Face("y", -1.4, -1), 2.3, 0.8, 2.0, leaf="door", step=False)
    P.strut("metal", (0.55, 0.0, 2.3), (1.2, 0.0, 2.3), 0.05, seg=6)
    return None


def chimney(kit, P):
    """34 m tapered brick factory chimney on a concrete plinth with steel bands and a sooted top."""
    P.span("gconc", -2.8, 2.8, -2.8, 2.8, SUB, 2.2)
    P.span("trim", -2.9, 2.9, -2.9, 2.9, 2.2, 2.4)
    P.lathe("brick", [(2.2, 2.4), (1.25, 33.4)], seg=16)
    P.lathe("dark", [(1.25, 33.4), (1.4, 33.6), (1.4, 34.2), (1.05, 34.2), (1.05, 33.9)], seg=16)
    for z in (8.0, 15.0, 22.0, 29.0):
        r = 2.2 - 0.95 * (z - 2.4) / 31.0
        P.lathe("metal", [(r + 0.02, z), (r + 0.06, z + 0.06), (r + 0.06, z + 0.26), (r + 0.02, z + 0.32)], seg=16)
    K.ladder(P, (0.0, -2.1, 2.4), (1, 0, 0), 30, 30.0, (0, -1, 0))
    return None


def silos(kit, P):
    """Three 16 m galvanised storage silos with conical roofs on a ring base, a lattice elevator tower and an inclined
    conveyor gallery."""
    for x in (-4.2, 0.0, 4.2):
        P.cyl("gconc", (x, 1.6, 0.25), 2.15, 1.5, seg=16)
        P.lathe("galv", [(2.0, 0.9), (2.0, 15.0), (0.5, 16.6), (0.0, 16.7)], M=K.Matrix.Translation((x, 1.6, 0.0)), seg=16)
        for z in (5.0, 10.0):
            P.lathe("metal", [(2.02, z), (2.06, z + 0.05), (2.06, z + 0.2), (2.02, z + 0.25)], M=K.Matrix.Translation((x, 1.6, 0.0)), seg=16)
    lattice(P, lambda z: [(-0.9, -4.9), (0.9, -4.9), (0.9, -3.1), (-0.9, -3.1)], [0.0, 4.5, 9.0, 13.5, 18.0], "steel", 0.06)
    P.span("corr_grey", -1.1, 1.1, -5.1, -2.9, 18.0, 20.2)
    P.span("roof_grey", -1.2, 1.2, -5.2, -2.8, 20.2, 20.4)
    P.prism("corr_grey", [(-2.9, 18.6), (1.6, 17.0), (1.6, 17.8), (-2.9, 19.4)], "x", -0.6, 0.6)
    P.span("corr_grey", -4.6, 4.6, 1.0, 2.2, 16.6, 17.4)
    P.span("gconc", -6.0, -3.2, -5.6, -2.6, SUB, 2.6)
    return None


def fuel_tanks(kit, P):
    """Two 6.5 m vertical fuel storage tanks inside a concrete bund wall, with pipe runs and stairs."""
    X0, X1, Y0, Y1 = -7.0, 7.0, -5.0, 5.0
    for (a0, a1, b0, b1) in ((X0, X1, Y0, Y0 + 0.3), (X0, X1, Y1 - 0.3, Y1), (X0, X0 + 0.3, Y0 + 0.3, Y1 - 0.3), (X1 - 0.3, X1, Y0 + 0.3, Y1 - 0.3)):
        P.span("gconc", a0, a1, b0, b1, SUB, 1.1)
    P.span("gconc", X0 + 0.3, X1 - 0.3, Y0 + 0.3, Y1 - 0.3, -0.1, 0.05)
    for x in (-3.4, 3.4):
        P.lathe("tank_w", [(2.7, 0.0), (2.7, 6.5), (2.2, 7.1), (0.0, 7.4)], M=K.Matrix.Translation((x, 0.4, 0.0)), seg=20)
        P.cyl("gconc", (x, 0.4, 0.05), 2.9, 0.2, seg=20, bottom=True)
        P.strut("metal", (x, 0.4, 7.4), (x, 0.4, 7.9), 0.12, seg=6)
    for z in (0.6, 0.9):
        P.strut("steel", (-6.8, -3.6, z), (6.8, -3.6, z), 0.11, seg=8)
    P.strut("steel", (-3.4, -2.3, 0.75), (-3.4, -3.6, 0.75), 0.11, seg=8)
    P.strut("steel", (3.4, -2.3, 0.75), (3.4, -3.6, 0.75), 0.11, seg=8)
    K.ladder(P, (0.0, -2.0, 0.0), (1, 0, 0), 16, 6.5, (0, -1, 0))
    for k, x in enumerate((-6.0, 6.0)):
        P.span("yellow", x - 0.3, x + 0.3, -4.95, -4.65, 1.1, 1.4)
    return None


def gantry_crane(kit, P):
    """Rail-mounted container gantry: yellow box-girder legs and beams spanning 22 m along Y, trolley, spreader."""
    LY, LX, H = 11.0, 3.4, 12.0
    for sy in (-1, 1):
        y = sy * LY
        for sx in (-1, 1):
            P.span("yellow", sx * LX - 0.35, sx * LX + 0.35, y - 0.35, y + 0.35, 0.6, H)
        P.span("yellow", -LX - 0.5, LX + 0.5, y - 0.45, y + 0.45, 0.0, 0.6)           # sill beam with bogies
        for sx in (-1, 1):
            P.span("dark", sx * LX - 0.6, sx * LX + 0.6, y - 0.5, y + 0.5, 0.0, 0.25)
        P.span("yellow", -LX, LX, y - 0.3, y + 0.3, H - 1.6, H - 1.0)
        for sx in (-1, 1):
            P.strut("yellow", (sx * LX, y, 4.0), (-sx * LX * 0.2, y, H - 1.6), 0.14, seg=6)
    for sx in (-1, 1):
        P.span("yellow", sx * LX - 0.45, sx * LX + 0.45, -LY - 1.5, LY + 1.5, H, H + 1.3)
    P.span("yellow", -LX - 0.4, LX + 0.4, 1.0, 4.0, H + 1.3, H + 2.2)               # trolley
    P.span("glass", 1.2, 2.6, 1.4, 3.4, H - 1.0, H)                                 # operator cab under it
    P.span("yellow", 1.1, 2.7, 1.3, 3.5, H - 1.2, H - 1.0)
    for dx in (-0.8, 0.8):
        P.strut("dark", (dx, 2.5, H + 1.3), (dx, 2.5, 6.3), 0.03, seg=4)
    P.span("yellow", -1.3, 1.3, -0.6, 5.6, 6.0, 6.3)                                # spreader
    for sy in (-1, 1):
        kit.light(f"Warn{sy + 1}", [("box", (0.0, sy * (LY + 1.2), H + 1.45), (0.25, 0.25, 0.2))])
    return None


def container_stack(kit, P):
    """Two rows of 40 ft containers (long axis Y), stacked 2 and 3 high, plain faded colours."""
    cols = [("cont_red", "cont_blue", None), ("cont_green", "cont_tan", "cont_grey")]
    for i, (x, stack) in enumerate(zip((-1.3, 1.3), cols)):
        for k, m in enumerate(stack):
            if m:
                container(P, x, 0.0 + (0.4 if k % 2 else 0.0), k * 2.6, 12.19, m)
    return None


def compound_wall(kit, P):
    """4 m compound wall segment (Y): rendered mud-plaster on a stone footing, flat coping."""
    P.span("mud", -0.2, 0.2, -2.0, 2.0, SUB - 0.3, 2.4)
    P.span("lime", -0.26, 0.26, -2.0, 2.0, SUB - 0.3, 0.35)
    P.span("trim", -0.27, 0.27, -2.02, 2.02, 2.4, 2.5)
    return None


def fence(kit, P):
    """6 m chain-link fence panel (Y) with galvanised posts, top rail and barbed-wire outriggers."""
    for y in (-3.0, 3.0):
        P.strut("galv", (0, y, SUB), (0, y, 2.2), 0.045, seg=6)
        P.strut("galv", (0, y, 2.2), (-0.35, y, 2.55), 0.02, seg=4)
    P.strut("galv", (0, -3.0, 2.15), (0, 3.0, 2.15), 0.025, seg=4)
    for z in (2.35, 2.48):
        P.strut("metal", (-0.2 - (z - 2.35), -3.0, z), (-0.2 - (z - 2.35), 3.0, z), 0.008, seg=3)
    kit.fence((0.0, -3.0), (0.0, 3.0), 0.0, 2.15)
    return None


BUILD = {k: globals()[k] for k in IDS}


def make(pid, out):
    kit = K.Kit(pid if pid != "fence" else "chainlink_fence", "IF", atlas=ATLAS.get(pid, 1024), ao_res=min(512, ATLAS.get(pid, 1024)), ao_dist=2.5)
    P = kit.part(pid)
    BUILD[pid](kit, P)
    P.build()
    return kit.finish(out, pid + ".glb", ground_size=60)


def main(argv):
    argv = list(argv)

    def opt(name):
        if name in argv:
            i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
        return None
    only = opt("--only"); sheet = opt("--sheet")
    out = argv[0] if argv else "."
    os.makedirs(out, exist_ok=True)
    ids = [i for i in IDS if not only or i in only.split(",")]
    for pid in ids:
        make(pid, out)
    for pid in ids:
        tris, emp, (lo, hi), names, mats = CV.inspect(os.path.join(out, pid + ".glb"))
        print(f"== {pid}: tris {tris} materials {mats} bbox x[{lo[0]:.1f},{hi[0]:.1f}] y[{lo[1]:.1f},{hi[1]:.1f}] z[{lo[2]:.1f},{hi[2]:.1f}]")
    if sheet:
        review_sheet(out, ids, sheet)


def review_sheet(out, ids, sheet):
    """Workbench (fast, back-face culled like Godot) 3/4 views of every prop in one contact sheet."""
    from PIL import Image, ImageDraw
    tiles = []
    for pid in ids:
        glb = os.path.join(out, pid + ".glb")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=glb)
        pts = [o.matrix_world @ V(b) for o in bpy.context.scene.objects if o.type == "MESH" for b in o.bound_box]
        lo = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        span = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
        tgt = (0, 0, max(0.0, (lo.z + hi.z) / 2))
        png = os.path.join(out, f"_{pid}_rev.png")
        K.cull_check(glb, png, [dict(az=-35, el=30, dist=span * 1.9 + 4, target=tgt), dict(az=145, el=35, dist=span * 1.9 + 4, target=tgt)],
                     res=(480, 300))
        tiles.append((pid, Image.open(png).convert("RGB"))); os.remove(png)
    W = tiles[0][1].width; Hh = tiles[0][1].height
    cols = 2
    img = Image.new("RGB", (W * cols, (Hh + 18) * ((len(tiles) + cols - 1) // cols)), (24, 24, 26))
    dr = ImageDraw.Draw(img)
    for i, (pid, t) in enumerate(tiles):
        x = (i % cols) * W; y = (i // cols) * (Hh + 18)
        img.paste(t, (x, y + 18)); dr.text((x + 6, y + 3), pid, fill=(240, 220, 150))
    img.save(sheet)
    print("sheet", sheet)


if __name__ == "__main__":
    main(sys.argv[1:])
