"""Steel Accord - map prop: date palm (~9 m) with a slightly bent diamond-patterned trunk, 18 keeled fronds
(double-sided material), old frond-base boots and hanging date clusters. Original.

Run:  python3 -I prop_date_palm.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/date_palm.glb - one mesh node `Palm` (materials DP_DatePalm opaque + DP_DatePalm_2S double-sided
fronds). Origin = trunk base on the ground; crown spread ~7 m.
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
    kit = K.Kit("date_palm", "DP", atlas=1024, ao_res=512, ao_dist=1.5)
    P = kit.part("Palm")
    rng = np.random.default_rng(12)
    top = V((0.45, 0.25, 8.6))
    C.trunk(P, "bark", (0, 0, -0.3), top, 0.3, 0.22, seg=10, rings=10, bend=(0.35, 0.2), seed=1.0)
    P.cyl("bark", (0, 0, 0.05), 0.42, 0.5, seg=10, r2=0.3)                      # root flare
    # boots: rough collar of old frond bases under the crown
    for k in range(10):
        a = 2 * PI * k / 10 + 0.3
        p0 = top + V((0.2 * math.cos(a), 0.2 * math.sin(a), -0.9))
        p1 = top + V((0.55 * math.cos(a), 0.55 * math.sin(a), -0.15))
        P.strut("twig", p0, p1, 0.07, seg=4)
    P.cyl("bark", tuple(top + V((0, 0, -0.1))), 0.34, 0.6, seg=10, r2=0.2)
    # fronds: arching keeled ribbons in two whorls
    for k in range(18):
        whorl = k % 2
        a = 2 * PI * k / 18 + rng.normal(0, 0.08) + whorl * 0.17
        L = rng.uniform(3.6, 4.4) * (0.85 if whorl else 1.0)
        rise = rng.uniform(0.6, 1.4) if whorl else rng.uniform(-0.2, 0.8)       # inner whorl stands up more
        droop = rng.uniform(1.6, 2.4)
        pts, wid = [], []
        n = 8
        for i in range(n + 1):
            t = i / n
            r = L * t
            z = rise * 2.2 * t - droop * t * t
            pts.append(tuple(top + V((r * math.cos(a), r * math.sin(a), 0.1 + z))))
            wid.append(0.05 + 0.42 * math.sin(min(1.0, t * 1.15) * PI) * (1 - 0.3 * t))
        C.ribbon(P, "frond", pts, wid, keel=0.35)
    # date clusters hanging below the crown
    for k in range(4):
        a = 2 * PI * k / 4 + 0.6
        c = top + V((0.55 * math.cos(a), 0.55 * math.sin(a), -0.75))
        P.strut("strap", tuple(top + V((0.25 * math.cos(a), 0.25 * math.sin(a), -0.3))), tuple(c), 0.03, seg=4)
        C.blob(P, "dates", tuple(c + V((0, 0, -0.25))), 0.28, 70 + k, squash=1.4, subdiv=1, amp=0.3)
    P.build()
    return kit


C.finish_and_preview(build, A, "date_palm.glb", "prop_date_palm",
                     [dict(name="rts", az=-38, el=52, dist=26, target=(0, 0, 4.5)), dict(name="front", az=0, el=10, dist=26, target=(0, 0, 4.5)),
                      dict(name="top", az=0, el=89.9, dist=40, ortho=10, target=(0, 0, 0))])
