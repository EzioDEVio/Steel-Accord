"""Steel Accord - M1 3D structure: US 'Power Plant' (code-built + texture-baked in Blender, bpy 5.x). Original design
recreated from the client's concept sheet (individual_views/Power_Generator_Plant).

Run:  python3 -I bld_power_plant_3d.py <out_dir> [--previews <dir>] [--concept <overhead.png>] [--only rts,front]
      [--previews-only]
Out:  <out_dir>/power_plant.glb  nodes: Building, Props, Light_Status0..2, Light_Beacon0..1, Light_Flood0..1
Slab 18 (X) x 16 (Y) m, origin = slab bottom centre, front (door + generator modules) = Blender -Y = Godot +Z.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit as K
from bldkit import PI, V

O = K.cli(sys.argv[1:])
ID = "power_plant"
GLB = os.path.join(O["out"], ID + ".glb")


def build():
    kit = K.Kit(ID, "PP", "PP_PowerPlant", atlas=4096)
    B = kit.part("Building"); P = kit.part("Props")
    SL = 0.25
    HX0, HX1, HY0, HY1 = -5.1, 5.1, 0.4, 7.4          # generator hall (front wall at HY0)
    WT, PZ = 6.3, 6.8                                  # wall top / parapet top
    # ---------------------------------------------------------------- slab, pads, walkway
    B.frustum("slab", -9.0, 9.0, -8.0, 8.0, 0.0, SL, 0.12)
    B.span("slab", HX0 - 0.5, HX1 + 0.5, HY0 - 0.4, HY1 + 0.5, SL - 0.05, SL + 0.06)
    B.span("grate", -0.9, 0.9, -7.6, HY0 - 0.4, SL, SL + 0.03)                       # central access grating
    for x in (-1.0, 1.0):
        B.span("yellow", x - 0.05, x + 0.05, -7.6, HY0 - 0.4, SL, SL + 0.035)
    # ---------------------------------------------------------------- hall shell (beige precast concrete)
    T = 0.35
    B.span("bconc", HX0, HX1, HY0, HY0 + T, SL, WT)
    B.span("bconc", HX0, HX1, HY1 - T, HY1, SL, WT)
    B.span("bconc", HX0, HX0 + T, HY0 + T, HY1 - T, SL, WT)
    B.span("bconc", HX1 - T, HX1, HY0 + T, HY1 - T, SL, WT)
    B.span("gconc", HX0 - 0.06, HX1 + 0.06, HY0 - 0.06, HY1 + 0.06, SL, SL + 0.75, bev=True)   # darker plinth band
    B.span("bconc", HX0 - 0.1, HX1 + 0.1, HY0 - 0.1, HY1 + 0.1, WT - 0.1, PZ, bev=True)        # parapet band
    B.span("roofg", HX0 + 0.25, HX1 - 0.25, HY0 + 0.25, HY1 - 0.25, PZ - 0.45, PZ - 0.35)
    B.span("metal", HX0 + 0.2, HX1 - 0.2, HY0 + 0.2, HY0 + 0.25, PZ - 0.35, PZ)  # inner parapet faces (read)
    # chamfered corner pilasters + front/side pilasters
    for sx in (-1, 1):
        for sy, yy in ((-1, HY0), (1, HY1)):
            x0, x1 = sorted((sx * 5.1 - sx * 0.5, sx * 5.1 + sx * 0.3))
            y0, y1 = sorted((yy - sy * 0.5, yy + sy * 0.3))
            B.span("bconc", x0, x1, y0, y1, SL, PZ + 0.15, bev=True)
            B.span("bconc", x0 - 0.04, x1 + 0.04, y0 - 0.04, y1 + 0.04, PZ + 0.15, PZ + 0.25, bev=True)
    for x in (-1.3, 1.3):
        B.span("bconc", x - 0.3, x + 0.3, HY0 - 0.2, HY0 + 0.1, SL, PZ, bev=True)
    for y in (3.9,):
        for sx in (-1, 1):
            x0, x1 = sorted((sx * 5.1, sx * 5.3))
            B.span("bconc", x0, x1, y - 0.3, y + 0.3, SL, PZ, bev=True)
    B.span("team", HX0 + 0.5, HX1 - 0.5, HY0 - 0.12, HY0 - 0.1, PZ - 0.35, PZ - 0.15, bottom=True)   # team band
    # front louvres (2 big), side louvres, rear louvre
    for x in (-3.2, 3.2):
        K.louvre_panel(B, "y", HY0, x, 4.3, -1, w=3.0, h=1.6)
    for sx, xo in ((-1, HX0), (1, HX1)):
        for y in (2.2, 5.6):
            K.louvre_panel(B, "x", xo, y, 4.6, sx, w=2.2, h=0.9)
    K.louvre_panel(B, "y", HY1, -2.4, 4.6, 1, w=2.6, h=0.9)
    K.louvre_panel(B, "y", HY1, 3.0, 4.6, 1, w=2.0, h=0.9)
    for z in (1.5, 1.75):                                                                      # rear conduit run
        B.strut("rubber", (-4.4, HY1 + 0.12, z), (0.9, HY1 + 0.12, z), 0.05)
    B.strut("rubber", (-4.4, HY1 + 0.12, 1.5), (-4.4, HY1 + 0.12, 3.6), 0.05)
    B.span("cabinet", -4.8, -4.0, HY1, HY1 + 0.3, 3.4, 4.2)
    B.span("cabinet", -1.0, 0.6, HY1, HY1 + 0.45, SL, 2.0, bev=True)
    B.span("metal", -1.1, 0.7, HY1, HY1 + 0.5, 2.0, 2.08)
    # central door with concrete hood + lamp (status light)
    B.span("gconc", -1.0, 1.0, HY0 - 0.12, HY0, SL, 2.75, bev=True)
    B.span("door", -0.65, 0.65, HY0 - 0.14, HY0 - 0.12, SL + 0.1, 2.45)
    B.span("bconc", -1.25, 1.25, HY0 - 1.0, HY0, 2.9, 3.35, bev=True)                    # hood
    B.span("lamp", -0.5, 0.5, HY0 - 0.9, HY0 - 0.6, 2.88, 2.9, bottom=True)
    K.wall_lamp(B, kit, "y", HY0 - 0.12, 0.0, 3.65, -1, "Light_Status0")
    # rear personnel door + side double cabinet door (west)
    B.span("door", 1.4, 2.5, HY1, HY1 + 0.04, SL, 2.4)
    B.span("bconc", 1.2, 2.7, HY1, HY1 + 0.55, 2.5, 2.7, bottom=True)
    # wall junction boxes + conduits on the front wall (cable bundles land here)
    for sx in (-1, 1):
        x = sx * 2.0
        B.span("cabinet", x - 0.35, x + 0.35, HY0 - 0.3, HY0, 1.2, 2.2)
        B.span("metal", x - 0.4, x + 0.4, HY0 - 0.34, HY0, 2.2, 2.28, bottom=True)
        B.strut("metal", (x, HY0 - 0.12, 2.28), (x, HY0 - 0.12, 2.9), 0.05)
    # side conduit runs (east wall, concept side view)
    for z in (1.6, 1.85):
        B.strut("rubber", (HX1 + 0.12, 1.0, z), (HX1 + 0.12, 6.8, z), 0.05)
    B.span("cabinet", HX1, HX1 + 0.35, 4.6, 5.6, SL, 2.2)
    # ---------------------------------------------------------------- roof hardware
    RZ = PZ - 0.35
    for x in (-2.6, 2.6):                                 # two raised louvred vent boxes with grating tops
        B.span("bconc", x - 0.95, x + 0.95, 3.0, 4.9, RZ, RZ + 0.35, bev=True)
        B.span("vent", x - 0.8, x + 0.8, 3.15, 4.75, RZ + 0.35, RZ + 0.95)
        B.span("metal", x - 0.9, x + 0.9, 3.05, 4.85, RZ + 0.95, RZ + 1.02)
        B.span("grate", x - 0.75, x + 0.75, 3.2, 4.7, RZ + 1.02, RZ + 1.04)
    for sx in (-1, 1):                                     # rear-corner roof exhaust stacks (beacons on top)
        x, y = sx * 4.2, 6.6
        B.cyl("metal", (x, y, RZ + 0.2), 0.42, 0.4, seg=10)
        B.cyl("steel", (x, y, RZ + 1.75), 0.24, 3.1, seg=10)
        B.cyl("dark", (x, y, RZ + 3.32), 0.28, 0.06, seg=10, bottom=True)
        K.roof_beacon(B, kit, x + 0.38 * sx, y, RZ + 2.9, f"Light_Beacon{0 if sx < 0 else 1}", r=0.1)
        B.span("metal", *sorted((x + sx * 0.2, x + sx * 0.46)), y - 0.05, y + 0.05, RZ + 2.83, RZ + 2.9, bottom=True)
    B.span("hvac", -0.6, 0.6, 5.6, 6.6, RZ, RZ + 0.55, bev=True)                     # roof hatch housing
    B.strut("metal", (HX0 + 0.5, 1.0, RZ + 0.1), (HX0 + 0.5, 6.6, RZ + 0.1), 0.05)
    # roof-edge flood heads at the two front corners (aimed forward/down)
    for sx, nm in ((-1, "Light_Flood0"), (1, "Light_Flood1")):
        K.flood_head(B, kit, sx * 4.9, HY0 - 0.45, PZ + 0.05, -PI / 2 + sx * 0.35, nm, tilt=40)
        B.span("metal", sx * 4.9 - 0.05, sx * 4.9 + 0.05, HY0 - 0.45, HY0, PZ - 0.2, PZ + 0.0, bottom=True)
    B.ladder((HX1 + 0.1, 6.4, SL), (0, 1, 0), PZ - SL + 0.6, (1, 0, 0))

    # ---------------------------------------------------------------- generator modules (olive, front)
    def genset(cx, idx):
        x0, x1, y0, y1 = cx - 2.1, cx + 2.1, -5.6, -1.6
        z0 = SL + 0.28
        P.span("dark", x0 - 0.15, x1 + 0.15, y0 - 0.2, y1 + 0.15, SL, z0)                      # skid
        P.span("hazard", x0 - 0.15, x1 + 0.15, y0 - 0.22, y0 - 0.2, SL + 0.03, z0 - 0.02)
        P.span("cabinet", x0, x1, y0, y1, z0, z0 + 2.35, bev=True)
        P.frustum("tank", x0, x1, y0, y1, z0 + 2.35, z0 + 2.6, 0.18, bev=False)                   # bevelled lid
        P.span("team", x0 + 0.02, x1 - 0.02, y0 - 0.02, y0, z0 + 2.15, z0 + 2.3, bottom=True)
        K.louvre_panel(P, "y", y0, cx, z0 + 1.1, -1, w=3.3, h=1.5)                                   # radiator grille
        for sx in (-1, 1):                                                                         # side louvres
            K.louvre_panel(P, "x", cx + sx * 2.1, -3.6, z0 + 1.4, sx, w=2.4, h=0.7)
        zt = z0 + 2.6
        for y in (-4.4, -2.8):                                                                      # silencer saddles
            P.span("metal", cx - 0.5, cx + 0.5, y - 0.12, y + 0.12, zt, zt + 0.3)
        P.tank("metal", (cx, -3.6, zt + 0.5), 0.42, 2.7, axis=(0, 1, 0), seg=12)                  # horizontal silencer
        P.cyl("steel", (cx, -2.0, zt + 0.95), 0.2, 1.0, seg=10)                                     # vertical outlet
        P.cyl("dark", (cx, -2.0, zt + 1.48), 0.24, 0.08, seg=10, r2=0.18, bottom=True)
        for s in (-1, 1):                                                                           # bands on silencer
            P.cyl("dark", (cx, -3.6 + s * 0.9, zt + 0.5), 0.44, 0.08, rot=(PI / 2, 0, 0), seg=12, bottom=True)
        # cable bundle from module inner side to the wall junction box
        side = -1 if cx > 0 else 1
        xs = cx + side * 2.1
        for k in range(3):
            o = (k - 1) * 0.14
            P.pipe("rubber", [(xs, -3.0 + o, z0 + 1.3), (xs + side * 0.35, -3.0 + o, z0 + 1.0),
                              (xs + side * 0.45, -3.0 + o, SL + 0.08), (xs + side * 0.45, -1.2 + o * 0.5, SL + 0.08),
                              (math.copysign(2.0, cx) + o, HY0 - 0.6, SL + 0.08), (math.copysign(2.0, cx) + o, HY0 - 0.25, 1.2)], 0.06)
        # status lamp on the module's outer front corner
        sx = 1 if cx > 0 else -1
        P.span("metal", cx + sx * 1.8 - 0.1, cx + sx * 1.8 + 0.1, y0 + 0.1, y0 + 0.3, zt, zt + 0.1)
        kit.light(f"Light_Status{idx}", (cx + sx * 1.8, y0 + 0.2, zt + 0.1), "dome", r=0.12)
        # yellow bollards at the outer front corner
        for bx, by in ((x0 - 0.45, y0 - 0.5), (x1 + 0.45, y0 - 0.5)):
            P.cyl("yellow", (bx, by, SL + 0.5), 0.1, 1.0, seg=8)
    genset(-3.7, 1)
    genset(3.7, 2)

    # ---------------------------------------------------------------- fuel tanks (east) with yellow pipework
    for i, (ty, L) in enumerate(((3.7, 4.6), (-3.3, 5.0))):
        tx = 7.15
        for y in (ty - L * 0.3, ty + L * 0.3):
            P.span("conc", tx - 0.75, tx + 0.75, y - 0.25, y + 0.25, SL, SL + 0.6, bev=True)   # saddle
        P.tank("tank", (tx, ty, SL + 1.45), 0.95, L, axis=(0, 1, 0), seg=16)
        P.cyl("metal", (tx, ty + 0.6, SL + 2.45), 0.26, 0.2, seg=10)                                # manway
        P.cyl("metal", (tx, ty + 0.6, SL + 2.56), 0.3, 0.05, seg=10, bottom=True)
        P.cyl("yellow", (tx - 0.3, ty - 0.8, SL + 2.5), 0.06, 0.4, seg=6)                          # vent
        for s in (-1, 1):
            P.cyl("metal", (tx, ty + s * L * 0.3, SL + 1.45), 0.97, 0.1, rot=(PI / 2, 0, 0), seg=16, bottom=True)
    P.ladder((6.15, -3.3, SL), (0, 1, 0), 2.4, (-1, 0, 0), m="yellow")
    P.pipe("yellow", [(6.4, 3.7, SL + 0.9), (5.8, 3.7, SL + 0.9), (5.8, -1.0, SL + 0.9), (5.8, -1.0, SL + 0.15),
                      (5.9, -3.3, SL + 0.15), (6.25, -3.3, SL + 0.6)], 0.07)
    P.pipe("yellow", [(5.8, -1.0, SL + 0.9), (5.8, -1.3, SL + 1.5), (5.8, -2.4, SL + 1.5)], 0.06)
    for y in (2.5, 0.5, -1.5):
        P.span("metal", 5.65, 5.95, y - 0.05, y + 0.05, SL, SL + 0.95)

    # ---------------------------------------------------------------- west: electrical cabinets / transformer
    P.span("cabinet", -8.2, -6.6, -1.2, 1.6, SL, SL + 2.2, bev=True)
    P.span("metal", -8.3, -6.5, -1.3, 1.7, SL + 2.2, SL + 2.3)
    P.span("cabinet", -8.1, -6.7, 2.4, 3.6, SL, SL + 1.9, bev=True)
    P.span("cabinet", -7.9, -6.9, -3.6, -2.2, SL, SL + 1.6, bev=True)
    P.span("metal", HX0 - 0.1, -6.6, 0.2, 0.3, SL + 1.7, SL + 1.85)
    for z in (SL + 1.95, SL + 2.1):
        P.strut("rubber", (-6.6, 0.0, z), (HX0, 0.0, z), 0.05)
    P.span("cabinet", -8.2, -6.9, 5.0, 6.6, SL, SL + 1.5, bev=True)
    for (x, y) in ((-6.3, -2.0), (-6.3, 4.2)):
        P.cyl("yellow", (x, y, SL + 0.5), 0.1, 1.0, seg=8)

    # ---------------------------------------------------------------- perimeter: kerb, concrete pillars, mesh fence
    FZ = SL + 0.32
    FH = 1.75
    runs = [((-8.6, -7.5), (-8.6, 7.6)), ((-8.6, 7.6), (8.6, 7.6)), ((8.6, 7.6), (8.6, -7.5)),
            ((-8.6, -7.5), (-6.4, -7.5)), ((6.4, -7.5), (8.6, -7.5))]
    for (x0, y0), (x1, y1) in runs:
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / 2.6)))
        ax = "x" if abs(y1 - y0) < 1e-6 else "y"
        if ax == "x":
            P.span("conc", min(x0, x1), max(x0, x1), y0 - 0.14, y0 + 0.14, SL, FZ)
        else:
            P.span("conc", x0 - 0.14, x0 + 0.14, min(y0, y1), max(y0, y1), SL, FZ)
        for k in range(n + 1):
            t = k / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if not P.once("post", x, y):
                continue
            P.span("conc", x - 0.2, x + 0.2, y - 0.2, y + 0.2, SL, FZ + FH + 0.15, bev=True)
            P.span("metal", x - 0.22, x + 0.22, y - 0.22, y + 0.22, FZ + FH + 0.15, FZ + FH + 0.2)
        for k in range(n):
            a = (x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
            b = (x0 + (x1 - x0) * (k + 1) / n, y0 + (y1 - y0) * (k + 1) / n)
            P.strut("metal", (*a, FZ + FH), (*b, FZ + FH), 0.03, seg=4)
            P.strut("metal", (*a, FZ + 0.05), (*b, FZ + 0.05), 0.03, seg=4)
            kit.fence(a, b, FZ, FH)
    # front corner concrete walls (solid) + bollards at the open front
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 6.4, sx * 5.4))
        P.span("bconc", x0, x1, -7.65, -7.35, SL, SL + 1.1, bev=True)
        for x in (sx * 1.6, sx * 5.0):
            P.cyl("yellow", (x, -7.3, SL + 0.5), 0.1, 1.0, seg=8)
            P.cyl("dark", (x, -7.3, SL + 1.01), 0.105, 0.03, seg=8, bottom=True)
    return kit, B, P


if not O["skip_build"]:
    kit, B, P = build()
    kit.finish(B, P, O["out"])
if O["previews"]:
    K.previews(GLB, O["previews"], ID, extent=18.0, concept=O["concept"], only=O["only"], target_z=2.6)
