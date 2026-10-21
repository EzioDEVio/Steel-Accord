"""Steel Accord - original main battle tank 'Vanguard' v2 (procedurally modelled in Blender, bpy 5.x).

Run: python3 mbt_vanguard.py <out_dir>
Outputs: vanguard.glb (nodes Hull, Tracks, Turret, Gun, Muzzle) + vanguard_<part>_ao.png (baked AO).
Forward is Blender +Y (Godot -Z). Metres. Original design; no reference meshes used.
"""
import bpy, bmesh, math, sys, os
from mathutils import Matrix, Euler, Vector

OUT = sys.argv[-1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
PI = math.pi


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

    def cyl(self, m, c, r, depth, rot=(0, 0, 0), seg=24, r2=None):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=depth, matrix=M)

    def side(self, m, pts_yz, width, x0=0.0):
        bm = self.bm(m)
        A = [bm.verts.new((x0 - width / 2, y, z)) for y, z in pts_yz]
        B = [bm.verts.new((x0 + width / 2, y, z)) for y, z in pts_yz]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def plan(self, m, pts_xy, z0, z1, top=1.0, shift=(0, 0)):
        bm = self.bm(m)
        cx = sum(p[0] for p in pts_xy) / len(pts_xy); cy = sum(p[1] for p in pts_xy) / len(pts_xy)
        A = [bm.verts.new((x, y, z0)) for x, y in pts_xy]
        B = [bm.verts.new((cx + (x - cx) * top + shift[0], cy + (y - cy) * top + shift[1], z1)) for x, y in pts_xy]
        n = len(A)
        bm.faces.new(A[::-1]); bm.faces.new(B)
        for i in range(n):
            bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))

    def bolts(self, p0, p1, n, axis, r=0.028):
        """Row of bolt heads from p0 to p1; axis = 'x'|'y'|'z' surface normal direction."""
        rot = {"x": (0, PI / 2, 0), "y": (PI / 2, 0, 0), "z": (0, 0, 0)}[axis]
        for i in range(n):
            t = i / max(1, n - 1)
            c = Vector(p0).lerp(Vector(p1), t)
            self.cyl("SA_Metal", c, r, 0.035, rot, seg=6)

    def build(self, bevel=0.02, angle=30):
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
                b.width = bevel; b.segments = 2; b.limit_method = "ANGLE"; b.angle_limit = math.radians(angle)
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
    cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = 0.004
    o = bpy.data.objects.new("txt", cu); scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.clear(); o.data.materials.append(MATS["SA_Decal"])
    return o


# =========================================================== HULL
H = Part("Hull")
# lower hull core (between the tracks)
H.side("SA_Paint", [(-3.6, 0.55), (3.0, 0.55), (3.62, 1.0), (3.62, 1.22), (-3.6, 1.22)], 2.4)
# upper hull with a long, shallow upper glacis and a short steep lower plate (sharp modern wedge)
H.side("SA_Paint", [(-3.65, 1.2), (3.55, 1.2), (3.78, 1.24), (2.25, 1.70), (-3.42, 1.72), (-3.65, 1.52)], 3.5)
# glacis splash board (V) and driver station
for s in (-1, 1):
    H.box("SA_Paint", (s * 0.55, 2.55, 1.66), (1.2, 0.07, 0.1), (0, 0, s * math.radians(-22)))
H.cyl("SA_Paint", (0.0, 2.05, 1.73), 0.34, 0.07, seg=28)                        # driver hatch
for k, x in enumerate((-0.34, 0.0, 0.34)):
    H.box("SA_Glass", (x, 2.42, 1.72), (0.2, 0.05, 0.08), (math.radians(-30), 0, 0))
    H.box("SA_Metal", (x, 2.43, 1.75), (0.24, 0.1, 0.03))
