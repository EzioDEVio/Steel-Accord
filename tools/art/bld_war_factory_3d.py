"""Steel Accord - M1 3D structure: US 'War Factory' (code-built + texture-baked in Blender, bpy 5.x). Original design
recreated from the client's concept sheet (individual_views/War_Factory).

Run:  python3 -I bld_war_factory_3d.py <out_dir> [--previews <dir>] [--concept <overhead.png>] [--only rts,front]
      [--previews-only]
Out:  <out_dir>/war_factory.glb  nodes: Building, Props, Light_Status0..2, Light_Beacon0..1, Light_Flood0..1,
      Exit (in front of the west bay), RepairBay (in front of the east bay)
Slab 28 (X) x 22 (Y) m, origin = slab bottom centre, front (vehicle bays) = Blender -Y = Godot +Z.
Layout: olive barrel-vault vehicle hall (standing-seam roof, raised central spine with ventilators, two skylight
strips, tan concrete buttresses) with two large open bays (yellow gantry crane in the west bay), a flat-roofed tan
annex with a lean-to supply canopy on the west side, apron with drain grates.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit as K
from bldkit import PI, V

O = K.cli(sys.argv[1:])
ID = "war_factory"
GLB = os.path.join(O["out"], ID + ".glb")


def build():
    kit = K.Kit(ID, "WF", "WF_WarFactory", atlas=4096)
    B = kit.part("Building"); P = kit.part("Props")
    SL = 0.25
    HX0, HX1, HY0, HY1 = -6.2, 12.2, -4.6, 10.2       # hall walls (front gable at HY0)
    HC = (HX0 + HX1) / 2
    WH, CROWN = 7.4, 11.6                             # eaves height, arch crown (roof surface)
    BAYS = ((-4.8, 2.0), (4.0, 10.8))                 # vehicle bay openings (x ranges)
    BT = 6.4                                          # bay opening top
    half = (HX1 - HX0) / 2 + 0.35                     # roof overhang 0.35 beyond the walls
    s = CROWN - WH
    R = (half ** 2 + s ** 2) / (2 * s); zc = CROWN - R
    a0 = math.asin(half / R)

    def arc(r_off=0.0, n=14, x_half=None):
        """Arch points (x, z) from west to east at radius R + r_off."""
        pts = []
        for i in range(n + 1):
            t = -a0 + 2 * a0 * i / n
            pts.append((HC + (R + r_off) * math.sin(t), zc + (R + r_off) * math.cos(t)))
        return pts

    def roof_z(x):
        return zc + math.sqrt(max(R * R - (x - HC) ** 2, 0.0))

    # ---------------------------------------------------------------- slab + apron
    B.frustum("slab", -14.0, 14.0, -11.0, 11.0, 0.0, SL, 0.12)
    for (bx0, bx1) in BAYS:
        B.span("grate", bx0 + 0.6, bx1 - 0.6, -8.9, -8.1, SL, SL + 0.02)
        for x in (bx0 + 0.15, bx1 - 0.15):
            B.span("yellow", x - 0.06, x + 0.06, -10.8, HY0, SL, SL + 0.008)
    B.span("yellow", BAYS[0][0], BAYS[1][1], -10.85, -10.73, SL, SL + 0.008)

    # ---------------------------------------------------------------- hall walls
    T = 0.4
    B.span("olivewall", HX0, HX0 + T, HY0 + T, HY1 - T, SL, WH)                # side walls (between gables)
    B.span("olivewall", HX1 - T, HX1, HY0 + T, HY1 - T, SL, WH)
    for xa, xb in ((HX0 - 0.08, HX0 + 0.1), (HX1 - 0.1, HX1 + 0.08)):
        B.span("conc", xa, xb, HY0, HY1, SL, SL + 0.9, bev=True)                  # concrete base course
    B.span("conc", HX0, HX1, HY1 - 0.1, HY1 + 0.08, SL, SL + 0.9, bev=True)
    # rear gable (closed)
    rear = [(HX0, SL), (HX1, SL), (HX1, WH)] + [(x, z) for x, z in reversed(arc(-0.3)) if HX0 + 0.3 < x < HX1 - 0.3] + [(HX0, WH)]
    B.prism("olivewall", rear, "y", HY1 - T, HY1)
    # front gable: tympanum above the bays + piers
    tym = [(HX0, BT), (HX1, BT), (HX1, WH)] + [(x, z) for x, z in reversed(arc(-0.3)) if HX0 + 0.3 < x < HX1 - 0.3] + [(HX0, WH)]
    B.prism("olivewall", tym, "y", HY0, HY0 + T)
    piers = [(HX0, BAYS[0][0]), (BAYS[0][1], BAYS[1][0]), (BAYS[1][1], HX1)]
    for x0, x1 in piers:
        B.span("olivewall", x0, x1, HY0, HY0 + T, SL, BT)
        B.span("conc", x0 - 0.06, x1 + 0.06, HY0 - 0.06, HY0 + T, SL, SL + 0.9, bev=True)
    B.span("conc", BAYS[0][0] - 0.2, BAYS[1][1] + 0.2, HY0 - 0.3, HY0 + T, BT, BT + 0.55, bev=True)   # lintel beam
    B.span("team", BAYS[0][0] + 0.3, BAYS[1][1] - 0.3, HY0 - 0.32, HY0 - 0.3, BT + 0.15, BT + 0.4, bottom=True)
    B.span("conc", HC - 0.55, HC + 0.55, HY0 - 0.35, HY0, SL, BT, bev=True)
    # roll-up door housings (doors fully raised) and guide rails
    for bx0, bx1 in BAYS:
        B.cyl("metal", ((bx0 + bx1) / 2, HY0 + 0.2, BT - 0.25), 0.3, bx1 - bx0, rot=(0, PI / 2, 0), seg=10, bottom=True)
        for x in (bx0 + 0.06, bx1 - 0.06):
            B.span("metal", x - 0.06, x + 0.06, HY0 + T - 0.05, HY0 + T + 0.05, SL, BT)
    # arch coping band (tan concrete) on front + rear gables, following the roof edge
    band = arc(0.25) + list(reversed(arc(-0.35)))
    for y0, y1 in ((HY0 - 0.45, HY0 + 0.05), (HY1 - 0.05, HY1 + 0.45)):
        B.prism("conc", band, "y", y0, y1, bev=True, drop=False)

    # ---------------------------------------------------------------- barrel-vault roof (olive standing seam)
    shell = arc(0.0) + list(reversed(arc(-0.25)))
    B.prism("roof", shell, "y", HY0 - 0.35, HY1 + 0.35, drop=False)
    # raised central spine (darker olive) with ventilators
    sp = 1.1
    B.prism("clad", [(HC - sp, roof_z(HC - sp) - 0.05), (HC + sp, roof_z(HC + sp) - 0.05), (HC + sp - 0.1, CROWN + 0.55),
                     (HC - sp + 0.1, CROWN + 0.55)], "y", HY0 - 0.3, HY1 + 0.3, drop=False)
    B.span("metal", HC - sp + 0.05, HC + sp - 0.05, HY0 - 0.3, HY1 + 0.3, CROWN + 0.55, CROWN + 0.62)
    for y in (HY0 + 1.6, HY0 + 5.4, HY0 + 9.2, HY1 - 1.4):
        z = CROWN + 0.62
        B.span("steel", HC - 0.7, HC + 0.7, y - 0.55, y + 0.55, z, z + 0.7, bev=True)
        B.prism("steel", [(y - 0.6, z + 0.7), (y + 0.6, z + 0.7), (y + 0.45, z + 1.05), (y - 0.45, z + 1.05)], "x", HC - 0.75, HC + 0.75)
        B.span("vent", HC - 0.6, HC + 0.6, y - 0.57, y - 0.55, z + 0.15, z + 0.6)
    # skylight strips (two per side of the spine, broken into bays)
    for xs in (HC - 3.0, HC + 3.0):
        slope = -(xs - HC) / max(roof_z(xs) - zc, 1e-3)
        ang = math.atan(slope)
        for (y0, y1) in ((HY0 + 0.6, HY0 + 4.2), (HY0 + 5.0, HY0 + 8.6), (HY0 + 9.4, HY1 - 0.6)):
            B.box("metal", (xs, (y0 + y1) / 2, roof_z(xs) + 0.07), (1.6, y1 - y0 + 0.16, 0.14), (0, ang, 0), bottom=True)
            B.box("glass", (xs, (y0 + y1) / 2, roof_z(xs) + 0.15), (1.36, y1 - y0 - 0.1, 0.04), (0, ang, 0), bottom=True)
    # eave ventilators along both sides
    for xe in (HX0 + 1.4, HX1 - 1.4):
        slope = -(xe - HC) / max(roof_z(xe) - zc, 1e-3)
        ang = math.atan(slope)
        for y in (HY0 + 2.6, HY0 + 7.6, HY1 - 2.0):
            B.box("steel", (xe, y, roof_z(xe) + 0.35), (0.9, 1.0, 0.7), (0, ang, 0), bottom=True)
            B.box("dark", (xe, y - 0.51, roof_z(xe) + 0.35), (0.7, 0.03, 0.4), (0, ang, 0), bottom=True)
    # beacons on spine ends (short masts), flood heads on the gable above the bays
    for i, y in enumerate((HY0 + 0.2, HY1 - 0.2)):
        B.cyl("metal", (HC, y, CROWN + 0.62 + 0.5), 0.05, 1.0, seg=6)
        K.roof_beacon(B, kit, HC, y, CROWN + 1.62, f"Light_Beacon{i}", r=0.13)
    for i, bx in enumerate(BAYS):
        xc = (bx[0] + bx[1]) / 2
        B.span("metal", xc - 0.05, xc + 0.05, HY0 - 0.5, HY0 - 0.3, BT + 1.1, BT + 1.25, bottom=True)
        K.flood_head(B, kit, xc, HY0 - 0.6, BT + 1.15, -PI / 2, f"Light_Flood{i}", tilt=50)
        # status beacon on the lintel at the bay's outer side
        sx = bx[0] + 0.5 if i == 0 else bx[1] - 0.5
        B.span("metal", sx - 0.12, sx + 0.12, HY0 - 0.5, HY0 - 0.3, BT + 0.55, BT + 0.65)
        kit.light(f"Light_Status{i}", (sx, HY0 - 0.4, BT + 0.65), "dome", r=0.15)

    # ---------------------------------------------------------------- buttresses (tan concrete, battered)
    def butt_y(x0, x1, face, out, top, base, cap=0.5):
        B.prism("conc", [(face, SL), (face + out * base, SL), (face + out * cap, top - 0.6), (face + out * cap, top),
                         (face, top)], "x", x0, x1, bev=True)

    def butt_x(y0, y1, face, out, top, base, cap=0.5):
        B.prism("conc", [(face, SL), (face + out * base, SL), (face + out * cap, top - 0.6), (face + out * cap, top),
                         (face, top)], "y", y0, y1, bev=True)
    butt_y(HX0 - 0.3, HX0 + 1.1, HY0, -1, 9.0, 2.6, 0.6)                       # big front corner wedges
    butt_y(HX1 - 1.1, HX1 + 0.3, HY0, -1, 9.0, 2.6, 0.6)
    butt_x(HY0 - 0.3, HY0 + 1.0, HX0, -1, 8.6, 1.6)
    butt_x(HY0 - 0.3, HY0 + 1.0, HX1, 1, 8.6, 1.6)
    for y in (HY0 + 4.8, HY0 + 9.6):
        butt_x(y - 0.4, y + 0.4, HX1, 1, WH + 0.9, 1.4, 0.45)
    butt_x(HY1 - 1.0, HY1 + 0.3, HX1, 1, 8.6, 1.6)
    butt_x(HY1 - 1.0, HY1 + 0.3, HX0, -1, 8.6, 1.6)
    butt_y(HX0 - 0.3, HX0 + 1.0, HY1, 1, 8.6, 1.6)
    butt_y(HX1 - 1.0, HX1 + 0.3, HY1, 1, 8.6, 1.6)
    for x in (HC - 3.5, HC + 3.5):
        butt_y(x - 0.4, x + 0.4, HY1, 1, WH + 0.6, 1.2, 0.45)
    # wall details on the east side: louvres, small door, conduit
    for y in (HY0 + 2.6, HY0 + 7.4):
        K.louvre_panel(B, "x", HX1, y, 5.4, 1, w=2.2, h=0.9)
    B.span("door", HX1, HX1 + 0.04, HY1 - 3.6, HY1 - 2.6, SL, 2.5)
    B.span("conc", HX1, HX1 + 0.6, HY1 - 3.8, HY1 - 2.4, 2.6, 2.75, bottom=True)
    K.louvre_panel(B, "y", HY1, HC, 5.0, 1, w=3.0, h=1.0)

    # ---------------------------------------------------------------- bay interiors (seen through the openings)
    IY1 = HY0 + 9.5
    for bi, (bx0, bx1) in enumerate(BAYS):
        B.room("clad", "floor", "dark", bx0 + 0.02, bx1 - 0.02, HY0 + 0.02, IY1, SL + 0.01, WH - 0.2)
        # crane runway beams along both bay walls
        for x in (bx0 + 0.25, bx1 - 0.25):
            B.span("yellow" if bi == 0 else "metal", x - 0.15, x + 0.15, HY0 + 0.6, IY1 - 0.3, WH - 1.3, WH - 1.0, bottom=True)
        if bi == 0:                                       # yellow gantry crane bridge + hoist
            yb = HY0 + 1.6
            B.span("yellow", bx0 + 0.1, bx1 - 0.1, yb - 0.3, yb + 0.3, WH - 1.75, WH - 1.05, bottom=True)
            B.span("hazard", bx0 + 0.3, bx1 - 0.3, yb - 0.32, yb - 0.3, WH - 1.65, WH - 1.4, bottom=True)
            hx = (bx0 + bx1) / 2 - 0.8
            B.span("yellow", hx - 0.45, hx + 0.45, yb - 0.45, yb + 0.45, WH - 2.25, WH - 1.75, bottom=True)
            B.strut("dark", (hx, yb, WH - 2.25), (hx, yb, 3.2), 0.025, seg=4)
            B.box("yellow", (hx, yb, 3.05), (0.3, 0.2, 0.3), bottom=True)
            # red machinery / tool carts inside (as in the concept)
            for (x, y, sx, sy, h) in ((bx0 + 1.0, HY0 + 4.5, 1.2, 0.8, 1.3), (bx1 - 1.1, HY0 + 5.2, 1.0, 1.4, 1.6),
                                      (bx0 + 1.2, HY0 + 7.0, 1.4, 1.0, 1.1)):
                P.span("red", x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, SL, SL + h, bev=True)
            P.span("metal", bx0 + 0.3, bx0 + 0.9, HY0 + 2.0, HY0 + 6.5, SL, SL + 2.4)                     # racking
        else:
            yb = HY0 + 2.8
            B.span("metal", bx0 + 0.1, bx1 - 0.1, yb - 0.25, yb + 0.25, WH - 1.65, WH - 1.05, bottom=True)
            for (x, y) in ((bx0 + 1.0, HY0 + 3.6), (bx1 - 1.0, HY0 + 4.6)):
                K.ammo_pallet(P, x, y, SL, 2)
            P.span("red", bx1 - 1.4, bx1 - 0.4, HY0 + 6.2, HY0 + 7.6, SL, SL + 1.2, bev=True)
            P.span("metal", bx0 + 0.3, bx0 + 2.6, HY0 + 6.8, HY0 + 7.6, SL, SL + 0.95)                     # workbench
        for x in (bx0 - 0.35, bx1 + 0.35):                                                            # bollards
            P.cyl("yellow", (x, HY0 - 0.45, SL + 0.55), 0.12, 1.1, seg=8)
            P.cyl("dark", (x, HY0 - 0.45, SL + 1.11), 0.125, 0.03, seg=8, bottom=True)
    # ---------------------------------------------------------------- west annex + lean-to supply canopy
    AX0, AX1, AY0, AY1, AH = -12.8, HX0, -1.0, 9.0, 5.0
    B.span("tanwall", AX0, AX1, AY0, AY1, SL, AH)
    B.span("conc", AX0 - 0.1, AX1, AY0 - 0.1, AY1 + 0.1, AH - 0.15, AH + 0.35, bev=True)
    B.span("roofg", AX0 + 0.2, AX1 - 0.1, AY0 + 0.2, AY1 - 0.2, AH + 0.1, AH + 0.2)
    B.span("conc", AX0 - 0.08, AX1, AY0 - 0.08, AY1 + 0.08, SL, SL + 0.6, bev=True)
    for y in (AY0 + 3.4, AY0 + 6.8):                                                            # pilasters
        B.span("conc", AX0 - 0.25, AX0, y - 0.3, y + 0.3, SL, AH + 0.35, bev=True)
    B.span("door", AX0 + 3.0, AX0 + 4.6, AY0 - 0.04, AY0, SL, 3.0)                                # roll door
    B.span("metal", AX0 + 2.9, AX0 + 4.7, AY0 - 0.35, AY0, 3.0, 3.35, bottom=True)
    B.span("door", AX0 + 0.8, AX0 + 1.8, AY0 - 0.04, AY0, SL, 2.3)
    B.span("metal", AX0 + 0.5, AX0 + 0.75, AY0 - 0.35, AY0 - 0.1, 2.5, 2.75)
    kit.light("Light_Status2", (AX0 + 0.62, AY0 - 0.32, 2.75), "dome", r=0.12)
    K.louvre_panel(B, "y", AY0, AX0 + 5.6, 3.6, -1, w=0.9, h=0.7)
    for y in (AY0 + 1.6, AY0 + 5.0, AY0 + 8.2):
        K.louvre_panel(B, "x", AX0, y, 3.6, -1, w=1.4, h=0.7)
    B.span("door", AX0 - 0.04, AX0, AY0 + 4.2, AY0 + 5.6, SL, 2.6)
    # annex roof: condensers + duct to the hall
    for (x, y) in ((AX0 + 1.8, AY0 + 2.2), (AX0 + 1.8, AY0 + 5.0), (AX0 + 4.4, AY0 + 7.6)):
        K.hvac(B, x, y, AH + 0.2, sx=1.4, sy=1.2, h=0.8)
    B.span("steel", AX0 + 3.8, AX0 + 5.4, AY0 + 2.0, AY0 + 4.6, AH + 0.2, AH + 1.1, bev=True)
    B.strut("steel", (AX0 + 5.4, AY0 + 3.3, AH + 0.75), (HX0 - 0.05, AY0 + 3.3, AH + 0.75), 0.28, seg=10)
    B.railing("metal", [(AX0 + 0.1, AY0 + 0.1), (AX1 - 0.1, AY0 + 0.1)], AH + 0.35, h=0.95, spacing=1.7)
    # west side pipework, tanks and a yellow-railed platform (concept side/rear views)
    for (y, h) in ((AY0 + 2.6, 4.2), (AY0 + 3.2, 4.6)):
        B.pipe("steel", [(AX0 - 0.35, y, SL), (AX0 - 0.35, y, h), (AX0 + 0.3, y, h)], 0.16, seg=8)
    P.tank("steel", (AX0 - 0.6, AY0 + 7.4, SL + 1.3), 0.5, 2.2, axis=(0, 0, 1), seg=12)
    P.span("grate", AX0 - 1.1, AX0, AY0 + 5.8, AY0 + 6.8, SL + 1.6, SL + 1.7)
    P.railing("yellow", [(AX0 - 1.05, AY0 + 5.8), (AX0 - 1.05, AY0 + 6.8)], SL + 1.7, h=0.9, spacing=1.0)
    P.ladder((AX0 - 0.55, AY0 + 5.75, SL), (1, 0, 0), 1.8, (0, -1, 0), m="yellow")
    # lean-to canopy in front of the annex with stacked supplies underneath
    CY0 = -5.4
    B.prism("corr", [(AY0, 3.8), (AY0, 3.6), (CY0, 3.0), (CY0, 3.15)], "x", AX0 - 0.2, AX1 - 0.3)
    B.span("metal", AX0 - 0.2, AX1 - 0.3, CY0 - 0.06, CY0 + 0.06, 2.85, 3.05, bottom=True)
    for x in (AX0, (AX0 + AX1) / 2, AX1 - 0.5):
        B.cyl("metal", (x, CY0 + 0.1, SL + 1.4), 0.06, 2.8, seg=6)
    for (x, y, l) in ((AX0 + 0.9, -2.0, 2), (AX0 + 2.2, -2.0, 1), (AX0 + 0.9, -3.4, 1)):
        K.ammo_pallet(P, x, y, SL, l)
    for (x, y, sx, sy, h) in ((AX0 + 3.6, -2.2, 1.2, 1.0, 1.1), (AX0 + 3.6, -3.6, 1.1, 1.0, 0.8),
                              (AX0 + 5.0, -2.1, 1.0, 1.0, 1.4)):
        K.crate(P, x, y, SL, sx, sy, h, m="wood")
    for (x, y) in ((AX0 + 5.4, -3.8), (AX0 + 5.9, -4.3), (AX0 + 2.4, -4.5)):
        K.drum(P, x, y, SL, "olive")
    K.tarp_stack(P, AX0 + 1.0, -6.6, SL, 1.4, 1.2, 1.2)
    # east side clutter
    for (x, y, l) in ((13.3, 7.0, 2), (13.3, 5.6, 1)):
        K.ammo_pallet(P, x, y, SL, l)
    K.crate(P, 13.3, -1.8, SL, 1.0, 1.4, 1.0, m="wood")
    # rear: generator cabinets
    for (x, y, sx, sy, h) in ((-2.0, 10.7, 1.6, 0.7, 1.6), (0.2, 10.7, 1.0, 0.7, 1.2), (8.0, 10.7, 1.8, 0.7, 1.5)):
        P.span("cabinet", x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, SL, SL + h, bev=True)

    # ---------------------------------------------------------------- markers
    kit.empty("Exit", ((BAYS[0][0] + BAYS[0][1]) / 2, -12.0, 0.0))
    kit.empty("RepairBay", ((BAYS[1][0] + BAYS[1][1]) / 2, -8.0, SL))
    return kit, B, P


if not O["skip_build"]:
    kit, B, P = build()
    kit.finish(B, P, O["out"])
if O["previews"]:
    K.previews(GLB, O["previews"], ID, extent=28.0, concept=O["concept"], only=O["only"], target_z=3.5)
