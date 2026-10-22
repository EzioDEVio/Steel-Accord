"""Steel Accord - original tandem-seat attack helicopter 'Kite' (procedurally modelled in Blender, bpy 5.x).

Run: python3 heli_kite.py <out_dir>
Outputs: kite.glb + kite_body_ao.png (baked AO for Body).
Node hierarchy: Body (origin on the ground under the airframe centre)
                  -> MainRotor (origin on the rotor hub axis; spin about local Z / Godot Y)
                  -> TailRotor (origin on the tail-rotor hub; spin about local X)
                  -> Cannon (origin at the chin-turret pivot; traverse about local Z / Godot Y) -> Muzzle (empty)
Forward is Blender +Y (Godot -Z). Metres. ~15 m rotor diameter, ~14.3 m fuselage. Original design.
"""
import bpy, bmesh, math, sys, os
from mathutils import Matrix, Euler, Vector

OUT = sys.argv[-1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
PI = math.pi
V = Vector


def mat(name, rgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


MATS = {n: mat(n, c) for n, c in [("SA_Paint", (0.1, 0.11, 0.06)), ("SA_Metal", (0.03, 0.03, 0.03)),
        ("SA_Rubber", (0.01, 0.01, 0.01)), ("SA_Glass", (0.01, 0.02, 0.02)), ("SA_Team", (0.5, 0.5, 0.5)),
        ("SA_Track", (0.04, 0.035, 0.03)), ("SA_Decal", (0.7, 0.7, 0.65)), ("SA_Canvas", (0.12, 0.1, 0.06))]}


class Part:
    """Accumulates primitives per material into bmeshes, then builds one bevelled object."""

    def __init__(self, name):
        self.name, self.bms, self.extra = name, {}, []

    def bm(self, m):
        return self.bms.setdefault(m, bmesh.new())

    def box(self, m, c, size, rot=(0, 0, 0)):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(self.bm(m), size=1.0, matrix=M)

    def boxm(self, m, M, size):
        bmesh.ops.create_cube(self.bm(m), size=1.0, matrix=M @ Matrix.Diagonal((*size, 1)))

    def cyl(self, m, c, r, depth, rot=(0, 0, 0), seg=16, r2=None):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=depth, matrix=M)

    def ell(self, m, c, r, rot=(0, 0, 0), u=16, v=10):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*r, 1))
        bmesh.ops.create_uvsphere(self.bm(m), u_segments=u, v_segments=v, radius=1.0, matrix=M)

    def rings(self, m, rings, caps=True):
        """Skin a list of equal-length vertex rings (lists of 3D points) with quads."""
        bm = self.bm(m)
        R = [[bm.verts.new(V(p)) for p in r] for r in rings]
        n = len(R[0])
        for a, b in zip(R, R[1:]):
            for k in range(n):
                bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
        if caps:
            bm.faces.new(R[0][::-1]); bm.faces.new(R[-1])

    def side(self, m, pts_yz, width, x0=0.0):
        bm = self.bm(m)
        A = [bm.verts.new((x0 - width / 2, y, z)) for y, z in pts_yz]
        B = [bm.verts.new((x0 + width / 2, y, z)) for y, z in pts_yz]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def plate(self, m, pts_xy, z0, z1):
        """Extruded plan-view polygon (x, y) between z0 and z1."""
        bm = self.bm(m)
        A = [bm.verts.new((x, y, z0)) for x, y in pts_xy]
        B = [bm.verts.new((x, y, z1)) for x, y in pts_xy]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def bolts(self, p0, p1, n, axis, r=0.022):
        rot = {"x": (0, PI / 2, 0), "y": (PI / 2, 0, 0), "z": (0, 0, 0)}[axis]
        for i in range(n):
            c = V(p0).lerp(V(p1), i / max(1, n - 1))
            self.cyl("SA_Metal", c, r, 0.025, rot, seg=6)

    def build(self, bevel=0.02, angle=30, segs=2):
        objs = []
        for mname, bm in self.bms.items():
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            me = bpy.data.meshes.new(f"{self.name}_{mname}")
            bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(me.name, me); scene.collection.objects.link(o)
            me.materials.append(MATS[mname])
            if bevel and mname not in ("SA_Decal", "SA_Glass"):
                b = o.modifiers.new("bv", "BEVEL")
                b.width = bevel; b.segments = segs; b.limit_method = "ANGLE"; b.angle_limit = math.radians(angle)
                b.harden_normals = True; b.use_clamp_overlap = True
            objs.append(o)
        objs += self.extra
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            bpy.context.view_layer.objects.active = o
            for md in list(o.modifiers):
                bpy.ops.object.modifier_apply(modifier=md.name)
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        j = bpy.context.active_object; j.name = self.name; j.data.name = self.name
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(33))
        return j