# front lights with wire guards, tow hooks, lower-plate bolts
for s in (-1, 1):
    H.box("SA_Metal", (s * 1.42, 3.62, 1.32), (0.36, 0.14, 0.2))
    H.box("SA_Glass", (s * 1.42, 3.70, 1.32), (0.26, 0.03, 0.12))
    for k in range(3):
        H.box("SA_Metal", (s * 1.42 + (k - 1) * 0.14, 3.79, 1.32), (0.025, 0.025, 0.26))
    H.box("SA_Metal", (s * 1.42, 3.79, 1.46), (0.34, 0.025, 0.025))
    H.cyl("SA_Metal", (s * 0.85, 3.68, 0.78), 0.09, 0.3, (PI / 2, 0, 0), seg=10)
    H.box("SA_Metal", (s * 0.85, 3.72, 0.78), (0.08, 0.12, 0.24))
H.bolts((-1.0, 3.33, 0.90), (1.0, 3.33, 0.90), 9, "y")
# engine deck: recessed grilles + access panels with seams
for i in range(9):
    H.box("SA_Metal", (0, -3.32 + i * 0.075, 1.73), (2.2, 0.035, 0.04))
for s in (-1, 1):
    H.box("SA_Metal", (s * 1.25, -3.05, 1.73), (0.55, 0.6, 0.025))
# rear plate: exhaust louvres, tail lights, towing pintle, ID panel
for i in range(5):
    H.box("SA_Metal", (0, -3.66, 1.0 + i * 0.09), (1.8, 0.06, 0.035), (math.radians(30), 0, 0))
for s in (-1, 1):
    H.box("SA_Metal", (s * 1.45, -3.68, 1.42), (0.22, 0.05, 0.12))
    H.box("SA_Glass", (s * 1.45, -3.71, 1.42), (0.16, 0.02, 0.07))
H.cyl("SA_Metal", (0, -3.72, 0.72), 0.08, 0.25, (PI / 2, 0, 0), seg=10)
H.box("SA_Team", (0, -3.67, 1.56), (0.9, 0.02, 0.18))
# side skirts: heavy bolted front modules + lighter segmented rear panels + rubber flap
for s in (-1, 1):
    x = s * 1.93
    for k in range(2):                                   # heavy armour modules (front)
        y0 = 3.35 - k * 0.78
        H.box("SA_Paint", (s * 1.99, y0 - 0.37, 1.05), (0.2, 0.74, 0.7))
        H.bolts((s * 2.1, y0 - 0.66, 1.33), (s * 2.1, y0 - 0.08, 1.33), 4, "x")
        H.bolts((s * 2.1, y0 - 0.66, 0.77), (s * 2.1, y0 - 0.08, 0.77), 4, "x")
    for k in range(5):                                   # lighter panels (rear), 2 cm seams
        y0 = 1.77 - k * 1.06
        H.box("SA_Paint", (x, y0 - 0.52, 1.1), (0.07, 1.02, 0.6))
        H.bolts((s * 1.975, y0 - 0.9, 1.33), (s * 1.975, y0 - 0.14, 1.33), 3, "x", r=0.022)
    H.box("SA_Rubber", (x, -0.3, 0.75), (0.03, 6.6, 0.12))
    H.box("SA_Paint", (s * 1.82, 0.05, 1.415), (0.26, 7.3, 0.04))   # fender lip
    H.box("SA_Team", (s * 1.975, 0.6, 1.25), (0.012, 1.6, 0.11))     # painted team band
    # stowage bins on the rear fenders, with latches
    for y in (-2.25, -2.95):
        H.box("SA_Paint", (s * 1.55, y, 1.86), (0.5, 0.62, 0.3))
        H.box("SA_Metal", (s * 1.81, y, 1.9), (0.02, 0.08, 0.1))
hull = H.build(bevel=0.03)

# =========================================================== RUNNING GEAR
T = Part("Tracks")
TRACK_X, PITCH = 1.55, 0.155


