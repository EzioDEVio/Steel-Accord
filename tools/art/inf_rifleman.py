"""Steel Accord - original modern infantry rifleman (procedurally modelled in Blender, bpy 5.x).

Run: python3 inf_rifleman.py <out_dir>
Output: rifleman.glb, segmented for procedural animation:
  Pelvis (root, origin at hip centre)
    Torso (origin at waist)            -> Head (neck), ArmUpper_L/R (shoulders) -> ArmLower_L/R (elbows)
                                       -> Rifle (origin at stock butt) -> Muzzle (empty)
    LegUpper_L/R (hips) -> LegLower_L/R (knees; carries knee pad + boot)
Forward is Blender +Y (Godot -Z); character's right is +X. Metres. Default pose: standing, rifle at low-ready.
No AO bake (small, segmented asset; engine SSAO covers it). Original design; no reference meshes used.
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
        ("SA_Decal", (0.7, 0.7, 0.65)), ("SA_Canvas", (0.12, 0.1, 0.06)), ("SA_Skin", (0.5, 0.35, 0.28))]}


def frame(d, up=V((0, 0, 1))):
    """Orthonormal basis (x, y, z) with z along d."""
    z = V(d).normalized()
    ref = up if abs(z.dot(up)) < 0.95 else V((1, 0, 0))
    x = ref.cross(z).normalized()
    y = z.cross(x)
    return x, y, z


class Part:
    """Accumulates primitives per material into bmeshes, then builds one (lightly bevelled) object."""

    def __init__(self, name):
        self.name, self.bms, self.extra = name, {}, []

    def bm(self, m):
        return self.bms.setdefault(m, bmesh.new())

    def box(self, m, c, size, rot=(0, 0, 0)):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(self.bm(m), size=1.0, matrix=M)

    def boxm(self, m, M, size):
        bmesh.ops.create_cube(self.bm(m), size=1.0, matrix=M @ Matrix.Diagonal((*size, 1)))

    def cyl(self, m, c, r, depth, rot=(0, 0, 0), seg=10, r2=None):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=depth, matrix=M)

    def ell(self, m, c, r, rot=(0, 0, 0), u=10, v=7):
        """Ellipsoid with radii r=(rx, ry, rz)."""
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*r, 1))
        bmesh.ops.create_uvsphere(self.bm(m), u_segments=u, v_segments=v, radius=1.0, matrix=M)

    def tube(self, m, pts, radii, seg=10, up=V((0, 0, 1)), caps=True):
        """Lofted tube through centre points; radii = (rx, ry) per ring, ring frame follows the path."""
        bm = self.bm(m)
        rings = []
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
            x, y, _ = frame(d, up)
            rx, ry = radii[i]
            rings.append([bm.verts.new(V(p) + x * rx * math.cos(a) + y * ry * math.sin(a))
                          for a in [k * 2 * PI / seg for k in range(seg)]])
        for a, b in zip(rings, rings[1:]):
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
        if caps:
            bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])

    def loftz(self, m, secs, seg=12, cx=0.0):
        """Vertical loft of super-elliptical sections (z, rx, ry, cy, power)."""
        bm = self.bm(m)
        rings = []
        for z, rx, ry, cy, pw in secs:
            ring = []
            for k in range(seg):
                a = k * 2 * PI / seg
                c, s = math.cos(a), math.sin(a)
                ring.append(bm.verts.new((cx + rx * math.copysign(abs(c) ** pw, c),
                                          cy + ry * math.copysign(abs(s) ** pw, s), z)))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])

    def build(self, bevel=0.006, angle=50):
        objs = []
        for mname, bm in self.bms.items():
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            me = bpy.data.meshes.new(f"{self.name}_{mname}")
            bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(me.name, me); scene.collection.objects.link(o)
            me.materials.append(MATS[mname])
            if bevel and mname not in ("SA_Decal", "SA_Glass", "SA_Skin"):
                b = o.modifiers.new("bv", "BEVEL")
                b.width = bevel; b.segments = 1; b.limit_method = "ANGLE"; b.angle_limit = math.radians(angle)
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
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
        return j


def ik(a, target, l1, l2, pole):
    """Two-bone IK: returns the middle joint for root a reaching target, bending toward pole."""
    d = target - a
    L = min(d.length, l1 + l2 - 1e-4)
    dn = d.normalized()
    x = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = (pole - a); p = (p - dn * p.dot(dn)).normalized()
    return a + dn * x + p * h


def set_origin(o, joint):
    o.data.transform(Matrix.Translation(-V(joint)))
    o.location = joint


def parent(child, par):
    """Parent with world joints preserved (no node carries rotation, so local = child joint - parent joint)."""
    child.parent = par
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.location = JOINT[child.name] - JOINT[par.name]


# ------------------------------------------------------------------ skeleton (world space, rest pose)
HIP_C = V((0, 0.0, 0.95))
WAIST = V((0, 0.0, 1.06))
NECK = V((0, 0.035, 1.535))
SH = {s: V((s * 0.205, 0.03, 1.44)) for s in (-1, 1)}
HIP = {s: V((s * 0.095, 0.0, 0.93)) for s in (-1, 1)}
KNEE = {1: V((0.125, 0.035, 0.515)), -1: V((-0.12, 0.10, 0.52))}
ANKLE = {1: V((0.14, -0.02, 0.095)), -1: V((-0.135, 0.05, 0.095))}

# rifle frame: low-ready, stock in the right shoulder pocket, muzzle 40 deg down and slightly inboard
BUTT = V((0.125, 0.07, 1.37))
RD = V((-0.16, math.cos(math.radians(40)), -math.sin(math.radians(40)))).normalized()
RU = (V((0, 0, 1)) - RD * RD.z).normalized()
RX = RD.cross(RU).normalized()
RIFLE_M = Matrix((RX, RD, RU)).transposed().to_4x4()   # columns: rifle local x, y (forward), z (up)
RIFLE_M.translation = BUTT


def rifle_pt(y, z=0.0):
    return BUTT + RD * y + RU * z


GRIP = rifle_pt(0.255, -0.085)
FORE = rifle_pt(0.53, -0.035)
UA, FA = 0.30, 0.27
ELB = {1: ik(SH[1], GRIP - RD * 0.0, UA, FA, SH[1] + V((0.25, -0.25, -0.2))),
       -1: ik(SH[-1], FORE, UA, FA, SH[-1] + V((-0.2, 0.0, -0.4)))}

# ------------------------------------------------------------------ PELVIS (hips, trousers seat, battle belt)
P = Part("Pelvis")
P.loftz("SA_Paint", [(0.83, 0.125, 0.085, -0.005, 0.8), (0.90, 0.165, 0.11, -0.01, 0.7),
                     (0.99, 0.17, 0.115, 0.0, 0.7), (1.09, 0.155, 0.10, 0.005, 0.75)], seg=14)
P.loftz("SA_Canvas", [(0.985, 0.182, 0.127, 0.0, 0.6), (1.06, 0.178, 0.122, 0.003, 0.6)], seg=16)  # belt
P.box("SA_Metal", (0, 0.127, 1.02), (0.07, 0.012, 0.04))                                        # buckle
for s in (-1, 1):
    P.box("SA_Canvas", (s * 0.17, -0.045, 0.99), (0.06, 0.1, 0.12), (0, 0, s * -0.4))          # hip pouches
    P.box("SA_Canvas", (s * 0.12, -0.12, 0.99), (0.09, 0.06, 0.11), (0, 0, s * 0.25))
P.cyl("SA_Canvas", (0.0, -0.13, 0.995), 0.035, 0.12, (0, PI / 2, 0), seg=8)                      # dump roll
pelvis = P.build()
set_origin(pelvis, HIP_C)

# ------------------------------------------------------------------ TORSO (shirt, plate carrier, pouches, pack)
T = Part("Torso")
T.loftz("SA_Paint", [(1.05, 0.15, 0.10, 0.0, 0.75), (1.20, 0.165, 0.11, 0.01, 0.7), (1.33, 0.185, 0.115, 0.02, 0.7),
                     (1.43, 0.18, 0.10, 0.025, 0.65), (1.50, 0.11, 0.08, 0.03, 0.8), (1.545, 0.06, 0.055, 0.035, 1.0)],
        seg=14)
# plate carrier: front and back plate bags with chamfered tops, cummerbund wrap, shoulder straps
T.loftz("SA_Canvas", [(1.10, 0.185, 0.135, 0.015, 0.45), (1.30, 0.20, 0.14, 0.02, 0.45),
                      (1.38, 0.17, 0.13, 0.025, 0.55)], seg=16)
T.box("SA_Canvas", (0, 0.155, 1.28), (0.27, 0.05, 0.3), (0.05, 0, 0))
T.box("SA_Canvas", (0, -0.12, 1.29), (0.28, 0.05, 0.32), (-0.04, 0, 0))
for s in (-1, 1):
    T.box("SA_Canvas", (s * 0.11, 0.03, 1.46), (0.07, 0.25, 0.03), (0.0, 0, 0))                # shoulder straps
    T.box("SA_Canvas", (s * 0.11, 0.135, 1.42), (0.07, 0.03, 0.09), (0.35, 0, 0))
    T.box("SA_Canvas", (s * 0.11, -0.10, 1.42), (0.07, 0.03, 0.09), (-0.35, 0, 0))
# front: triple rifle-mag pouch with flaps, admin pouch above, side radio + IFAK
for k in (-1, 0, 1):
    T.box("SA_Canvas", (k * 0.075, 0.19, 1.19), (0.068, 0.055, 0.13))
    T.box("SA_Canvas", (k * 0.075, 0.197, 1.255), (0.07, 0.05, 0.03), (0.3, 0, 0))
T.box("SA_Canvas", (0.0, 0.188, 1.34), (0.16, 0.035, 0.09))
T.box("SA_Team", (0.0, 0.2065, 1.345), (0.09, 0.003, 0.04))                                    # team ID patch
T.box("SA_Team", (0.0, -0.245, 1.487), (0.15, 0.09, 0.006), (-0.12, 0, 0))                     # pack-lid ID panel (top-down read)
T.box("SA_Canvas", (-0.2, -0.02, 1.18), (0.07, 0.11, 0.17))                                     # radio pouch
T.cyl("SA_Metal", (-0.215, -0.06, 1.36), 0.007, 0.32, seg=5)                                    # whip antenna
T.box("SA_Canvas", (0.2, -0.01, 1.17), (0.06, 0.1, 0.12))                                       # IFAK
# assault pack: main body, lid, side pockets, compression straps, hydration tube
T.box("SA_Canvas", (0, -0.235, 1.26), (0.29, 0.17, 0.36), (-0.06, 0, 0))
T.box("SA_Canvas", (0, -0.24, 1.455), (0.27, 0.16, 0.06), (-0.12, 0, 0))
T.box("SA_Canvas", (0, -0.33, 1.2), (0.2, 0.05, 0.18), (-0.06, 0, 0))
for s in (-1, 1):
    T.box("SA_Canvas", (s * 0.155, -0.24, 1.22), (0.04, 0.12, 0.2))
    T.box("SA_Rubber", (s * 0.08, -0.326, 1.29), (0.025, 0.012, 0.34), (-0.06, 0, 0))
T.box("SA_Rubber", (0, -0.32, 1.1), (0.24, 0.012, 0.025))
T.tube("SA_Rubber", [V((0.12, -0.15, 1.47)), V((0.14, 0.02, 1.47)), V((0.11, 0.17, 1.38))],
       [(0.008, 0.008)] * 3, seg=5)
# collar of the shirt
T.loftz("SA_Paint", [(1.49, 0.085, 0.075, 0.03, 0.9), (1.53, 0.075, 0.07, 0.035, 0.9)], seg=12)
torso = T.build()
set_origin(torso, WAIST)

# ------------------------------------------------------------------ HEAD (face, ears, goggles, helmet with cover + NVG mount)
Hd = Part("Head")
HC = V((0, 0.045, 1.635))
Hd.cyl("SA_Skin", (0, 0.035, 1.555), 0.046, 0.08, seg=10)                                      # neck
# neck gaiter pulled up over the jaw (reads better than a bare face at this scale)
Hd.loftz("SA_Canvas", [(1.525, 0.062, 0.062, 0.035, 1.0), (1.575, 0.07, 0.08, 0.05, 1.0), (1.612, 0.074, 0.093, 0.06, 1.0),
                       (1.628, 0.07, 0.088, 0.062, 1.0)], seg=12)
Hd.ell("SA_Skin", HC, (0.08, 0.095, 0.105), u=12, v=8)
Hd.ell("SA_Skin", HC + V((0, 0.09, -0.04)), (0.055, 0.035, 0.055), u=10, v=6)                  # jaw/chin mass
Hd.box("SA_Skin", HC + V((0, 0.096, -0.012)), (0.018, 0.022, 0.035), (0.3, 0, 0))              # nose
for s in (-1, 1):
    Hd.ell("SA_Skin", HC + V((s * 0.078, 0.0, -0.005)), (0.014, 0.025, 0.032), u=6, v=4)       # ears
# ballistic goggles: wrap lens + frame + strap
Hd.tube("SA_Glass", [HC + V((-0.077, 0.045, 0.0)), HC + V((-0.05, 0.088, 0.0)), HC + V((0, 0.1, 0.0)),
                     HC + V((0.05, 0.088, 0.0)), HC + V((0.077, 0.045, 0.0))], [(0.024, 0.008)] * 5,
        seg=6, up=V((0, 0, 1)))
Hd.tube("SA_Rubber", [HC + V((-0.079, 0.03, 0.0)), HC + V((-0.086, -0.03, 0.01)), HC + V((0, -0.098, 0.02)),
                      HC + V((0.086, -0.03, 0.01)), HC + V((0.079, 0.03, 0.0))], [(0.012, 0.004)] * 5, seg=4)
# helmet: high-cut shell (dome + ear cut-outs suggested by a raised side edge), cover, team band, NVG shroud, rails
HM = HC + V((0, -0.012, 0.012))
bm = Hd.bm("SA_Paint")
ring_pts = []
seg, rows = 18, 6
verts = []
for i in range(rows + 1):                         # dome rows from rim (i=0) to crown
    t = i / rows
    el = t * PI / 2
    row = []
    for k in range(seg):
        a = k * 2 * PI / seg                      # a=PI/2 is the front (+Y)
        side = abs(math.cos(a))                   # 1 at the ears
        back = max(0.0, -math.sin(a))
        front = max(0.0, math.sin(a))
        rim_drop = 0.05 * back + 0.012 * (1 - side) - 0.02 * side - 0.012 * front  # low at the nape, cut high at ears
        r = 0.13 * math.cos(el)
        z = 0.125 * math.sin(el) - rim_drop * (1 - t) ** 2
        row.append(bm.verts.new(HM + V((r * math.cos(a) * 1.0, r * math.sin(a) * 1.08, z))))
    verts.append(row)
for a, b in zip(verts, verts[1:]):
    for k in range(seg):
        bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
top = bm.verts.new(HM + V((0, 0, 0.128)))
for k in range(seg):
    bm.faces.new((verts[-1][k], verts[-1][(k + 1) % seg], top))
inner = [bm.verts.new(HM + (v.co - HM) * 0.93) for v in verts[0]]    # give the rim a thickness
for k in range(seg):
    bm.faces.new((verts[0][(k + 1) % seg], verts[0][k], inner[k], inner[(k + 1) % seg]))
bm.faces.new(inner)
Hd.loftz("SA_Team", [(HM.z + 0.045, 0.1255, 0.1355, HM.y, 1.0), (HM.z + 0.072, 0.1185, 0.128, HM.y, 1.0)], seg=18)
Hd.box("SA_Metal", HM + V((0, 0.132, 0.06)), (0.055, 0.022, 0.045), (-0.35, 0, 0))             # NVG shroud
Hd.box("SA_Metal", HM + V((0, 0.143, 0.03)), (0.032, 0.025, 0.03))
for s in (-1, 1):
    Hd.box("SA_Metal", HM + V((s * 0.126, 0.01, 0.035)), (0.012, 0.11, 0.022))                 # side rails
    Hd.ell("SA_Rubber", HM + V((s * 0.088, 0.005, -0.03)), (0.024, 0.042, 0.048), u=8, v=5)     # ear-pro cups
Hd.box("SA_Canvas", HM + V((0, -0.125, 0.04)), (0.075, 0.03, 0.045), (0.5, 0, 0))              # counterweight pouch
head = Hd.build()
set_origin(head, NECK)

# ------------------------------------------------------------------ ARMS (sleeve, team armband, glove)
arms = {}
for s, nm in ((1, "R"), (-1, "L")):
    sh, el = SH[s], ELB[s]
    hand_t = GRIP if s == 1 else FORE
    d1 = (el - sh).normalized()
    wr = el + (hand_t - el).normalized() * FA
    U = Part(f"ArmUpper_{nm}")
    U.ell("SA_Paint", sh + V((-s * 0.012, 0, 0.0)), (0.062, 0.066, 0.058), u=10, v=6)          # deltoid
    U.tube("SA_Paint", [sh, sh + d1 * 0.12, sh + d1 * 0.24, el + d1 * 0.03],
           [(0.057, 0.06), (0.056, 0.058), (0.047, 0.05), (0.043, 0.045)], seg=10)
    U.tube("SA_Team", [sh + d1 * 0.085, sh + d1 * 0.135], [(0.064, 0.066)] * 2, seg=10)
    arms[f"ArmUpper_{nm}"] = (U.build(), sh)
    L = Part(f"ArmLower_{nm}")
    d2 = (wr - el).normalized()
    L.ell("SA_Paint", el, (0.047, 0.047, 0.047), u=8, v=6)
    L.tube("SA_Paint", [el, el + d2 * 0.1, wr - d2 * 0.05], [(0.046, 0.05), (0.044, 0.046), (0.034, 0.036)], seg=10)
    L.tube("SA_Paint", [wr - d2 * 0.07, wr - d2 * 0.02], [(0.038, 0.040)] * 2, seg=10)        # rolled cuff
    # glove: wrist, palm block, finger wrap and thumb, roughly closed around the grip / handguard
    hx, hy, hz = frame(d2)
    M = Matrix((hx, hy, hz)).transposed().to_4x4(); M.translation = wr + d2 * 0.05
    L.boxm("SA_Rubber", M, (0.07, 0.04, 0.1))
    M2 = M.copy(); M2.translation = wr + d2 * 0.09 + hy * 0.012
    L.boxm("SA_Rubber", M2, (0.072, 0.05, 0.05))
    L.boxm("SA_Rubber", Matrix.Translation(-hx * s * 0.03 + hy * 0.02 + d2 * 0.02) @ M, (0.02, 0.025, 0.06))
    arms[f"ArmLower_{nm}"] = (L.build(), el)
for o, j in arms.values():
    set_origin(o, j)

# ------------------------------------------------------------------ LEGS (trousers, cargo pocket, knee pad, boot)
legs = {}
for s, nm in ((1, "R"), (-1, "L")):
    hp, kn, an = HIP[s], KNEE[s], ANKLE[s]
    d1 = (kn - hp).normalized(); d2 = (an - kn).normalized()
    U = Part(f"LegUpper_{nm}")
    U.tube("SA_Paint", [hp + V((0, 0, 0.05)), hp, hp + d1 * 0.14, hp + d1 * 0.30, kn + d1 * 0.02],
           [(0.09, 0.09), (0.094, 0.096), (0.09, 0.092), (0.075, 0.078), (0.062, 0.064)], seg=12)
    pc = hp + d1 * 0.22 + V((s * 0.083, 0.0, 0))                                                # cargo pocket
    U.box("SA_Paint", pc, (0.03, 0.12, 0.14))
    U.box("SA_Paint", pc + V((s * 0.003, 0, 0.07)), (0.034, 0.125, 0.025))
    legs[f"LegUpper_{nm}"] = (U.build(), hp)
    L = Part(f"LegLower_{nm}")
    L.tube("SA_Paint", [kn - d2 * 0.02, kn + d2 * 0.12, kn + d2 * 0.25, an + V((0, 0, 0.11))],
           [(0.062, 0.064), (0.063, 0.069), (0.053, 0.056), (0.054, 0.057)], seg=12)
    # knee pad: hard cap over a soft pad, with strap
    kx, ky, kz = frame(d2)
    L.ell("SA_Rubber", kn + V((0, 0.05, -0.02)), (0.05, 0.03, 0.065), u=10, v=6)
    L.ell("SA_Canvas", kn + V((0, 0.035, -0.02)), (0.055, 0.03, 0.075), u=10, v=6)
    L.tube("SA_Rubber", [kn + d2 * 0.05, kn + d2 * 0.075], [(0.062, 0.065)] * 2, seg=12)
    # boot: shaft, foot, toe cap, sole + heel, laces
    L.loftz("SA_Canvas", [(an.z + 0.12, 0.05, 0.055, an.y, 1.0), (an.z + 0.03, 0.05, 0.06, an.y, 1.0)],
            seg=12, cx=an.x)
    L.loftz("SA_Canvas", [(0.025, 0.05, 0.135, an.y + 0.055, 0.6), (0.085, 0.045, 0.12, an.y + 0.045, 0.65),
                          (0.105, 0.038, 0.08, an.y + 0.02, 0.8)], seg=14, cx=an.x)
    L.loftz("SA_Rubber", [(0.0, 0.053, 0.14, an.y + 0.055, 0.55), (0.03, 0.054, 0.142, an.y + 0.055, 0.55)],
            seg=14, cx=an.x)
    L.box("SA_Rubber", (an.x, an.y + 0.12, 0.045), (0.08, 0.06, 0.04))                         # toe cap
    for k in range(3):
        L.box("SA_Rubber", (an.x, an.y + 0.09 - k * 0.03, 0.1 + k * 0.012), (0.05, 0.008, 0.006))
    legs[f"LegLower_{nm}"] = (L.build(), kn)
for o, j in legs.values():
    set_origin(o, j)

# ------------------------------------------------------------------ RIFLE (original generic modern carbine), local frame
R = Part("Rifle")
# stock: buttpad, adjustable stock body, buffer tube
R.box("SA_Rubber", (0, 0.012, -0.025), (0.042, 0.025, 0.13))
R.box("SA_Metal", (0, 0.07, -0.02), (0.038, 0.1, 0.11))
R.box("SA_Metal", (0, 0.07, 0.04), (0.03, 0.12, 0.03), (0.15, 0, 0))
R.cyl("SA_Metal", (0, 0.15, 0.01), 0.016, 0.14, (-PI / 2, 0, 0), seg=8)
# receiver (upper + lower), ejection cover, charging handle, magwell, trigger guard, pistol grip
R.box("SA_Metal", (0, 0.32, 0.015), (0.045, 0.22, 0.05))
R.box("SA_Metal", (0, 0.31, -0.03), (0.04, 0.17, 0.045))
R.box("SA_Metal", (0.024, 0.33, 0.01), (0.004, 0.08, 0.025))
R.box("SA_Metal", (0, 0.36, -0.08), (0.036, 0.055, 0.07), (0.15, 0, 0))
R.box("SA_Metal", (0, 0.29, -0.065), (0.008, 0.055, 0.005))
R.box("SA_Rubber", (0, 0.255, -0.085), (0.032, 0.035, 0.09), (0.35, 0, 0))
# curved polymer magazine
for k in range(4):
    R.box("SA_Rubber", (0, 0.375 + k * 0.012, -0.135 - k * 0.04), (0.03, 0.065, 0.046), (0.15 + k * 0.1, 0, 0))
# handguard: long octagonal free-float rail with vent slots, barrel, muzzle brake
R.cyl("SA_Metal", (0, 0.565, 0.008), 0.03, 0.27, (-PI / 2, 0, 0), seg=8)
for k in range(5):
    R.box("SA_Rubber", (0.031, 0.47 + k * 0.045, 0.008), (0.004, 0.025, 0.012))
    R.box("SA_Rubber", (-0.031, 0.47 + k * 0.045, 0.008), (0.004, 0.025, 0.012))
R.box("SA_Metal", (0, 0.45, 0.044), (0.022, 0.5, 0.012))                                        # top rail
R.cyl("SA_Metal", (0, 0.78, 0.008), 0.009, 0.18, (-PI / 2, 0, 0), seg=8)
R.cyl("SA_Metal", (0, 0.875, 0.008), 0.015, 0.06, (-PI / 2, 0, 0), seg=8)
R.box("SA_Rubber", (0, 0.6, -0.04), (0.022, 0.03, 0.06))                                       # vertical foregrip
# optic: compact prism sight on a riser mount, lens caps, flip-up rear sight
R.box("SA_Metal", (0, 0.335, 0.065), (0.03, 0.06, 0.02))
R.box("SA_Metal", (0, 0.335, 0.095), (0.044, 0.11, 0.045))
R.cyl("SA_Metal", (0, 0.40, 0.098), 0.022, 0.035, (-PI / 2, 0, 0), seg=10)
R.cyl("SA_Glass", (0, 0.418, 0.098), 0.018, 0.004, (-PI / 2, 0, 0), seg=10)
R.box("SA_Metal", (0.028, 0.335, 0.095), (0.012, 0.03, 0.02))
R.box("SA_Metal", (0, 0.235, 0.06), (0.015, 0.012, 0.02))
R.box("SA_Metal", (0, 0.69, 0.06), (0.012, 0.01, 0.022))
# sling
R.tube("SA_Canvas", [V((0.03, 0.08, -0.02)), V((0.06, 0.35, -0.12)), V((0.035, 0.66, -0.01))],
       [(0.015, 0.004)] * 3, seg=4, caps=False)
rifle = R.build(bevel=0.003, angle=50)
rifle.matrix_world = RIFLE_M
muzzle = bpy.data.objects.new("Muzzle", None); scene.collection.objects.link(muzzle)
muzzle.location = (0, 0.91, 0.008)

# ------------------------------------------------------------------ hierarchy
JOINT = {"Pelvis": HIP_C, "Torso": WAIST, "Head": NECK}
for nm, s_ in (("R", 1), ("L", -1)):
    JOINT[f"ArmUpper_{nm}"] = SH[s_]; JOINT[f"ArmLower_{nm}"] = ELB[s_]
    JOINT[f"LegUpper_{nm}"] = HIP[s_]; JOINT[f"LegLower_{nm}"] = KNEE[s_]
for o in [pelvis, torso, head, rifle] + [o for o, _ in arms.values()] + [o for o, _ in legs.values()]:
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")

parent(torso, pelvis)
parent(head, torso)
for nm in ("L", "R"):
    parent(arms[f"ArmUpper_{nm}"][0], torso)
    parent(arms[f"ArmLower_{nm}"][0], arms[f"ArmUpper_{nm}"][0])
    parent(legs[f"LegUpper_{nm}"][0], pelvis)
    parent(legs[f"LegLower_{nm}"][0], legs[f"LegUpper_{nm}"][0])
rifle.parent = torso
rifle.matrix_parent_inverse = Matrix.Identity(4)
rifle.matrix_basis = Matrix.Translation(-WAIST) @ RIFLE_M
muzzle.parent = rifle

meshes = [o for o in scene.objects if o.type == "MESH"]
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "rifleman.glb"), export_format="GLB", export_apply=True)
for o in meshes:
    print(f"  {o.name:12s} faces {len(o.data.polygons):5d}  parent {o.parent.name if o.parent else '-'}  loc {tuple(round(v, 3) for v in o.location)}")
print("RIFLEMAN OK faces", sum(len(o.data.polygons) for o in meshes))
