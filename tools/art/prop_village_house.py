"""Steel Accord - map prop: rural flat-roofed house (mud-plaster over brick, lime-washed annex) with a low mud-brick
courtyard wall. Original design for the fictional villages of the Zagros Basin map.

Run:  python3 -I prop_village_house.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/village_house.glb - one mesh node `House` (materials VH_VillageHouse, VH_VillageHouse_2S unused).
Footprint ~8 x 8 m (x, y in [-4, 4]); origin = footprint centre on the ground; the courtyard gate faces the front
(Blender -Y = Godot +Z). Walls continue 0.5 m below the origin so the house sits on uneven terrain without gaps.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C
K = C.K
import numpy as np

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "village_house.glb")
PI = math.pi
SUB = -0.5                                       # walls start below ground


def build():
    kit = K.Kit("village_house", "VH", atlas=1024, ao_res=512, ao_dist=2.0)
    H = kit.part("House")
    # ---------------------------------------------------------------- main block + annex
    MX0, MX1, MY0, MY1, MH = -3.6, 1.3, 0.1, 3.9, 3.05
    H.span("mud", MX0, MX1, MY0, MY1, SUB, MH)
    H.span("mud", MX0 - 0.05, MX1 + 0.05, MY0 - 0.05, MY1 + 0.05, MH, MH + 0.12, bottom=True)          # roof slab edge
    for (x0, x1, y0, y1) in ((MX0, MX1, MY0, MY0 + 0.22), (MX0, MX1, MY1 - 0.22, MY1),
                             (MX0, MX0 + 0.22, MY0, MY1), (MX1 - 0.22, MX1, MY0, MY1)):
        H.span("mud", x0, x1, y0, y1, MH + 0.12, MH + 0.5)                                           # parapet
    H.span("conc", MX0 + 0.22, MX1 - 0.22, MY0 + 0.22, MY1 - 0.22, MH + 0.1, MH + 0.14)               # roof screed
    AX0, AX1, AY0, AY1, AH = MX1, 3.85, 1.0, 3.9, 2.55
    H.span("plaster", AX0, AX1, AY0, AY1, SUB, AH)
    H.span("plaster", AX0, AX1 + 0.05, AY0 - 0.05, AY1 + 0.05, AH, AH + 0.25, bottom=True)
    H.span("mud", AX0 - 0.02, AX1 + 0.02, AY0 - 0.02, AY1 + 0.02, SUB, 0.35, bev=True)                  # plinth
    H.span("mud", MX0 - 0.04, MX1, MY0 - 0.04, MY1 + 0.04, SUB, 0.4, bev=True)
    # protruding roof beams (front + rear, main block) and rain spouts
    for x in np.arange(MX0 + 0.45, MX1 - 0.2, 0.62):
        for y0, y1 in ((MY0 - 0.35, MY0), (MY1, MY1 + 0.35)):
            H.span("woodold", x - 0.07, x + 0.07, y0, y1, MH - 0.28, MH - 0.14)
    for (x, y, dx, dy) in ((MX0 + 0.8, MY1, 0, 1), (MX0, 2.4, -1, 0), (AX1, 2.6, 1, 0)):
        z = (MH if x < MX1 else AH) + 0.05
        H.span("metal", min(x, x + dx * 0.6) - (0.06 if dx == 0 else 0), max(x, x + dx * 0.6) + (0.06 if dx == 0 else 0),
               min(y, y + dy * 0.6) - (0.06 if dy == 0 else 0), max(y, y + dy * 0.6) + (0.06 if dy == 0 else 0), z, z + 0.1)
    # ---------------------------------------------------------------- openings (front = -Y)
    fy = MY0
    H.span("woodold", -2.75, -1.85, fy - 0.06, fy, 0.35, 2.35, bottom=True)                           # door frame
    H.span("doorb", -2.68, -1.92, fy - 0.08, fy - 0.06, 0.38, 2.27, bottom=True)                       # door leaf
    H.span("woodold", -2.95, -1.65, fy - 0.3, fy, 2.4, 2.5, bottom=True)                              # lintel/hood
    for x in (-0.6, 0.6):
        H.span("woodold", x - 0.42, x + 0.42, fy - 0.05, fy, 1.15, 1.95, bottom=True)
        H.span("dark", x - 0.34, x + 0.34, fy - 0.06, fy - 0.05, 1.22, 1.88, bottom=True)
        for k in range(4):
            xx = x - 0.25 + k * 0.17
            H.span("metal", xx - 0.015, xx + 0.015, fy - 0.09, fy - 0.06, 1.22, 1.88, bottom=True)
    H.span("doorb", AX0 + 0.6, AX0 + 1.4, AY0 - 0.05, AY0, 0.35, 2.15, bottom=True)                    # annex door
    H.span("dark", AX0 + 1.75, AX0 + 2.25, AY0 - 0.05, AY0, 1.25, 1.75, bottom=True)
    for (x, y, nx) in ((MX0, 2.0, -1), (AX1, 2.4, 1)):                                              # side windows
        H.span("dark", x + nx * 0.05 - 0.03, x + nx * 0.05 + 0.03, y - 0.3, y + 0.3, 1.3, 1.85)
    H.span("dark", -1.6, -1.0, MY1, MY1 + 0.05, 1.5, 2.0)                                            # rear window
    # ---------------------------------------------------------------- roof clutter
    H.cyl("white", (-2.8, 3.0, MH + 0.62), 0.45, 0.95, seg=12)                                       # water tank
    H.cyl("metal", (-2.8, 3.0, MH + 1.1), 0.12, 0.05, seg=8, bottom=True)
    H.span("metal", -3.3, -2.3, 2.5, 3.5, MH + 0.12, MH + 0.16)
    H.cyl("dark", (0.6, 3.2, MH + 0.25), 0.12, 0.3, seg=8)                                           # flue
    H.box("metal", (0.6, 3.2, MH + 0.45), (0.3, 0.3, 0.06), bottom=True)
    H.strut("metal", (-1.0, 3.4, MH + 0.12), (-1.0, 3.4, MH + 1.6), 0.025, seg=4)                     # antenna mast
    H.strut("metal", (-1.4, 3.4, MH + 1.5), (-0.6, 3.4, MH + 1.5), 0.015, seg=4)
    H.span("woodold", -0.4, 1.0, 1.0, 2.6, MH + 0.12, MH + 0.2)                                      # drying rack
    # stair to the roof against the annex front (solid mud steps)
    for k in range(7):
        z1 = 0.4 * (k + 1)
        H.span("mud", AX0 + 1.9 + 0.0, AX0 + 2.5, AY0 - 0.1 - (7 - k) * 0.32, AY0 - 0.1 - (6 - k) * 0.32, SUB, z1, bev=True)
    # ---------------------------------------------------------------- courtyard wall (mud brick, worn caps), gate
    WT, WH = 0.34, 1.55

    def wall(x0, y0, x1, y1, h=WH):
        if abs(y1 - y0) < 1e-6:
            H.span("mudbrick", x0, x1, y0 - WT / 2, y0 + WT / 2, SUB, h)
            H.prism("mud", [(y0 - WT / 2 - 0.03, h), (y0 + WT / 2 + 0.03, h), (y0 + 0.06, h + 0.16), (y0 - 0.06, h + 0.16)], "x", x0, x1)
        else:
            H.span("mudbrick", x0 - WT / 2, x0 + WT / 2, y0, y1, SUB, h)
            H.prism("mud", [(x0 - WT / 2 - 0.03, h), (x0 + WT / 2 + 0.03, h), (x0 + 0.06, h + 0.16), (x0 - 0.06, h + 0.16)], "y", y0, y1)
    wall(-3.95, -3.95, 0.3, -3.95)
    wall(2.3, -3.95, 3.95, -3.95)
    wall(-3.95, -3.95, -3.95, 0.1)
    wall(3.95, -3.95, 3.95, 1.0)
    for x in (0.3, 2.3):                                                                             # gate piers
        H.span("mud", x - 0.25 if x > 1 else x - 0.05, x + 0.05 if x > 1 else x + 0.25, -4.2, -3.7, SUB, 2.0, bev=True)
    H.span("doorb", 0.55, 1.3, -3.98, -3.92, 0.05, 1.65, bottom=True)                               # gate leaf (half open)
    H.box("doorb", (1.75, -3.6, 0.85), (0.06, 0.75, 1.6), rot=(0, 0, 0.6))
    # ---------------------------------------------------------------- courtyard dressing
    H.span("earth", -3.78, 3.78, -3.78, MY0 - 0.02, -0.06, 0.03)                                     # swept earth floor
    H.cyl("mud", (-2.9, -2.9, 0.4), 0.45, 0.8, seg=10, r2=0.3)                                       # bread oven (tanoor)
    H.cyl("dark", (-2.9, -2.9, 0.81), 0.2, 0.02, seg=10, bottom=True)
    H.span("woodold", -1.3, 0.3, -1.0, -0.6, 0.0, 0.45, bev=True)                                    # bench
    for k, (x, y) in enumerate(((2.9, -1.5), (3.3, -2.2), (2.6, -2.4))):                             # water jars
        H.cyl("sandstone", (x, y, 0.32), 0.24, 0.64, seg=10, r2=0.14)
    for k in range(5):                                                                               # firewood pile
        y = -3.3 + k * 0.12
        H.strut("woodold", (0.9, y, 0.08 + 0.1 * (k % 2)), (2.2, y + 0.05, 0.08 + 0.1 * (k % 2)), 0.06, seg=5)
    # clothes line between the house and the wall
    H.strut("metal", (-3.6, -0.3, 0.0), (-3.6, -0.3, 1.9), 0.03, seg=4)
    H.strut("dark", (-3.6, -0.3, 1.85), (-1.5, -2.5, 1.85), 0.008, seg=3)
    H.strut("metal", (-1.5, -2.5, 0.0), (-1.5, -2.5, 1.9), 0.03, seg=4)
    H.box("red", (-2.9, -1.0, 1.55), (0.6, 0.02, 0.55), rot=(0, 0, -0.8))
    H.box("blue", (-2.2, -1.75, 1.6), (0.5, 0.02, 0.45), rot=(0, 0, -0.8))
    H.build()
    return kit


C.finish_and_preview(build, A, "village_house.glb", "prop_village_house", K.std_shots(8.0, 3.6, top_ortho=10.0))