def track_path():
    pts = []
    def arc(cy, cz, r, a0, a1, n):
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    pts += [(-2.75 + i * 0.5, 0.045) for i in range(12)]                 # ground run (rear -> front)
    arc(3.35, 0.78, 0.355, -110, 90, 20)                                 # front idler
    pts += [(3.35 - i * 0.5, 1.135 - 0.03 * math.sin(i * 0.95) ** 2) for i in range(1, 14)]  # top run, slight sag
    arc(-3.3, 0.75, 0.385, 90, 250, 18)                                  # rear drive sprocket
    # resample at link pitch
    poly = pts + [pts[0]]
    seg = [(Vector((0, *poly[i])), Vector((0, *poly[i + 1]))) for i in range(len(poly) - 1)]
    total = sum((b - a).length for a, b in seg)
    n = int(total / PITCH)
    step = total / n
    out, d, si, acc = [], 0.0, 0, 0.0
    for k in range(n):
        target = k * step
        while acc + (seg[si][1] - seg[si][0]).length < target:
            acc += (seg[si][1] - seg[si][0]).length; si += 1
        a, b = seg[si]
        t = (target - acc) / max(1e-6, (b - a).length)
        out.append((a.lerp(b, t), (b - a).normalized()))
    return out


centre = Vector((0, 0, 0.6))
for s in (-1, 1):
    xc = s * TRACK_X
    for p, t in track_path():
        nrm = Vector((0, -t.z, t.y))
        if nrm.dot(p - centre) < 0:
            nrm = -nrm
        R = Matrix(((1, 0, 0), (0, t.y, nrm.y), (0, t.z, nrm.z))).to_4x4()
        base = Matrix.Translation(Vector((xc, p.y, p.z)))
        T.boxm("SA_Track", base @ R, (0.6, 0.13, 0.05))                                   # link shoe
        T.boxm("SA_Track", Matrix.Translation(nrm * 0.035) @ base @ R, (0.56, 0.035, 0.03))  # grouser
        T.boxm("SA_Metal", Matrix.Translation(-nrm * 0.07) @ base @ R, (0.06, 0.07, 0.09))   # guide horn
        for e in (-1, 1):
            T.boxm("SA_Metal", Matrix.Translation(Vector((e * 0.32, 0, 0))) @ base @ R, (0.05, 0.09, 0.07))
    for i in range(7):                                    # dual road wheels: rubber tyre, dished disc, bolt circle
        y = -2.75 + i * 0.917
        for e in (-1, 1):
            x = xc + e * 0.165
            T.cyl("SA_Rubber", (x, y, 0.46), 0.38, 0.19, (0, PI / 2, 0), seg=32)
            T.cyl("SA_Paint", (x + e * 0.01, y, 0.46), 0.3, 0.2, (0, PI / 2, 0), seg=32)
            T.cyl("SA_Paint", (x + e * 0.08, y, 0.46), 0.13, 0.08, (0, PI / 2, 0), seg=16)
            for b in range(8):
                a = b * PI / 4
                T.cyl("SA_Metal", (x + e * 0.11, y + 0.19 * math.cos(a), 0.46 + 0.19 * math.sin(a)), 0.025, 0.03, (0, PI / 2, 0), seg=6)
    for i in range(3):                                    # return rollers
        T.cyl("SA_Metal", (xc, -1.9 + i * 1.9, 1.0), 0.1, 0.5, (0, PI / 2, 0), seg=14)
    for e in (-1, 1):                                     # toothed drive sprocket (rear)
        x = xc + e * 0.2
        T.cyl("SA_Metal", (x, -3.3, 0.75), 0.33, 0.1, (0, PI / 2, 0), seg=26)
        for k in range(12):
            a = k * PI / 6
            T.box("SA_Metal", (x, -3.3 + 0.36 * math.cos(a), 0.75 + 0.36 * math.sin(a)), (0.09, 0.1, 0.08), (a, 0, 0))
    T.cyl("SA_Paint", (xc + s * 0.27, -3.3, 0.75), 0.16, 0.12, (0, PI / 2, 0), seg=16)
    for e in (-1, 1):                                     # idler (front)
        T.cyl("SA_Metal", (xc + e * 0.165, 3.35, 0.78), 0.31, 0.18, (0, PI / 2, 0), seg=28)
tracks = T.build(bevel=0.012)

# =========================================================== TURRET
U = Part("Turret")
Z0, Z1 = 1.76, 2.6
U.plan("SA_Paint", [(-1.32, -2.0), (1.32, -2.0), (1.48, -0.5), (1.48, 0.95), (1.0, 1.7), (-1.0, 1.7), (-1.48, 0.95), (-1.48, -0.5)],
       Z0, Z1, top=0.95, shift=(0, -0.05))
