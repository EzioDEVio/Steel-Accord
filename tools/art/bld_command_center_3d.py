"""Steel Accord - M1 3D structure: US 'Command Center' (code-built + texture-baked in Blender, bpy 5.x). Original
design recreated from the client's concept sheet (individual_views/Command_Center).

Run:  python3 -I bld_command_center_3d.py <out_dir> [--previews <dir>] [--concept <overhead.png>] [--only rts,front]
      [--previews-only]
Out:  <out_dir>/command_center.glb  nodes: Building, Props, Light_Status0..2, Light_Beacon0..1, Light_Flood0..1, Exit
Slab 26 (X) x 22 (Y) m, origin = slab bottom centre, front (main door) = Blender -Y = Godot +Z.
Layout: fortified two-storey HQ block (grey cast concrete, battered base, buttresses, lit clerestory band) with a
satellite dish, lattice radar tower and antenna masts on its roof; lower operations annex to the west with
condenser units; olive generator shelters front-left and rear; tarp shelter and equipment boxes east;
perimeter of T-wall barriers + sandbags at the front, HESCO bastions at the rear.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit as K
from bldkit import PI, V

O = K.cli(sys.argv[1:])
ID = "command_center"
GLB = os.path.join(O["out"], ID + ".glb")


def build():
    kit = K.Kit(ID, "CC", "CC_CommandCenter", atlas=4096)
    B = kit.part("Building"); P = kit.part("Props")
    SL = 0.25
    MX0, MX1, MY0, MY1 = -1.5, 8.0, -4.5, 5.0       # main HQ block
    RZ, PZ = 9.4, 10.0                              # roof deck / parapet top
    DX = (MX0 + MX1) / 2                            # door centre x
    AX0, AX1, AY0, AY1 = -10.8, MX0, -3.4, 5.0      # operations annex
    ARZ, APZ = 4.6, 5.05

    # ---------------------------------------------------------------- slab
    B.frustum("slab", -13.0, 13.0, -11.0, 11.0, 0.0, SL, 0.12)
    B.span("slab", -11.4, 9.4, -5.6, 6.0, SL - 0.05, SL + 0.06)
    for x in (DX - 1.3, DX + 1.3):                                    # painted walkway to the door
        B.span("yellow", x - 0.05, x + 0.05, -10.8, MY0 - 2.4, SL, SL + 0.008)

    # ---------------------------------------------------------------- main block: battered base + walls
    B.frustum("gconc", MX0 - 0.75, MX1 + 0.75, MY0 - 0.75, MY1 + 0.75, SL, 2.2, 0.75, bev=True)
    T = 0.4
    B.span("gconc", MX0, MX1, MY0, MY0 + T, 2.2, RZ)
    B.span("gconc", MX0, MX1, MY1 - T, MY1, 2.2, RZ)
    B.span("gconc", MX1 - T, MX1, MY0, MY1, 2.2, RZ)
    B.span("gconc", MX0, MX0 + T, MY0, MY1, 2.2, RZ)
    B.span("gconc", MX0 - 0.12, MX1 + 0.12, MY0 - 0.12, MY1 + 0.12, RZ - 0.3, PZ, bev=True)      # parapet band
    B.span("roofg", MX0 + 0.3, MX1 - 0.3, MY0 + 0.3, MY1 - 0.3, RZ - 0.1, RZ)
    B.span("team", MX0 + 1.4, MX1 - 1.4, MY0 - 0.14, MY0 - 0.12, RZ + 0.05, RZ + 0.3, bottom=True)
    # horizontal string course + clerestory window band (lit) on front and east
    B.span("gconc", MX0 - 0.1, MX1 + 0.1, MY0 - 0.1, MY1 + 0.1, 5.85, 6.05, bev=True)
    B.span("gconc", MX0 + 1.1, MX1 - 1.1, MY0 - 0.28, MY0, 6.15, 6.35, bev=True)               # sill
    B.span("gconc", MX0 + 1.1, MX1 - 1.1, MY0 - 0.32, MY0, 7.45, 7.75, bev=True)               # hood
    B.span("winlit", MX0 + 1.2, MX1 - 1.2, MY0 - 0.04, MY0, 6.35, 7.45)
    B.span("gconc", MX1, MX1 + 0.28, MY0 + 1.2, MY1 - 1.6, 6.15, 6.35, bev=True)
    B.span("gconc", MX1, MX1 + 0.32, MY0 + 1.2, MY1 - 1.6, 7.45, 7.75, bev=True)
    B.span("winlit", MX1, MX1 + 0.04, MY0 + 1.3, MY1 - 1.7, 6.35, 7.45)
    B.span("winlit", MX0 + 1.4, MX0 + 4.2, MY1, MY1 + 0.04, 6.45, 7.35)                          # rear window
    B.span("gconc", MX0 + 1.3, MX0 + 4.3, MY1, MY1 + 0.3, 7.35, 7.6, bev=True)
    # battered buttresses (front corners, door piers, east side, rear corners)
    def butt_y(x0, x1, face, out, top=8.6, base=1.7):
        B.prism("gconc", [(face, SL), (face + out * base, SL), (face + out * 0.45, top - 0.5), (face + out * 0.45, top),
                          (face, top)], "x", x0, x1, bev=True)

    def butt_x(y0, y1, face, out, top=8.6, base=1.7):
        B.prism("gconc", [(face, SL), (face + out * base, SL), (face + out * 0.45, top - 0.5), (face + out * 0.45, top),
                          (face, top)], "y", y0, y1, bev=True)
    butt_y(MX0 - 0.1, MX0 + 1.0, MY0, -1)
    butt_y(MX1 - 1.0, MX1 + 0.1, MY0, -1)
    butt_y(DX - 2.0, DX - 1.4, MY0, -1, top=5.85, base=1.3)
    butt_y(DX + 1.4, DX + 2.0, MY0, -1, top=5.85, base=1.3)
    butt_x(MY0 - 0.1, MY0 + 1.0, MX1, 1)
    butt_x(MY1 - 1.0, MY1 + 0.1, MX1, 1)
    butt_x(-0.4, 0.4, MX1, 1, top=5.85, base=1.3)
    butt_y(MX1 - 1.0, MX1 + 0.1, MY1, 1)
    butt_y(MX0 + 4.6, MX0 + 5.4, MY1, 1, top=5.85, base=1.3)
    # entrance: landing, steps, recessed steel door, canopy, door lamps (status)
    LY = MY0 - 1.5
    B.span("gconc", DX - 1.4, DX + 1.4, LY, MY0, SL, SL + 0.75, bev=True)
    for k in range(3):
        y0 = LY - (k + 1) * 0.32
        B.span("gconc", DX - 1.25, DX + 1.25, y0, y0 + 0.33, SL, SL + 0.75 - (k + 1) * 0.19, bev=True)
    B.span("yellow", DX - 1.25, DX + 1.25, LY - 0.06, LY + 0.02, SL + 0.75, SL + 0.76)
    B.span("gconc", DX - 1.2, DX + 1.2, MY0 - 0.3, MY0, SL + 0.75, 3.6, bev=True)               # door surround
    B.span("dark", DX - 0.85, DX + 0.85, MY0 - 0.32, MY0 - 0.3, SL + 0.75, 3.3)
    B.span("door", DX - 0.75, DX + 0.75, MY0 - 0.34, MY0 - 0.32, SL + 0.75, 3.2)
    B.span("metal", DX - 0.06, DX + 0.06, MY0 - 0.38, MY0 - 0.34, SL + 0.8, 3.2)
    B.prism("metal", [(MY0 - 0.3, 3.95), (MY0 - 0.3, 3.75), (MY0 - 1.7, 3.5), (MY0 - 1.7, 3.62)], "x", DX - 1.45, DX + 1.45)
    for s in (-1, 1):
        B.strut("metal", (DX + s * 1.3, MY0 - 0.3, 4.55), (DX + s * 1.3, MY0 - 1.6, 3.62), 0.03, seg=4)
        K.wall_lamp(B, kit, "y", MY0 - 0.3, DX + s * 1.0, 2.9, -1, f"Light_Status{0 if s < 0 else 1}")
    for s in (-1, 1):                                                                           # rails on steps
        B.strut("metal", (DX + s * 1.3, LY - 0.96, SL + 0.95), (DX + s * 1.3, LY, SL + 1.7), 0.025, seg=4)
        B.strut("metal", (DX + s * 1.3, LY - 0.96, SL), (DX + s * 1.3, LY - 0.96, SL + 0.95), 0.025, seg=4)
        B.strut("metal", (DX + s * 1.3, LY, SL + 0.75), (DX + s * 1.3, LY, SL + 1.7), 0.025, seg=4)
    # wall-mounted equipment: louvres on the east, conduit on front-left
    K.louvre_panel(B, "x", MX1, 2.6, 3.4, 1, w=1.4, h=0.8)
    K.louvre_panel(B, "y", MY1, 5.5, 3.6, 1, w=1.6, h=0.8)
    B.strut("metal", (MX0 + 1.2, MY0 - 0.1, 2.3), (MX0 + 1.2, MY0 - 0.1, 9.3), 0.07)
    # ---------------------------------------------------------------- main roof hardware
    rail = [(MX0 + 0.05, MY0 + 0.05), (MX1 - 0.05, MY0 + 0.05), (MX1 - 0.05, MY1 - 0.05), (MX0 + 0.05, MY1 - 0.05), (MX0 + 0.05, MY0 + 0.05)]
    B.railing("metal", rail, PZ, h=0.95, spacing=1.9)
    # satellite dish (front-left of roof)
    dx, dy = MX0 + 2.4, MY0 + 2.4
    B.span("metal", dx - 0.7, dx + 0.7, dy - 0.7, dy + 0.7, RZ, RZ + 0.45, bev=True)
    B.cyl("steel", (dx, dy, RZ + 1.15), 0.22, 1.4, seg=10)
    ax = V((-0.35, -0.55, 0.76)).normalized()
    dc = V((dx, dy, RZ + 2.25))
    B.cyl("metal", (dx, dy, RZ + 1.95), 0.32, 0.35, seg=10, bottom=True)
    B.dish("white", dc, 1.95, 0.55, ax, t=0.07, seg=20)
    feed = dc + ax * 1.45
    for a in range(3):
        ang = 2 * PI * a / 3
        q = ax.to_track_quat("Z", "Y")
        rim = dc + q @ V((1.85 * math.cos(ang), 1.85 * math.sin(ang), 0.5))
        B.strut("metal", rim, feed, 0.025, seg=4)
    B.box("white", feed + ax * 0.12, (0.28, 0.28, 0.3), ax.to_track_quat("Z", "Y").to_euler(), bottom=True)
    # lattice radar tower (rear-right of roof)
    tx, ty = MX1 - 1.9, MY1 - 1.9
    H = 6.0; b0, b1 = 0.95, 0.42
    legs = [(sx, sy) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for sx, sy in legs:
        B.span("metal", tx + sx * b0 - 0.18, tx + sx * b0 + 0.18, ty + sy * b0 - 0.18, ty + sy * b0 + 0.18, RZ, RZ + 0.25)
        B.strut("dark", (tx + sx * b0, ty + sy * b0, RZ), (tx + sx * b1, ty + sy * b1, RZ + H), 0.06, seg=4)
    lv = [0.0, 1.6, 3.1, 4.6, H]
    for i in range(len(lv) - 1):
        z0, z1 = lv[i], lv[i + 1]
        w0 = b0 + (b1 - b0) * z0 / H; w1 = b0 + (b1 - b0) * z1 / H
        for (ax0, ay0), (ax1, ay1) in zip(legs, legs[1:] + legs[:1]):
            p0 = (tx + ax0 * w0, ty + ay0 * w0, RZ + z0); p1 = (tx + ax1 * w1, ty + ay1 * w1, RZ + z1)
            q0 = (tx + ax1 * w0, ty + ay1 * w0, RZ + z0); q1 = (tx + ax0 * w1, ty + ay0 * w1, RZ + z1)
            B.strut("dark", p0, p1, 0.025, seg=4); B.strut("dark", q0, q1, 0.025, seg=4)
            B.strut("dark", q1, p1, 0.03, seg=4)
    zt = RZ + H
    B.span("metal", tx - 0.75, tx + 0.75, ty - 0.75, ty + 0.75, zt, zt + 0.12, bottom=True)          # top platform
    B.railing("metal", [(tx - 0.72, ty - 0.72), (tx + 0.72, ty - 0.72), (tx + 0.72, ty + 0.72), (tx - 0.72, ty + 0.72), (tx - 0.72, ty - 0.72)], zt + 0.12, h=0.6, spacing=1.5)
    B.cyl("steel", (tx, ty, zt + 0.45), 0.24, 0.66, seg=10)
    B.box("olive", (tx, ty - 0.05, zt + 1.55), (2.9, 0.28, 1.5), (math.radians(-12), 0, math.radians(-20)), bottom=True)
    B.box("grate", (tx + 0.06, ty - 0.21, zt + 1.53), (2.7, 0.04, 1.32), (math.radians(-12), 0, math.radians(-20)), bottom=True)
    B.cyl("metal", (tx + 0.25, ty + 0.25, zt + 2.6), 0.035, 0.9, seg=6)
    K.roof_beacon(B, kit, tx + 0.25, ty + 0.25, zt + 3.05, "Light_Beacon0")
    # antenna masts (rear centre)
    masts = [(MX0 + 3.6, MY1 - 1.0, 6.2), (MX0 + 4.7, MY1 - 0.9, 7.6), (MX0 + 5.8, MY1 - 1.2, 5.4)]
    for i, (x, y, h) in enumerate(masts):
        B.span("metal", x - 0.25, x + 0.25, y - 0.25, y + 0.25, RZ, RZ + 0.3)
        B.cyl("dark", (x, y, RZ + 0.3 + h / 2), 0.09, h, seg=6, r2=0.035)
        for z in (0.45, 0.7):
            B.strut("dark", (x - 0.35, y, RZ + 0.3 + h * z), (x + 0.35, y, RZ + 0.3 + h * z), 0.018, seg=4)
        if i == 1:
            K.roof_beacon(B, kit, x, y, RZ + 0.3 + h, "Light_Beacon1", r=0.11)
    # rooftop cabinets / shelter / hvac
    B.span("steel", MX0 + 4.6, MX0 + 6.4, MY0 + 0.8, MY0 + 2.2, RZ, RZ + 1.5, bev=True)
    B.span("metal", MX0 + 4.5, MX0 + 6.5, MY0 + 0.7, MY0 + 2.3, RZ + 1.5, RZ + 1.6)
    B.span("steel", MX0 + 7.2, MX0 + 8.4, MY0 + 0.8, MY0 + 1.8, RZ, RZ + 1.0, bev=True)
    B.span("steel", MX0 + 0.8, MX0 + 2.0, MY1 - 2.6, MY1 - 1.0, RZ, RZ + 1.2, bev=True)
    K.hvac(B, MX0 + 4.6, MY0 + 4.3, RZ, sx=1.4, sy=1.1, h=0.8)
    B.strut("rubber", (MX0 + 2.4, MY0 + 2.4, RZ + 0.2), (MX0 + 5.5, MY0 + 2.2, RZ + 0.2), 0.05)
    # status lamp on the front-right parapet corner, flood heads on the front corners
    B.span("metal", MX1 - 0.55, MX1 - 0.25, MY0 + 0.15, MY0 + 0.45, PZ, PZ + 0.35)
    kit.light("Light_Status2", (MX1 - 0.4, MY0 + 0.3, PZ + 0.35), "dome", r=0.14)
    for sx, nm in ((-1, "Light_Flood0"), (1, "Light_Flood1")):
        xc = MX0 + 0.4 if sx < 0 else MX1 - 0.4
        B.span("metal", xc - 0.05, xc + 0.05, MY0 - 0.5, MY0, PZ - 0.25, PZ - 0.1, bottom=True)
        K.flood_head(B, kit, xc, MY0 - 0.55, PZ - 0.2, -PI / 2 + sx * 0.5, nm, tilt=45)

    # ---------------------------------------------------------------- operations annex (west, lower)
    T = 0.35
    B.span("gconc", AX0, AX1, AY0, AY0 + T, SL, ARZ)
    B.span("gconc", AX0, AX1, AY1 - T, AY1, SL, ARZ)
    B.span("gconc", AX0, AX0 + T, AY0, AY1, SL, ARZ)
    B.span("gconc", AX0 - 0.1, AX1, AY0 - 0.1, AY1 + 0.1, ARZ - 0.2, APZ, bev=True)
    B.span("roofg", AX0 + 0.25, AX1 - 0.05, AY0 + 0.25, AY1 - 0.25, ARZ - 0.1, ARZ)
    B.span("gconc", AX0 - 0.1, AX1, AY0 - 0.1, AY1 + 0.1, SL, SL + 0.8, bev=True)
    for x in (AX0 + 0.1, AX0 + 3.3, AX0 + 6.5):                                     # pilasters on the front
        B.span("gconc", x - 0.3, x + 0.3, AY0 - 0.3, AY0, SL, APZ, bev=True)
    for x in (AX0 + 0.1, AX0 + 4.9):
        B.span("gconc", x - 0.3, x + 0.3, AY1, AY1 + 0.3, SL, APZ, bev=True)
    B.span("gconc", AX0 - 0.3, AX0, AY0 + 4.2, AY0 + 4.8, SL, APZ, bev=True)
    B.span("team", AX0 + 0.6, AX0 + 2.8, AY0 - 0.12, AY0 - 0.1, ARZ - 0.05, ARZ + 0.2, bottom=True)
    # annex front door + small window slits + louvre; side door
    ax_d = AX0 + 4.9
    B.span("gconc", ax_d - 0.8, ax_d + 0.8, AY0 - 0.15, AY0, SL, 2.75, bev=True)
    B.span("door", ax_d - 0.55, ax_d + 0.55, AY0 - 0.17, AY0 - 0.15, SL + 0.05, 2.4)
    B.prism("metal", [(AY0, 3.05), (AY0, 2.9), (AY0 - 1.0, 2.75), (AY0 - 1.0, 2.85)], "x", ax_d - 0.9, ax_d + 0.9)
    for x in (AX0 + 1.7, AX0 + 8.0):
        B.span("win", x - 0.6, x + 0.6, AY0 - 0.03, AY0, 2.7, 3.4)
        B.span("gconc", x - 0.7, x + 0.7, AY0 - 0.2, AY0, 2.55, 2.7, bev=True)
    K.louvre_panel(B, "x", AX0, 1.8, 3.2, -1, w=1.6, h=0.8)
    B.span("door", AX0 - 0.04, AX0, -0.6, 0.5, SL + 0.05, 2.4)
    B.ladder((AX0 + 2.2, AY0 - 0.02, SL), (1, 0, 0), APZ - SL + 0.7, (0, -1, 0))
    B.railing("metal", [(AX0 + 0.05, AY0 + 0.05), (AX1 - 0.2, AY0 + 0.05)], APZ, h=0.95, spacing=2.0)
    B.railing("metal", [(AX0 + 0.05, AY0 + 0.05), (AX0 + 0.05, AY1 - 0.05), (AX1 - 0.2, AY1 - 0.05)], APZ, h=0.95, spacing=2.2)
    # condenser units on the annex roof (twin-fan, the concept's rows of fan boxes)
    for x in (AX0 + 1.6, AX0 + 3.7, AX0 + 5.8):
        K.hvac(B, x, AY1 - 1.5, ARZ, sx=1.7, sy=1.0, h=0.75, fans=2)
    for x in (AX0 + 1.6, AX0 + 3.7):
        K.hvac(B, x, AY1 - 3.3, ARZ, sx=1.7, sy=1.0, h=0.75, fans=2)
    B.span("steel", AX0 + 6.6, AX0 + 8.4, AY0 + 0.8, AY0 + 2.2, ARZ, ARZ + 0.9, bev=True)
    B.strut("metal", (AX0 + 7.5, AY0 + 2.2, ARZ + 0.5), (AX0 + 7.5, AY1 - 1.0, ARZ + 0.5), 0.12, seg=8)
    B.span("hvac", AX0 + 7.0, AX0 + 8.0, AY1 - 1.0, AY1 - 0.3, ARZ, ARZ + 0.7, bev=True)

    # ---------------------------------------------------------------- generator shelters (olive)
    def gen_shelter(x0, x1, y0, y1, h, front_out, fans=2):
        P.span("dark", x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, SL, SL + 0.15)
        P.span("cont", x0, x1, y0, y1, SL + 0.15, SL + h, bev=True)
        P.span("olive", x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, SL + h, SL + h + 0.08)
        fy = y0 if front_out < 0 else y1
        K.louvre_panel(P, "y", fy, x0 + (x1 - x0) * 0.3, SL + 1.3, front_out, w=1.6, h=1.2)
        P.span("cabinet", x0 + (x1 - x0) * 0.58, x0 + (x1 - x0) * 0.58 + 1.1, *sorted((fy, fy + front_out * 0.04)), SL + 0.3, SL + 2.2)
        K.hvac(P, x0 + (x1 - x0) * 0.32, (y0 + y1) / 2, SL + h + 0.08, sx=1.8, sy=1.1, h=0.6, fans=fans)
        P.cyl("steel", (x1 - 0.6, (y0 + y1) / 2, SL + h + 0.6), 0.14, 1.1, seg=8)
        P.cyl("dark", (x1 - 0.6, (y0 + y1) / 2, SL + h + 1.17), 0.17, 0.05, seg=8, bottom=True)
        P.ladder((x1 + 0.02, y0 + 0.6, SL), (0, 1, 0), h + 0.6, (1, 0, 0))
    gen_shelter(-10.4, -4.6, -8.6, -5.4, 2.6, -1)
    gen_shelter(1.4, 7.0, 6.3, 9.0, 2.5, 1)
    # ---------------------------------------------------------------- tarp shelter + supplies (east)
    sx0, sx1, sy0, sy1 = 9.2, 11.4, -1.4, 4.4
    for x in (sx0, sx1):
        for y in (sy0, (sy0 + sy1) / 2, sy1):
            P.cyl("metal", (x, y, SL + 1.2), 0.05, 2.4, seg=6)
    P.prism("tarp", [(sx0 - 0.15, SL + 2.35), (sx1 + 0.15, SL + 2.35), (sx1 + 0.15, SL + 2.5), ((sx0 + sx1) / 2, SL + 3.05),
                     (sx0 - 0.15, SL + 2.5)], "y", sy0 - 0.2, sy1 + 0.2, drop=False)
    P.span("tarp", sx1 + 0.02, sx1 + 0.06, sy0, sy1, SL + 0.4, SL + 2.35)
    P.span("tarp", sx0, sx1, sy1 + 0.02, sy1 + 0.06, SL + 0.4, SL + 2.35)
    for (cx, cy, l) in ((10.0, 3.3, 2), (10.0, 2.0, 1), (10.6, 0.4, 2)):
        K.ammo_pallet(P, cx, cy, SL, l)
    K.tarp_stack(P, 10.4, -0.9, SL, 1.4, 1.0, 1.1)
    # grey equipment boxes (front-right)
    for (x, y, sx, sy, h) in ((10.0, -7.6, 1.6, 1.3, 1.5), (11.5, -7.3, 1.1, 1.1, 1.1), (10.1, -5.9, 1.4, 1.2, 1.2),
                              (11.4, -5.6, 1.2, 1.5, 1.6), (10.2, -4.4, 1.2, 1.0, 0.9), (11.5, -3.9, 1.0, 1.0, 1.25)):
        P.span("steel", x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, SL, SL + h, bev=True)
        P.span("metal", x - sx / 2 + 0.1, x + sx / 2 - 0.1, y - sy / 2 - 0.02, y - sy / 2, SL + 0.15, SL + h - 0.15)
    for (x, y) in ((8.9, -8.6), (8.9, -8.0)):
        K.drum(P, x, y, SL)
    # rear clutter by the annex
    for (x, y, sx, sy, h) in ((-9.8, 6.6, 1.4, 1.2, 1.4), (-8.2, 6.4, 1.2, 1.0, 1.0), (-6.4, 6.5, 1.6, 1.2, 1.8)):
        P.span("steel", x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, SL, SL + h, bev=True)
    for (x, y) in ((-4.2, 6.4), (-3.6, 6.8), (-4.0, 7.3)):
        K.drum(P, x, y, SL, "olive")
    K.tarp_stack(P, 9.9, 7.4, SL, 2.0, 1.8, 1.6)
    K.ammo_pallet(P, -8.6, -4.4, SL, 1)

    # ---------------------------------------------------------------- perimeter defences
    GX0, GX1 = DX - 1.7, DX + 1.7          # gap in front of the door
    K.jersey_run(P, -12.6, GX0, -10.45, "x", SL, seglen=1.9, gap=0.08, sx=1.25, sz=1.75)
    K.jersey_run(P, GX1, 12.6, -10.45, "x", SL, seglen=1.9, gap=0.08, sx=1.25, sz=1.75)
    K.sandbag_run(P, -11.95, GX0 - 0.2, -9.55, "x", SL)
    K.sandbag_run(P, GX1 + 0.2, 11.95, -9.55, "x", SL)
    for sx in (-1, 1):
        K.jersey_run(P, -9.9, 0.2, sx * 12.65, "y", SL, seglen=1.9, gap=0.08, sx=1.25, sz=1.75)
        K.sandbag_run(P, -9.05, 0.3, sx * 11.85, "y", SL)
        K.hesco_run(P, 0.6, 10.4, sx * 12.4, "y", SL)
    K.hesco_run(P, -11.85, 11.85, 10.4, "x", SL)
    # door-side sandbag bunkers flanking the gap
    for x in (GX0 - 0.6, GX1 + 0.6):
        K.sandbag_run(P, -9.1, -7.6, x, "y", SL, h=0.9)

    # ---------------------------------------------------------------- exit marker (ground, in front of the door gap)
    kit.empty("Exit", (DX, -12.0, 0.0))
    return kit, B, P


if not O["skip_build"]:
    kit, B, P = build()
    kit.finish(B, P, O["out"])
if O["previews"]:
    K.previews(GLB, O["previews"], ID, extent=26.0, concept=O["concept"], only=O["only"], target_z=3.5)
