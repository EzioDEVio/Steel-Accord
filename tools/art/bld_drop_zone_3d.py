"""Steel Accord - M1 structure: Supply Drop Zone (new).

Run:  python3 -I bld_drop_zone_3d.py <out_dir> [--previews <dir>] [--concept <png>] [--only rts] [--previews-only]
Out:  <out_dir>/drop_zone.glb
  Building - raised concrete pad with painted drop target, chamfered barrier blocks, access ramp, fence,
             site office container, antenna mast
  Props    - parachute bundles, crate stacks, pallets, equipment boxes, flood tripods
  Light_Status0..1, Light_Beacon0, Light_Flood0..3
  Empty: DropPoint (centre of the drop target, on the pad surface)
Footprint 24 x 24 m, origin = footprint centre at ground, front (ramp) = Blender -Y = Godot +Z.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import numpy as np
from mathutils import Matrix, Euler, Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "drop_zone.glb")
PI = math.pi
SL = 0.55                                   # pad top (raised platform)
TX, TY = -2.6, 0.4                          # drop target centre
YEL, WHT = (222, 176, 40), (232, 230, 222)


def paint_plan(kit):
    C = kit.set_plan(-12, 12, -12, 12, 56)
    C.fill((-12, 12, -12, 12), K.ground_concrete((150, 148, 142), joint=3.0, seed=610, stains=0.09))
    C.fill((-10.6, 10.6, -10.6, 10.6), K.ground_asphalt((84, 85, 86), seed=630))
    # landing-area outline (notched around the stores area on the right)
    out = [(-10.0, -9.8), (3.4, -9.8), (3.4, -4.6), (4.6, -3.4), (4.6, 8.6), (-10.0, 8.6)]
    for a, b in zip(out, out[1:] + out[:1]):
        C.line(a, b, 0.32, YEL, wear=0.3)
    # corner brackets
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = TX + sx * 6.6, TY + sy * 6.6
            C.line((cx, cy), (cx - sx * 1.8, cy), 0.4, WHT, wear=0.3)
            C.line((cx, cy), (cx, cy - sy * 1.8), 0.4, WHT, wear=0.3)
    # target: broken yellow ring + white cross with an open centre
    C.ring(TX, TY, 4.6, 5.1, YEL, gaps=[(0, 9), (90, 9), (180, 9), (270, 9)], wear=0.25)
    for ang in (0, PI / 2):
        for s in (-1, 1):
            c = V((math.cos(ang), math.sin(ang))) * s
            C.orect(TX + c.x * 3.4, TY + c.y * 3.4, 4.6, 0.95, ang, WHT, wear=0.25)
    C.rect(TX - 0.45, TX + 0.45, TY - 0.45, TY + 0.45, WHT, wear=0.2)
    # direction arrow toward the stores area + grid ref
    C.digit("4", -8.6, -8.4, 1.2, YEL, wear=0.3); C.digit("2", -7.7, -8.4, 1.2, YEL, wear=0.3)
    # scorch / tyre marks
    for (x, y, r) in ((TX + 1.0, TY - 0.8, 2.0), (6.5, 0.0, 2.2), (0.0, -9.0, 1.4)):
        C.paint((x - r, x + r, y - r, y + r), lambda X, Y, x=x, y=y, r=r: np.hypot(X - x, (Y - y) * 1.4) - r,
                (52, 52, 50), alpha=0.25, wear=0.8)


def bundle(P, cx, cy, base, r=1.6, h=1.15, seed=0):
    """Collapsed parachute bundle: lumpy camo dome with straps and a cargo net ring."""
    rng = np.random.default_rng(seed)
    rings = []
    for z, rr in ((0.0, 1.0), (0.22, 1.05), (0.45, 0.98), (0.68, 0.84), (0.86, 0.62), (1.0, 0.3)):
        ring = []
        for i in range(24):
            a = 2 * PI * i / 24
            k = rr * (1 + 0.09 * math.sin(5 * a + 3 * z + seed) + rng.uniform(-0.06, 0.06))     # folds
            ring.append((cx + r * k * math.cos(a), cy + r * 0.85 * k * math.sin(a), base + h * z + rng.uniform(-0.04, 0.04)))
        rings.append(ring)
    P.loft("camonet", rings, cap1=True)
    for a in (0.3, 0.3 + PI / 2):                                   # cross straps
        pts = []
        for t in np.linspace(-1, 1, 7):
            rr = abs(t)
            zz = base + h * (1.0 - rr ** 2 * 0.95) + 0.03
            pts.append((cx + r * t * 1.02 * math.cos(a), cy + r * 0.86 * t * 1.02 * math.sin(a), zz))
        for p0, p1 in zip(pts[:-1], pts[1:]):
            P.strut("strap", p0, p1, 0.05, seg=4)
    ring = [(cx + r * 1.05 * math.cos(2 * PI * i / 16), cy + r * 0.9 * math.sin(2 * PI * i / 16), base + 0.32) for i in range(17)]
    for p0, p1 in zip(ring[:-1], ring[1:]):
        P.strut("rubber", p0, p1, 0.04, seg=4)
    # loose suspension cords draped over the bundle (white)
    for i in range(10):
        a = 2 * PI * (i + rng.uniform(-0.2, 0.2)) / 10
        pts = []
        for t in np.linspace(0.0, 1.08, 6):
            zz = base + h * max(0.0, 1.0 - (t / 1.0) ** 2 * 0.9) + 0.04 if t <= 1.0 else base + 0.03
            pts.append((cx + r * t * math.cos(a + 0.25 * t), cy + r * 0.86 * t * math.sin(a + 0.25 * t), zz))
        for p0, p1 in zip(pts[:-1], pts[1:]):
            P.strut("white", p0, p1, 0.028, seg=3)


def tripod_flood(kit, P, name, x, y, aim):
    yaw = math.atan2(aim[1] - y, aim[0] - x)
    top = (x, y, SL + 2.4)
    for k in range(3):
        a = yaw + PI + (k - 1) * 2 * PI / 3
        P.strut("yellow", (x + 0.6 * math.cos(a), y + 0.6 * math.sin(a), SL), top, 0.04, seg=5)
    P.cyl("metal", (x, y, SL + 2.6), 0.06, 0.5, seg=6)
    P.box("dark", (x, y, SL + 2.95), (0.42, 0.55, 0.45), (0, 0, yaw), bottom=True)
    P.box("yellow", (x, y, SL + 3.2), (0.46, 0.6, 0.06), (0, 0, yaw), bottom=True)
    kit.light(name, [("box", (x + 0.22 * math.cos(yaw), y + 0.22 * math.sin(yaw), SL + 2.95), (0.04, 0.46, 0.36), (0, 0, yaw))])


def build():
    kit = K.Kit("drop_zone", "DZ", atlas=2048, ao_res=1024, ao_dist=3.0)
    paint_plan(kit)
    B = kit.part("Building")
    P = kit.part("Props")

    # ---------------------------------------------------------------- raised pad
    B.frustum("gconc", -12.0, 12.0, -12.0, 12.0, 0.0, SL - 0.004, 0.25, top=False)
    B.quad("plan", [(-11.75, -11.75, SL), (11.75, -11.75, SL), (11.75, 11.75, SL), (-11.75, 11.75, SL)])
    # front access ramp (down to the ground, grated, hazard cheeks)
    RX0, RX1 = -1.6, 1.6
    B.span("grate", RX0, RX1, -11.8, -9.6, SL, SL + 0.03)
    for x in (RX0 - 0.15, RX1 + 0.15):
        B.span("hazard", x - 0.12, x + 0.12, -11.9, -9.6, SL, SL + 0.5, bev=True)
    # drain grate along the left edge
    B.span("grate", -11.2, -10.8, -8.0, 6.0, SL, SL + 0.02)

    # ---------------------------------------------------------------- perimeter barrier blocks + fence
    def block(cx, cy, along_x, L=1.7):
        prof = [(-0.45, 0.0), (0.45, 0.0), (0.45, 0.25), (0.22, 0.95), (-0.22, 0.95), (-0.45, 0.25)]
        if along_x:
            B.prism("gconc", [(cy + p, SL + q) for p, q in prof], "x", cx - L / 2, cx + L / 2, bev=True)
        else:
            B.prism("gconc", [(cx + p, SL + q) for p, q in prof], "y", cy - L / 2, cy + L / 2, bev=True)
    E = 11.15
    for k in range(12):
        t = -10.2 + k * 1.85
        block(t, E, True); block(-E, t, False); block(E, t, False)
        if t < RX0 - 1.0 or t > RX1 + 1.0:
            block(t, -E, True)
    for s in (-1, 1):                                                   # corner pillars
        for t in (-1, 1):
            B.frustum("gconc", s * E - 0.55, s * E + 0.55, t * E - 0.55, t * E + 0.55, SL, SL + 1.15, 0.12)
    # equipment boxes between blocks (concept detail)
    for (x, y, sx, sy) in ((-6.0, -E, 0.9, 0.55), (6.5, -E, 0.8, 0.55), (-E, 3.0, 0.55, 0.9), (E, -5.0, 0.55, 0.8), (2.0, E, 0.8, 0.55)):
        K.cabinet(B, x, y, SL, sx, sy, 1.05)
    FH = 2.0
    fence_runs = [((-11.7, 11.7), (11.7, 11.7)), ((-11.7, -11.7), (-11.7, 11.7)), ((11.7, -11.7), (11.7, 11.7)),
                  ((-11.7, -11.7), (RX0 - 0.5, -11.7)), ((RX1 + 0.5, -11.7), (11.7, -11.7))]
    for (x0, y0), (x1, y1) in fence_runs:
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / 2.8)))
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            B.cyl("metal", (x, y, SL + FH / 2 + 0.05), 0.045, FH + 0.1, seg=6)
        B.strut("metal", (x0, y0, SL + FH), (x1, y1, SL + FH), 0.025, seg=4)
        kit.fence((x0, y0), (x1, y1), SL + 0.1, SL + FH)
    for x in (RX0 - 0.5, RX1 + 0.5):                                     # gate posts
        B.span("yellow", x - 0.12, x + 0.12, -11.82, -11.58, SL, SL + 2.3, bev=True)
    kit.light("Light_Status1", [("box", (RX1 + 0.5, -11.86, SL + 2.0), (0.18, 0.06, 0.18))])

    # ---------------------------------------------------------------- site office container (back right)
    OX0, OX1, OY0, OY1 = 3.6, 8.8, 7.3, 10.4
    B.span("metal", OX0 + 0.1, OX1 - 0.1, OY0 + 0.1, OY1 - 0.1, SL, SL + 0.15)
    B.span("cont", OX0, OX1, OY0, OY1, SL + 0.15, SL + 2.75, bev=True)
    B.frustum("tarp", OX0 - 0.15, OX1 + 0.15, OY0 - 0.15, OY1 + 0.15, SL + 2.75, SL + 3.1, 0.25)        # canvas roof cover
    B.span("team", OX0 - 0.01, OX1 + 0.01, OY0 - 0.02, OY0, SL + 2.35, SL + 2.55, bottom=True)
    B.span("olive", 6.6, 7.6, OY0 - 0.05, OY0, SL + 0.2, SL + 2.3)                                         # door
    B.span("metal", 6.55, 7.65, OY0 - 0.5, OY0, SL + 2.4, SL + 2.48, bottom=True)
    for k in range(2):
        B.span("slab", 6.5, 7.7, OY0 - 0.35 * (k + 1), OY0, SL, SL + 0.15 - 0.07 * k)
    B.span("louvre", 4.3, 5.6, OY0 - 0.05, OY0, SL + 1.2, SL + 1.9)
    B.span("hvac", OX0 - 0.6, OX0, 8.2, 9.4, SL + 1.2, SL + 2.1, bev=True)                                    # wall AC unit
    B.cyl("dark", (OX0 - 0.61, 8.8, SL + 1.65), 0.32, 0.02, (0, PI / 2, 0), seg=12)
    kit.light("Light_Status0", [("box", (7.85, OY0 - 0.05, SL + 2.05), (0.16, 0.06, 0.16))])
    K.cabinet(B, 9.9, 7.9, SL, 0.8, 0.7, 1.6, face="-y")                                                      # generator box
    B.strut("rubber", (9.5, 7.9, SL + 0.05), (OX1, 7.9, SL + 0.05), 0.05, seg=5)

    # ---------------------------------------------------------------- antenna mast (back-right corner)
    MX, MY = 10.0, 10.0
    B.frustum("gconc", MX - 0.45, MX + 0.45, MY - 0.45, MY + 0.45, SL, SL + 0.35, 0.06)
    B.cyl("dark", (MX, MY, SL + 0.35 + 4.5), 0.13, 9.0, seg=8, r2=0.08)
    for k in range(3):                                                   # panel antennas
        a = 2 * PI * k / 3 + 0.3
        B.box("dark", (MX + 0.28 * math.cos(a), MY + 0.28 * math.sin(a), SL + 7.4), (0.12, 0.26, 1.2), (0, 0, a), bev=True)
    B.cyl("white", (MX - 0.45, MY - 0.45, SL + 5.6), 0.38, 0.4, (PI / 2, 0, math.radians(45)), seg=12, r2=0.12)   # horn dish
    B.strut("metal", (MX, MY, SL + 5.6), (MX - 0.35, MY - 0.35, SL + 5.6), 0.04, seg=4)
    B.box("team", (MX + 0.45, MY, SL + 8.3), (0.8, 0.02, 0.5))                                                  # pennant
    B.cyl("metal", (MX, MY, SL + 9.38), 0.09, 0.06, seg=8, bottom=True)
    kit.light("Light_Beacon0", [("sph", (MX, MY, SL + 9.55), 0.16)])
    B.strut("rubber", (MX, MY - 0.1, SL + 0.4), (8.8, 9.5, SL + 2.0), 0.035, seg=4)

    # ---------------------------------------------------------------- stores: chute bundles, crates, pallets
    bundle(P, 7.1, 3.7, SL, 2.45, 1.7, seed=1)
    bundle(P, 9.75, 6.1, SL, 0.95, 0.75, seed=2)
    for (x, y, l, s) in ((6.0, -0.4, 3, "crate"), (7.4, -0.4, 3, "crate"), (9.9, -0.6, 2, "crate"),
                         (6.0, -2.4, 2, "crate"), (9.9, -2.6, 3, "crate"), (8.3, -4.6, 2, "crate")):
        K.ammo_pallet(P, x, y, SL, l, s)
    for (x, y, h) in ((8.65, -0.5, 1.35), (7.9, -2.5, 1.45), (6.4, -4.5, 1.2), (9.9, -4.5, 1.5)):  # tan plywood supply cubes
        z = K.pallet(P, x, y, SL)
        P.span("tcrate", x - 0.58, x + 0.58, y - 0.48, y + 0.48, z, z + h, bev=True)
        P.span("strap", x - 0.6, x + 0.6, y - 0.05, y + 0.05, z, z + h + 0.02)
        P.span("strap", x - 0.05, x + 0.05, y - 0.5, y + 0.5, z, z + h + 0.025)
    for (x, y) in ((-9.9, 9.9), (-8.6, 9.9), (-7.3, 9.9)):                            # equipment cases on the back wall
        P.span("cabinet", x - 0.55, x + 0.55, y - 0.35, y + 0.35, SL, SL + 0.7, bev=True)
    P.span("crate", -9.95, -9.0, 8.5, 9.35, SL, SL + 0.5, bev=True)
    for k, (x, y) in enumerate(((-10.0, -9.2), (-9.4, -9.9))):
        K.drum(P, x, y, SL, "olive")
    P.span("pallet", 4.0, 5.2, -9.4, -8.4, SL, SL + 0.14)
    P.span("pallet", 4.0, 5.2, -9.4, -8.4, SL + 0.14, SL + 0.28)
    # flood tripods in the four corners (aimed at the target)
    for k, (x, y) in enumerate(((-10.1, -10.1), (10.1, -10.1), (-10.1, 10.1), (10.1, 8.6))):
        tripod_flood(kit, P, f"Light_Flood{k}", x, y, (TX, TY))

    B.build(); P.build()
    kit.empty("DropPoint", (TX, TY, SL))
    return kit.finish(A.out, "drop_zone.glb", ground_size=60)


if not A.skip_build:
    build()
if A.previews:
    K.previews(GLB, A.previews, "m1_drop_zone", [dict(d, target=(0, 2.5, 2.5)) if d["name"] != "top" else d for d in K.std_shots(24.0, 6.0, dmul=1.2)], only=A.only, concept=A.concept)
