"""Steel Accord - M1 prop: air-dropped supply crate with a deployed cargo parachute.

Run:  python3 -I prop_supply_crate_chute.py <out_dir> [--previews <dir>] [--only rts] [--previews-only]
Out:  <out_dir>/supply_crate_chute.glb
  Crate  - strapped 2 x 2 m pallet load (~1.5 m tall), corner boards, 4 risers up to the clevis; origin = crate
           bottom centre (ground)
  Canopy - round cargo canopy (16 alternating olive / sand gores, apex vent) + 16 suspension lines down to the
           clevis; origin = the suspension point (clevis, 2.6 m above the ground) so the game can scale / collapse /
           hide it independently of the crate. Canvas is double-sided.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import numpy as np
from mathutils import Matrix, Euler, Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "supply_crate_chute.glb")
PI = math.pi
CLEVIS = (0.0, 0.0, 2.6)
GORES = 16


def build():
    kit = K.Kit("supply_crate_chute", "SC", atlas=1024, ao_res=512, ao_dist=1.5)
    C = kit.part("Crate")
    N = kit.part("Canopy", pivot=CLEVIS)

    # ---------------------------------------------------------------- pallet + load
    C.span("pallet", -1.0, 1.0, -1.0, 1.0, 0.0, 0.05)
    for y in (-0.85, 0.0, 0.85):
        C.span("pallet", -1.0, 1.0, y - 0.1, y + 0.1, 0.05, 0.12)
    C.span("pallet", -1.0, 1.0, -1.0, 1.0, 0.12, 0.17)
    z = 0.17
    for layer, (h, surf) in enumerate(((0.62, "crate"), (0.62, "tcrate"))):
        for i in (-1, 1):
            for j in (-1, 1):
                C.span(surf, i * 0.49 - 0.47, i * 0.49 + 0.47, j * 0.49 - 0.47, j * 0.49 + 0.47, z, z + h, bev=True)
        z += h + 0.01
    top = z
    # corner boards + straps (two each way, over the top and down the sides)
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.span("wood", sx * 0.97 - 0.05, sx * 0.97 + 0.05, sy * 0.97 - 0.05, sy * 0.97 + 0.05, 0.17, top + 0.02)
    for t in (-0.5, 0.5):
        C.span("strap", t - 0.05, t + 0.05, -1.0, 1.0, top, top + 0.02)
        C.span("strap", -1.0, 1.0, t - 0.05, t + 0.05, top + 0.005, top + 0.025)
        for s in (-1, 1):
            C.span("strap", t - 0.05, t + 0.05, s * 1.0 - 0.015, s * 1.0 + 0.015, 0.12, top + 0.02)
            C.span("strap", s * 1.0 - 0.015, s * 1.0 + 0.015, t - 0.05, t + 0.05, 0.12, top + 0.02)
    C.span("team", -0.35, 0.35, -1.0 - 0.02, -1.0, 0.6, 0.95, bottom=True)              # team ID panel (front)
    C.span("yellow", -0.9, -0.5, -1.0 - 0.02, -1.0, 1.3, 1.4, bottom=True)              # stencil band
    # risers from the top corners to the clevis
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.strut("strap", (sx * 0.9, sy * 0.9, top + 0.02), CLEVIS, 0.035, seg=4)
    C.box("metal", CLEVIS, (0.18, 0.18, 0.14), bottom=True)

    # ---------------------------------------------------------------- canopy (separate object)
    SKIRT_Z, APEX_Z, RS, RV = 6.5, 9.0, 3.3, 0.35
    outer = [(RV, APEX_Z - 0.05), (1.1, APEX_Z - 0.12), (1.9, APEX_Z - 0.42), (2.55, APEX_Z - 0.95),
             (3.0, APEX_Z - 1.6), (RS, SKIRT_Z + 0.25), (RS - 0.08, SKIRT_Z)]
    inner = [(r - 0.05, z - 0.07) for r, z in outer[::-1]]
    prof = outer + inner
    for g in range(GORES):
        a0 = 2 * PI * g / GORES
        N.lathe("canvas_o" if g % 2 == 0 else "canvas_t", prof, seg=3, a0=a0, a1=a0 + 2 * PI / GORES, closed_prof=True)
    # radial seam tapes on the outside + skirt hem
    for g in range(GORES):
        a = 2 * PI * g / GORES
        pts = [(r * math.cos(a) * 1.006, r * math.sin(a) * 1.006, z + 0.02) for r, z in outer[:-1]]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            N.strut("olive", p0, p1, 0.03, seg=3)
    # suspension lines: skirt points -> clevis
    for g in range(GORES):
        a = 2 * PI * g / GORES
        N.strut("white", ((RS - 0.1) * math.cos(a), (RS - 0.1) * math.sin(a), SKIRT_Z + 0.02), CLEVIS, 0.018, seg=3)

    C.build(); N.build()
    return kit.finish(A.out, "supply_crate_chute.glb", ground_size=30)


if not A.skip_build:
    build()
if A.previews:
    shots = [dict(name="rts", az=-38, el=40, dist=24, target=(0, 0, 4.2)),
             dict(name="front", az=0, el=8, dist=24, target=(0, 0, 4.4)),
             dict(name="side", az=-90, el=-12, dist=22, target=(0, 0, 5.0)),          # from below: canopy underside
             dict(name="top", az=0, el=89.9, dist=40, ortho=8.0, target=(0, 0, 0))]
    K.previews(GLB, A.previews, "m1_crate", shots, only=A.only)