def text_mesh(body, size, loc, rot):
    cu = bpy.data.curves.new("txt", "FONT"); cu.body = body; cu.size = size
    cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = 0.003
    o = bpy.data.objects.new("txt", cu); scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.clear(); o.data.materials.append(MATS["SA_Decal"])
    return o


def section(y, wb, w, wt, zb, z1, z2, zt, keel=0.0):
    """Chined, faceted armour cross-section (10 points, counter-clockwise seen from the front)."""
    return [V(p) for p in [(0, y, zb - keel), (wb, y, zb), (w, y, z1), (w, y, z2), (wt, y, zt), (0, y, zt + 0.04),
                           (-wt, y, zt), (-w, y, z2), (-w, y, z1), (-wb, y, zb)]]


def lerp_sec(a, b, t):
    return [p.lerp(q, t) for p, q in zip(a, b)]


# ================================================================== BODY
B = Part("Body")
# -- fuselage: nose -> gunner -> pilot -> engine bay -> tail-boom root
S = [section(6.55, 0.06, 0.10, 0.05, 1.50, 1.56, 1.62, 1.66),
     section(6.25, 0.22, 0.30, 0.18, 1.28, 1.42, 1.62, 1.76),
     section(5.70, 0.34, 0.47, 0.30, 1.08, 1.36, 1.74, 1.92, 0.04),
     section(4.40, 0.40, 0.55, 0.36, 0.96, 1.32, 1.80, 1.98, 0.06),
     section(2.90, 0.42, 0.58, 0.40, 0.94, 1.32, 1.86, 2.02, 0.06),
     section(1.60, 0.46, 0.62, 0.46, 0.94, 1.34, 1.94, 2.16, 0.06),
     section(0.60, 0.52, 0.70, 0.56, 0.95, 1.38, 2.05, 2.42, 0.05),
     section(-1.20, 0.52, 0.70, 0.56, 1.00, 1.42, 2.08, 2.45, 0.03),
     section(-2.50, 0.40, 0.54, 0.42, 1.22, 1.52, 2.04, 2.30),
     section(-3.30, 0.24, 0.31, 0.24, 1.55, 1.70, 1.98, 2.10),
     section(-7.75, 0.13, 0.16, 0.12, 1.86, 1.92, 2.06, 2.12),
     section(-8.20, 0.10, 0.12, 0.09, 1.90, 1.95, 2.06, 2.10)]
B.rings("SA_Paint", S)
# -- stepped tandem canopy: flat armoured-glass facets over each cockpit, frame bows between them
def canopy(y0, y1, sill, top, w_sill, w_top, nose_drop):
    r = []
    for t in (0.0, 0.18, 0.55, 1.0):
        y = y0 + (y1 - y0) * t
        tz = top - nose_drop * (1 - min(1, t / 0.55)) ** 1.6
        wt = w_top * (0.55 + 0.45 * min(1, t / 0.4))
        ws = w_sill * (0.85 + 0.15 * min(1, t / 0.3))
        r.append([V((ws, y, sill)), V((ws * 0.93, y, sill + (tz - sill) * 0.55)), V((wt, y, tz)), V((-wt, y, tz)),
                  V((-ws * 0.93, y, sill + (tz - sill) * 0.55)), V((-ws, y, sill))])
    return r[::-1]
