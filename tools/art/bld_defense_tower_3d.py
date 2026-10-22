"""Steel Accord - M1 structure: Base Defense Tower.

Run:  python3 -I bld_defense_tower_3d.py <out_dir> [--previews <dir>] [--concept <png>] [--only rts] [--previews-only]
Out:  <out_dir>/defense_tower.glb
  Building - battered octagonal concrete bastion with buttresses, deck with sandbag ring, octagonal tower +
             glazed cab, roof railing, radome mast, searchlight bracket, deck clutter
  Turret   - remote weapon station: yaw ring, cradle, 2x2 missile pod + sensor head + MG; origin ON the yaw axis
             (rest pose aims at the front, Blender -Y = Godot +Z)
    Muzzle - empty, child of Turret, at the launcher front (centre of the tube mouths)
  Light_Status0..1, Light_Beacon0, Light_Flood0 (searchlight)
Footprint 8 x 8 m (octagon flat-to-flat 7.7 m at ground), origin = centre at ground, front = Blender -Y.
The concept sheet clips the tower top; the roof turret + radome here are an original design.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import numpy as np
from mathutils import Matrix, Euler, Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "defense_tower.glb")
PI = math.pi
C8 = math.cos(PI / 8)

A0, A1, HB = 3.85, 3.5, 2.35         # bastion apothem at ground / at top, wall height
DECK = HB + 0.25                     # deck level (top of the cap band)
TA = 1.65                            # tower apothem
CAB0, CAB1, ROOF = 5.35, 6.55, 6.85  # cab glazing from/to, roof deck
PIV = (0.0, -0.25, ROOF + 0.12)      # turret yaw pivot


def oct_pts(ap, z, rot=PI / 8):
    r = ap / C8
    return [(r * math.cos(rot + k * PI / 4), r * math.sin(rot + k * PI / 4), z) for k in range(8)]


def face_frame(theta, ap, z):
    """Matrix at the centre of an octagon face (angle theta, apothem ap): local x = outward normal, y = tangent."""
    return Matrix.Translation((ap * math.cos(theta), ap * math.sin(theta), z)) @ Euler((0, 0, theta)).to_matrix().to_4x4()


def build():
    kit = K.Kit("defense_tower", "DT", atlas=2048, ao_res=1024, ao_dist=2.5)
    B = kit.part("Building")
    T = kit.part("Turret", pivot=PIV)

    # ---------------------------------------------------------------- bastion: battered octagon + cap band
    B.loft("conc", [oct_pts(A0, 0.0), oct_pts(A0 - 0.04, 0.25), oct_pts(A1, HB)], cap1=False, bev=False)
    B.loft("conc", [oct_pts(A1 + 0.08, HB), oct_pts(A1 + 0.08, DECK), oct_pts(A1 - 0.25, DECK)], cap1=False, bev=False)
    B.loft("slab", [oct_pts(A1 - 0.25, DECK)], cap1=True)
    B.loft("gconc", [oct_pts(A0 + 0.12, 0.0), oct_pts(A0 + 0.12, 0.12), oct_pts(A0 - 0.02, 0.12)], cap1=False)   # footing
    # buttresses at the 8 corners (wedges leaning on the wall)
    for k in range(8):
        th = PI / 8 + k * PI / 4
        r0 = A0 / C8
        M = Matrix.Translation((0, 0, 0)) @ Euler((0, 0, th)).to_matrix().to_4x4()
        prof = [(r0 - 0.15, 0.0), (r0 + 0.55, 0.0), (r0 + 0.55, 0.35), (r0 + 0.05, HB - 0.05), (r0 - 0.3, HB - 0.05)]
        B.prism("conc", [(p, q) for p, q in prof], "y", -0.28, 0.28, bev=True, M=M)
    # face features: front door, vent grilles, drain spouts
    for k in range(8):
        th = k * PI / 4
        ap = (A0 + A1) / 2
        lean = math.atan2(A0 - A1, HB)
        Mf = face_frame(th, ap, HB / 2) @ Euler((0, -lean, 0)).to_matrix().to_4x4()
        if k == 6:                                                    # front (-Y): steel door
            B.box("metal", Mf @ V((0.03, 0, -0.25)), (0.08, 1.2, 1.9), Euler((0, -lean, th)), bottom=True)
            B.box("odoor", Mf @ V((0.06, 0, -0.27)), (0.04, 1.0, 1.75), Euler((0, -lean, th)), bottom=True)
            B.box("hazard", Mf @ V((0.05, 0, 0.82)), (0.06, 1.3, 0.16), Euler((0, -lean, th)), bottom=True)
            kit.light("Light_Status0", [("box", tuple(Mf @ V((0.08, 0.8, 0.45))), (0.06, 0.16, 0.16), (0, -lean, th))])
        elif k % 2 == 1 or k in (0, 4):
            B.box("metal", Mf @ V((0.02, 0, 0.0)), (0.06, 1.5, 0.75), Euler((0, -lean, th)), bottom=True)
            B.box("louvre", Mf @ V((0.05, 0, 0.0)), (0.03, 1.36, 0.62), Euler((0, -lean, th)), bottom=True)
        if k in (1, 5):                                               # small hatch below a grille
            B.box("metal", Mf @ V((0.03, 0.9, -0.6)), (0.05, 0.4, 0.8), Euler((0, -lean, th)), bottom=True)

    # ---------------------------------------------------------------- deck: sandbag ring, clutter
    ring = [(x, y) for x, y, _ in oct_pts(A1 - 0.55, 0)]
    for i in range(8):
        a, b = ring[i], ring[(i + 1) % 8]
        if i == 1:                     # rear-right gap for the ladder top
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            K.sandbag_row(B, a, (a[0] + (m[0] - a[0]) * 0.55, a[1] + (m[1] - a[1]) * 0.55), DECK, layers=3)
            continue
        K.sandbag_row(B, a, b, DECK, layers=3)
    # deck clutter: ammo boxes, drums, a crate stack
    K.ammo_pallet(B, -1.9, 1.85, DECK, 1)
    K.drum(B, 2.0, 1.4, DECK, "olive"); K.drum(B, 2.3, 0.85, DECK, "olive")
    B.span("crate", -2.45, -1.75, -1.6, -1.05, DECK, DECK + 0.45, bev=True)
    B.span("crate", -2.4, -1.85, -1.55, -1.1, DECK + 0.45, DECK + 0.8, bev=True)
    B.span("cabinet", 1.75, 2.45, -1.75, -1.15, DECK, DECK + 0.9, bev=True)
    # ladder from ground to deck (rear-right face) + ladder deck -> roof
    th = PI / 4 + PI / 8 - PI / 8          # face at 45 deg (+X+Y)
    th = PI / 4
    K.ladder(B, (A0 * math.cos(th) + 0.05, A0 * math.sin(th) + 0.05, 0.0), (-math.sin(th), math.cos(th), 0), 9, DECK + 0.9,
             (math.cos(th), math.sin(th), 0))
    K.ladder(B, (TA / C8 * 0.0 + 0.0, TA + 0.02, DECK), (1, 0, 0), 12, ROOF - DECK + 0.9, (0, 1, 0))

    # ---------------------------------------------------------------- central tower + cab
    B.loft("conc", [oct_pts(TA, DECK - 0.05), oct_pts(TA, CAB0 - 0.15)], cap1=False)
    B.loft("olive", [oct_pts(TA + 0.05, CAB0 - 0.15), oct_pts(TA + 0.12, CAB0)], cap1=False)
    B.loft("cab", [oct_pts(TA + 0.1, CAB0), oct_pts(TA + 0.38, CAB1)], cap1=False)
    B.loft("olive", [oct_pts(TA + 0.4, CAB1), oct_pts(TA + 0.45, CAB1 + 0.05), oct_pts(TA + 0.45, ROOF), oct_pts(TA + 0.1, ROOF)],
           cap1=False)
    B.loft("slab", [oct_pts(TA + 0.1, ROOF)], cap1=True)
    B.loft("team", [oct_pts(TA + 0.47, CAB1 + 0.14), oct_pts(TA + 0.47, CAB1 + 0.24)], cap1=False)
    # window mullions
    for x, y, _ in oct_pts(TA, 0):
        s = (TA + 0.1) / TA; s2 = (TA + 0.38) / TA
        B.strut("olive", (x * s, y * s, CAB0), (x * s2, y * s2, CAB1), 0.045, seg=4)
    # tower door (front) + small awning
    B.box("metal", (0, -TA - 0.03, DECK + 1.05), (1.0, 0.08, 2.1))
    B.box("odoor", (0, -TA - 0.06, DECK + 1.0), (0.85, 0.04, 1.9))
    B.span("metal", -0.7, 0.7, -TA - 0.75, -TA, DECK + 2.25, DECK + 2.33, bottom=True)
    kit.light("Light_Status1", [("box", (0.65, -TA - 0.06, DECK + 1.6), (0.14, 0.05, 0.14))])
    for k in (1, 3, 5, 7):                                     # side slit windows on the shaft
        th = k * PI / 4 if k != 7 else -PI / 4
        th = k * PI / 4
        B.box("dark", (TA * math.cos(th), TA * math.sin(th), DECK + 1.5), (0.06, 0.6, 0.25), (0, 0, th))
    # roof railing + radome mast + whip + searchlight
    rr = [(x, y) for x, y, _ in oct_pts(TA + 0.32, 0)]
    K.railing(B, rr, ROOF, h=0.9, post=2.0, closed=True)
    RX, RY = 0.0, 1.25
    B.cyl("metal", (RX, RY, ROOF + 0.6), 0.08, 1.2, seg=8)
    B.cyl("olive", (RX, RY, ROOF + 1.25), 0.32, 0.15, seg=12)
    B.lathe("lolive", [(0.42, 0.0), (0.42, 0.18), (0.36, 0.42), (0.22, 0.6), (0.0, 0.66)], Matrix.Translation((RX, RY, ROOF + 1.32)), seg=16)
    for s in (-1, 1):
        B.strut("metal", (s * 0.6, 1.1, ROOF), (s * 0.08, RY, ROOF + 0.9), 0.025, seg=4)
    B.cyl("metal", (-0.9, 1.0, ROOF + 1.5), 0.03, 3.0, seg=6)
    B.cyl("metal", (0.95, 0.9, ROOF + 1.0), 0.025, 2.0, seg=6)
    kit.light("Light_Beacon0", [("cyl", (-0.9, 1.0, ROOF + 3.08), 0.08, 0.16, (0, 0, 0), 8)])
    # searchlight on the front-left roof corner
    SX, SY = -1.55, -0.85
    B.cyl("metal", (SX, SY, ROOF + 0.35), 0.06, 0.7, seg=8)
    B.box("metal", (SX, SY, ROOF + 0.75), (0.5, 0.08, 0.08), bottom=True)
    B.cyl("olive", (SX, SY, ROOF + 0.95), 0.27, 0.45, (math.radians(70), 0, math.radians(-30)), seg=14)
    kit.light("Light_Flood0", [("cyl", (SX + 0.11, SY - 0.2, ROOF + 1.02), 0.23, 0.04, (math.radians(70), 0, math.radians(-30)), 14)])
    B.span("cabinet", 0.75, 1.35, 0.65, 1.15, ROOF, ROOF + 0.55, bev=True)       # roof junction box

    # ---------------------------------------------------------------- TURRET (remote weapon station)
    px, py, pz = PIV
    T.cyl("metal", (px, py, pz + 0.1), 0.72, 0.2, seg=20, bottom=True)
    T.cyl("cabinet", (px, py, pz + 0.32), 0.62, 0.25, seg=20, r2=0.55)
    T.cyl("team", (px, py, pz + 0.2), 0.73, 0.06, seg=20, bottom=True)
    # cradle uprights
    for s in (-1, 1):
        T.prism("cabinet", [(py - 0.35, pz + 0.44), (py + 0.35, pz + 0.44), (py + 0.2, pz + 1.0), (py - 0.25, pz + 1.0)],
                "x", px + s * 0.42 - 0.07, px + s * 0.42 + 0.07)
    T.cyl("metal", (px, py, pz + 0.85), 0.1, 0.98, (0, PI / 2, 0), seg=10)          # trunnion
    # missile pod (right): 2x2 tubes
    LX, LY, LZ = px + 0.82, py - 0.1, pz + 0.95
    T.span("cabinet", LX - 0.33, LX + 0.33, LY - 0.7, LY + 0.55, LZ - 0.33, LZ + 0.33, bev=True)
    for i in (-1, 1):
        for j in (-1, 1):
            T.cyl("dark", (LX + i * 0.15, LY - 0.71, LZ + j * 0.15), 0.12, 0.04, (PI / 2, 0, 0), seg=10)
            T.cyl("olive", (LX + i * 0.15, LY - 0.69, LZ + j * 0.15), 0.135, 0.02, (PI / 2, 0, 0), seg=10, bottom=True)
    T.span("hazard", LX - 0.34, LX + 0.34, LY - 0.4, LY - 0.3, LZ + 0.32, LZ + 0.345, bottom=True)
    # sensor head (left): box with two dark lenses
    SXh = px - 0.72
    T.span("cabinet", SXh - 0.25, SXh + 0.25, py - 0.4, py + 0.3, pz + 0.7, pz + 1.15, bev=True)
    for dz in (0.82, 1.02):
        T.cyl("dark", (SXh - 0.07 if dz < 0.9 else SXh + 0.08, py - 0.41, pz + dz), 0.085, 0.04, (PI / 2, 0, 0), seg=10)
    # centre receiver + MG barrel
    T.span("olive", px - 0.25, px + 0.25, py - 0.45, py + 0.5, pz + 0.75, pz + 1.08, bev=True)
    T.span("metal", px - 0.12, px + 0.12, py + 0.1, py + 0.45, pz + 1.08, pz + 1.22)          # ammo can on top
    T.cyl("metal", (px, py - 0.95, pz + 0.92), 0.04, 1.0, (PI / 2, 0, 0), seg=8)
    T.cyl("dark", (px, py - 1.42, pz + 0.92), 0.055, 0.12, (PI / 2, 0, 0), seg=8)

    B.build(); turret = T.build()
    kit.empty("Muzzle", (LX, LY - 0.74, LZ), parent=turret)
    return kit.finish(A.out, "defense_tower.glb", ground_size=40)


if not A.skip_build:
    build()
if A.previews:
    K.previews(GLB, A.previews, "m1_defense_tower", K.std_shots(8.0, 9.0, tz=3.8, dmul=1.35), only=A.only, concept=A.concept)
