"""Steel Accord - original HQ building 'Command Post' (procedurally modelled in Blender, bpy 5.x).

Run: python3 bld_command_post.py <out_dir>
Outputs: command_post.glb (single mesh node 'Building', origin at ground centre) + command_post_building_ao.png.
Footprint 16 x 16 m. Front (main entrance, bay door, helipad) faces Blender +Y (Godot -Z). Metres.
Materials: SA_Concrete (plain walls/slabs, new palette entry), SA_Paint (camouflaged armour cladding),
SA_Metal, SA_Glass, SA_Team, SA_Decal, SA_Canvas (gabion geotextile), SA_Rubber. Original design.
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
        ("SA_Decal", (0.7, 0.7, 0.65)), ("SA_Canvas", (0.12, 0.1, 0.06)), ("SA_Concrete", (0.3, 0.3, 0.28))]}


class Part:
    """Accumulates primitives per material into bmeshes, then builds one bevelled object."""

    def __init__(self, name):
        self.name, self.bms, self.extra = name, {}, []

    def bm(self, m):
        return self.bms.setdefault(m, bmesh.new())

    def box(self, m, c, size, rot=(0, 0, 0)):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(self.bm(m), size=1.0, matrix=M)

    def span(self, m, x0, x1, y0, y1, z0, z1):
        """Axis-aligned box from min/max corners."""
        self.box(m, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))

    def cyl(self, m, c, r, depth, rot=(0, 0, 0), seg=16, r2=None):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=depth, matrix=M)

    def strut(self, m, a, b, r, seg=6):
        """Cylinder between two points."""
        a, b = V(a), V(b)
        d = b - a
        M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r,
                              depth=d.length, matrix=M)

    def frustum(self, m, x0, x1, y0, y1, z0, z1, inset, inset_y=None):
        """Rectangular block whose top is inset (sloped armour roof / chamfered plinth)."""
        iy = inset if inset_y is None else inset_y
        bm = self.bm(m)
        A = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
        B = [bm.verts.new(p) for p in ((x0 + inset, y0 + iy, z1), (x1 - inset, y0 + iy, z1), (x1 - inset, y1 - iy, z1),
                                      (x0 + inset, y1 - iy, z1))]
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(4):
            bm.faces.new((A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]))

    def side(self, m, pts_yz, width, x0=0.0):
        bm = self.bm(m)
        A = [bm.verts.new((x0 - width / 2, y, z)) for y, z in pts_yz]
        B = [bm.verts.new((x0 + width / 2, y, z)) for y, z in pts_yz]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def ring2d(self, m, c, r0, r1, z0, z1, seg=40):
        """Flat annulus (painted helipad circle)."""
        bm = self.bm(m)
        pts = [(math.cos(k * 2 * PI / seg), math.sin(k * 2 * PI / seg)) for k in range(seg)]
        O0 = [bm.verts.new((c[0] + r1 * x, c[1] + r1 * y, z0)) for x, y in pts]
        I0 = [bm.verts.new((c[0] + r0 * x, c[1] + r0 * y, z0)) for x, y in pts]
        O1 = [bm.verts.new((c[0] + r1 * x, c[1] + r1 * y, z1)) for x, y in pts]
        I1 = [bm.verts.new((c[0] + r0 * x, c[1] + r0 * y, z1)) for x, y in pts]
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new((O1[k], O1[j], I1[j], I1[k]))
            bm.faces.new((O0[k], O0[j], O1[j], O1[k]))
            bm.faces.new((I0[j], I0[k], I1[k], I1[j]))

    def bolts(self, p0, p1, n, axis, r=0.03):
        rot = {"x": (0, PI / 2, 0), "y": (PI / 2, 0, 0), "z": (0, 0, 0)}[axis]
        for i in range(n):
            c = V(p0).lerp(V(p1), i / max(1, n - 1))
            self.cyl("SA_Metal", c, r, 0.04, rot, seg=6)

    def build(self, bevel=0.03, angle=30, segs=2):
        objs = []
        for mname, bm in self.bms.items():
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            me = bpy.data.meshes.new(f"{self.name}_{mname}")
            bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(me.name, me); scene.collection.objects.link(o)
            me.materials.append(MATS[mname])
            if bevel and mname not in ("SA_Decal", "SA_Glass", "SA_Team"):
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


def text_mesh(body, size, loc, rot, m="SA_Decal"):
    cu = bpy.data.curves.new("txt", "FONT"); cu.body = body; cu.size = size
    cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = 0.004
    o = bpy.data.objects.new("txt", cu); scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.clear(); o.data.materials.append(MATS[m])
    return o


B = Part("Building")
G0 = 0.3                       # top of the base slab

# ================================================================== base slab + aprons
B.frustum("SA_Concrete", -8.0, 8.0, -8.0, 8.0, 0.0, G0, 0.12)
for k in range(1, 4):                                                    # expansion joints
    B.span("SA_Rubber", -7.85 + k * 4.0 - 0.025, -7.85 + k * 4.0 + 0.025, -7.85, 7.85, G0 - 0.01, G0 + 0.006)
    B.span("SA_Rubber", -7.85, 7.85, -7.85 + k * 4.0 - 0.025, -7.85 + k * 4.0 + 0.025, G0 - 0.01, G0 + 0.006)

# ================================================================== MAIN BLOCK (two storeys, x -7..1.5, y -7..0.5)
MX0, MX1, MY0, MY1 = -6.6, 1.5, -7.0, 0.5
F1, F2, TOP = G0, 3.6, 6.9
B.frustum("SA_Concrete", MX0 - 0.25, MX1 + 0.25, MY0 - 0.25, MY1 + 0.25, G0, G0 + 0.6, 0.18)      # chamfered plinth
B.span("SA_Paint", MX0, MX1, MY0, MY1, G0, TOP)                                                       # core
B.span("SA_Concrete", MX0 - 0.06, MX1 + 0.06, MY0 - 0.06, MY1 + 0.06, F2 - 0.12, F2 + 0.12)          # floor band
# prefab armour cladding panels: slightly proud, with vertical seams, on both storeys
def clad_face(axis, fixed, a0, a1, outward, z0, z1, n, skip=()):
    w = (a1 - a0) / n
    for i in range(n):
        if i in skip:
            continue
        c0, c1 = a0 + i * w + 0.04, a0 + (i + 1) * w - 0.04
        if axis == "y":                                     # face normal along y
            B.span("SA_Paint", c0, c1, fixed, fixed + outward * 0.1, z0 + 0.1, z1 - 0.1)
        else:
            B.span("SA_Paint", fixed, fixed + outward * 0.1, c0, c1, z0 + 0.1, z1 - 0.1)
for z0, z1 in ((G0 + 0.6, F2 - 0.12), (F2 + 0.12, TOP - 0.1)):
    clad_face("y", MY1, MX0, MX1, 1, z0, z1, 5, skip=(2,) if z0 < 1 else ())
    clad_face("y", MY0, MX0, MX1, -1, z0, z1, 5)
    clad_face("x", MX0, MY0, MY1, -1, z0, z1, 4)
    clad_face("x", MX1, MY0, MY1, 1, z0, z1, 4, skip=(0, 1, 2, 3) if z0 < 1 else ())
# armoured slit windows with steel shutters (upper storey all round, a few on the ground floor)
def slit(axis, fixed, a, z, outward, w=1.1, h=0.4):
    if axis == "y":
        B.span("SA_Metal", a - w / 2 - 0.1, a + w / 2 + 0.1, fixed + outward * 0.1, fixed + outward * 0.18, z - h / 2 - 0.1, z + h / 2 + 0.1)
        B.span("SA_Glass", a - w / 2, a + w / 2, fixed + outward * 0.18, fixed + outward * 0.2, z - h / 2, z + h / 2)
        B.span("SA_Metal", a - w / 2 - 0.15, a + w / 2 + 0.15, fixed + outward * 0.1, fixed + outward * 0.45, z + h / 2 + 0.1, z + h / 2 + 0.18)
    else:
        B.span("SA_Metal", fixed + outward * 0.1, fixed + outward * 0.18, a - w / 2 - 0.1, a + w / 2 + 0.1, z - h / 2 - 0.1, z + h / 2 + 0.1)
        B.span("SA_Glass", fixed + outward * 0.18, fixed + outward * 0.2, a - w / 2, a + w / 2, z - h / 2, z + h / 2)
        B.span("SA_Metal", fixed + outward * 0.1, fixed + outward * 0.45, a - w / 2 - 0.15, a + w / 2 + 0.15, z + h / 2 + 0.1, z + h / 2 + 0.18)
for i in range(5):
    a = MX0 + (i + 0.5) * (MX1 - MX0) / 5
    slit("y", MY1, a, 5.4, 1)
    slit("y", MY0, a, 5.4, -1)
    if i in (0, 4):
        slit("y", MY1, a, 2.3, 1, w=0.8)
for i in range(4):
    a = MY0 + (i + 0.5) * (MY1 - MY0) / 4
    if i != 1:                                   # i=1 is the upper door off the external stairs
        slit("x", MX0, a, 5.4, -1)
    slit("x", MX1, a, 5.4, 1)
# personnel entrance: recessed steel door, armoured awning, ID plate, team-coloured door surround
DX = MX0 + 2.5 * (MX1 - MX0) / 5
B.span("SA_Concrete", DX - 0.95, DX + 0.95, MY1, MY1 + 0.25, G0 + 0.6, 3.0)
B.span("SA_Metal", DX - 0.6, DX + 0.6, MY1 + 0.25, MY1 + 0.3, G0 + 0.6, 2.75)
B.span("SA_Metal", DX - 0.62, DX + 0.62, MY1 + 0.3, MY1 + 0.33, 1.75, 1.8)
B.span("SA_Team", DX - 0.8, DX + 0.8, MY1 + 0.25, MY1 + 0.29, 2.82, 2.98)
B.side("SA_Paint", [(MY1, 3.25), (MY1 + 1.6, 3.0), (MY1 + 1.6, 2.9), (MY1, 3.05)], 2.6, DX)
for s in (-1, 1):
    B.strut("SA_Metal", (DX + s * 1.15, MY1 + 1.5, G0 + 0.6), (DX + s * 1.15, MY1 + 1.5, 2.95), 0.06)
B.frustum("SA_Concrete", DX - 1.2, DX + 1.2, MY1, MY1 + 1.8, G0, G0 + 0.6, 0.0, 0.0)                 # door landing
for k in range(3):                                                                                       # steps down
    B.span("SA_Concrete", DX - 1.0, DX + 1.0, MY1 + 1.8 + k * 0.3, MY1 + 2.1 + k * 0.3, G0, G0 + 0.45 - k * 0.15)
# sloped armour roof with chamfered edges, parapet band (team colour) and roof hardware
B.span("SA_Concrete", MX0 - 0.15, MX1 + 0.15, MY0 - 0.15, MY1 + 0.15, TOP - 0.1, TOP + 0.15)
B.span("SA_Team", MX0 - 0.17, MX1 + 0.17, MY0 - 0.17, MY1 + 0.17, TOP - 0.05, TOP + 0.1)
B.frustum("SA_Paint", MX0 - 0.35, MX1 + 0.35, MY0 - 0.35, MY1 + 0.35, TOP + 0.15, TOP + 1.05, 1.25)   # armour roof
RZ = TOP + 1.05
for i in range(1, 5):                                                                                    # roof plate seams
    x = MX0 - 0.35 + i * (MX1 - MX0 + 0.7) / 5
    B.span("SA_Metal", x - 0.03, x + 0.03, MY0 + 0.9, MY1 - 0.9, RZ - 0.02, RZ + 0.03)
B.span("SA_Team", MX0 + 1.0, MX1 - 1.15, -3.35, -2.25, RZ - 0.01, RZ + 0.03)                            # roof team band (top-down read)
# roof AC units with fan grilles and ducts
for x, y in ((-1.2, -1.3), (-0.2, -4.6), (-2.6, -4.6)):
    B.span("SA_Metal", x - 0.65, x + 0.65, y - 0.5, y + 0.5, RZ, RZ + 0.08)
    B.span("SA_Concrete", x - 0.6, x + 0.6, y - 0.45, y + 0.45, RZ + 0.08, RZ + 0.9)
    B.cyl("SA_Metal", (x, y, RZ + 0.92), 0.38, 0.05, seg=20)
    B.cyl("SA_Rubber", (x, y, RZ + 0.95), 0.33, 0.02, seg=20)
    for k in range(5):
        B.span("SA_Metal", x - 0.62, x - 0.6, y - 0.4 + k * 0.2 - 0.03, y - 0.4 + k * 0.2 + 0.03, RZ + 0.2, RZ + 0.8)
B.strut("SA_Metal", (-1.2, -1.85, RZ + 0.5), (-1.2, -3.0, RZ + 0.5), 0.16, seg=10)
# comms mast: three-leg lattice tower on a roof plinth (back-left), dish, antennas, team beacon
MCx, MCy = -4.6, -4.4
B.frustum("SA_Concrete", MCx - 1.0, MCx + 1.0, MCy - 1.0, MCy + 1.0, RZ, RZ + 0.4, 0.15)
legs = [V((MCx + 0.8 * math.cos(a), MCy + 0.8 * math.sin(a), 0)) for a in (PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3)]
MZ0, MZ1 = RZ + 0.4, RZ + 9.2
def leg_at(i, z):
    t = (z - MZ0) / (MZ1 - MZ0)
    c = V((MCx, MCy, 0))
    return (c + (legs[i] - c) * (1 - 0.65 * t)) + V((0, 0, z))
for i in range(3):
    B.strut("SA_Metal", leg_at(i, MZ0), leg_at(i, MZ1), 0.06)
nseg = 6
for k in range(nseg):
    za, zb = MZ0 + k * (MZ1 - MZ0) / nseg, MZ0 + (k + 1) * (MZ1 - MZ0) / nseg
    for i in range(3):
        j = (i + 1) % 3
        B.strut("SA_Metal", leg_at(i, za), leg_at(j, za), 0.025, seg=4)
        B.strut("SA_Metal", leg_at(i, za), leg_at(j, zb), 0.022, seg=4)
B.cyl("SA_Metal", (MCx, MCy, MZ1 + 1.4), 0.05, 2.8, seg=8)                                             # top whip mast
B.cyl("SA_Team", (MCx, MCy, MZ1 + 0.15), 0.22, 0.3, seg=12)                                           # beacon housing
B.cyl("SA_Glass", (MCx, MCy, MZ1 + 0.4), 0.12, 0.2, seg=10)
for k, (z, a) in enumerate(((MZ0 + 6.6, 0.6), (MZ0 + 5.0, 2.6), (MZ0 + 7.9, 4.4))):                  # panel antennas
    c = V((MCx, MCy, 0))
    p = c + V((0.5 * math.cos(a), 0.5 * math.sin(a), z))
    B.box("SA_Concrete", p, (0.3, 0.12, 1.1), (0, 0, a + PI / 2))
for z in (MZ0 + 2.6, MZ0 + 7.2):                                                                       # yagi crossarms
    B.strut("SA_Metal", (MCx - 1.2, MCy, z), (MCx + 1.2, MCy, z), 0.025, seg=4)
    for k in range(5):
        x = MCx - 1.0 + k * 0.5
        B.strut("SA_Metal", (x, MCy - 0.35, z), (x, MCy + 0.35, z), 0.012, seg=4)
# satellite dish on the roof (front-left), on a pedestal, aimed up and forward
DCx, DCy = -5.1, -0.9
B.span("SA_Concrete", DCx - 0.5, DCx + 0.5, DCy - 0.5, DCy + 0.5, RZ, RZ + 0.25)
B.cyl("SA_Metal", (DCx, DCy, RZ + 0.7), 0.1, 0.9, seg=10)
dish_rot = (math.radians(-50), 0, math.radians(20))
dish_c = V((DCx, DCy, RZ + 1.5))
bm = B.bm("SA_Concrete")
Md = Matrix.Translation(dish_c) @ Euler(dish_rot).to_matrix().to_4x4()
rings = []
for i, r in enumerate((0.0, 0.35, 0.7, 1.0, 1.2)):
    z = 0.25 * (r / 1.2) ** 2
    rings.append([bm.verts.new((Md @ V((r * math.cos(a), r * math.sin(a), z, 1))).xyz)
                  for a in [k * 2 * PI / 20 for k in range(20)]])
for a, b in zip(rings, rings[1:]):
    for k in range(20):
        bm.faces.new((a[k], a[(k + 1) % 20], b[(k + 1) % 20], b[k]))
for k in range(3):                                                                                        # feed horn struts
    a = k * 2 * PI / 3
    B.strut("SA_Metal", Md @ V((1.1 * math.cos(a), 1.1 * math.sin(a), 0.2)), Md @ V((0, 0, 0.95)), 0.02, seg=4)
B.cyl("SA_Metal", Md @ V((0, 0, 1.0)), 0.08, 0.18, dish_rot, seg=8)
# floodlights on the roof corners
for x, y in ((MX0 + 0.2, MY1 + 0.2), (MX1 - 0.2, MY1 + 0.2), (MX1 - 0.2, MY0 - 0.2)):
    B.strut("SA_Metal", (x, y, TOP + 0.15), (x, y, TOP + 2.2), 0.05)
    B.box("SA_Metal", (x, y + 0.15, TOP + 2.25), (0.5, 0.25, 0.35), (math.radians(25), 0, 0))
    B.box("SA_Glass", (x, y + 0.29, TOP + 2.2), (0.4, 0.02, 0.25), (math.radians(25), 0, 0))
# external stairs (left wall): two flights with a mid landing to the upper-floor door, rails, stringers
SX = MX0 - 0.75
B.span("SA_Metal", MX0 - 0.1, MX0, -5.6, -4.4, F2 + 0.12, F2 + 2.3)                                     # upper door frame
B.span("SA_Metal", MX0 - 0.14, MX0 - 0.1, -5.45, -4.55, F2 + 0.15, F2 + 2.1)
B.span("SA_Metal", SX - 0.6, SX + 0.6, -6.6, -4.2, F2 - 0.1, F2)                                         # top landing
nstep = 14
for k in range(nstep):
    t = k / (nstep - 1)
    y = 0.8 - t * 4.9
    z = G0 + 0.2 + t * (F2 - G0 - 0.35)
    B.span("SA_Metal", SX - 0.55, SX + 0.55, y - 0.18, y + 0.18, z - 0.04, z)
for s in (-1, 1):
    B.strut("SA_Metal", (SX + s * 0.58, 1.05, G0), (SX + s * 0.58, -4.2, F2 - 0.05), 0.07, seg=4)       # stringers
    B.strut("SA_Metal", (SX + s * 0.58, 1.05, G0 + 1.0), (SX + s * 0.58, -4.2, F2 + 1.0), 0.03, seg=6)  # handrails
    for k in range(5):
        t = k / 4
        y = 1.0 - t * 5.2; z = G0 + t * (F2 - G0 - 0.05)
        B.strut("SA_Metal", (SX + s * 0.58, y, z), (SX + s * 0.58, y, z + 1.0), 0.025, seg=6)
B.strut("SA_Metal", (SX - 0.58, -4.2, F2 + 1.0), (SX - 0.58, -6.6, F2 + 1.0), 0.03, seg=6)
B.strut("SA_Metal", (SX - 0.58, -6.6, F2 + 1.0), (MX0, -6.6, F2 + 1.0), 0.03, seg=6)
for y in (-4.2, -6.6):
    B.strut("SA_Metal", (SX - 0.58, y, G0), (SX - 0.58, y, F2 + 1.0), 0.05, seg=6)

# ================================================================== VEHICLE BAY ANNEX (x 1.5..7.5, y -5.5..1.5)
AX0, AX1, AY0, AY1, AT = MX1, 7.5, -5.5, 1.5, 5.0
B.frustum("SA_Concrete", AX0, AX1 + 0.2, AY0 - 0.2, AY1 + 0.2, G0, G0 + 0.45, 0.12)
B.span("SA_Concrete", AX0, AX1, AY0, AY1, G0, AT)
for k in range(6):                                                                                        # tilt-up panel seams
    y = AY0 + (k + 0.5) * (AY1 - AY0) / 6
    B.span("SA_Metal", AX1, AX1 + 0.05, y - 0.03, y + 0.03, G0 + 0.45, AT - 0.1)
for k in range(1, 3):
    x = AX0 + k * (AX1 - AX0) / 3
    B.span("SA_Metal", x - 0.03, x + 0.03, AY0 - 0.05, AY0, G0 + 0.45, AT - 0.1)
B.frustum("SA_Concrete", AX0 - 0.1, AX1 + 0.25, AY0 - 0.25, AY1 + 0.25, AT, AT + 0.35, 0.0, 0.0)         # roof slab
B.side("SA_Paint", [(AY0 - 0.25, AT + 0.35), (AY1 + 0.25, AT + 0.35), (AY1 + 0.25, AT + 0.55),
                    (AY0 - 0.25, AT + 0.95)], AX1 - AX0 + 0.35, (AX0 + AX1 + 0.15) / 2)                  # lean-to armour roof
# roll-up bay door with slats, guide rails, housing, hazard header (decal), bollards
DX0, DX1 = AX0 + 0.9, AX1 - 0.9
B.span("SA_Concrete", DX0 - 0.35, DX1 + 0.35, AY1, AY1 + 0.15, G0, AT - 0.4)
B.span("SA_Metal", DX0, DX1, AY1 + 0.05, AY1 + 0.12, G0, 4.1)
for k in range(16):
    z = G0 + 0.12 + k * 0.24
    B.span("SA_Metal", DX0 + 0.02, DX1 - 0.02, AY1 + 0.12, AY1 + 0.16, z, z + 0.05)
B.span("SA_Metal", DX0 - 0.15, DX1 + 0.15, AY1 + 0.1, AY1 + 0.5, 4.1, 4.6)
for s in (DX0 - 0.12, DX1 + 0.12):
    B.span("SA_Metal", s - 0.08, s + 0.08, AY1 + 0.1, AY1 + 0.25, G0, 4.1)
for k in range(6):                                                                                        # hazard chevrons
    x = DX0 + 0.3 + k * (DX1 - DX0 - 0.6) / 5
    B.box("SA_Decal", (x, AY1 + 0.505, 4.35), (0.32, 0.01, 0.14), (0, math.radians(35), 0))
for x in (DX0 - 0.6, DX1 + 0.6):
    B.cyl("SA_Concrete", (x, AY1 + 0.6, G0 + 0.5), 0.16, 1.0, seg=12)
    B.span("SA_Decal", x - 0.165, x + 0.165, AY1 + 0.44, AY1 + 0.76, G0 + 0.75, G0 + 0.85)
B.extra.append(text_mesh("C2", 1.3, (AX1 + 0.012, -4.5, 2.4), (PI / 2, 0, PI / 2)))
B.span("SA_Team", AX0 + 0.1, AX1 - 0.1, AY1, AY1 + 0.04, AT - 0.32, AT - 0.1)
B.span("SA_Team", AX1, AX1 + 0.04, AY0 + 0.1, AY1 - 0.1, AT - 0.32, AT - 0.1)
# side personnel door + vents on the annex
B.span("SA_Metal", AX1, AX1 + 0.08, -3.4, -2.4, G0 + 0.45, 2.6)
for k in range(4):
    B.span("SA_Metal", AX1, AX1 + 0.1, -0.6 + k * 0.4 - 0.12, -0.6 + k * 0.4 + 0.12, 3.6, 4.4)

# ================================================================== GENERATOR (back right) + fuel tank + cable trays
GX, GY = 4.4, -6.75
B.span("SA_Concrete", GX - 2.1, GX + 2.1, GY - 1.0, GY + 1.0, G0, G0 + 0.2)
B.span("SA_Paint", GX - 1.8, GX + 1.8, GY - 0.8, GY + 0.8, G0 + 0.2, G0 + 2.3)
for k in range(10):                                                                                       # radiator louvres
    B.span("SA_Metal", GX + 1.8, GX + 1.85, GY - 0.65, GY + 0.65, G0 + 0.5 + k * 0.17, G0 + 0.6 + k * 0.17)
for s in (-1, 1):
    B.span("SA_Metal", GX - 1.2 + (s + 1) * 0.6, GX - 0.2 + (s + 1) * 0.6, GY + 0.8, GY + 0.85, G0 + 0.4, G0 + 2.0)
B.cyl("SA_Metal", (GX - 1.2, GY - 0.3, G0 + 2.9), 0.12, 1.3, seg=10)                                     # exhaust stack
B.cyl("SA_Rubber", (GX - 1.2, GY - 0.3, G0 + 3.56), 0.14, 0.04, seg=10)
B.span("SA_Team", GX - 1.82, GX + 1.82, GY - 0.82, GY + 0.82, G0 + 1.9, G0 + 2.05)
B.cyl("SA_Paint", (GX - 3.2, GY - 0.1, G0 + 0.75), 0.55, 1.6, (0, PI / 2, 0), seg=16)                  # fuel tank
for x in (GX - 3.75, GX - 2.65):
    B.span("SA_Metal", x - 0.08, x + 0.08, GY - 0.55, GY + 0.35, G0, G0 + 0.4)
B.span("SA_Metal", GX - 1.8, GX - 1.7, GY + 0.4, MY0 - 0.1, G0 + 2.0, G0 + 2.15)                         # cable tray
B.span("SA_Metal", MX1 - 0.4, GX - 1.7, GY + 0.4, GY + 0.55, G0 + 2.0, G0 + 2.15)

# ================================================================== HELIPAD (front left) with painted circle + H
HX, HY = -4.4, 4.6
B.frustum("SA_Concrete", HX - 3.1, HX + 3.1, HY - 3.0, HY + 3.0, G0, G0 + 0.12, 0.08)
HZ = G0 + 0.12
B.ring2d("SA_Decal", (HX, HY), 2.25, 2.5, HZ - 0.01, HZ + 0.008)
for x0, x1, y0, y1 in ((-0.9, -0.55, -1.2, 1.2), (0.55, 0.9, -1.2, 1.2), (-0.55, 0.55, -0.17, 0.17)):
    B.span("SA_Decal", HX + x0, HX + x1, HY + y0, HY + y1, HZ - 0.01, HZ + 0.008)
for k in range(4):                                                                                        # edge lights
    a = k * PI / 2 + PI / 4
    B.cyl("SA_Glass", (HX + 2.85 * math.cos(a), HY + 2.75 * math.sin(a), HZ + 0.06), 0.09, 0.12, seg=8)
# windsock pole by the pad
B.strut("SA_Metal", (-7.5, 7.5, G0), (-7.5, 7.5, G0 + 4.2), 0.05)
B.cyl("SA_Team", (-7.5, 6.95, G0 + 4.0), 0.18, 1.0, (math.radians(95), 0, 0), seg=10, r2=0.09)
# floodlight masts on the pad corners
for x, y in ((HX + 3.0, HY + 2.9),):
    B.strut("SA_Metal", (x, y, G0), (x, y, G0 + 5.5), 0.07)
    for s in (-1, 1):
        B.box("SA_Metal", (x + s * 0.3, y - 0.1, G0 + 5.6), (0.45, 0.3, 0.35), (math.radians(-30), 0, s * 0.4))
        B.box("SA_Glass", (x + s * 0.32, y - 0.27, G0 + 5.5), (0.36, 0.02, 0.24), (math.radians(-30), 0, s * 0.4))

# ================================================================== HESCO-style gabion barrier runs
def gabion(cx, cy, along_x, w=1.0, d=1.0, h=1.3):
    sx, sy = (w, d) if along_x else (d, w)
    B.span("SA_Canvas", cx - sx / 2 + 0.04, cx + sx / 2 - 0.04, cy - sy / 2 + 0.04, cy + sy / 2 - 0.04, G0, G0 + h - 0.03)
    B.span("SA_Canvas", cx - sx / 2 + 0.1, cx + sx / 2 - 0.1, cy - sy / 2 + 0.1, cy + sy / 2 - 0.1, G0 + h - 0.03, G0 + h + 0.05)  # soil fill
    for ex in (-1, 1):                                                                                     # corner posts
        for ey in (-1, 1):
            B.span("SA_Metal", cx + ex * sx / 2 - 0.03, cx + ex * sx / 2 + 0.03, cy + ey * sy / 2 - 0.03, cy + ey * sy / 2 + 0.03, G0, G0 + h)
    for z in (G0 + 0.45, G0 + 0.9, G0 + h - 0.02):                                                       # mesh bands
        B.span("SA_Metal", cx - sx / 2 - 0.01, cx + sx / 2 + 0.01, cy - sy / 2 - 0.01, cy + sy / 2 + 0.01, z - 0.015, z + 0.015)
def gabion_run(x0, y0, x1, y1):
    n = int(round(max(abs(x1 - x0), abs(y1 - y0)) / 1.0))
    along_x = abs(x1 - x0) > abs(y1 - y0)
    for k in range(n):
        t = (k + 0.5) / n
        gabion(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, along_x)
gabion_run(-7.4, 7.5, -3.4, 7.5)                     # pad front run
gabion_run(-0.6, 1.7, -0.6, 7.7)                     # divider between pad and bay apron
gabion_run(-3.0, -7.55, 1.0, -7.55)                  # rear run behind main block
gabion_run(7.55, 2.2, 7.55, 7.2)                     # bay apron right flank

# ================================================================== misc dressing: stencils, signage, conduit, sandbag-free details
B.extra.append(text_mesh("HQ", 0.9, (MX0 + 1.0, MY1 + 0.11, 5.35), (PI / 2, 0, 0)))
B.span("SA_Metal", MX1 + 0.1, MX1 + 0.2, MY0 + 0.4, MY0 + 0.6, G0 + 0.6, TOP)                           # downpipe
B.span("SA_Metal", MX0 + 0.3, MX0 + 0.5, MY0 - 0.2, MY0 - 0.1, G0 + 0.6, TOP)
B.span("SA_Metal", MX0 + 3.5, MX0 + 4.3, MY0 - 0.3, MY0 - 0.1, 1.2, 2.0)
B.span("SA_Metal", MX0 + 4.4, MX0 + 4.8, MY0 - 0.25, MY0 - 0.1, 1.3, 1.8)
B.strut("SA_Metal", (MX0 + 3.9, MY0 - 0.2, 2.0), (MX0 + 3.9, MY0 - 0.2, TOP), 0.05)

building = B.build(bevel=0.03, segs=1)

# ================================================================== UVs + baked AO (with a ground plane for contact occlusion)
scene.render.engine = "CYCLES"; scene.cycles.samples = 48; scene.cycles.device = "CPU"
bpy.ops.object.select_all(action="DESELECT"); building.select_set(True); bpy.context.view_layer.objects.active = building
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); ground = bpy.context.active_object
img = bpy.data.images.new("command_post_building_ao", 2048, 2048)
for m in building.data.materials:
    n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n
bpy.ops.object.select_all(action="DESELECT"); building.select_set(True); bpy.context.view_layer.objects.active = building
bpy.ops.object.bake(type="AO", margin=4)
img.filepath_raw = os.path.join(OUT, "command_post_building_ao.png"); img.file_format = "PNG"; img.save()
for m in building.data.materials:
    for n in [n for n in m.node_tree.nodes if n.type == "TEX_IMAGE"]:
        m.node_tree.nodes.remove(n)
bpy.data.objects.remove(ground)

bpy.ops.object.select_all(action="DESELECT"); building.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "command_post.glb"), export_format="GLB", export_apply=True,
                          use_selection=True)
print("COMMAND_POST OK faces", len(building.data.polygons), "dims", tuple(round(v, 2) for v in building.dimensions))