CF = canopy(3.05, 5.55, 1.86, 2.42, 0.47, 0.26, 0.42)       # gunner (front, low)
CR = canopy(1.30, 3.05, 1.98, 2.78, 0.50, 0.28, 0.48)       # pilot (rear, raised: the step)
for C in (CF, CR):
    B.rings("SA_Glass", C)
    for ring in (C[0], C[-1], C[1]):                         # frame bows
        for a, b in zip(ring, ring[1:]):
            d = b - a
            M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("X", "Z").to_matrix().to_4x4()
            B.boxm("SA_Metal", M, (d.length + 0.05, 0.07, 0.07))
    for k in (2,):                                           # centre spine + sill rails
        for i in range(len(C) - 1):
            for p, q in ((C[i][k], C[i + 1][k]), (C[i][k + 1], C[i + 1][k + 1]), (C[i][0], C[i + 1][0]), (C[i][5], C[i + 1][5])):
                d = q - p
                M = Matrix.Translation((p + q) / 2) @ d.to_track_quat("X", "Z").to_matrix().to_4x4()
                B.boxm("SA_Metal", M, (d.length + 0.04, 0.05, 0.05))
# blast shield between the seats and the rear decking fairing behind the pilot
B.rings("SA_Paint", [section(1.35, 0.46, 0.5, 0.3, 1.95, 2.1, 2.5, 2.74), section(0.4, 0.5, 0.56, 0.4, 2.05, 2.2, 2.55, 2.72),
                     section(-0.6, 0.5, 0.56, 0.44, 2.2, 2.3, 2.6, 2.86)])
# -- rotor pylon ("doghouse") + engine nacelles with intakes, grilles and upturned IR-suppressing exhaust shrouds
B.rings("SA_Paint", [section(0.9, 0.42, 0.48, 0.3, 2.3, 2.5, 2.75, 2.84), section(0.2, 0.5, 0.56, 0.42, 2.3, 2.5, 2.95, 3.12),
                     section(-1.5, 0.5, 0.56, 0.42, 2.3, 2.5, 2.95, 3.1), section(-2.4, 0.3, 0.36, 0.25, 2.2, 2.35, 2.6, 2.7)])
B.cyl("SA_Metal", (0, 0.35, 3.5), 0.17, 0.8, seg=16)                                       # mast
B.cyl("SA_Paint", (0, 0.35, 3.16), 0.36, 0.14, seg=16, r2=0.24)                           # mast boot
B.cyl("SA_Paint", (0, 0.35, 3.3), 0.24, 0.16, seg=16, r2=0.19)
for s in (-1, 1):
    x = s * 0.92
    nac = []
    for y, r in ((1.0, 0.30), (0.75, 0.40), (0.2, 0.42), (-1.3, 0.42), (-1.9, 0.36)):
        nac.append([V((x + r * math.cos(a) * 0.95, y, 2.42 + r * math.sin(a) * 0.9)) for a in [k * PI / 6 for k in range(12)]])
    B.rings("SA_Paint", nac)
    B.cyl("SA_Metal", (x, 1.02, 2.42), 0.25, 0.06, (PI / 2, 0, 0), seg=12)                # intake face
    B.cyl("SA_Metal", (x, 0.98, 2.42), 0.08, 0.2, (PI / 2, 0, 0), seg=10)                 # inlet bullet
    for k in range(5):                                                                      # intake screen bars
        B.box("SA_Metal", (x, 1.06, 2.24 + k * 0.09), (0.5, 0.03, 0.02))
    B.box("SA_Paint", (x - s * 0.36, 0.55, 2.62), (0.2, 0.5, 0.18), (0, 0, 0))             # nacelle-to-pylon fairing
    for k in range(6):                                                                      # cooling grilles on nacelle side
        B.box("SA_Metal", (x + s * 0.395, -0.3 - k * 0.14, 2.42), (0.03, 0.07, 0.34))
    # exhaust shroud: boxy duct that turns outward and up, with dark outlet
    B.rings("SA_Paint", [[V((x + dx, -1.85, 2.42 + dz)) for dx, dz in ((0.3, -0.3), (0.3, 0.3), (-0.3, 0.3), (-0.3, -0.3))],
                         [V((x + s * 0.12 + dx, -2.3, 2.47 + dz)) for dx, dz in ((0.26, -0.24), (0.26, 0.26), (-0.26, 0.26), (-0.26, -0.24))],
                         [V((x + s * 0.32 + dx, -2.62, 2.55 + dz)) for dx, dz in ((0.2, -0.17), (0.2, 0.2), (-0.2, 0.2), (-0.2, -0.17))]])
    B.box("SA_Metal", (x + s * 0.33, -2.64, 2.56), (0.36, 0.03, 0.33), (-0.2, 0, s * 0.45))   # dark outlet
