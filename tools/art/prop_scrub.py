"""Steel Accord - map prop: dry desert shrub (~1.7 m wide, ~0.9 m tall): low rounded mound of dusty grey-green
foliage puffs with bare woody twigs poking out. Original. Scatter many with random yaw/scale.

Run:  python3 -I prop_scrub.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/scrub.glb - one mesh node `Scrub`; origin = root on the ground.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C
K = C.K
import numpy as np
from mathutils import Vector as V

A = K.Args(sys.argv[1:])
PI = math.pi


def build():
    kit = K.Kit("scrub", "SB", atlas=512, ao_res=256, ao_dist=0.6)
    S = kit.part("Scrub")
    rng = np.random.default_rng(23)
    C.blob(S, "shrub", (0.0, 0.0, 0.18), 0.62, 99, squash=0.55, subdiv=3, amp=0.3)          # dense core mound
    for k in range(16):                                          # foliage puffs on a dome
        a = 2 * PI * k / 16 + rng.normal(0, 0.15)
        el = rng.uniform(0.15, 0.95)
        r = 0.62 * math.cos(el) + rng.uniform(-0.05, 0.08)
        p = V((r * math.cos(a), r * math.sin(a), 0.12 + 0.55 * math.sin(el)))
        C.blob(S, "shrub", tuple(p), rng.uniform(0.17, 0.27), 100 + k, squash=0.8, subdiv=2, amp=0.35)
    for k in range(14):                                          # bare twigs poking out of the mound
        a = 2 * PI * k / 14 + rng.normal(0, 0.3)
        el = rng.uniform(0.25, 1.1)
        p0 = V((0.25 * math.cos(a), 0.25 * math.sin(a), 0.2))
        L = rng.uniform(0.75, 1.0)
        p1 = p0 + V((L * math.cos(a) * math.cos(el), L * math.sin(a) * math.cos(el), L * math.sin(el) * 0.85))
        S.strut("twig", p0, p1, 0.014, seg=3)
        pm = p0.lerp(p1, 0.6)
        S.strut("twig", pm, pm + V((0.18 * math.cos(a + 0.8), 0.18 * math.sin(a + 0.8), 0.12)), 0.008, seg=3)
    S.span("earth", -0.55, 0.55, -0.55, 0.55, -0.05, 0.03)          # small dust mound (hides the stem base)
    S.build()
    return kit


C.finish_and_preview(build, A, "scrub.glb", "prop_scrub",
                     [dict(name="rts", az=-38, el=52, dist=5.5, target=(0, 0, 0.4)), dict(name="front", az=0, el=12, dist=5.5, target=(0, 0, 0.4)),
                      dict(name="top", az=0, el=89.9, dist=10, ortho=2.4, target=(0, 0, 0))], ground=8)