for s in (-1, 1):                                         # arrow-head wedge add-on armour
    U.plan("SA_Paint", [(s * 1.5, 0.92), (s * 0.62, 1.72), (s * 0.6, 2.55)][::s], 1.86, 2.52, top=0.94)
    U.bolts((s * 0.66, 1.9, 2.53), (s * 1.3, 1.2, 2.53), 4, "z", r=0.024)
    # bolted side armour modules
    U.box("SA_Paint", (s * 1.6, -0.35, 2.17), (0.18, 2.3, 0.62))
    U.bolts((s * 1.70, -1.4, 2.42), (s * 1.70, 0.7, 2.42), 7, "x")
    U.bolts((s * 1.70, -1.4, 1.93), (s * 1.70, 0.7, 1.93), 7, "x")
    U.box("SA_Team", (s * 1.695, -0.35, 2.17), (0.012, 2.1, 0.09))
U.plan("SA_Paint", [(-1.28, -2.95), (1.28, -2.95), (1.32, -2.0), (-1.32, -2.0)], 1.9, 2.5, top=0.96)     # bustle
# mantlet + gun cradle
U.box("SA_Paint", (0, 1.95, 2.2), (1.05, 0.62, 0.66))
U.box("SA_Metal", (0, 2.3, 2.2), (0.5, 0.12, 0.42))
# gunner's primary sight (armoured box, doors) and commander's panoramic sight
U.box("SA_Paint", (-0.82, 1.35, 2.78), (0.5, 0.65, 0.36))
U.box("SA_Glass", (-0.82, 1.69, 2.8), (0.36, 0.02, 0.2))
for s in (-1, 1):
    U.box("SA_Paint", (-0.82 + s * 0.22, 1.71, 2.8), (0.06, 0.05, 0.3))
U.cyl("SA_Metal", (0.7, -0.35, 2.78), 0.13, 0.36, seg=14)
U.box("SA_Paint", (0.7, -0.35, 3.1), (0.52, 0.48, 0.34))
U.box("SA_Glass", (0.7, -0.1, 3.12), (0.38, 0.02, 0.2))
U.box("SA_Glass", (0.7, -0.6, 3.12), (0.38, 0.02, 0.2))
# commander hatch with periscope ring, loader hatch
U.cyl("SA_Paint", (0.7, -1.25, 2.64), 0.42, 0.08, seg=32)
U.cyl("SA_Paint", (0.7, -1.25, 2.7), 0.33, 0.06, seg=32)
for k in range(8):
    a = k * PI / 4
    U.box("SA_Glass", (0.7 + 0.47 * math.cos(a), -1.25 + 0.47 * math.sin(a), 2.65), (0.1, 0.1, 0.07), (0, 0, a))
U.cyl("SA_Paint", (-0.65, -0.95, 2.64), 0.36, 0.07, seg=28)
# remote weapon station: base, cradle, MG, ammo box, sensor head
U.box("SA_Metal", (-0.55, -0.2, 2.72), (0.5, 0.55, 0.16))
U.box("SA_Paint", (-0.55, -0.15, 2.92), (0.34, 0.5, 0.26))
U.cyl("SA_Metal", (-0.55, 0.45, 2.94), 0.035, 0.95, (PI / 2, 0, 0), seg=10)
U.box("SA_Paint", (-0.82, -0.2, 2.9), (0.16, 0.34, 0.2))
U.box("SA_Glass", (-0.3, 0.12, 2.98), (0.12, 0.02, 0.1))
# wind sensor mast + antennas
U.cyl("SA_Metal", (-1.0, -1.7, 2.95), 0.02, 0.7, seg=6)
U.cyl("SA_Metal", (-1.0, -1.7, 3.32), 0.05, 0.08, seg=10)
for s in (-1, 1):
    U.cyl("SA_Metal", (s * 1.05, -2.6, 2.58), 0.07, 0.14, seg=10)
    U.cyl("SA_Metal", (s * 1.05, -2.6, 3.7), 0.011, 2.1, seg=5)