B.box("SA_Paint", (0, -0.8, 3.15), (0.5, 0.9, 0.12))                                      # IR jammer plinth
B.cyl("SA_Glass", (0, -1.0, 3.3), 0.13, 0.2, seg=12)
B.cyl("SA_Metal", (0, -1.0, 3.42), 0.15, 0.04, seg=12)
# -- tail: boom strake, canted vertical fin with tail-rotor gearbox, stabilator with end plates, tail wheel
B.box("SA_Paint", (0.0, -5.4, 2.17), (0.04, 3.6, 0.08))                                   # dorsal strake
fin = [(-7.0, 2.05), (-7.7, 2.05), (-8.4, 3.75), (-7.9, 3.85), (-7.35, 2.75)]
B.side("SA_Paint", fin, 0.16, 0.0)
B.side("SA_Team", [(-8.05, 3.4), (-8.4, 3.75), (-7.9, 3.85), (-7.73, 3.47)], 0.17, 0.0)  # team-coloured fin tip
B.cyl("SA_Paint", (-0.13, -7.95, 3.15), 0.2, 0.3, (0, PI / 2, 0), seg=12)                  # tail gearbox fairing
B.plate("SA_Paint", [(-1.45, -6.75), (1.45, -6.75), (1.45, -7.25), (0.2, -7.4), (-0.2, -7.4), (-1.45, -7.25)], 2.0, 2.07)
for s in (-1, 1):
    B.side("SA_Paint", [(-6.7, 1.9), (-7.4, 1.85), (-7.35, 2.3), (-6.85, 2.25)], 0.05, s * 1.47)
# team band: a ring slightly proud of the boom skin
def boom_sec(y, grow):
    t = (y - S[9][0].y) / (S[10][0].y - S[9][0].y)
    c = V((0, y, 1.98))
    return [c + (p - c) * grow for p in lerp_sec(S[9], S[10], t)]
B.rings("SA_Team", [boom_sec(-5.25, 1.04), boom_sec(-5.85, 1.04)])
# ventral fin with a short trailing tail-wheel fork (keeps the tail-wheel leg short and solid)
B.side("SA_Paint", [(-6.2, 1.95), (-7.1, 1.95), (-7.0, 1.05), (-6.75, 0.95)], 0.12, 0.0)
B.box("SA_Metal", (0, -6.95, 0.72), (0.09, 0.12, 0.5), (0.35, 0, 0))
for s in (-1, 1):
    B.box("SA_Metal", (s * 0.09, -7.08, 0.42), (0.03, 0.08, 0.32), (0.35, 0, 0))
B.cyl("SA_Rubber", (0, -7.15, 0.22), 0.22, 0.13, (0, PI / 2, 0), seg=16)
B.cyl("SA_Metal", (0, -7.15, 0.22), 0.1, 0.2, (0, PI / 2, 0), seg=10)
# -- fixed main gear: trailing-arm legs with fairings, wheels, hubs
for s in (-1, 1):
    B.box("SA_Paint", (s * 0.75, 2.25, 1.05), (0.35, 0.7, 0.18), (0, 0, 0))               # sponson
    B.box("SA_Metal", (s * 1.0, 2.15, 0.7), (0.1, 0.12, 0.8), (0.3, s * -0.3, 0))         # oleo
    B.box("SA_Metal", (s * 1.08, 1.95, 0.4), (0.1, 0.55, 0.1), (0.15, 0, 0))              # trailing arm
    B.cyl("SA_Rubber", (s * 1.15, 1.75, 0.33), 0.33, 0.2, (0, PI / 2, 0), seg=20)
    B.cyl("SA_Metal", (s * 1.15, 1.75, 0.33), 0.17, 0.22, (0, PI / 2, 0), seg=12)
