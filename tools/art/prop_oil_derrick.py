"""Steel Accord - map prop: capturable oil well site (beam pumpjack on a fenced gravel pad). Original design.

Run:  python3 -I prop_oil_derrick.py <out_dir> [--previews <dir>] [--only rts,cull] [--previews-only]
Out:  <out_dir>/oil_derrick.glb  (pad ~10 m (X) x 14 m (Y); front = Blender -Y = Godot +Z = the wellhead end)

Nodes (metres, origin = pad centre on the ground):
  Base         static: gravel pad, skid + foundation, samson post, gearbox, motor + belt guard, wellhead, flowline,
               storage tank (SA_Team band), control box, fence posts + chain-link, flag pole   [OD_OilDerrick, SA_Team]
  WalkingBeam  origin at the saddle bearing on top of the samson post (0, -0.8, 5.15) [Blender];
               the game rocks it about its LOCAL X axis.
    HorseHead  child of WalkingBeam (origin at the beam nose): arc head + bridle + carrier bar + polished rod
    Pitman     child of WalkingBeam (origin at the equalizer bearing (0, 1.4, 4.75)): equalizer + 2 pitman arms
               hanging to the crank pins; the game may re-aim it at the crank pins or leave it riding on the beam.
  Crank        origin at the gearbox output axle (0, 1.4, 1.9) [Blender]; the game spins it about its LOCAL X axis.
               At rest the crank pins point to -Y (towards the well) at radius 1.0 m.
  Flag         empty at the flag-pole top (owner flag attachment point)

Animation hint (not baked): crank angle theta (continuous); beam angle ~= asin(1.0 * sin(theta) / 2.2) (radians,
rear arm 2.2 m). One stroke every ~4 s reads well at RTS distance.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_zb_common as C  # noqa: applies the face-normal fix for tile UVs
K = C.K
import numpy as np
from mathutils import Matrix, Euler, Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "oil_derrick.glb")
PI = math.pi
PIVOT = (0.0, -0.8, 5.15)          # saddle bearing
NOSE = (0.0, -3.35, 5.15)          # beam / horse head joint
EQ = (0.0, 1.4, 4.75)              # equalizer bearing (pitman top)
AXLE = (0.0, 1.4, 1.9)             # crank axle
WELL_Y = -4.6                      # wellhead centre line (= PIVOT.y - head radius)
HEAD_R = 3.8


def t_paint():         # weathered pumpjack paint (sand-ochre), streaks + chips
    k = 1 + 0.03 * K.noise(40, 40, 401) + 0.02 * K.noise(2, 2, 402) - 0.07 * np.clip(K.noise(2, 60, 403), 0, None)
    chips = (K.noise(3, 3, 404) > 2.1).astype(np.float32)
    img = K.shade(K.col(186, 150, 72), k)
    return img * (1 - 0.45 * chips)[..., None]


def t_steel():         # dark painted steel with rust-brown grime
    k = 1 + 0.04 * K.noise(30, 30, 411) + 0.03 * K.noise(2, 2, 412)
    rust = np.clip(K.noise(6, 6, 413) - 1.0, 0, None)[..., None]
    img = K.shade(K.col(72, 74, 72), k)
    return img * (1 - 0.3 * rust) + K.col(110, 70, 42)[None, None] * 0.3 * rust


def t_gpad():          # compacted gravel pad (S = 3 m)
    k = 1 + 0.09 * K.noise(2, 2, 421) + 0.06 * K.noise(10, 10, 422) + 0.05 * K.noise(40, 40, 423)
    img = K.shade(K.col(150, 138, 118), k)
    stones = (K.noise(1.5, 1.5, 424) > 1.7).astype(np.float32)[..., None]
    oil = np.clip(K.noise(30, 30, 425) - 1.3, 0, None)[..., None]
    return img * (1 - 0.18 * stones) * (1 - 0.35 * oil)


def t_tank():          # pale grey tank shell with weld seams
    k = (1 + 0.03 * K.noise(40, 40, 431) + 0.02 * K.noise(2, 2, 432) - 0.05 * np.clip(K.noise(2, 60, 433), 0, None))
    k *= 1 - 0.15 * K.lines(K.VV, 2, 0.006)
    return K.shade(K.col(184, 180, 168), k)


K.SURF.update({"paint": (t_paint, 3.0), "steel": (t_steel, 2.0), "gpad": (t_gpad, 3.0), "tank": (t_tank, 3.0),
               "pipe": (K.t_flat((96, 92, 84), 0.05, 440), 2.0), "valve": (K.t_flat((150, 40, 32), 0.05, 442), 1.0)})


def build():
    kit = K.Kit("oil_derrick", "OD", atlas=2048, ao_res=1024, ao_dist=2.5)
    B = kit.part("Base")
    WB = kit.part("WalkingBeam", pivot=PIVOT)
    HH = kit.part("HorseHead", pivot=NOSE)
    PM = kit.part("Pitman", pivot=EQ)
    CR = kit.part("Crank", pivot=AXLE)

    # ---------------------------------------------------------------- pad, skid, foundation
    B.frustum("gpad", -5.0, 5.0, -7.0, 7.0, 0.0, 0.14, 0.25)
    B.span("conc", -1.7, 1.7, -2.4, 4.7, 0.1, 0.4, bev=True)                          # pumpjack foundation
    for x in (-0.75, 0.75):                                                            # skid rails (I-beams)
        B.span("steel", x - 0.16, x + 0.16, -2.2, 4.5, 0.4, 0.75)
    for y in (-2.0, 0.0, 2.4, 4.2):
        B.span("steel", -0.95, 0.95, y - 0.12, y + 0.12, 0.4, 0.7)

    # ---------------------------------------------------------------- samson post (A-frame, 3 legs) + saddle
    top = V((PIVOT[0], PIVOT[1], PIVOT[2] - 0.35))
    for a in ((-1.05, -2.0, 0.75), (1.05, -2.0, 0.75)):
        B.strut("paint", a, top + V((math.copysign(0.18, a[0]), -0.05, 0)), 0.11, seg=6)
    B.strut("paint", (0.0, 0.5, 0.75), top + V((0, 0.08, 0)), 0.11, seg=6)             # rear leg
    for z in (2.0, 3.3):                                                               # cross braces
        f = (z - 0.75) / (top.z - 0.75)
        xa = -1.05 + f * (1.05 - 0.18); ya = -2.0 + f * (top.y + 0.05 + 2.0)
        B.strut("paint", (xa, ya, z), (-xa, ya, z), 0.05, seg=4)
        B.strut("paint", (xa, ya, z), (0.0, 0.5 + f * (top.y - 0.5), z), 0.04, seg=4)
    B.span("steel", -0.42, 0.42, top.y - 0.3, top.y + 0.3, top.z - 0.1, top.z + 0.12)  # saddle plate
    B.cyl("steel", PIVOT, 0.2, 0.7, rot=(0, PI / 2, 0), seg=10, bottom=True)           # bearing housing
    K.ladder(B, (0.0, 0.62, 0.75), (1, 0, 0), 10, 4.0, (0, 1, 0), m="steel", half=0.2)

    # ---------------------------------------------------------------- gearbox, motor, belt guard, brake
    gx = 0.62
    B.span("paint", -gx, gx, AXLE[1] - 0.8, AXLE[1] + 0.85, 0.75, AXLE[2] - 0.15, bev=True)   # lower case
    B.prism("paint", [(AXLE[1] - 0.8, AXLE[2] - 0.15), (AXLE[1] + 0.85, AXLE[2] - 0.15), (AXLE[1] + 0.55, AXLE[2] + 0.45),
                      (AXLE[1] - 0.5, AXLE[2] + 0.45)], "x", -gx, gx)
    B.cyl("steel", AXLE, 0.16, 2.0, rot=(0, PI / 2, 0), seg=10, bottom=True)          # output shaft (static stub)
    B.span("team", -gx - 0.01, -gx, AXLE[1] - 0.6, AXLE[1] + 0.6, 1.05, 1.3, bottom=True)   # team plate on the case
    B.span("team", gx, gx + 0.01, AXLE[1] - 0.6, AXLE[1] + 0.6, 1.05, 1.3, bottom=True)
    my = 4.05
    B.span("steel", -0.6, 0.6, my - 0.45, my + 0.45, 0.75, 0.95)                      # motor base
    B.cyl("cabinet", (0.0, my, 1.45), 0.42, 1.1, rot=(0, PI / 2, 0), seg=12, bottom=True)
    for k in range(5):                                                                 # cooling fins
        B.cyl("steel", (-0.4 + k * 0.2, my, 1.45), 0.46, 0.05, rot=(0, PI / 2, 0), seg=12, bottom=True)
    B.prism("yellow", [(AXLE[1] + 0.2, 1.0), (my, 1.0), (my, 1.95), (AXLE[1] + 0.2, 2.25)], "x", 0.66, 0.9)  # belt guard
    B.span("team", 0.9, 0.91, my - 0.9, my - 0.2, 1.3, 1.65, bottom=True)
    # control box on a post (left of the motor)
    B.cyl("steel", (-1.6, 4.2, 0.9), 0.05, 1.8, seg=6)
    K.cabinet(B, -1.6, 4.45, 0.9, 0.6, 0.3, 0.75, face="-y")

    # ---------------------------------------------------------------- wellhead + flowline
    wy = WELL_Y
    B.cyl("conc", (0, wy, 0.17), 0.85, 0.34, seg=14)                                  # cellar ring
    B.cyl("dark", (0, wy, 0.345), 0.68, 0.01, seg=14, bottom=True)
    B.cyl("pipe", (0, wy, 0.55), 0.24, 0.5, seg=10)                                   # casing head
    B.cyl("steel", (0, wy, 0.82), 0.3, 0.08, seg=10, bottom=True)                     # flange
    B.cyl("pipe", (0, wy, 1.0), 0.13, 0.36, seg=8)
    B.cyl("steel", (0, wy, 1.2), 0.2, 0.06, seg=8, bottom=True)
    B.cyl("pipe", (0, wy, 1.32), 0.11, 0.2, seg=8)                                    # stuffing box
    B.cyl("pipe", (0.35, wy, 1.0), 0.09, 0.7, rot=(0, PI / 2, 0), seg=8, bottom=True)  # tee to the flowline
    B.cyl("valve", (0.55, wy, 1.0), 0.16, 0.12, rot=(0, PI / 2, 0), seg=10, bottom=True)
    B.cyl("valve", (0.55, wy, 1.2), 0.12, 0.04, seg=10, bottom=True)                  # hand wheel
    B.strut("pipe", (0.7, wy, 1.0), (1.2, wy, 0.35), 0.07, seg=6)
    B.strut("pipe", (1.2, wy, 0.35), (2.7, 1.5, 0.35), 0.07, seg=6)                   # flowline to the tank
    B.strut("pipe", (2.7, 1.5, 0.35), (3.2, 3.4, 0.35), 0.07, seg=6)
    for t in np.linspace(0.1, 0.9, 4):                                                 # pipe sleepers
        p = V((1.2, wy, 0)).lerp(V((2.7, 1.5, 0)), t)
        B.span("wood", p.x - 0.25, p.x + 0.25, p.y - 0.08, p.y + 0.08, 0.1, 0.28)

    # ---------------------------------------------------------------- storage tank (SA_Team band) + walkway
    tx, ty, tr, th = 3.25, 4.75, 1.25, 3.0
    B.cyl("conc", (tx, ty, 0.2), tr + 0.2, 0.2, seg=16)
    B.cyl("tank", (tx, ty, 0.3 + th / 2), tr, th, seg=16)
    B.cyl("tank", (tx, ty, 0.3 + th + 0.12), tr, 0.24, seg=16, r2=0.25, bottom=True)
    B.cyl("team", (tx, ty, 2.05), tr + 0.012, 0.32, seg=16, bottom=True)
    B.cyl("steel", (tx + 0.5, ty - 0.3, 0.3 + th + 0.3), 0.08, 0.2, seg=6)            # vent
    K.ladder(B, (tx - tr - 0.02, ty, 0.3), (0, 1, 0), 9, th, (-1, 0, 0), m="steel", half=0.18)
    B.span("yellow", -4.75, -4.5, 5.6, 5.85, 0.14, 0.9)                               # bollard posts by the gate road
    # ---------------------------------------------------------------- fence posts + chain link (gate at the front)
    FX, FY, FH = 4.85, 6.85, 1.9
    runs = [((-FX, -FY), (-1.8, -FY)), ((1.8, -FY), (FX, -FY)), ((FX, -FY), (FX, FY)), ((FX, FY), (-FX, FY)),
            ((-FX, FY), (-FX, -FY))]
    for (x0, y0), (x1, y1) in runs:
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / 2.9)))
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            B.cyl("metal", (x, y, 0.1 + FH / 2), 0.04, FH + 0.05, seg=6)
        B.strut("metal", (x0, y0, FH + 0.08), (x1, y1, FH + 0.08), 0.022, seg=4)
        kit.fence((x0, y0), (x1, y1), 0.14, FH + 0.05)
    # gate leaves (open, swung outwards)
    for s in (-1, 1):
        x0 = s * 1.8
        B.cyl("metal", (x0, -FY, 0.1 + FH / 2), 0.06, FH + 0.1, seg=6)
        a = (x0, -FY); b = (x0 + s * 0.3, -FY - 1.5)
        B.strut("metal", (*a, 0.3), (*b, 0.3), 0.025, seg=4)
        B.strut("metal", (*a, FH), (*b, FH), 0.025, seg=4)
        B.strut("metal", (*b, 0.3), (*b, FH), 0.025, seg=4)
        kit.fence(a, b, 0.3, FH)
    # warning sign on the gate post + flag pole (front-left corner)
    B.span("white", -2.6, -2.0, -FY - 0.05, -FY - 0.03, 1.0, 1.4, bottom=True)
    B.span("red", -2.55, -2.05, -FY - 0.06, -FY - 0.05, 1.28, 1.36, bottom=True)
    fpx, fpy, fph = -4.3, -6.3, 4.6
    B.span("conc", fpx - 0.25, fpx + 0.25, fpy - 0.25, fpy + 0.25, 0.1, 0.35, bev=True)
    B.cyl("steel", (fpx, fpy, 0.35 + (fph - 0.35) / 2), 0.05, fph - 0.35, seg=8, r2=0.035)
    B.cyl("steel", (fpx, fpy, fph + 0.04), 0.07, 0.08, seg=8)
    kit.empty("Flag", (fpx, fpy, fph))

    # ---------------------------------------------------------------- walking beam (rocks about local X)
    bz = PIVOT[2] + 0.22
    WB.span("paint", -0.18, 0.18, NOSE[1], EQ[1] + 0.35, bz - 0.3, bz + 0.3, bev=True)     # web
    for z in (bz - 0.3, bz + 0.3):                                                         # flanges
        WB.span("paint", -0.3, 0.3, NOSE[1], EQ[1] + 0.35, z - 0.04 if z > bz else z, z + 0.04 if z < bz else z, bev=False)
    WB.span("steel", -0.32, 0.32, PIVOT[1] - 0.35, PIVOT[1] + 0.35, PIVOT[2] - 0.08, bz - 0.3)   # centre bearing block
    WB.span("team", -0.185, -0.18, PIVOT[1] - 1.6, PIVOT[1] + 1.0, bz - 0.12, bz + 0.12, bottom=True)  # team stripe
    WB.span("team", 0.18, 0.185, PIVOT[1] - 1.6, PIVOT[1] + 1.0, bz - 0.12, bz + 0.12, bottom=True)
    WB.span("yellow", -0.31, 0.31, EQ[1] - 0.05, EQ[1] + 0.35, bz + 0.34, bz + 0.36, bottom=True)  # tail cap
    # ---------------------------------------------------------------- pitman (equalizer + arms to the crank pins)
    PM.cyl("steel", (0, EQ[1], EQ[2]), 0.14, 2.0, rot=(0, PI / 2, 0), seg=10, bottom=True)     # equalizer bar
    PM.span("steel", -0.3, 0.3, EQ[1] - 0.15, EQ[1] + 0.15, EQ[2], bz - 0.3)                 # tail bearing hanger
    pin_y = AXLE[1] - 1.0
    for x in (-0.98, 0.98):
        PM.strut("paint", (x, EQ[1], EQ[2]), (x, pin_y, AXLE[2] + 0.02), 0.07, seg=6)
    # ---------------------------------------------------------------- horse head (arc about the saddle bearing)
    phi = np.radians(np.linspace(-32.0, 24.0, 15))
    outer = [(PIVOT[1] - HEAD_R * math.cos(p), PIVOT[2] + HEAD_R * math.sin(p)) for p in phi]
    inner = [(PIVOT[1] - (HEAD_R - 0.75) * math.cos(p), PIVOT[2] + (HEAD_R - 0.75) * math.sin(p)) for p in phi[::-1]]
    prof = outer + inner
    HH.prism("paint", prof, "x", -0.32, 0.32)
    HH.prism("steel", [(y, z) for y, z in outer] + [(PIVOT[1] - (HEAD_R - 0.06) * math.cos(p), PIVOT[2] + (HEAD_R - 0.06) * math.sin(p)) for p in phi[::-1]],
             "x", -0.36, 0.36)                                                                  # wear face
    HH.span("paint", -0.2, 0.2, NOSE[1] - 0.15, NOSE[1] + 0.25, bz - 0.35, bz + 0.35)          # neck to the beam
    hy = PIVOT[1] - HEAD_R                                                                       # bridle hangs here
    for x in (-0.2, 0.2):
        HH.strut("dark", (x, hy - 0.02, PIVOT[2] - 0.2), (x, hy - 0.02, 1.85), 0.022, seg=4)
    HH.span("steel", -0.32, 0.32, hy - 0.1, hy + 0.06, 1.75, 1.9)                              # carrier bar
    HH.strut("steel", (0, hy, 1.75), (0, hy, 1.25), 0.03, seg=6)                               # polished rod
    HH.span("dark", -0.08, 0.08, hy - 0.08, hy + 0.08, 1.9, 2.0)                               # rod clamp

    # ---------------------------------------------------------------- crank arms + counterweights (spin about X)
    for x in (-0.98, 0.98):
        sx = 1 if x > 0 else -1
        x0, x1 = sorted((x - 0.07, x + 0.07))
        CR.prism("steel", [(AXLE[1] - 1.12, AXLE[2] - 0.13), (AXLE[1] + 0.2, AXLE[2] - 0.22), (AXLE[1] + 0.2, AXLE[2] + 0.22),
                           (AXLE[1] - 1.12, AXLE[2] + 0.13)], "x", x0, x1)                       # arm towards the pin
        cw = [(AXLE[1] + 0.25 + 1.05 * math.cos(a), AXLE[2] + 1.05 * math.sin(a)) for a in np.radians(np.linspace(-55, 55, 9))]
        cw += [(AXLE[1] + 0.25 + 0.35 * math.cos(a), AXLE[2] + 0.35 * math.sin(a)) for a in np.radians(np.linspace(55, -55, 5))]
        c0, c1 = sorted((x + sx * 0.08, x + sx * 0.32))
        CR.prism("steel", cw, "x", c0, c1, bev=True)                                              # counterweight
        CR.span("yellow", min(c1, c0) if sx < 0 else c1, (c0 - 0.005) if sx < 0 else c1 + 0.005,
                AXLE[1] + 0.9, AXLE[1] + 1.15, AXLE[2] - 0.12, AXLE[2] + 0.12, bottom=True)        # stroke marker
        CR.cyl("metal", (x, AXLE[1] - 1.0, AXLE[2]), 0.09, 0.3, rot=(0, PI / 2, 0), seg=8, bottom=True)   # crank pin
    CR.cyl("steel", AXLE, 0.22, 0.3, rot=(0, PI / 2, 0), seg=10, bottom=True)

    beam = WB.build(); head = HH.build(); pit = PM.build(); crank = CR.build(); base = B.build()
    for child in (head, pit):                                     # ride with the beam
        loc = child.location.copy()
        child.parent = beam
        child.matrix_parent_inverse = Matrix.Identity(4)
        child.location = loc - beam.location
    kit.parts = [base, beam, head, pit, crank]                    # Base first: the fence joins into it
    return kit.finish(A.out, "oil_derrick.glb", ground_size=40)


if not A.skip_build:
    build()
if A.previews:
    K.previews(GLB, A.previews, "prop_oil_derrick", K.std_shots(14.0, 6.0, top_ortho=16.0), only=A.only)