# smoke grenade launchers: 2x2 tube banks on brackets, angled up and outward
for s in (-1, 1):
    U.box("SA_Metal", (s * 1.42, 0.85, 2.58), (0.3, 0.32, 0.06))
    for r in range(2):
        for c in range(2):
            U.cyl("SA_Metal", (s * (1.33 + c * 0.13), 0.78 + r * 0.14, 2.7), 0.05, 0.3, (math.radians(-55), 0, s * math.radians(-30)), seg=10)
# bustle stowage basket: rails, posts, floor slats, stowed tarp roll + boxes
for zr in (2.0, 2.3, 2.58):
    U.cyl("SA_Metal", (0, -3.42, zr), 0.022, 2.7, (0, PI / 2, 0), seg=6)
    for s in (-1, 1):
        U.cyl("SA_Metal", (s * 1.35, -2.7, zr), 0.022, 1.45, (PI / 2, 0, 0), seg=6)
for k in range(9):
    x = -1.35 + k * 0.3375
    U.cyl("SA_Metal", (x, -3.42, 2.29), 0.018, 0.6, seg=6)
for s in (-1, 1):
    for k in range(4):
        U.cyl("SA_Metal", (s * 1.35, -2.1 - k * 0.43, 2.29), 0.018, 0.6, seg=6)
for k in range(5):
    U.box("SA_Metal", (0, -3.0 - k * 0.1, 1.98), (2.66, 0.03, 0.02))
U.cyl("SA_Canvas", (-0.3, -3.15, 2.18), 0.2, 1.7, (0, PI / 2, 0), seg=18)
U.box("SA_Paint", (0.85, -3.1, 2.16), (0.42, 0.42, 0.32))
U.box("SA_Canvas", (0.85, -3.2, 2.43), (0.5, 0.3, 0.2))
U.extra.append(text_mesh("214", 0.34, (1.701, -0.85, 2.17), (PI / 2, 0, PI / 2)))
U.extra.append(text_mesh("214", 0.34, (-1.701, -0.85, 2.17), (PI / 2, 0, -PI / 2)))
turret = U.build(bevel=0.025)

# =========================================================== GUN
G = Part("Gun")
GZ = 2.2
G.cyl("SA_Metal", (0, 5.0, GZ), 0.13, 5.4, (PI / 2, 0, 0), seg=28, r2=0.105)
for i in range(3):                                        # thermal sleeve sections + clamp bands
    y = 2.95 + i * 1.32
    G.cyl("SA_Paint", (0, y, GZ), 0.158, 1.2, (PI / 2, 0, 0), seg=28)
    G.cyl("SA_Metal", (0, y + 0.62, GZ), 0.172, 0.06, (PI / 2, 0, 0), seg=28)
G.cyl("SA_Paint", (0, 4.6, GZ), 0.2, 0.75, (PI / 2, 0, 0), seg=28)        # fume extractor
G.cyl("SA_Metal", (0, 7.6, GZ), 0.135, 0.22, (PI / 2, 0, 0), seg=28)       # muzzle ring
G.box("SA_Metal", (0, 7.35, GZ + 0.16), (0.1, 0.16, 0.08))                  # muzzle reference sensor
gun = G.build(bevel=0.01)

mz = bpy.data.objects.new("Muzzle", None); mz.location = (0, 7.75, GZ); scene.collection.objects.link(mz)

# =========================================================== UVs + baked AO
scene.render.engine = "CYCLES"; scene.cycles.samples = 32; scene.cycles.device = "CPU"
parts = [(hull, 2048), (tracks, 2048), (turret, 2048), (gun, 1024)]
for o, _ in parts:
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
for o, res in parts:
    img = bpy.data.images.new(f"{o.name}_ao", res, res)
    for m in o.data.materials:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type="AO", margin=4)
    img.filepath_raw = os.path.join(OUT, f"vanguard_{o.name.lower()}_ao.png"); img.file_format = "PNG"; img.save()
    for m in o.data.materials:
        for n in [n for n in m.node_tree.nodes if n.type == "TEX_IMAGE"]:
            m.node_tree.nodes.remove(n)

gun.parent = turret; mz.parent = gun
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "vanguard.glb"), export_format="GLB", export_apply=True)
print("VANGUARD OK faces", sum(len(o.data.polygons) for o, _ in parts))