# -- stub wings (cranked, slight anhedral) with two pylons each: rocket pod inboard, guided-missile rack outboard
for s in (-1, 1):
    wing = [(0, 0.95), (1.0, 0.95), (2.35, 0.55), (2.45, -0.15), (1.0, -0.35), (0, -0.35)]
    pts = [(s * x, y) for x, y in wing]
    if s < 0: pts = pts[::-1]
    bm = B.bm("SA_Paint")
    A = [bm.verts.new((x, y, 1.68 - abs(x) * 0.06)) for x, y in pts]
    T = [bm.verts.new((x, y, 1.86 - abs(x) * 0.08 - (0.06 if abs(x) > 1.5 else 0))) for x, y in pts]
    bm.faces.new(A[::-1]); bm.faces.new(T)
    for i in range(len(A)):
        bm.faces.new((A[i], A[(i + 1) % len(A)], T[(i + 1) % len(A)], T[i]))
    B.box("SA_Team", (s * 2.0, 0.25, 1.76), (0.35, 0.95, 0.03), (0, s * -0.05, 0))           # wing top team panel
    B.box("SA_Paint", (s * 2.48, 0.2, 1.68), (0.16, 0.9, 0.36))                               # wingtip countermeasure pod
    B.cyl("SA_Glass", (s * 2.48, 0.66, 1.7), 0.08, 0.03, (PI / 2, 0, 0), seg=10)
    for px in (1.3, 2.0):
        B.box("SA_Paint", (s * px, 0.25, 1.5), (0.14, 0.9, 0.22))                             # pylon
        B.box("SA_Metal", (s * px, 0.25, 1.37), (0.1, 1.1, 0.06))
    # 19-tube-style rocket pod, original proportions: faceted can with recessed tube face
    rx = s * 1.3
    B.cyl("SA_Paint", (rx, 0.2, 1.08), 0.26, 1.55, (PI / 2, 0, 0), seg=12)
    B.cyl("SA_Paint", (rx, 1.05, 1.08), 0.26, 0.15, (PI / 2, 0, 0), seg=12, r2=0.2)
    B.cyl("SA_Metal", (rx, 1.12, 1.08), 0.2, 0.04, (PI / 2, 0, 0), seg=12)
    for k in range(7):
        a = k * PI / 3
        rr = 0 if k == 6 else 0.12
        B.cyl("SA_Rubber", (rx + rr * math.cos(a), 1.13, 1.08 + rr * math.sin(a)), 0.045, 0.03, (PI / 2, 0, 0), seg=8)
    B.cyl("SA_Paint", (rx, -0.6, 1.08), 0.26, 0.1, (PI / 2, 0, 0), seg=12, r2=0.18)
    B.box("SA_Team", (rx, 0.2, 1.345), (0.08, 1.2, 0.012))
    # guided-missile rack: launcher rail with 2x2 missiles (body, nose seeker, fins)
    mx = s * 2.0
    B.box("SA_Metal", (mx, 0.25, 1.22), (0.5, 1.4, 0.08))
    for dx in (-0.14, 0.14):
        for dz in (0.0, -0.3):
            c = V((mx + dx, 0.3, 1.04 + dz))
            B.cyl("SA_Paint", c, 0.09, 1.45, (PI / 2, 0, 0), seg=10)
            B.cyl("SA_Glass", c + V((0, 0.77, 0)), 0.09, 0.1, (-PI / 2, 0, 0), seg=10, r2=0.03)
            for f in range(4):
                a = f * PI / 2 + PI / 4
                B.box("SA_Metal", c + V((0.11 * math.cos(a), -0.6, 0.11 * math.sin(a))), (0.015, 0.22, 0.12), (0, a, 0))
# -- chin sensor turret (rotating ball look, two windows) and nose details
B.cyl("SA_Paint", (0, 6.0, 1.2), 0.22, 0.2, seg=16)
B.ell("SA_Paint", (0, 6.0, 0.98), (0.36, 0.36, 0.32), u=18, v=10)
for dx, r in ((-0.14, 0.11), (0.13, 0.08)):
    B.cyl("SA_Glass", (dx, 6.31, 0.98), r, 0.08, (PI / 2, 0, 0), seg=14)
B.box("SA_Metal", (0, 6.28, 1.17), (0.5, 0.12, 0.06))
for s in (-1, 1):
    B.cyl("SA_Metal", (s * 0.2, 6.4, 1.62), 0.015, 0.6, (PI / 2, 0, 0), seg=6)             # pitot probes
    B.box("SA_Glass", (s * 0.28, 6.05, 1.55), (0.02, 0.12, 0.08), (0, 0, s * 0.5))          # forward warning sensors
    B.cyl("SA_Glass", (s * 0.3, -3.0, 1.8), 0.06, 0.03, (0, PI / 2, 0), seg=8)              # rear warning sensors
