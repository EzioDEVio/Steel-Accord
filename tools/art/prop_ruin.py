"""Steel Accord - map prop: ruined walled compound (old caravan-stop style; fictional): broken mud-brick / rubble-stone
walls with jagged tops, one standing arched portal, collapsed rubble mounds and fallen roof beams. Original design.

Run:  python3 -I prop_ruin.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/ruin.glb - one mesh node `Ruin`. Footprint ~11 x 10 m; origin = footprint centre on the ground;
the arch faces the front (Blender -Y = Godot +Z). Walls continue 0.5 m below the origin for uneven terrain.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C
K = C.K
import numpy as np

A = K.Args(sys.argv[1:])
PI = math.pi
SUB = -0.5


def build():
    kit = K.Kit("ruin", "RU", atlas=1024, ao_res=512, ao_dist=2.0)
    R = kit.part("Ruin")
    rng = np.random.default_rng(31)
    T = 0.6                                                    # wall thickness

    def broken_wall(a, b, h0, h1, surf="mudbrick", piece=0.55, gaps=()):
        """Wall from a to b as vertical slices with jagged (random-walk) top between h0 and h1."""
        a = np.array(a, float); b = np.array(b, float)
        L = float(np.linalg.norm(b - a)); n = max(1, int(round(L / piece)))
        d = (b - a) / L; ang = math.atan2(d[1], d[0])
        hh = rng.uniform(h0, h1)
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            tm = (t0 + t1) / 2
            if any(g0 <= tm <= g1 for g0, g1 in gaps):
                continue
            hh = float(np.clip(hh + rng.normal(0, 0.35), h0, h1))
            c = a + (b - a) * tm
            th = T * rng.uniform(0.85, 1.0)
            R.box(surf, (c[0], c[1], (SUB + hh) / 2), (L / n + 0.01, th, hh - SUB), rot=(0, 0, ang))
            if rng.random() < 0.35:                                # loose bricks on top
                R.box("mudbrick", (c[0] + rng.normal(0, 0.1), c[1] + rng.normal(0, 0.1), hh + 0.08),
                      (0.36, 0.22, 0.14), rot=(0, 0, ang + rng.normal(0, 0.4)), bottom=True)

    # perimeter: x in [-5.3, 5.3], y in [-4.8, 4.8]; front (y = -4.8) has the arched portal in the middle
    broken_wall((-5.3, -4.8), (-1.6, -4.8), 0.6, 2.4, gaps=((0.1, 0.32),))
    broken_wall((1.6, -4.8), (5.3, -4.8), 0.4, 1.8)
    broken_wall((5.3, -4.8), (5.3, 4.8), 0.5, 3.0, surf="sandstone", gaps=((0.42, 0.62),))
    broken_wall((5.3, 4.8), (-5.3, 4.8), 1.2, 3.4, gaps=((0.15, 0.3),))
    broken_wall((-5.3, 4.8), (-5.3, -4.8), 0.3, 2.6, surf="sandstone", gaps=((0.55, 0.85),))
    # interior cross wall (a collapsed room at the rear)
    broken_wall((-5.0, 1.2), (1.0, 1.2), 0.3, 2.2, piece=0.5, gaps=((0.45, 0.6),))
    broken_wall((1.0, 1.2), (1.0, 4.5), 0.6, 2.8, piece=0.5)
    # arched portal (iwan front): thick wall with a pointed arch opening, extruded along y
    W0, W1, PH, AW, AS = -1.8, 1.8, 4.3, 1.05, 2.3            # extents, portal height, arch half width, spring height
    prof = [(W0, SUB), (-AW, SUB), (-AW, AS)]
    for k in range(1, 8):                                       # pointed arch: two arcs meeting at the apex
        t = k / 8
        a = PI * (1 - t) / 2 * 1.0
        prof.append((-AW + AW * (1 - math.cos(t * PI / 2)) * 0.98, AS + 1.55 * math.sin(t * PI / 2)))
    prof.append((0.0, AS + 1.6))
    for k in range(7, 0, -1):
        t = k / 8
        prof.append((AW - AW * (1 - math.cos(t * PI / 2)) * 0.98, AS + 1.55 * math.sin(t * PI / 2)))
    prof += [(AW, AS), (AW, SUB), (W1, SUB), (W1, PH - 0.4), (0.9, PH), (-0.6, PH - 0.15), (W0, PH - 0.7)]
    R.prism("mudbrick", prof, "y", -5.15, -4.45)
    R.span("plaster", -1.5, 1.2, -5.17, -5.15, AS + 1.72, AS + 1.98, bottom=True)              # traces of tile frieze
    R.span("blue", -1.4, 0.5, -5.18, -5.17, AS + 1.78, AS + 1.92, bottom=True)
    R.span("plaster", -1.6, -1.25, -5.17, -5.15, SUB + 0.6, AS + 1.9, bottom=True)              # frame pilasters
    R.span("plaster", 1.25, 1.6, -5.17, -5.15, SUB + 0.6, AS + 0.9, bottom=True)
    # rubble mounds (fallen walls)
    for k, (x, y, sx, sy, sz) in enumerate(((-3.6, -3.4, 1.4, 1.0, 0.45), (3.3, 2.8, 1.8, 1.3, 0.6), (-2.2, 3.2, 1.5, 1.1, 0.5),
                                             (5.9, 0.6, 1.2, 1.4, 0.4), (2.6, -5.6, 1.4, 0.8, 0.35), (-5.9, -0.8, 0.9, 1.3, 0.35))):
        C.boulder(R, "rubble", (x, y, 0.0), (sx, sy, sz), 40 + k, rot_z=k * 0.9, subdiv=2, facet=0.25, sink=0.3)
    for k in range(14):                                          # loose blocks
        x, y = rng.uniform(-6.0, 6.0), rng.uniform(-5.8, 5.6)
        R.box("mudbrick" if k % 3 else "sandstone", (x, y, 0.1), (rng.uniform(0.3, 0.5), rng.uniform(0.2, 0.35), 0.22),
              rot=(rng.normal(0, 0.2), rng.normal(0, 0.2), rng.uniform(0, PI)))
    # fallen roof beams across the rear room + a leaning one
    R.strut("woodold", (-4.6, 2.0, 0.15), (-1.0, 3.9, 0.35), 0.11, seg=6)
    R.strut("woodold", (-3.8, 1.5, 2.0), (-4.9, 4.2, 0.1), 0.1, seg=6)
    R.strut("woodold", (0.6, 2.4, 2.4), (-0.6, 3.6, 0.1), 0.1, seg=6)
    # a dead tree stump by the portal
    R.strut("twig", (2.6, -6.0, -0.2), (2.75, -6.1, 1.4), 0.12, seg=6)
    R.strut("twig", (2.72, -6.08, 1.1), (3.3, -6.4, 1.9), 0.05, seg=4)
    R.build()
    return kit


C.finish_and_preview(build, A, "ruin.glb", "prop_ruin", K.std_shots(12.0, 4.0, top_ortho=14.0))
