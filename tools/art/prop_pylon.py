"""Steel Accord - map prop: rural lattice power-line pylon (~21 m, "cat-head" single circuit). Original.

Run:  python3 -I prop_pylon.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/pylon.glb - mesh node `Pylon` + empties for the game to string conductors between pylons:
        Wire_0, Wire_1, Wire_2  conductor attachment points (insulator string bottoms; left / centre / right)
        Earth_0, Earth_1        earth-wire peaks
      The line runs along local Blender Y (= Godot Z): rotate the pylon so its local Z points along the line.
      Origin = tower centre on the ground; footings stand 0.4 m proud and continue 0.5 m below for slopes.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C
K = C.K
import numpy as np
from mathutils import Vector as V

A = K.Args(sys.argv[1:])


def build():
    kit = K.Kit("pylon", "PY", atlas=1024, ao_res=512, ao_dist=2.0)
    P = kit.part("Pylon")
    B0, B1, Z1 = 2.2, 0.75, 15.0                                  # half base, half width at the waist, waist height
    ZA, ZH, ZT = 15.0, 19.0, 20.6                                 # main arm, cat-head bar, top
    rr = 0.07

    def leg_pt(sx, sy, z):
        if z <= Z1:
            w = B0 + (B1 - B0) * z / Z1
        else:
            w = B1 + 0.55 * (z - Z1) / (ZH - Z1)                  # flares out to the cat-head
        return V((sx * w, sy * w, z))
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    levels = [0.4, 3.2, 5.8, 8.2, 10.4, 12.6, Z1, 17.0, ZH]
    for sx, sy in corners:                                        # footings + legs
        P.span("conc", sx * B0 - 0.4, sx * B0 + 0.4, sy * B0 - 0.4, sy * B0 + 0.4, -0.5, 0.4, bev=True)
        for z0, z1 in zip(levels[:-1], levels[1:]):
            P.strut("galv", leg_pt(sx, sy, z0), leg_pt(sx, sy, z1), rr, seg=4)
    for i, (z0, z1) in enumerate(zip(levels[:-1], levels[1:])):   # horizontals + X bracing on each face
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            P.strut("galv", leg_pt(*a, z1), leg_pt(*b, z1), rr * 0.7, seg=4)
            if z1 <= Z1 + 0.01:
                P.strut("galv", leg_pt(*a, z0), leg_pt(*b, z1), rr * 0.55, seg=4)
                P.strut("galv", leg_pt(*b, z0), leg_pt(*a, z1), rr * 0.55, seg=4)
    # main cross arm (along X), triangular truss
    AL = 5.2
    for sx in (-1, 1):
        root_b = [leg_pt(sx, -1, ZA), leg_pt(sx, 1, ZA)]
        tip = V((sx * AL, 0, ZA))
        top_root = leg_pt(sx, 0, ZA + 1.3); top_root.y = 0
        for r in root_b:
            P.strut("galv", r, tip, rr * 0.8, seg=4)
        P.strut("galv", top_root, tip, rr * 0.7, seg=4)
        for t in (0.35, 0.7):
            m = root_b[0].lerp(tip, t); n = root_b[1].lerp(tip, t); u = top_root.lerp(tip, t)
            P.strut("galv", m, n, rr * 0.5, seg=4); P.strut("galv", m, u, rr * 0.5, seg=4); P.strut("galv", n, u, rr * 0.5, seg=4)
    # cat-head: horizontal bar between the flared legs + top peaks for the earth wires
    for sy in (-1, 1):
        P.strut("galv", leg_pt(-1, sy, ZH), leg_pt(1, sy, ZH), rr * 0.8, seg=4)
    for sx in (-1, 1):
        peak = V((sx * 1.15, 0, ZT + 0.6))
        for sy in (-1, 1):
            P.strut("galv", leg_pt(sx, sy, ZH), peak, rr * 0.6, seg=4)
        kit.empty(f"Earth_{0 if sx < 0 else 1}", tuple(peak))
    # insulator strings: two on the main arm tips, one hanging from the cat-head bar centre
    strings = [(-AL + 0.3, ZA), (0.0, ZH), (AL - 0.3, ZA)]
    for i, (x, z) in enumerate(strings):
        L = 1.6
        P.strut("metal", (x, 0, z), (x, 0, z - 0.15), 0.03, seg=4)
        for k in range(7):
            P.cyl("insul", (x, 0, z - 0.25 - k * 0.2), 0.13, 0.06, seg=10, bottom=True)
        P.strut("metal", (x, 0, z - 0.15), (x, 0, z - L), 0.02, seg=4)
        P.box("metal", (x, 0, z - L - 0.05), (0.12, 0.3, 0.1), bottom=True)
        kit.empty(f"Wire_{i}", (x, 0, z - L - 0.1))
    # danger plate + anti-climb band
    P.span("white", -0.35, 0.35, -1.97, -1.95, 2.6, 3.0, bottom=True)
    P.span("red", -0.2, 0.2, -1.98, -1.97, 2.75, 2.9, bottom=True)
    P.strut("galv", (-1.9, -1.93, 2.8), (1.9, -1.93, 2.8), 0.04, seg=4)
    P.build()
    return kit


C.finish_and_preview(build, A, "pylon.glb", "prop_pylon",
                     [dict(name="rts", az=-38, el=52, dist=48, target=(0, 0, 9)), dict(name="front", az=0, el=8, dist=48, target=(0, 0, 10)),
                      dict(name="top", az=0, el=89.9, dist=60, ortho=13, target=(0, 0, 0))])