# -- cannon turret mount fairing under the gunner
B.cyl("SA_Paint", (0, 4.35, 0.92), 0.3, 0.14, seg=16)
# -- armour panel seams, access doors, steps, antennas
for y in (4.9, 3.4, 0.0, -1.9):
    for s in (-1, 1):
        B.box("SA_Metal", (s * 0.6, y, 1.6), (0.02, 0.025, 0.6))
for s in (-1, 1):
    B.box("SA_Paint", (s * 0.66, -0.4, 1.7), (0.03, 1.4, 0.55))                             # avionics bay doors
    B.bolts((s * 0.68, -1.05, 1.95), (s * 0.68, 0.25, 1.95), 6, "x")
    B.bolts((s * 0.68, -1.05, 1.45), (s * 0.68, 0.25, 1.45), 6, "x")
    B.box("SA_Metal", (s * 0.6, 3.5, 1.12), (0.05, 0.2, 0.04))                              # boarding steps
    B.box("SA_Metal", (s * 0.64, 1.7, 1.5), (0.05, 0.2, 0.04))
B.box("SA_Metal", (0, -2.0, 2.35), (0.03, 0.4, 0.35), (0.6, 0, 0))                          # blade antenna
B.box("SA_Metal", (0, 1.2, 0.86), (0.03, 0.35, 0.25), (-0.5, 0, 0))                         # belly antenna
B.cyl("SA_Metal", (0.0, -4.2, 2.45), 0.01, 0.65, seg=5)                                     # whip
B.box("SA_Glass", (0, -8.27, 2.0), (0.06, 0.02, 0.06))                                     # tail light
B.extra.append(text_mesh("31", 0.22, (0.268, -4.6, 1.89), (PI / 2, 0, PI / 2)))
B.extra.append(text_mesh("31", 0.22, (-0.268, -4.6, 1.89), (PI / 2, 0, -PI / 2)))
B.extra.append(text_mesh("31", 0.3, (0.555, 4.4, 1.56), (PI / 2, 0, PI / 2)))
B.extra.append(text_mesh("31", 0.3, (-0.555, 4.4, 1.56), (PI / 2, 0, -PI / 2)))
body = B.build(bevel=0.02)

# ================================================================== MAIN ROTOR (origin at hub)
HUB = V((0, 0.35, 3.98))
MR = Part("MainRotor")
MR.cyl("SA_Metal", (0, 0, 0), 0.34, 0.16, seg=16)                     # hub plate
MR.cyl("SA_Metal", (0, 0, 0.14), 0.18, 0.18, seg=12, r2=0.1)          # hub cap
MR.cyl("SA_Paint", (0, 0, -0.16), 0.24, 0.16, seg=12)                 # swashplate
R_TIP = 7.25
for k in range(4):
    a = k * PI / 2 + PI / 4
    Rz = Matrix.Rotation(a, 4, "Z")
    # blade grip + pitch link
    MR.boxm("SA_Metal", Rz @ Matrix.Translation((0.55, 0, 0)), (0.5, 0.2, 0.12))
    MR.boxm("SA_Metal", Rz @ Matrix.Translation((0.32, 0.17, -0.12)), (0.04, 0.04, 0.3))
    # blade: flattened lofted aerofoil, slight twist, swept tip, droop
    rings = []
    for i, (r, chord, sweep) in enumerate([(0.75, 0.38, 0), (1.3, 0.55, 0), (6.4, 0.55, 0), (6.9, 0.5, -0.08), (R_TIP, 0.3, -0.28)]):
        tw = math.radians(8 - 8 * r / R_TIP)
        th = 0.07 * chord / 0.55
        ring = []
        for ang in [j * 2 * PI / 8 for j in range(8)]:
            cy = chord * 0.5 * math.cos(ang); cz = th * 0.5 * math.sin(ang) * (1.3 if math.cos(ang) > 0 else 0.8)
            y = cy * math.cos(tw) - cz * math.sin(tw) + sweep
            z = cy * math.sin(tw) + cz * math.cos(tw) - 0.012 * r
            ring.append((Rz @ V((r, y + 0.04, z, 1))).xyz)
        rings.append(ring)
    MR.rings("SA_Metal", rings)
    MR.boxm("SA_Team", Rz @ Matrix.Translation((6.62, 0.04, -0.08)), (0.35, 0.58, 0.1))      # blade tip band
