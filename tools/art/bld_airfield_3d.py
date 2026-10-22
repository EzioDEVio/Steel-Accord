"""Steel Accord - M1 structure: Airfield (redesign with a RUNWAY).

Run:  python3 -I bld_airfield_3d.py <out_dir> [--previews <dir>] [--concept <png>] [--only rts] [--previews-only]
Out:  <out_dir>/airfield.glb
  Building - slab (painted runway / taxiway / apron markings), arched olive hangar, control tower, ops annex
  Props    - fuel tank, containers, crates, GSE cart, windsock, light poles, runway light housings, taxi lights
  Light_Runway0..15 (pairs along the runway from RunwayStart to RunwayEnd: even = front edge, odd = back edge),
  Light_Status0..2, Light_Beacon0..1, Light_Flood0..3
  Empties: Pad0..Pad3 (centre of each parking spot, on the slab), RunwayStart, RunwayEnd (runway centreline ends;
           take-off and landing run from RunwayStart toward RunwayEnd = Blender +X = Godot +X)
Footprint 60 (X) x 44 (depth) m, origin = footprint centre at ground, front = Blender -Y = Godot +Z.
Runway 60 x 10 m along X at the BACK (Blender +Y = Godot -Z); hangar + tower on the left end; 2 x 2 parking
apron in the front half linked to the runway by a taxiway. Stylised RTS proportions (real runways are far longer).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import numpy as np
from mathutils import Matrix, Euler, Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "airfield.glb")
PI = math.pi

SL = 0.2
RY0, RY1 = 11.5, 21.5                      # runway band (Blender Y)
RCY = (RY0 + RY1) / 2
TWX0, TWX1 = 8.0, 16.0                     # taxiway (runway <-> apron)
PADS = [(5.0, -14.0), (19.0, -14.0), (5.0, 0.0), (19.0, 0.0)]
LANE_X = 12.0
HX0, HX1, HY0, HY1 = -21.0, -5.0, -8.0, 7.0   # hangar
HCX = (HX0 + HX1) / 2
HW = (HX1 - HX0) / 2
WALL, RIDGE = 2.3, 8.2
TWR = (-25.6, 3.0)                         # control tower centre
YEL, WHT = (222, 176, 40), (232, 230, 222)

# hangar arch circle through (+-HW, WALL) and (0, RIDGE)
_h = RIDGE - WALL
ARC_R = (HW * HW + _h * _h) / (2 * _h)
ARC_ZC = RIDGE - ARC_R


def arc_z(dx):
    return ARC_ZC + math.sqrt(max(ARC_R * ARC_R - dx * dx, 0.0))


def arc_pts(off=0.0, n=22):
    """Outer arch (offset `off` inward) from left wall top to right wall top, as (x, z)."""
    R = ARC_R - off
    p0 = math.atan2(WALL - ARC_ZC, -(HW - off))
    p1 = math.atan2(WALL - ARC_ZC, HW - off)
    return [(HCX + R * math.cos(p0 + (p1 - p0) * i / n), ARC_ZC + R * math.sin(p0 + (p1 - p0) * i / n)) for i in range(n + 1)]


# ---------------------------------------------------------------------- ground plan
def paint_plan(kit):
    C = kit.set_plan(-30, 30, -22, 22, 40)
    C.fill((-30, 30, -22, 22), K.ground_concrete((162, 158, 148), joint=5.0, seed=510, stains=0.07))
    asph = K.ground_asphalt((72, 73, 75), seed=530)
    C.fill((-30, 30, RY0 - 0.6, RY1 + 0.5), asph)                       # runway + shoulders
    C.fill((TWX0, TWX1, 6.5, RY0), asph)                                 # taxiway
    # runway: edge lines, centreline dashes, threshold piano keys, designators, aiming bars
    for y in (RY0 + 0.35, RY1 - 0.35):
        C.line((-29.6, y), (29.6, y), 0.3, WHT, wear=0.2)
    for sgn in (-1, 1):
        x0 = sgn * 28.6
        for k in range(8):
            y = RY0 + 1.2 + k * (RY1 - RY0 - 2.4) / 7
            if abs(y - RCY) < 0.6:
                continue
            C.line((x0, y), (x0 - sgn * 3.2, y), 0.55, WHT, wear=0.25)
        C.line((sgn * 29.6, RY0 + 0.4), (sgn * 29.6, RY1 - 0.4), 0.4, WHT, wear=0.25)
        for y in (RCY - 2.6, RCY + 2.6):                                  # aiming-point bars
            C.line((sgn * 15.5, y), (sgn * 11.5, y), 1.1, WHT, wear=0.3)
    # designators: '09' at the RunwayStart (left) end reading toward +X; '27' at the right end
    C.digit("0", -22.6, RCY + 1.25, 3.2, WHT, ang=-PI / 2, wear=0.3)
    C.digit("9", -22.6, RCY - 1.25, 3.2, WHT, ang=-PI / 2, wear=0.3)
    C.digit("2", 22.6, RCY - 1.25, 3.2, WHT, ang=PI / 2, wear=0.3)
    C.digit("7", 22.6, RCY + 1.25, 3.2, WHT, ang=PI / 2, wear=0.3)
    # taxiway edge lines + centreline curving onto the runway centreline both ways
    for x in (TWX0 + 0.25, TWX1 - 0.25):
        C.line((x, 6.6), (x, RY0 - 0.6), 0.18, YEL, wear=0.3)
    C.line((LANE_X, -21.5), (LANE_X, RCY - 4.0), 0.3, YEL, wear=0.3)
    C.arc(LANE_X - 4.0, RCY - 4.0, 4.0, 0, 90, 0.3, YEL, wear=0.3)
    C.arc(LANE_X + 4.0, RCY - 4.0, 4.0, 90, 180, 0.3, YEL, wear=0.3)
    C.line((LANE_X - 4.0, RCY), (LANE_X - 7.0, RCY), 0.3, YEL, wear=0.35)
    C.line((LANE_X + 4.0, RCY), (LANE_X + 7.0, RCY), 0.3, YEL, wear=0.35)
    x = -19.0  # runway centreline dashes (painted over the lead-on ends)
    while x + 3.0 <= 19.2:
        C.line((x, RCY), (x + 3.0, RCY), 0.45, WHT, wear=0.3)
        x += 5.0
    # holding-position marking across the taxiway (2 solid + 2 dashed)
    for k, y in enumerate((RY0 - 1.6, RY0 - 1.95)):
        C.line((TWX0 + 0.4, y), (TWX1 - 0.4, y), 0.15, YEL, wear=0.2)
    for y in (RY0 - 2.4, RY0 - 2.75):
        for x in np.arange(TWX0 + 0.5, TWX1 - 0.6, 1.2):
            C.line((x, y), (x + 0.7, y), 0.15, YEL, wear=0.2)
    # parking spots: circle + lead-in + T stop bar + number
    for i, (px, py) in enumerate(PADS):
        C.ring(px, py, 4.75, 5.0, YEL, wear=0.3)
        C.ring(px, py, 1.0, 1.15, YEL, wear=0.3)
        side = 1 if px > LANE_X else -1
        C.line((LANE_X, py), (px, py), 0.3, YEL, wear=0.3)
        C.line((px + side * -0.0, py - 2.4), (px, py + 2.4), 0.25, YEL, wear=0.3)          # nose line
        C.line((px - 1.6, py + 2.6), (px + 1.6, py + 2.6), 0.45, YEL, wear=0.3)            # T stop bar
        C.digit(str(i + 1), px + side * 3.4, py - 3.3, 1.4, YEL, wear=0.3)
        for a in (45, 135, 225, 315):                                                       # tie-down points
            C.disc(px + 3.6 * math.cos(math.radians(a)), py + 3.6 * math.sin(math.radians(a)), 0.18, (60, 60, 58), wear=0.0)
    # hangar lead-in: from the door down then across to the lane
    C.line((HCX, HY0 + 1.0), (HCX, -16.0), 0.3, YEL, wear=0.3)
    C.arc(HCX + 3.0, -16.0, 3.0, 180, 270, 0.3, YEL, wear=0.3)
    C.line((HCX + 3.0, -19.0), (LANE_X, -19.0), 0.3, YEL, wear=0.3)
    # apron boundary (solid + dashed) and a red/white keep-clear box at the fuel tank
    C.line((-3.0, -21.6), (-3.0, 6.3), 0.2, YEL, wear=0.3)
    C.line((-3.0, 6.3), (29.6, 6.3), 0.2, YEL, wear=0.3)
    C.rect(-29.4, -22.2, -21.4, -12.6, (172, 52, 40), alpha=0.0)
    for y0 in (-21.3, -12.75):
        C.line((-29.3, y0), (-22.3, y0), 0.2, (190, 60, 44), wear=0.3)
    for x0 in (-29.3, -22.3):
        C.line((x0, -21.3), (x0, -12.75), 0.2, (190, 60, 44), wear=0.3)
    # oil / tyre stains on the stands and hangar mouth
    for (x, y, r) in [(px, py + 0.5, 1.5) for px, py in PADS] + [(HCX, HY0 - 2.0, 3.0), (HCX, 0.0, 3.0)]:
        C.paint((x - r, x + r, y - r, y + r), lambda X, Y, x=x, y=y, r=r: np.hypot((X - x) * 1.3, Y - y) - r,
                (96, 92, 86), alpha=0.3, wear=0.7)


# ---------------------------------------------------------------------- build
def build():
    kit = K.Kit("airfield", "AF", atlas=4096, ao_res=2048, ao_dist=5.0)
    paint_plan(kit)
    B = kit.part("Building")
    P = kit.part("Props")

    # slab
    B.frustum("slab", -30.0, 30.0, -22.0, 22.0, 0.0, SL - 0.004, 0.08, top=False)
    B.quad("plan", [(-29.92, -21.92, SL), (29.92, -21.92, SL), (29.92, 21.92, SL), (-29.92, 21.92, SL)])

    # ================================================================ HANGAR (arched, olive, door to the front)
    outer = arc_pts(0.0); inner = arc_pts(0.28)[::-1]
    shell = [(HX0, SL), (HX0 + 0.0, WALL)] + outer[1:-1] + [(HX1, WALL), (HX1, SL), (HX1 - 0.28, SL), (HX1 - 0.28, WALL)] + \
        inner[1:-1] + [(HX0 + 0.28, WALL), (HX0 + 0.28, SL)]
    B.prism("roof", shell, "y", HY0, HY1, arc_uv=True)
    # concrete plinth walls along the sides
    for x0, x1 in ((HX0 - 0.15, HX0 + 0.05), (HX1 - 0.05, HX1 + 0.15)):
        B.span("conc", x0, x1, HY0, HY1, SL, SL + 1.0, bev=True)
    # external arch ribs
    for y in np.linspace(HY0 + 0.15, HY1 - 0.15, 5):
        ro = arc_pts(-0.12); ri = arc_pts(0.02)[::-1]
        B.prism("olive", [(HX0 - 0.12, SL + 1.0)] + ro + [(HX1 + 0.12, SL + 1.0), (HX1 - 0.02, SL + 1.0)] + ri + [(HX0 + 0.02, SL + 1.0)],
                "y", y - 0.12, y + 0.12)
    # rear gable (closed)
    B.prism("clad", [(HX0 + 0.1, SL)] + [(HCX + (x - HCX) * 0.995, z - 0.02) for x, z in outer] + [(HX1 - 0.1, SL)], "y", HY1 - 0.35, HY1 - 0.1)
    # front gable: piers + header above the door opening
    DX0, DX1, DZ = HX0 + 1.4, HX1 - 1.4, 6.0
    FY0, FY1 = HY0 - 0.3, HY0 + 0.1
    for xa, xb in ((HX0, DX0), (DX1, HX1)):
        pts = [(xa, SL), (xb, SL)]
        topx = [x for x, _ in outer if xa - 1e-6 <= x <= xb + 1e-6]
        top = [(x, z) for x, z in outer if xa - 1e-6 <= x <= xb + 1e-6]
        xe = xb if xa == HX0 else xa
        pts = [(xa, SL), (xb, SL), (xb, arc_z(xb - HCX) if xb != HX1 else WALL)] if xa == HX0 else \
              [(xa, SL), (xb, SL), (xb, WALL)]
        if xa == HX0:
            pts = [(xa, SL), (xb, SL), (xb, arc_z(xb - HCX))] + [p for p in top[::-1] if p[0] < xb - 1e-3] + [(xa, WALL)]
        else:
            pts = [(xa, SL), (xb, SL), (xb, WALL)] + [p for p in top[::-1] if p[0] > xa + 1e-3] + [(xa, arc_z(xa - HCX))]
        B.prism("clad", pts, "y", FY0, FY1)
    hdr = [(DX0, DZ), (DX1, DZ), (DX1, arc_z(DX1 - HCX))] + [p for p in outer[::-1] if DX0 < p[0] < DX1 and p[1] > DZ] + [(DX0, arc_z(DX0 - HCX))]
    B.prism("clad", hdr, "y", FY0, FY1)
    # header truss: box girder + X bracing, team band
    B.span("metal", DX0, DX1, FY0 - 0.25, FY0, DZ - 0.05, DZ + 0.35)
    B.span("team", DX0 + 0.2, DX1 - 0.2, FY0 - 0.27, FY0 - 0.25, DZ + 0.02, DZ + 0.28, bottom=True)
    nb = 6
    for k in range(nb):
        xa = DX0 + (DX1 - DX0) * k / nb; xb = DX0 + (DX1 - DX0) * (k + 1) / nb
        za = min(arc_z(xa - HCX), arc_z(xb - HCX)) - 0.25
        if za - DZ < 0.6:
            continue
        zt = DZ + 0.35 + min(1.3, za - DZ - 0.4)
        B.strut("metal", (xa, FY0 - 0.12, DZ + 0.35), (xb, FY0 - 0.12, zt), 0.05, seg=4)
        B.strut("metal", (xb, FY0 - 0.12, DZ + 0.35), (xa, FY0 - 0.12, zt), 0.05, seg=4)
        B.strut("metal", (xa, FY0 - 0.12, zt), (xb, FY0 - 0.12, zt), 0.05, seg=4)
    # retracted door leaves (olive slats) stacked in front of the piers + top track
    for xa, xb in ((HX0 - 0.35, DX0 + 0.55), (DX1 - 0.55, HX1 + 0.35)):
        for j in range(2):
            y0 = FY0 - 0.35 - j * 0.22
            B.span("odoor", xa + j * 0.25, xb - j * 0.25, y0 - 0.16, y0, SL, DZ - 0.15)
    B.span("metal", HX0 - 0.4, HX1 + 0.4, FY0 - 0.85, FY0 - 0.3, DZ - 0.15, DZ - 0.02)
    # hangar interior: dark rear lining, side cabinets, tow tug
    B.span("dark", DX0, DX1, HY1 - 0.4, HY1 - 0.35, SL, 5.0)
    K.cabinet(B, HX0 + 1.0, 3.5, SL, 0.8, 2.0, 1.8, face="+x")
    K.cabinet(B, HX1 - 1.0, 4.5, SL, 0.8, 1.6, 1.6, face="-x")
    B.span("yellow", HCX - 0.8, HCX + 0.8, 2.0, 3.6, SL, SL + 0.9, bev=True)
    # skylights (two rows on the arch) + ridge vents
    for side in (-1, 1):
        dx = side * 3.6
        z = arc_z(dx)
        ang = math.atan2(dx, ARC_ZC - z + ARC_R * 0) if False else math.asin(dx / ARC_R)
        for yc in (-4.5, -0.5, 3.5):
            c = V((HCX + dx * 1.0, yc, z + 0.04))
            B.box("metal", c, (2.0, 3.0, 0.1), (0, ang, 0))
            B.box("glass", c + V((math.sin(ang), 0, math.cos(ang))) * 0.06, (1.8, 2.8, 0.04), (0, ang, 0))
    for yc in (-3.0, 2.5):
        B.span("hvac", HCX - 0.6, HCX + 0.6, yc - 0.6, yc + 0.6, RIDGE - 0.05, RIDGE + 0.55, bev=True)
        B.span("metal", HCX - 0.75, HCX + 0.75, yc - 0.75, yc + 0.75, RIDGE + 0.55, RIDGE + 0.65, bottom=True)
    # status lights on the door piers + ridge beacon
    kit.light("Light_Status0", [("box", (DX0 - 0.45, FY0 - 0.05, 4.2), (0.3, 0.1, 0.3))])
    kit.light("Light_Status1", [("box", (DX1 + 0.45, FY0 - 0.05, 4.2), (0.3, 0.1, 0.3))])
    B.cyl("metal", (HCX, 5.4, RIDGE - 0.05 + 0.35), 0.1, 0.7, seg=8)
    kit.light("Light_Beacon1", [("cyl", (HCX, 5.4, RIDGE + 0.42), 0.15, 0.26, (0, 0, 0), 10)])
    # side lean-to (workshop) on the hangar's right wall, rear half
    B.span("clad", HX1 + 0.1, HX1 + 3.2, 0.5, 6.5, SL, 3.4, bev=True)
    B.prism("roof", [(HX1 + 0.05, 3.6), (HX1 + 3.4, 3.2), (HX1 + 3.4, 3.35), (HX1 + 0.05, 3.75)], "y", 0.3, 6.7)
    B.span("odoor", HX1 + 3.2, HX1 + 3.26, 2.0, 5.0, SL, 2.8)

    # ================================================================ CONTROL TOWER (octagonal shaft + glazed cab)
    tx, ty = TWR
    C8 = math.cos(PI / 8)

    def octo(ap, z, rot=PI / 8):
        r = ap / C8
        return [(tx + r * math.cos(rot + k * PI / 4), ty + r * math.sin(rot + k * PI / 4), z) for k in range(8)]
    SH, CB0, CB1, CR = 10.6, 10.9, 12.7, 13.1
    B.loft("conc", [octo(2.1, SL), octo(2.1, SL + 0.6), octo(1.8, SL + 0.8), octo(1.8, SH)], cap1=False)
    B.loft("olive", [octo(1.85, SH), octo(2.25, SH + 0.15), octo(2.25, CB0), octo(2.3, CB0)], cap1=False)
    B.loft("cab", [octo(2.3, CB0), octo(2.6, CB1)], cap1=False)
    B.loft("olive", [octo(2.62, CB1), octo(2.68, CB1 + 0.05), octo(2.68, CR), octo(2.3, CR)], cap1=False)
    B.loft("slab", [octo(2.3, CR)], cap1=True)
    B.loft("team", [octo(2.7, CB1 + 0.12), octo(2.7, CB1 + 0.26)], cap1=False)
    for x, y, _ in octo(1.0, 0):
        s0, s1 = 2.3, 2.6
        B.strut("olive", (tx + (x - tx) * s0, ty + (y - ty) * s0, CB0), (tx + (x - tx) * s1, ty + (y - ty) * s1, CB1), 0.05, seg=4)
    # gallery deck + railing below the cab
    B.loft("grate", [octo(2.25, SH + 0.15), octo(2.9, SH + 0.15), octo(2.9, SH + 0.25), octo(2.25, SH + 0.25)], cap1=False)
    K.railing(B, [(x, y) for x, y, _ in octo(2.85, 0)], SH + 0.25, h=0.9, post=2.4, closed=True)
    # shaft details: slit windows, door, vertical conduit
    for k in range(4):
        th = PI / 2 * k
        for z in (3.5, 6.0, 8.5):
            B.box("dark", (tx + 1.8 * math.cos(th), ty + 1.8 * math.sin(th), z), (0.08, 0.35, 1.0), (0, 0, th))
    B.strut("metal", (tx + 1.75, ty + 0.9, SL), (tx + 1.75, ty + 0.9, SH), 0.06, seg=6)
    # roof: antenna farm, small radome, beacon mast
    K.railing(B, [(x, y) for x, y, _ in octo(2.55, 0)], CR, h=0.6, post=3.0, closed=True)
    B.lathe("white", [(0.55, 0), (0.55, 0.3), (0.42, 0.65), (0.0, 0.8)], Matrix.Translation((tx + 0.9, ty - 0.6, CR + 0.4)), seg=14)
    B.cyl("metal", (tx + 0.9, ty - 0.6, CR + 0.2), 0.1, 0.4, seg=8)
    for (ax, ay, h) in ((-0.9, 0.6, 3.4), (-0.3, 1.2, 2.4), (0.8, 1.0, 2.0), (-1.2, -0.6, 1.6)):
        B.cyl("metal", (tx + ax, ty + ay, CR + h / 2), 0.03, h, seg=6)
    B.box("hvac", (tx - 0.2, ty - 0.2, CR + 0.3), (0.9, 0.7, 0.6), bev=True)
    kit.light("Light_Beacon0", [("cyl", (tx - 0.9, ty + 0.6, CR + 3.5), 0.13, 0.24, (0, 0, 0), 10)])

    # ops annex at the tower foot (front)
    AX0, AX1, AY0, AY1 = -29.4, -21.9, -7.5, 0.6
    B.span("conc", AX0, AX1, AY0, AY1, SL, 3.8, bev=True)
    B.span("conc", AX0 - 0.08, AX1 + 0.08, AY0 - 0.08, AY1 + 0.08, 3.8, 4.15, bev=True)
    B.span("slab", AX0 + 0.12, AX1 - 0.12, AY0 + 0.12, AY1 - 0.12, 3.85, 3.95)
    B.span("odoor", -27.4, -24.8, AY0 - 0.06, AY0, SL, 3.0)                                 # roll-up door
    B.span("metal", -27.6, -24.6, AY0 - 0.3, AY0, 3.0, 3.3)
    B.span("metal", -23.6, -22.6, AY0 - 0.06, AY0, SL, 2.4)                                 # personnel door
    B.span("glass", AX1, AX1 + 0.05, -6.0, -3.0, 1.6, 2.8)
    for (x, y) in ((-27.6, -4.8), (-24.0, -2.0)):
        B.span("hvac", x - 0.7, x + 0.7, y - 0.55, y + 0.55, 3.95, 4.8, bev=True)
        B.cyl("dark", (x + 0.2, y, 4.81), 0.38, 0.03, seg=14)
    kit.light("Light_Status2", [("box", (-23.1, AY0 - 0.06, 2.7), (0.26, 0.08, 0.2))])
    for y in np.arange(AY0 + 1.0, AY1 - 0.5, 2.4):
        B.span("louvre", AX0 - 0.05, AX0, y - 0.6, y + 0.6, 2.0, 2.8)

    # ================================================================ PROPS
    # fuel tank on saddles + crates/containers in the front-left yard
    B_ = P
    for x in (-28.0, -24.0):
        P.span("conc", x - 0.25, x + 0.25, -18.3, -15.7, SL, SL + 0.9, bev=True)
    P.cyl("steel", (-26.0, -17.0, SL + 2.0), 1.25, 6.4, (0, PI / 2, 0), seg=18)
    for s in (-1, 1):
        P.lathe("steel", [(1.25, 0), (1.0, 0.35), (0.6, 0.55), (0.0, 0.62)],
                Matrix.Translation((-26.0 + s * 3.2, -17.0, SL + 2.0)) @ Euler((0, s * PI / 2, 0)).to_matrix().to_4x4(), seg=18)
    for x in (-27.5, -26.0, -24.5):
        P.cyl("olive", (x, -17.0, SL + 2.0), 1.28, 0.12, (0, PI / 2, 0), seg=18)
    P.cyl("metal", (-25.0, -17.0, SL + 3.35), 0.35, 0.2, seg=10)
    K.ladder(P, (-22.6, -17.0, SL), (0, 1, 0), 9, 3.2, (1, 0, 0), m="yellow")
    P.strut("metal", (-22.9, -16.0, SL + 0.4), (-21.5, -14.5, SL + 0.4), 0.08)
    K.cabinet(P, -21.6, -14.0, SL, 0.9, 0.7, 1.5)                                        # fuel pump cabinet
    P.span("cont", -29.4, -27.0, -11.6, -8.6, SL, SL + 2.4, bev=True)
    P.span("olive", -29.45, -26.95, -11.65, -8.55, SL + 2.4, SL + 2.45, bottom=True)
    K.ammo_pallet(P, -25.6, -10.4, SL, 2); K.ammo_pallet(P, -24.2, -10.4, SL, 1)
    P.span("tarp", -23.2, -21.9, -11.0, -9.6, SL, SL + 1.3, bev=True)
    for k, (x, y) in enumerate(((-29.0, -20.5), (-28.4, -20.8), (-29.1, -19.8))):
        K.drum(P, x, y, SL, "olive" if k else "red")
    # GSE: tow tractor + bomb-loader cart near the stands (outside the circles)
    P.span("yellow", 26.4, 28.6, -6.4, -5.2, SL + 0.35, SL + 1.1, bev=True)
    P.span("dark", 26.6, 27.4, -6.3, -5.3, SL + 1.1, SL + 1.6, bev=True)
    for x in (26.8, 28.2):
        for y in (-6.45, -5.15):
            P.cyl("rubber", (x, y, SL + 0.32), 0.3, 0.22, (PI / 2, 0, 0), seg=10, bottom=True)
    P.span("olive", 9.8, 13.6, -7.5, -6.5, SL + 0.4, SL + 0.65, bev=True)
    for x in (10.2, 13.2):
        for y in (-7.55, -6.45):
            P.cyl("rubber", (x, y, SL + 0.22), 0.2, 0.14, (PI / 2, 0, 0), seg=8, bottom=True)
    K.ammo_pallet(P, 11.0, -7.0, SL + 0.65, 1); K.ammo_pallet(P, 12.5, -7.0, SL + 0.65, 1)
    # fire extinguisher carts by the stands
    for (x, y) in ((-1.0, -7.0), (25.5, 6.0)):
        P.cyl("red", (x, y, SL + 0.6), 0.22, 1.0, seg=10)
        P.span("metal", x - 0.3, x + 0.3, y - 0.3, y + 0.3, SL, SL + 0.12)
    # windsock (team colour)
    WX, WY = 27.5, 8.2
    P.span("conc", WX - 0.4, WX + 0.4, WY - 0.4, WY + 0.4, SL, SL + 0.25, bev=True)
    P.cyl("white", (WX, WY, SL + 3.2), 0.07, 6.0, seg=8)
    P.lathe("team", [(0.45, 0), (0.42, 0.6), (0.36, 1.2), (0.3, 1.9), (0.24, 2.6), (0.0, 2.62)],
            Matrix.Translation((WX, WY, SL + 6.0)) @ Euler((0, math.radians(-82), math.radians(-25))).to_matrix().to_4x4(), seg=12)
    P.cyl("metal", (WX, WY, SL + 6.0), 0.47, 0.06, (0, math.radians(-82), math.radians(-25)), seg=12, bottom=True)
    # flood light poles
    for k, (x, y, aim) in enumerate(((-2.2, -21.2, (8, -8)), (29.2, -21.2, (14, -8)), (29.2, 5.6, (14, -6)),
                                      (-20.5, -21.2, (-13, -12)))):
        K.flood_pole(kit, P, f"Light_Flood{k}", x, y, SL, h=7.5, aim=aim)
    # runway edge lights: housings in Props, lenses as Light_Runway objects (pairs from start to end)
    xs = [-26.25 + 7.5 * k for k in range(8)]
    n = 0
    for x in xs:
        for y in (RY0 + 0.1, RY1 - 0.1):
            P.cyl("yellow", (x, y, SL + 0.1), 0.2, 0.2, seg=10)
            P.cyl("metal", (x, y, SL + 0.25), 0.07, 0.1, seg=6)
            kit.light(f"Light_Runway{n}", [("cyl", (x, y, SL + 0.38), 0.14, 0.18, (0, 0, 0), 8)])
            n += 1
    # blue taxiway edge markers (albedo only)
    for y in np.arange(7.5, RY0 - 0.5, 1.6):
        for x in (TWX0 - 0.25, TWX1 + 0.25):
            P.cyl("blue", (x, y, SL + 0.2), 0.11, 0.4, seg=8)
    for x in np.arange(-2.0, 29.0, 4.0):
        P.cyl("blue", (x, 6.0, SL + 0.2), 0.11, 0.4, seg=8)

    B.build(); P.build()
    for i, (px, py) in enumerate(PADS):
        kit.empty(f"Pad{i}", (px, py, SL))
    kit.empty("RunwayStart", (-28.0, RCY, SL))
    kit.empty("RunwayEnd", (28.0, RCY, SL))
    return kit.finish(A.out, "airfield.glb", ground_size=140)


if not A.skip_build:
    build()
if A.previews:
    K.previews(GLB, A.previews, "m1_airfield", K.std_shots(60.0, 13.0, tz=2.0, dmul=1.0, top_ortho=64), only=A.only, concept=A.concept)
