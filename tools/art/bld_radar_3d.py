"""Steel Accord - M1 structure: Radar / Communications Station.

Run:  python3 -I bld_radar_3d.py <out_dir> [--previews <dir>] [--concept <png>] [--only rts,front] [--previews-only]
Out:  <out_dir>/radar.glb
  Building  - pad, fence posts/footings + chain-link, ops building, pedestal, lattice tower, mast, cabinets
  RadarDish - turntable + yoke + tilted parabolic dish + feed; origin ON the vertical rotation axis (spin about Y)
  Light_Status0..1, Light_Beacon0..1, Light_Flood0..1 (own emissive materials SA_Light_<name>)
Footprint 12 x 12 m, origin = pad centre at ground, front (gate, door) = Blender -Y = Godot +Z.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K
import numpy as np
from mathutils import Matrix, Euler, Vector as V

A = K.Args(sys.argv[1:])
GLB = os.path.join(A.out, "radar.glb")
PI = math.pi

SL = 0.2                         # pad top
PX, PY = 2.1, 2.0                # pedestal / dish rotation axis (Blender XY)
PED_TOP = SL + 3.3               # top of the fixed pedestal (turntable sits on it)
EL_Z = PED_TOP + 1.55            # elevation axis height
BX0, BX1, BY0, BY1 = -4.7, 0.3, -4.3, -0.7      # ops building
BH = SL + 2.75                   # building wall top


def paint_plan(kit):
    C = kit.set_plan(-6, 6, -6, 6, 64)
    C.fill((-6, 6, -6, 6), K.ground_concrete((150, 148, 140), joint=2.0, seed=410, stains=0.08))
    # keep-clear ring around the pedestal, hatched
    C.ring(PX, PY, 1.75, 1.95, (214, 172, 42), wear=0.35)
    for k in range(16):
        a = 2 * PI * k / 16
        C.orect(PX + 2.15 * math.cos(a), PY + 2.15 * math.sin(a), 0.45, 0.12, a + 0.6, (214, 172, 42), wear=0.4)
    # walkway from gate to door, edge lines
    for x in (-3.15, -1.85):
        C.line((x, -5.6), (x, -4.45), 0.07, (214, 172, 42), wear=0.4)
    # oil / weather stains near the cabinets
    for (x, y, r) in ((4.2, -1.3, 0.9), (-4.3, 1.2, 0.7), (1.4, -3.3, 0.6)):
        C.paint((x - r, x + r, y - r, y + r), lambda X, Y, x=x, y=y, r=r: np.hypot(X - x, Y - y) - r, (90, 86, 78), alpha=0.35, wear=0.6)
    # stencilled number by the gate
    C.digit("7", 0.9, -5.0, 0.7, (214, 172, 42), wear=0.3)


def build():
    kit = K.Kit("radar", "RD", atlas=2048, ao_res=1024, ao_dist=3.0)
    paint_plan(kit)
    B = kit.part("Building")
    D = kit.part("RadarDish", pivot=(PX, PY, PED_TOP))

    # ---------------------------------------------------------------- pad
    B.frustum("gconc", -6.0, 6.0, -6.0, 6.0, 0.0, SL - 0.005, 0.06, top=False)
    B.quad("plan", [(-5.94, -5.94, SL), (5.94, -5.94, SL), (5.94, 5.94, SL), (-5.94, 5.94, SL)])

    # ---------------------------------------------------------------- fence with concrete footings
    FX = 5.65; FH = 2.1
    corners = [(-FX, -FX), (FX, -FX), (FX, FX), (-FX, FX)]
    runs = [((-FX, FX), (FX, FX)), ((FX, FX), (FX, -FX)), ((-FX, -FX), (-FX, FX)),
            ((FX, -FX), (-0.9, -FX)), ((-4.1, -FX), (-FX, -FX))]          # front gap = gate (x -4.1 .. -0.9)
    for (x0, y0), (x1, y1) in runs:
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / 2.4)))
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            corner = any(abs(x - cx) < 0.01 and abs(y - cy) < 0.01 for cx, cy in corners) or k in (0, n)
            s = 0.26 if corner else 0.18
            B.frustum("hazard" if corner else "gconc", x - s, x + s, y - s, y + s, SL, SL + 0.32, 0.05, bev=False)
            B.cyl("metal", (x, y, SL + 0.32 + FH / 2), 0.05, FH, seg=6)
            B.cyl("metal", (x, y, SL + 0.32 + FH + 0.02), 0.065, 0.05, seg=6, bottom=True)
        B.strut("metal", (x0, y0, SL + 0.32 + FH - 0.05), (x1, y1, SL + 0.32 + FH - 0.05), 0.025, seg=4)
        B.strut("metal", (x0, y0, SL + 0.45), (x1, y1, SL + 0.45), 0.02, seg=4)
        kit.fence((x0, y0), (x1, y1), SL + 0.4, SL + 0.32 + FH - 0.05)
    # gate leaves (open, swung inwards) with hazard band
    for gx, sgn in ((-4.1, 1), (-0.9, -1)):
        ang = math.radians(70) * sgn
        ex, ey = gx + sgn * 1.5 * math.cos(math.radians(70)), -FX + 1.5 * math.sin(math.radians(70))
        B.strut("metal", (gx, -FX, SL + 0.4), (ex, ey, SL + 0.4), 0.025, seg=4)
        B.strut("metal", (gx, -FX, SL + 2.0), (ex, ey, SL + 2.0), 0.025, seg=4)
        B.strut("metal", (ex, ey, SL + 0.4), (ex, ey, SL + 2.0), 0.025, seg=4)
        kit.fence((gx, -FX), (ex, ey), SL + 0.4, SL + 2.0)

    # ---------------------------------------------------------------- ops building (tan concrete, flat roof)
    B.span("conc", BX0, BX1, BY0, BY1, SL, BH, bev=True)
    B.span("conc", BX0 - 0.08, BX1 + 0.08, BY0 - 0.08, BY1 + 0.08, BH, BH + 0.35, bev=True)       # parapet band
    B.span("slab", BX0 + 0.12, BX1 - 0.12, BY0 + 0.12, BY1 - 0.12, BH + 0.05, BH + 0.2)            # roof deck
    B.span("team", BX0 - 0.09, BX1 + 0.09, BY0 - 0.1, BY0 - 0.08, BH + 0.08, BH + 0.24, bottom=True)
    B.span("conc", BX0 - 0.1, BX1 + 0.1, BY0 - 0.1, BY1 + 0.1, SL, SL + 0.35, bev=True)             # plinth
    # door + frame, canopy, steps with yellow rails
    DX = -2.5
    B.span("metal", DX - 0.55, DX + 0.55, BY0 - 0.06, BY0, SL + 0.55, SL + 2.45)
    B.span("odoor", DX - 0.45, DX + 0.45, BY0 - 0.08, BY0 - 0.06, SL + 0.6, SL + 2.38)
    B.span("metal", DX - 0.8, DX + 0.8, BY0 - 0.9, BY0, SL + 2.55, SL + 2.65, bottom=True)
    B.span("dark", DX - 0.12, DX + 0.12, BY0 - 0.12, BY0 - 0.06, SL + 2.66, SL + 2.78)               # wall lamp housing
    for k in range(3):
        B.span("gconc", DX - 0.7, DX + 0.7, BY0 - 0.3 * (k + 1) - 0.1, BY0, SL, SL + 0.55 - 0.18 * k, bev=True)
    for x in (DX - 0.68, DX + 0.68):
        B.strut("yellow", (x, BY0 - 1.0, SL + 0.95), (x, BY0 - 0.1, SL + 1.45), 0.025, seg=5)
        B.strut("yellow", (x, BY0 - 1.0, SL), (x, BY0 - 1.0, SL + 0.95), 0.025, seg=5)
        B.strut("yellow", (x, BY0 - 0.1, SL + 0.5), (x, BY0 - 0.1, SL + 1.45), 0.025, seg=5)
    kit.light("Light_Status0", [("box", (DX + 0.75, BY0 - 0.05, SL + 2.1), (0.16, 0.08, 0.16))])
    # windows / louvres
    for x in (-4.0, -0.6):
        B.span("metal", x - 0.45, x + 0.45, BY0 - 0.06, BY0, SL + 1.35, SL + 2.05)
        B.span("louvre", x - 0.38, x + 0.38, BY0 - 0.08, BY0 - 0.06, SL + 1.42, SL + 1.98)
    for y in (-3.2, -1.7):
        B.span("metal", BX0 - 0.06, BX0, y - 0.45, y + 0.45, SL + 1.4, SL + 2.0)
        B.span("glass", BX0 - 0.08, BX0 - 0.06, y - 0.38, y + 0.38, SL + 1.47, SL + 1.93)
    B.span("louvre", BX1, BX1 + 0.08, -3.0, -2.2, SL + 0.6, SL + 1.3)
    # roof HVAC units + hatch + conduit
    for (x, y) in ((-3.6, -2.4), (-1.2, -2.0)):
        B.span("metal", x - 0.62, x + 0.62, y - 0.5, y + 0.5, BH + 0.2, BH + 0.3)
        B.span("hvac", x - 0.55, x + 0.55, y - 0.45, y + 0.45, BH + 0.3, BH + 0.95, bev=True)
        B.cyl("dark", (x + 0.15, y, BH + 0.96), 0.3, 0.03, seg=14)
        B.cyl("metal", (x + 0.15, y, BH + 0.99), 0.08, 0.04, seg=8)
    B.span("hvac", -0.6, 0.0, -1.4, -0.9, BH + 0.2, BH + 0.45, bev=True)
    B.strut("metal", (BX1 - 0.3, -1.2, BH + 0.3), (PX - 1.25, PY - 0.7, SL + 2.0), 0.07, seg=6)     # cable tray to pedestal
    # wall flood (right rear corner of building, aimed at the yard)
    B.span("metal", BX1 - 0.05, BX1 + 0.2, BY1 - 0.35, BY1 - 0.15, BH - 0.4, BH - 0.2)
    B.box("metal", (BX1 + 0.3, BY1 - 0.25, BH - 0.35), (0.3, 0.26, 0.24), (0, math.radians(25), 0), bottom=True)
    kit.light("Light_Flood0", [("box", (BX1 + 0.46, BY1 - 0.25, BH - 0.42), (0.04, 0.22, 0.2), (0, math.radians(25), 0))])

    # ---------------------------------------------------------------- equipment cabinets, generator, cable runs
    K.cabinet(B, 1.3, -3.4, SL, 1.5, 1.0, 1.9)
    K.cabinet(B, 3.0, -3.7, SL, 0.9, 0.7, 1.4)
    K.cabinet(B, -4.3, 0.9, SL, 1.1, 1.2, 1.7, face="+x")
    K.cabinet(B, -0.7, 3.9, SL, 1.4, 0.9, 1.5)
    kit.light("Light_Status1", [("box", (1.75, -3.92, SL + 1.6), (0.14, 0.06, 0.14))])
    # generator skid (right side)
    B.span("metal", 3.7, 5.2, -2.3, -0.3, SL, SL + 0.15)
    B.span("cabinet", 3.8, 5.1, -2.2, -0.4, SL + 0.15, SL + 1.35, bev=True)
    B.span("louvre", 3.78, 3.8, -1.9, -0.7, SL + 0.4, SL + 1.1)
    B.cyl("dark", (4.8, -0.7, SL + 1.65), 0.07, 0.6, seg=8)
    B.span("olive", 3.75, 5.15, -2.25, -0.35, SL + 1.35, SL + 1.42, bottom=True)
    K.drum(B, 5.0, 0.4, SL, "olive"); K.drum(B, 4.4, 0.6, SL, "yellow")
    # ground conduit trays
    B.span("metal", -3.8, 1.0, 0.1, 0.35, SL, SL + 0.12)
    B.span("metal", 1.0, 1.25, -2.8, 0.35, SL, SL + 0.12)
    B.span("grate", -1.4, -0.4, -0.3, 0.05, SL, SL + 0.02)

    # ---------------------------------------------------------------- dish pedestal (fixed part)
    rp = 1.25
    B.lathe("cabinet", [(rp + 0.15, SL), (rp + 0.15, SL + 0.45), (rp, SL + 0.5), (rp, PED_TOP - 0.3),
                        (rp + 0.12, PED_TOP - 0.25), (rp + 0.12, PED_TOP), (0.0, PED_TOP)],
            Matrix.Translation((PX, PY, 0)), seg=20)
    for z in (SL + 1.3, SL + 2.2):                                                      # band rings
        B.cyl("olive", (PX, PY, z), rp + 0.05, 0.12, seg=20, bottom=True)
    B.cyl("team", (PX, PY, SL + 2.8), rp + 0.02, 0.18, seg=20, bottom=True)
    for k in range(8):                                                                  # vertical stiffeners
        a = 2 * PI * (k + 0.5) / 8
        x, y = PX + (rp + 0.04) * math.cos(a), PY + (rp + 0.04) * math.sin(a)
        B.box("olive", (x, y, (SL + 0.5 + PED_TOP - 0.3) / 2), (0.1, 0.08, PED_TOP - 0.3 - SL - 0.5), (0, 0, a))
    # access door on the pedestal (front)
    B.box("odoor", (PX, PY - rp - 0.03, SL + 1.25), (0.7, 0.06, 1.6))
    # catwalk ring + railing at the pedestal top
    CR = rp + 0.75
    B.lathe("grate", [(rp, PED_TOP - 0.4), (CR, PED_TOP - 0.4), (CR, PED_TOP - 0.32), (rp, PED_TOP - 0.32)],
            Matrix.Translation((PX, PY, 0)), seg=20, closed_prof=True)
    rail = [(PX + CR * math.cos(2 * PI * k / 14), PY + CR * math.sin(2 * PI * k / 14)) for k in range(14)]
    K.railing(B, rail, PED_TOP - 0.32, h=0.95, post=3.0, closed=True)
    for k in range(4):                                                                  # catwalk brackets
        a = 2 * PI * (k + 0.5) / 4
        B.strut("metal", (PX + rp * math.cos(a), PY + rp * math.sin(a), PED_TOP - 1.2),
                (PX + (CR - 0.1) * math.cos(a), PY + (CR - 0.1) * math.sin(a), PED_TOP - 0.42), 0.04, seg=4)
    # ladder up the pedestal (right side)
    K.ladder(B, (PX + rp + 0.02, PY - 0.2, SL), (0, 1, 0), 13, PED_TOP - 0.3 - SL, (1, 0, 0))

    # ---------------------------------------------------------------- lattice tower (left rear) with panel antennas
    TX, TY, TH = -4.2, 4.0, 10.5
    leg = [(TX + 0.55 * math.cos(a), TY + 0.55 * math.sin(a)) for a in (PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3)]
    for (x, y) in leg:
        B.frustum("gconc", x - 0.2, x + 0.2, y - 0.2, y + 0.2, SL, SL + 0.3, 0.04)
    lev = [SL + 0.3 + i * (TH - 0.3) / 9 for i in range(10)]
    for i, z in enumerate(lev):
        s = 1.0 - 0.35 * i / 9
        pts = [(TX + (x - TX) * s, TY + (y - TY) * s, z) for x, y in leg]
        for j in range(3):
            B.strut("steel", pts[j], pts[(j + 1) % 3], 0.022, seg=4)
        if i < 9:
            s2 = 1.0 - 0.35 * (i + 1) / 9
            nxt = [(TX + (x - TX) * s2, TY + (y - TY) * s2, lev[i + 1]) for x, y in leg]
            for j in range(3):
                B.strut("steel", pts[j], nxt[j], 0.04, seg=5)
                B.strut("steel", pts[j], nxt[(j + 1) % 3], 0.016, seg=4)
    for k, a in enumerate((PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3)):       # white panel antennas
        x, y = TX + 0.5 * math.cos(a), TY + 0.5 * math.sin(a)
        B.box("white", (x, y, SL + TH - 0.9), (0.3, 0.12, 1.5), (0, 0, a + PI / 2), bev=True)
        B.strut("metal", (TX, TY, SL + TH - 0.5), (x, y, SL + TH - 0.5), 0.02, seg=4)
    B.box("white", (TX + 0.55, TY - 0.3, SL + TH - 3.0), (0.12, 0.5, 0.5), bev=True)                  # microwave drum
    B.cyl("white", (TX + 0.62, TY - 0.3, SL + TH - 3.0), 0.3, 0.12, (0, PI / 2, 0), seg=12)
    B.cyl("metal", (TX, TY, SL + TH + 0.8), 0.035, 1.6, seg=6)
    B.cyl("metal", (TX, TY, SL + TH + 1.62), 0.08, 0.06, seg=8, bottom=True)
    kit.light("Light_Beacon0", [("cyl", (TX, TY, SL + TH + 1.75), 0.09, 0.2, (0, 0, 0), 8)])

    # ---------------------------------------------------------------- whip mast + small flood pole (right)
    MX, MY = 4.7, 4.6
    B.frustum("gconc", MX - 0.3, MX + 0.3, MY - 0.3, MY + 0.3, SL, SL + 0.3, 0.05)
    B.cyl("metal", (MX, MY, SL + 0.3 + 4.0), 0.09, 8.0, seg=8, r2=0.05)
    for z in (SL + 3.0, SL + 5.5):
        B.cyl("white", (MX, MY - 0.12, z), 0.25, 0.08, (PI / 2, 0, 0), seg=12)
        B.strut("metal", (MX, MY, z), (MX, MY - 0.1, z), 0.03, seg=4)
    B.strut("metal", (MX, MY, SL + 4.2), (MX + 0.5, MY - 0.4, SL + 4.6), 0.02, seg=4)
    B.cyl("metal", (MX, MY, SL + 8.35), 0.06, 0.05, seg=8, bottom=True)
    kit.light("Light_Beacon1", [("cyl", (MX, MY, SL + 8.47), 0.08, 0.18, (0, 0, 0), 8)])
    for g in range(3):                                                                 # guy wires
        a = 2 * PI * g / 3 + 0.4
        gx, gy = MX + 1.0 * math.cos(a), MY + 1.0 * math.sin(a)
        if abs(gx) < 5.6 and abs(gy) < 5.6:
            B.strut("steel", (MX, MY, SL + 6.0), (gx, gy, SL + 0.05), 0.008, seg=3)
    K.flood_pole(kit, B, "Light_Flood1", 4.9, -4.9, SL, h=5.0, aim=(0, 0), heads=1)

    # ---------------------------------------------------------------- RADAR DISH (separate rotating object)
    # turntable + team band + yoke arms
    D.cyl("cabinet", (PX, PY, PED_TOP + 0.22), 1.05, 0.44, seg=20)
    D.cyl("olive", (PX, PY, PED_TOP + 0.47), 0.95, 0.06, seg=20, bottom=True)
    D.cyl("team", (PX, PY, PED_TOP + 0.22), 1.07, 0.12, seg=20, bottom=True)
    for s in (-1, 1):                                                                   # yoke arms (box towers)
        D.prism("cabinet", [(PY - 0.5, PED_TOP + 0.44), (PY + 0.5, PED_TOP + 0.44), (PY + 0.3, EL_Z + 0.35), (PY - 0.3, EL_Z + 0.35)],
                "x", PX + s * 1.05 - 0.17, PX + s * 1.05 + 0.17)
        D.cyl("metal", (PX + s * 1.25, PY, EL_Z), 0.3, 0.25, (0, PI / 2, 0), seg=12)          # trunnion bearings
        D.cyl("dark", (PX + s * 1.39, PY, EL_Z), 0.18, 0.05, (0, PI / 2, 0), seg=10)
    D.span("cabinet", PX - 0.55, PX + 0.55, PY - 0.2, PY + 0.75, PED_TOP + 0.44, PED_TOP + 1.05, bev=True)   # drive housing
    D.cyl("olive", (PX, PY, EL_Z), 0.32, 2.2, (0, PI / 2, 0), seg=12)                   # elevation shaft
    # dish: axis tilted 30 deg above horizontal toward the front (-Y)
    EL = math.radians(30)
    Rm = Matrix.Translation((PX, PY, EL_Z)) @ Euler((PI / 2 - EL, 0, 0)).to_matrix().to_4x4()
    R, f, off = 2.85, 1.55, 0.45                        # radius, focal length, vertex offset in front of the axis
    zf = lambda r: off + r * r / (4 * f)
    rs = [0.0, 0.35, 0.8, 1.3, 1.85, 2.4, R]
    prof = [(r, zf(r)) for r in rs] + [(R + 0.06, zf(R) + 0.02), (R + 0.06, zf(R) - 0.1)] + \
           [(r, zf(r) - 0.12 - 0.06 * (1 - r / R)) for r in rs[::-1][1:-1]] + [(0.0, off - 0.2)]
    D.lathe("dish", prof, Rm, seg=28)
    # front panel seams (concentric + radial ribs)
    for rr in (1.2, 2.1):
        pts = [Rm @ V((rr * math.cos(2 * PI * k / 20), rr * math.sin(2 * PI * k / 20), zf(rr) + 0.025)) for k in range(21)]
        for a_, b_ in zip(pts[:-1], pts[1:]):
            D.strut("lolive", a_, b_, 0.022, seg=4)
    for k in range(12):
        a = 2 * PI * k / 12
        pts = [Rm @ V((r * math.cos(a), r * math.sin(a), zf(r) + 0.025)) for r in (0.35, 1.3, 2.1, R - 0.05)]
        for a_, b_ in zip(pts[:-1], pts[1:]):
            D.strut("lolive", a_, b_, 0.02, seg=4)
    # rim ring
    rim = [Rm @ V(((R + 0.03) * math.cos(2 * PI * k / 28), (R + 0.03) * math.sin(2 * PI * k / 28), zf(R) - 0.03)) for k in range(29)]
    for a_, b_ in zip(rim[:-1], rim[1:]):
        D.strut("olive", a_, b_, 0.05, seg=4)
    # back truss ribs + hub
    for k in range(8):
        a = 2 * PI * (k + 0.5) / 8
        D.strut("olive", Rm @ V((0.3 * math.cos(a), 0.3 * math.sin(a), off - 0.45)),
                Rm @ V((R * 0.92 * math.cos(a), R * 0.92 * math.sin(a), zf(R * 0.92) - 0.16)), 0.05, seg=4)
    D.cyl("cabinet", Rm @ V((0, 0, off - 0.45)), 0.55, 0.6, Euler((PI / 2 - EL, 0, 0)), seg=12)
    # feed: quadripod to the focus + feed horn
    F = Rm @ V((0, 0, off + f * 0.92))
    for k in range(4):
        a = 2 * PI * k / 4 + PI / 4
        D.strut("olive", Rm @ V((R * 0.93 * math.cos(a), R * 0.93 * math.sin(a), zf(R * 0.93) + 0.02)), F, 0.035, seg=4)
    D.cyl("cabinet", F, 0.2, 0.55, Euler((PI / 2 - EL, 0, 0)), seg=10, r2=0.12, bottom=True)
    D.cyl("dark", Rm @ V((0, 0, off + f * 0.92 - 0.29)), 0.13, 0.04, Euler((PI / 2 - EL, 0, 0)), seg=10, bottom=True)

    B.build(); D.build()
    return kit.finish(A.out, "radar.glb", ground_size=40)


if not A.skip_build:
    build()
if A.previews:
    K.previews(GLB, A.previews, "m1_radar", K.std_shots(12.0, 10.0, tz=3.5), only=A.only, concept=A.concept)