main_rotor = MR.build(bevel=0.0)
main_rotor.location = HUB

# ================================================================== TAIL ROTOR (origin at hub, left side of fin)
TH = V((-0.38, -7.95, 3.15))
TR = Part("TailRotor")
TR.cyl("SA_Metal", (0, 0, 0), 0.13, 0.22, (0, PI / 2, 0), seg=12)
TR.cyl("SA_Metal", (-0.14, 0, 0), 0.08, 0.12, (0, PI / 2, 0), seg=10, r2=0.03)
for k in range(4):
    a = k * PI / 2 + 0.3
    Rx = Matrix.Rotation(a, 4, "X")
    rings = []
    for r, chord in ((0.12, 0.2), (0.3, 0.26), (1.15, 0.24), (1.25, 0.16)):
        rings.append([(Rx @ V((-0.02 + 0.02 * math.sin(j * PI / 3), chord * 0.5 * math.cos(j * PI / 3), r, 1))).xyz for j in range(6)])
    TR.rings("SA_Metal", rings)
    TR.boxm("SA_Team", Rx @ Matrix.Translation((-0.02, 0, 1.08)), (0.05, 0.25, 0.12))
tail_rotor = TR.build(bevel=0.0)
tail_rotor.location = TH

# ================================================================== CANNON (chin turret: traverses about Z, origin at pivot)
PIV = V((0, 4.35, 0.82))
CN = Part("Cannon")
CN.cyl("SA_Paint", (0, 0, -0.02), 0.26, 0.12, seg=16)                 # turntable
CN.box("SA_Paint", (0, 0.05, -0.2), (0.34, 0.5, 0.26))               # cradle / receiver
CN.box("SA_Metal", (0, -0.05, -0.2), (0.4, 0.3, 0.2))
CN.box("SA_Paint", (0.24, -0.05, -0.18), (0.1, 0.36, 0.22))          # feed chute housing
CN.cyl("SA_Metal", (0, 0.95, -0.22), 0.05, 1.6, (PI / 2, 0, 0), seg=10)
CN.cyl("SA_Metal", (0, 0.42, -0.22), 0.08, 0.5, (PI / 2, 0, 0), seg=12)       # recoil jacket
for k in range(3):
    CN.cyl("SA_Metal", (0, 0.75 + k * 0.08, -0.22), 0.065, 0.03, (PI / 2, 0, 0), seg=10)
CN.cyl("SA_Metal", (0, 1.77, -0.22), 0.07, 0.12, (PI / 2, 0, 0), seg=10)      # muzzle brake
cannon = CN.build(bevel=0.01)
cannon.location = PIV
muzzle = bpy.data.objects.new("Muzzle", None); scene.collection.objects.link(muzzle)
muzzle.location = (0, 1.85, -0.22)

# ================================================================== UVs + baked AO (Body only)
scene.render.engine = "CYCLES"; scene.cycles.samples = 32; scene.cycles.device = "CPU"
for o in (body, main_rotor, tail_rotor, cannon):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
img = bpy.data.images.new("kite_body_ao", 2048, 2048)
for m in body.data.materials:
    n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); bpy.context.view_layer.objects.active = body
# ground plane so the belly picks up a little occlusion is NOT wanted (it hovers in flight) -> bake airframe alone
bpy.ops.object.bake(type="AO", margin=4)
img.filepath_raw = os.path.join(OUT, "kite_body_ao.png"); img.file_format = "PNG"; img.save()
for m in body.data.materials:
    for n in [n for n in m.node_tree.nodes if n.type == "TEX_IMAGE"]:
        m.node_tree.nodes.remove(n)

for o in (main_rotor, tail_rotor, cannon):
    o.parent = body
muzzle.parent = cannon
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "kite.glb"), export_format="GLB", export_apply=True)
for o in (body, main_rotor, tail_rotor, cannon):
    print(f"  {o.name:10s} faces {len(o.data.polygons):6d} loc {tuple(round(v, 3) for v in o.location)}")
print("KITE OK faces", sum(len(o.data.polygons) for o in (body, main_rotor, tail_rotor, cannon)))
