"""Steel Accord - map prop: cluster of limestone / sandstone boulders (fractured, bedded) for talus slopes and fans.

Run:  python3 -I prop_rock_cluster.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/rock_cluster.glb - one mesh node `Rocks`; footprint ~6 x 5 m, tallest boulder ~2.3 m; origin = centre
on the ground; boulders are sunk ~0.2-0.4 m so they sit on sloping ground. Closed meshes (normals recalculated).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C
K = C.K
import numpy as np

A = K.Args(sys.argv[1:])


def build():
    kit = K.Kit("rock_cluster", "RC", atlas=1024, ao_res=512, ao_dist=1.5)
    R = kit.part("Rocks")
    # (surface, centre, size (half extents x, y, z), seed, yaw, facet, strata, flat_top)
    rocks = [("lime", (-0.6, 0.3, 0), (1.6, 1.2, 1.15), 3, 0.3, 0.2, 0.5, 0.25),
             ("lime", (1.5, -0.6, 0), (1.1, 0.9, 0.8), 5, 1.2, 0.22, 0.6, 0.2),
             ("sandstone", (0.6, 1.6, 0), (0.9, 0.7, 0.55), 8, 2.0, 0.25, 0.4, 0.3),
             ("lime", (-2.3, -1.2, 0), (0.8, 0.65, 0.5), 11, 0.7, 0.25, 0.5, 0.0),
             ("lime", (2.6, 1.0, 0), (0.55, 0.5, 0.38), 13, 2.6, 0.25, 0.0, 0.0),
             ("sandstone", (-0.1, -1.7, 0), (0.6, 0.45, 0.32), 17, 0.1, 0.25, 0.0, 0.2)]
    for surf, c, sz, seed, yaw, facet, strata, ft in rocks:
        C.boulder(R, surf, c, sz, seed, rot_z=yaw, subdiv=3, facet=facet * 0.7, sink=0.28 * sz[2] + 0.1, strata=strata, flat_top=ft)
    rng = np.random.default_rng(4)
    for k in range(9):                                          # pebbles / small chips
        x, y = rng.uniform(-2.9, 2.9), rng.uniform(-2.4, 2.4)
        s = rng.uniform(0.12, 0.28)
        C.boulder(R, "lime" if k % 2 else "sandstone", (x, y, 0), (s * 1.3, s, s * 0.7), 30 + k, rot_z=rng.uniform(0, 3),
                  subdiv=2, facet=0.2, sink=0.05)
    R.build()
    return kit


C.finish_and_preview(build, A, "rock_cluster.glb", "prop_rock_cluster", K.std_shots(6.0, 2.0, top_ortho=7.5))
