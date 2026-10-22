"""Steel Accord - M1 3D structure: US 'Barracks' (code-built + texture-baked in Blender, bpy 5.x). Original design
recreated from the client's concept sheet (individual_views/Barracks).

Run:  python3 -I bld_barracks_3d.py <out_dir> [--previews <dir>] [--concept <overhead.png>] [--only rts,front]
      [--previews-only]
Out:  <out_dir>/barracks.glb  nodes: Building, Props, Light_Status0..2, Light_Beacon0, Light_Flood0..1, Exit
Slab 20 (X) x 16 (Y) m, origin = slab bottom centre, front (entrance block + gate) = Blender -Y = Godot +Z.
Layout: two long two-storey wings (tan block ground floor, olive-clad upper floor, flat tan roofs with condensers)
either side of a courtyard with a shade sail and picnic tables; single-storey entrance block at the front and a
utility block at the rear (corrugated roofs); steel stairs, upper-floor walkways, chain-link perimeter, open gate.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit as K
from bldkit import PI, V

O = K.cli(sys.argv[1:])
ID = "barracks"
GLB = os.path.join(O["out"], ID + ".glb")


def build():
    kit = K.Kit(ID, "BK", "BK_Barracks", atlas=4096)
    B = kit.part("Building"); P = kit.part("Props")
    SL = 0.25
    WY0, WY1 = -4.4, 7.2           # wings (long along Y)
    WINGS = ((-8.6, -3.6), (3.6, 8.6))
    F1, F2, RZ = 3.3, 6.2, 6.25    # first-floor level, wall top, roof deck
    EX0, EX1, EY0, EY1, EH = -2.3, 2.3, -5.6, -1.6, 3.7   # entrance block
    UX0, UX1, UY0, UY1, UH = -2.6, 2.6, 4.6, 7.2, 3.0     # utility block (rear)

    B.frustum("slab", -10.0, 10.0, -8.0, 8.0, 0.0, SL, 0.12)
    B.span("slab", -3.5, 3.5, -1.6, 4.6, SL - 0.05, SL + 0.05)                           # courtyard pad
    B.span("slab", -1.6, 1.6, -7.9, EY0, SL - 0.05, SL + 0.05)                            # entry path

    # ---------------------------------------------------------------- wings
    for wi, (x0, x1) in enumerate(WINGS):
        inner = x1 if wi == 0 else x0              # face towards the courtyard
        outer = x0 if wi == 0 else x1
        so = -1 if wi == 0 else 1                  # outward direction (x)
        si = -so
        T = 0.3
        # ground floor: tan block; upper floor: olive cladding; band + roof
        B.span("tanwall", x0, x1, WY0, WY1, SL, F1)
        B.span("olivewall", x0 + 0.04, x1 - 0.04, WY0 + 0.04, WY1 - 0.04, F1, F2)
        B.span("conc", x0 - 0.08, x1 + 0.08, WY0 - 0.08, WY1 + 0.08, F1 - 0.12, F1 + 0.08, bev=True)
        B.span("conc", x0 - 0.1, x1 + 0.1, WY0 - 0.1, WY1 + 0.1, SL, SL + 0.45, bev=True)
        for (cx0, cx1, cy0, cy1) in ((x0 - 0.14, x1 + 0.14, WY0 - 0.14, WY0 + 0.16), (x0 - 0.14, x1 + 0.14, WY1 - 0.16, WY1 + 0.14),
                                     (x0 - 0.14, x0 + 0.16, WY0 + 0.16, WY1 - 0.16), (x1 - 0.16, x1 + 0.14, WY0 + 0.16, WY1 - 0.16)):
            B.span("olive", cx0, cx1, cy0, cy1, F2 - 0.05, F2 + 0.42, bev=True)                     # coping ring
        B.span("rooft", x0 + 0.16, x1 - 0.16, WY0 + 0.16, WY1 - 0.16, F2 - 0.05, F2 + 0.2)          # tan roof deck
        B.span("team", x0 + 0.6, x1 - 0.6, WY0 - 0.16, WY0 - 0.14, F2 + 0.05, F2 + 0.25, bottom=True)
        # downpipes at the corners
        for (px, py) in ((x0 + 0.15, WY0 - 0.12), (x1 - 0.15, WY0 - 0.12), (x0 + 0.15, WY1 + 0.12), (x1 - 0.15, WY1 + 0.12)):
            B.cyl("olive", (px, py, (SL + F2) / 2), 0.06, F2 - SL, seg=6)
        # windows / doors on long faces (inner + outer), both storeys
        ys = [WY0 + 1.2 + k * 1.95 for k in range(6)]
        for face, out in ((outer, so), (inner, si)):
            for k, y in enumerate(ys):
                for z0, z1 in ((1.3, 2.4), (4.2, 5.3)):
                    door = (face == inner and z0 < 2 and k in (1, 4)) or (face == inner and z0 > 2 and k in (0, 3, 5))
                    if door:
                        zz0 = SL + 0.05 if z0 < 2 else F1 + 0.05
                        B.span("door", *sorted((face, face + out * 0.03)), y - 0.45, y + 0.45, zz0, zz0 + 2.15)
                        B.span("conc", *sorted((face, face + out * 0.1)), y - 0.55, y + 0.55, zz0 + 2.15, zz0 + 2.3)
                        B.span("lamp", *sorted((face + out * 0.1, face + out * 0.14)), y + 0.6, y + 0.72, zz0 + 1.9, zz0 + 2.08)
                    else:
                        B.span("win", *sorted((face, face + out * 0.03)), y - 0.5, y + 0.5, z0, z1)
                        B.span("conc", *sorted((face, face + out * 0.12)), y - 0.6, y + 0.6, z0 - 0.12, z0)
        # front + rear end walls: two windows each storey
        for face, out in ((WY0, -1), (WY1, 1)):
            for xc in ((x0 + x1) / 2 - 1.1, (x0 + x1) / 2 + 1.1):
                for z0, z1 in ((1.3, 2.4), (4.2, 5.3)):
                    B.span("win", xc - 0.5, xc + 0.5, *sorted((face, face + out * 0.03)), z0, z1)
                    B.span("conc", xc - 0.6, xc + 0.6, *sorted((face, face + out * 0.12)), z0 - 0.12, z0)
        # roof condensers + vents (as in the concept: three units per wing)
        cx = (x0 + x1) / 2
        K.hvac(B, cx + 0.3 * so, WY0 + 2.0, F2 + 0.2, sx=1.3, sy=1.1, h=0.75)
        K.hvac(B, cx - 0.4 * so, (WY0 + WY1) / 2 + 0.6, F2 + 0.2, sx=1.0, sy=0.9, h=0.6)
        K.hvac(B, cx, WY1 - 1.8, F2 + 0.2, sx=1.3, sy=1.1, h=0.75)
        B.cyl("metal", (cx - 1.2 * so, WY1 - 0.7, F2 + 0.6), 0.16, 0.6, seg=8)
        B.span("hvac", cx + 1.3 * so - 0.4, cx + 1.3 * so + 0.4, WY1 - 0.9, WY1 - 0.3, F2 + 0.2, F2 + 0.75)
        # upper walkway on the courtyard side (full length) + railing + posts
        bx0, bx1 = sorted((inner, inner + si * 1.05))
        B.span("grate", bx0, bx1, WY0 - 1.2, WY1, F1 - 0.12, F1)
        B.span("metal", bx0, bx1, WY0 - 1.2, WY1, F1 - 0.28, F1 - 0.12, bottom=True)
        edge = inner + si * 1.0
        B.railing("metal", [(edge, WY1), (edge, WY0 - 1.15), (inner, WY0 - 1.15)], F1, h=1.0, spacing=1.9)
        for y in (WY0 - 1.15, WY0 + 2.0, WY0 + 5.2, WY1 - 0.2):
            B.cyl("metal", (edge, y, (SL + F1) / 2), 0.06, F1 - SL, seg=6)
        # front stair: from the outer front corner up to the walkway landing at the inner front corner
        sy0, sy1 = WY0 - 1.15, WY0 - 0.1
        lx = inner - si * 0.6         # stair top end (just inside the wing's inner edge)
        ox = outer + si * 0.3         # stair bottom end
        B.stairs("dark", *sorted((ox, lx)), sy0, sy1, SL, F1 - 0.12, "+x" if lx > ox else "-x", stringer="metal")
        B.span("grate", *sorted((lx, inner)), sy0, sy1, F1 - 0.12, F1)                       # landing on the corner
        # outer side stair (rear half) to an upper door
        ex0, ex1 = sorted((outer, outer + so * 0.95))
        B.stairs("dark", ex0, ex1, WY1 - 5.2, WY1 - 1.6, SL, F1 - 0.12, "+y", stringer="metal")
        B.span("grate", ex0, ex1, WY1 - 1.6, WY1 - 0.4, F1 - 0.12, F1)
        B.span("metal", ex0, ex1, WY1 - 1.6, WY1 - 0.4, F1 - 0.28, F1 - 0.12, bottom=True)
        B.railing("metal", [(outer + so * 0.92, WY1 - 1.6), (outer + so * 0.92, WY1 - 0.42), (outer, WY1 - 0.42)], F1, h=1.0, spacing=1.3)
        B.cyl("metal", (outer + so * 0.88, WY1 - 0.45, (SL + F1) / 2), 0.05, F1 - SL, seg=6)
        B.span("door", *sorted((outer, outer + so * 0.03)), WY1 - 1.4, WY1 - 0.6, F1 + 0.05, F1 + 2.2)
        # wall lamps (warm, baked) along the upper floor
        for y in (WY0 + 0.2, (WY0 + WY1) / 2, WY1 - 0.2):
            B.span("metal", *sorted((outer, outer + so * 0.15)), y - 0.1, y + 0.1, F2 - 0.55, F2 - 0.35, bottom=True)
            B.span("lamp", *sorted((outer + so * 0.15, outer + so * 0.17)), y - 0.07, y + 0.07, F2 - 0.53, F2 - 0.37)
    # walkway bridge between the wings over the courtyard rear
    B.span("grate", -3.6, 3.6, UY0 - 1.0, UY0 - 0.1, F1 - 0.12, F1)
    B.span("metal", -3.6, 3.6, UY0 - 1.0, UY0 - 0.1, F1 - 0.28, F1 - 0.12, bottom=True)
    B.railing("metal", [(-2.6, UY0 - 1.0), (2.6, UY0 - 1.0)], F1, h=1.0, spacing=1.8)
    B.railing("metal", [(-2.6, UY0 - 0.1), (2.6, UY0 - 0.1)], F1, h=1.0, spacing=2.6)
    # single beacon on a short mast (east wing, rear)
    B.cyl("metal", (7.6, WY1 - 0.5, F2 + 0.3 + 1.1), 0.045, 2.2, seg=6)
    B.span("metal", 7.45, 7.75, WY1 - 0.65, WY1 - 0.35, F2 + 0.2, F2 + 0.45)
    K.roof_beacon(B, kit, 7.6, WY1 - 0.5, F2 + 0.3 + 2.2, "Light_Beacon0", r=0.11)

    # ---------------------------------------------------------------- entrance block (front, single storey)
    B.span("tanwall", EX0, EX1, EY0, EY1, SL, EH)
    B.span("conc", EX0 - 0.08, EX1 + 0.08, EY0 - 0.08, EY1, SL, SL + 0.45, bev=True)
    B.span("olive", EX0 - 0.12, EX1 + 0.12, EY0 - 0.12, EY1, EH - 0.1, EH + 0.15, bev=True)
    B.prism("corr", [(EY0 - 0.2, EH + 0.15), (EY1, EH + 0.15), (EY1, EH + 0.45), (EY0 - 0.2, EH + 0.25)], "x", EX0 - 0.1, EX1 + 0.1)
    B.span("team", EX0 + 0.3, EX1 - 0.3, EY0 - 0.14, EY0 - 0.12, EH - 0.05, EH + 0.1, bottom=True)
    for x in (EX0 + 0.35, EX1 - 0.35):
        B.span("conc", x - 0.3, x + 0.3, EY0 - 0.25, EY0, SL, EH - 0.1, bev=True)
    B.span("door", -0.9, 0.9, EY0 - 0.03, EY0, SL + 0.1, 2.6)
    B.span("metal", -0.03, 0.03, EY0 - 0.06, EY0 - 0.03, SL + 0.1, 2.6)
    B.prism("corr", [(EY0, 3.1), (EY0, 2.95), (EY0 - 1.3, 2.75), (EY0 - 1.3, 2.87)], "x", -1.3, 1.3)
    for s in (-1, 1):
        B.strut("metal", (s * 1.2, EY0, 3.25), (s * 1.2, EY0 - 1.2, 2.87), 0.025, seg=4)
        K.wall_lamp(B, kit, "y", EY0 - 0.25, s * 1.35, 2.3, -1, f"Light_Status{0 if s < 0 else 1}")
    B.span("metal", -0.15, 0.15, EY0 - 0.35, EY0 - 0.12, EH + 0.25, EH + 0.45)
    kit.light("Light_Status2", (0.0, EY0 - 0.24, EH + 0.45), "dome", r=0.13)
    B.span("conc", -0.6, 0.6, EY0 - 0.6, EY0, SL, SL + 0.12)                                        # door step
    # ---------------------------------------------------------------- utility block (rear) + courtyard
    B.span("tanwall", UX0, UX1, UY0, UY1, SL, UH)
    B.span("olive", UX0 - 0.1, UX1 + 0.1, UY0 - 0.1, UY1 + 0.1, UH - 0.1, UH + 0.12, bev=True)
    B.prism("corr", [(UY0 - 0.15, UH + 0.12), (UY1 + 0.1, UH + 0.12), (UY1 + 0.1, UH + 0.22), (UY0 - 0.15, UH + 0.4)], "x", UX0 - 0.1, UX1 + 0.1)
    B.span("door", -0.5, 0.5, UY0 - 0.03, UY0, SL, 2.3)
    for x in (-1.7, 1.7):
        B.span("win", x - 0.45, x + 0.45, UY0 - 0.03, UY0, 1.3, 2.1)
    # shade sail on four posts + picnic tables
    for (x, y) in ((-2.3, -0.3), (2.3, -0.3), (-2.3, 2.9), (2.3, 2.9)):
        P.cyl("metal", (x, y, SL + 1.45), 0.06, 2.9, seg=6)
    P.frustum("shade", -2.4, 2.4, -0.4, 3.0, SL + 2.7, SL + 2.95, 0.5, insety=0.3)
    P.span("shade", -2.4, 2.4, -0.4, 3.0, SL + 2.68, SL + 2.7, bottom=True)
    for (x, y) in ((-1.2, 0.4), (1.2, 0.4), (-1.2, 2.2), (1.2, 2.2)):
        P.span("wood", x - 0.9, x + 0.9, y - 0.4, y + 0.4, SL + 0.72, SL + 0.78)
        for s in (-1, 1):
            P.span("wood", x - 0.9, x + 0.9, y + s * 0.7 - 0.13, y + s * 0.7 + 0.13, SL + 0.42, SL + 0.47)
            P.span("metal", x + s * 0.7 - 0.04, x + s * 0.7 + 0.04, y - 0.8, y + 0.8, SL, SL + 0.72)
    for (x, y) in ((-2.9, 4.1), (-2.2, 4.1), (2.6, 4.1)):
        P.span("cabinet", x - 0.3, x + 0.3, y - 0.25, y + 0.25, SL, SL + 1.1)
    K.ammo_pallet(P, 2.4, -0.4, SL, 1)
    # lockers / bins along the outer walls
    for sx in (-1, 1):
        for y in (-3.4, -2.6, 0.8, 1.6):
            P.span("cabinet", sx * 8.7 + (0 if sx > 0 else -0.6), sx * 8.7 + (0.6 if sx > 0 else 0), y - 0.35, y + 0.35, SL, SL + 1.2)
    for (x, y) in ((-4.6, -6.6), (4.6, -6.6)):
        P.span("cabinet", x - 0.5, x + 0.5, y - 0.35, y + 0.35, SL, SL + 1.0, bev=True)

    # ---------------------------------------------------------------- perimeter: chain-link fence, kerb blocks, gate
    FZ, FH = SL, 2.0
    def fence_run(a, b, posts=True):
        (x0, y0), (x1, y1) = a, b
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / 2.4)))
        for k in range(n + 1):
            t = k / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if P.once("post", x, y):
                P.cyl("metal", (x, y, FZ + FH / 2 + 0.1), 0.05, FH + 0.2, seg=6)
        for k in range(n):
            pa = (x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
            pb = (x0 + (x1 - x0) * (k + 1) / n, y0 + (y1 - y0) * (k + 1) / n)
            kit.fence(pa, pb, FZ + 0.05, FH)
        P.strut("metal", (x0, y0, FZ + FH), (x1, y1, FZ + FH), 0.028, seg=4)
        P.strut("metal", (x0, y0, FZ + 0.1), (x1, y1, FZ + 0.1), 0.02, seg=4)
    fence_run((-9.6, -7.4), (-9.6, 7.6)); fence_run((-9.6, 7.6), (9.6, 7.6)); fence_run((9.6, 7.6), (9.6, -7.4))
    fence_run((-9.6, -7.4), (-2.5, -7.4)); fence_run((2.5, -7.4), (9.6, -7.4))
    for sx in (-1, 1):                                       # kerb blocks along the front fence line
        for x in (sx * 4.2, sx * 7.4):
            P.span("conc", x - 0.9, x + 0.9, -7.75, -7.55, SL, SL + 0.5, bev=True)
    # gate pillars with flood heads, and open gate leaves swung inwards
    for sx, nm in ((-1, "Light_Flood0"), (1, "Light_Flood1")):
        x = sx * 2.55
        P.span("tanwall", x - 0.4, x + 0.4, -7.8, -7.0, SL, SL + 2.1, bev=True)
        P.span("conc", x - 0.45, x + 0.45, -7.85, -6.95, SL + 2.1, SL + 2.25, bev=True)
        P.cyl("metal", (x, -7.4, SL + 2.6), 0.05, 0.7, seg=6)
        K.flood_head(P, kit, x, -7.55, SL + 2.95, -PI / 2 - sx * 0.3, nm, tilt=40)
        hinge = (sx * 2.12, -6.88)                     # on the pillar's inner face
        tip = (hinge[0] + sx * 1.95 * math.cos(math.radians(12)), hinge[1] + 1.95 * math.sin(math.radians(12)))   # folded back inside
        for z in (FZ + 0.1, FZ + FH):
            P.strut("metal", (*hinge, z), (*tip, z), 0.03, seg=4)
        P.strut("metal", (*tip, FZ + 0.1), (*tip, FZ + FH), 0.03, seg=4)
        P.strut("metal", (*hinge, FZ + 0.1), (*hinge, FZ + FH), 0.04, seg=6)
        kit.fence(hinge, tip, FZ + 0.1, FH - 0.1)
    kit.empty("Exit", (0.0, -9.0, 0.0))
    return kit, B, P


if not O["skip_build"]:
    kit, B, P = build()
    kit.finish(B, P, O["out"])
if O["previews"]:
    K.previews(GLB, O["previews"], ID, extent=20.0, concept=O["concept"], only=O["only"], target_z=2.6)
