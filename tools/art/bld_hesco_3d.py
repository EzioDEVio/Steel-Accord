"""Steel Accord - M1 structure: HESCO barrier wall SEGMENT (tileable side by side along X).

Run:  python3 -I bld_hesco_3d.py <out_dir> [--previews <dir>] [--concept <png>] [--only rts,front] [--previews-only]
Out:  <out_dir>/hesco.glb  nodes: Building (cells, berm, joints, placard), Light_Status0..1
Footprint 8 (X) x 4 (depth) m, origin = footprint centre at ground, front = Blender -Y = Godot +Z.
Front row: 8 cells 1.0 x 1.05 m, 2.2 m tall (welded mesh + geotextile, earth fill mounded on top).
Rear row: 8 cells 1.0 m tall-ish fire step (1.1 m) + an earth ramp behind. Cells end exactly at x = +-4 so
segments butt together seamlessly.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import numpy as np
from mathutils import Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "hesco.glb")


def cell(B, cx, cy, hx, hy, z0, h, seed, K_=16, expo=5.0):
    """One HESCO cell: rounded-square barrel sides (hesco) + mounded earth top."""
    def ring(sc, z, shrink=1.0):
        pts = []
        for i in range(K_):
            a = 2 * math.pi * (i + 0.5) / K_
            c, s = math.cos(a), math.sin(a)
            # superellipse |x|^e + |y|^e = 1
            r = (abs(c) ** expo + abs(s) ** expo) ** (-1.0 / expo)
            pts.append((cx + hx * sc * shrink * r * c, cy + hy * sc * shrink * r * s, z))
        return pts
    zs = [(z0, 0.965), (z0 + 0.25, 0.99), (z0 + h * 0.5, 1.0), (z0 + h - 0.25, 0.99), (z0 + h, 0.975)]
    B.loft("hesco", [ring(s, z) for z, s in zs], cap1=False)
    top = [ring(0.975, z0 + h)]
    for dz, sh in ((0.06, 1.0), (0.11, 0.86), (0.15, 0.6), (0.16, 0.3)):     # fill spills slightly over the rim
        top.append(ring(0.975, z0 + h + dz, sh))
    B.loft("earth", top, cap1=True, jitter=(np.random.default_rng(seed), 0.035, 0.05, 1))


def build():
    kit = K.Kit("hesco", "HS", atlas=2048, ao_res=1024, ao_dist=2.0)
    B = kit.part("Building")
    BASE = 0.08
    # earth berm strip (flat ends at x=+-4 for tiling)
    B.span("earth", -4.0, 4.0, -2.0, 2.0, 0.0, BASE)
    # front row (tall), rear row (fire step)
    FY0, FY1 = -1.75, -0.7
    RY0, RY1 = -0.7, 0.35
    for i in range(8):
        cx = -3.5 + i
        cell(B, cx, (FY0 + FY1) / 2, 0.5, (FY1 - FY0) / 2, BASE, 2.2, 100 + i)
        cell(B, cx, (RY0 + RY1) / 2, 0.5, (RY1 - RY0) / 2, BASE, 1.1, 200 + i)
    # vertical coil joints (one per cell boundary on the left of each cell, front + back faces)
    for i in range(8):
        x = -4.0 + i
        for y, h in ((FY0 + 0.02, 2.2), (RY1 - 0.02, 1.1)):
            B.strut("metal", (x, y, BASE), (x, y, BASE + h + 0.02), 0.03, seg=5)
        for y in (FY0 + 0.06, FY1 - 0.06):                       # top-edge wire on front row
            pass
        B.strut("metal", (x + 0.04, FY0 + 0.03, BASE + 2.2), (x + 0.96, FY0 + 0.03, BASE + 2.2), 0.018, seg=4)
        B.strut("metal", (x + 0.04, RY1 - 0.03, BASE + 1.1), (x + 0.96, RY1 - 0.03, BASE + 1.1), 0.018, seg=4)
    # earth ramp behind the step (rear row top -> ground)
    B.prism("earth", [(RY1 - 0.05, BASE), (RY1 - 0.05, BASE + 1.0), (RY1 + 0.35, BASE + 0.95), (1.95, BASE)], "x", -4.0, 4.0)
    # a few sandbags + a wooden plank on the fire step (central, keeps the tile edges clean)
    K.sandbag_row(B, (-1.6, -0.2), (-0.3, -0.2), BASE + 1.28, layers=1)
    K.sandbag_row(B, (1.4, -0.2), (2.6, -0.2), BASE + 1.28, layers=2)
    B.span("wood", -3.2, -2.0, -0.45, -0.2, BASE + 1.28, BASE + 1.34)
    # unit placard on the front (team colour) + stencil plate
    B.span("metal", 0.62, 1.38, FY0 - 0.08, FY0 - 0.03, BASE + 1.45, BASE + 1.95)
    B.span("team", 0.68, 1.32, FY0 - 0.1, FY0 - 0.08, BASE + 1.51, BASE + 1.89)
    B.span("team", -2.5, -2.38, FY0 - 0.08, FY0 - 0.03, BASE + 0.3, BASE + 2.15)  # team marker tape on a joint
    # rear marker lamps (battery perimeter lights) on stakes at the back of the step
    for k, x in enumerate((-2.5, 2.5)):
        B.strut("metal", (x, RY1 + 0.12, BASE + 0.9), (x, RY1 + 0.12, BASE + 1.45), 0.025, seg=5)
        B.span("dark", x - 0.09, x + 0.09, RY1 + 0.04, RY1 + 0.2, BASE + 1.45, BASE + 1.55, bottom=True)
        kit.light(f"Light_Status{k}", [("cyl", (x, RY1 + 0.12, BASE + 1.62), 0.09, 0.14, (0, 0, 0), 8)])
    B.build()
    return kit.finish(A.out, "hesco.glb", ground_size=40)


if not A.skip_build:
    build()
if A.previews:
    K.previews(GLB, A.previews, "m1_hesco", K.std_shots(9.0, 2.4), only=A.only, concept=A.concept)
