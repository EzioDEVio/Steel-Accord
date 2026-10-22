"""Steel Accord - PILOT 3D infantry: rigged + animated U.S. Army rifleman (procedural, Blender bpy 5.x).

Run:  python3 inf_rifleman_rigged.py <out_dir> [--previews <screens_dir>]
Out:  <out_dir>/rifleman.glb  (one skinned body mesh + Armature + bone-parented rifle with a Muzzle empty, 7 actions)
      <out_dir>/rifleman_camo.png (the procedural tiling camouflage texture, also embedded in the GLB)
      with --previews: pilot3d_rifleman_{front,side,back,top,rts,anims}.png in <screens_dir>

Conventions: metres; Blender +Y forward (= Godot -Z), +Z up, character's right = +X; origin on the ground between the
feet. Original design. The reference concept art was used only for proportions, gear layout and colour sampling
(the camo palette below); no image data from it is placed on the mesh.

Rig: hips root -> spine -> chest -> neck -> head; chest -> upper/lower arm -> hand (x2); hips -> upper/lower leg -> foot
(x2). Godot SkeletonProfileHumanoid bone names. Poses are solved analytically (FK spine, two-bone IK limbs, hands
driven by the rifle) and baked to one keyframe per frame at 30 fps, so the script is deterministic.
"""
import os, sys
if os.environ.get("PYTHONHASHSEED") != "0":       # the glTF exporter iterates hash-ordered sets; pin the seed so
    os.environ["PYTHONHASHSEED"] = "0"             # repeated runs write byte-identical files
    os.execv(sys.executable, [sys.executable] + sys.argv)
import bpy, bmesh, math, json
import numpy as np
from mathutils import Matrix, Euler, Vector, Quaternion

ARGV = [a for a in sys.argv[1:]]
PREV = None
if "--previews" in ARGV:
    i = ARGV.index("--previews"); PREV = ARGV[i + 1]; del ARGV[i:i + 2]
OUT = ARGV[0] if ARGV else "."
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
PI = math.pi
V = Vector
D = math.radians
FPS = 30


# =============================================================================== camouflage texture (procedural)
def periodic_noise(n, sx, sy, rng):
    """Gaussian-filtered white noise on a torus (tiles seamlessly), unit std. sx/sy = blob size in px."""
    w = rng.standard_normal((n, n))
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    g = np.exp(-2 * (PI ** 2) * ((sx * fx) ** 2 + (sy * fy) ** 2))
    o = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    return (o - o.mean()) / o.std()


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def make_camo(path, n=512):
    """Multicam-style layered pattern. Palette sampled (k-means) from the concept art's sleeves/trousers/helmet."""
    rng = np.random.default_rng(1977)
    pal = {"base": (158, 138, 104), "khaki": (126, 108, 80), "olive": (98, 97, 62), "brown": (108, 82, 58),
           "dark": (50, 41, 29), "cream": (198, 182, 148)}
    img = np.zeros((n, n, 3)) + np.array(pal["base"], float)

    def lay(col, mask):
        nonlocal img
        img = img * (1 - mask[..., None]) + np.array(pal[col], float) * mask[..., None]

    # sizes in px (the texture spans 0.55 m, so 10 px ~ 1 cm); slightly vertical brush-stroke shapes
    lay("khaki", smooth(0.25, 0.45, periodic_noise(n, 30, 44, rng) + 0.45 * periodic_noise(n, 9, 12, rng)))
    lay("olive", smooth(0.70, 0.85, periodic_noise(n, 20, 30, rng) + 0.45 * periodic_noise(n, 7, 9, rng)))
    lay("brown", smooth(0.85, 1.0, periodic_noise(n, 16, 24, rng) + 0.45 * periodic_noise(n, 6, 8, rng)))
    vein = np.abs(periodic_noise(n, 10, 16, rng))
    gate = smooth(0.2, 0.5, periodic_noise(n, 36, 36, rng))
    lay("dark", smooth(0.10, 0.04, vein) * gate * 0.95)
    lay("cream", smooth(1.55, 1.75, periodic_noise(n, 6, 8, rng)))
    weave = periodic_noise(n, 0.7, 0.7, rng) * 4.0 + periodic_noise(n, 3, 3, rng) * 3.0
    img = np.clip(img + weave[..., None], 0, 255).astype(np.uint8)
    from PIL import Image
    Image.fromarray(img, "RGB").save(path)
    return path


CAMO_PATH = make_camo(os.path.join(OUT, "rifleman_camo.png"))
CAMO_TILE = 0.55          # metres per texture repeat


# =============================================================================== materials
def mat(name, rgb, rough=0.7, metal=0.0, tex=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(tex); t.image.pack()
        if rgb != (1, 1, 1):      # multiply factor (exported as glTF baseColorFactor)
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            nt.links.new(t.outputs["Color"], mix.inputs["A"])
            mix.inputs["B"].default_value = (*rgb, 1)
            nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
        else:
            nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    return m


MATS = {
    "SA_Camo": mat("SA_Camo", (1, 1, 1), 0.85, tex=CAMO_PATH),                       # uniform, helmet cover, pack
    "SA_CamoGear": mat("SA_CamoGear", (0.86, 0.84, 0.8), 0.9, tex=CAMO_PATH),        # plate carrier + pouches
    "SA_Canvas": mat("SA_Canvas", (0.40, 0.32, 0.22), 0.9),                         # coyote: boots, pads, gloves, belt
    "SA_Skin": mat("SA_Skin", (0.62, 0.44, 0.33), 0.6),
    "SA_Metal": mat("SA_Metal", (0.035, 0.035, 0.037), 0.45, 0.6),
    "SA_Rubber": mat("SA_Rubber", (0.025, 0.025, 0.025), 0.85),
    "SA_Glass": mat("SA_Glass", (0.02, 0.025, 0.03), 0.08, 0.3),
    "SA_Team": mat("SA_Team", (0.75, 0.75, 0.75), 0.7),                            # IR/ID patches, tinted in-game
}
MAT_ORDER = list(MATS)


# =============================================================================== skeleton (rest pose, world space)
BONES = ["Hips", "Spine", "Chest", "Neck", "Head",
         "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
         "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot"]
PARENT = {"Hips": None, "Spine": "Hips", "Chest": "Spine", "Neck": "Chest", "Head": "Neck"}
SIDE = {1: "Right", -1: "Left"}
for s, nm in SIDE.items():
    PARENT.update({f"{nm}UpperArm": "Chest", f"{nm}LowerArm": f"{nm}UpperArm", f"{nm}Hand": f"{nm}LowerArm",
                   f"{nm}UpperLeg": "Hips", f"{nm}LowerLeg": f"{nm}UpperLeg", f"{nm}Foot": f"{nm}LowerLeg"})

HIPS_H, SPINE_H, CHEST_H = V((0, 0, 0.97)), V((0, 0.0, 1.07)), V((0, 0.012, 1.25))
NECK_H, HEAD_H, HEAD_T = V((0, 0.03, 1.50)), V((0, 0.04, 1.585)), V((0, 0.04, 1.80))
SH = {s: V((s * 0.195, 0.025, 1.44)) for s in (-1, 1)}
HIP = {s: V((s * 0.095, 0.0, 0.93)) for s in (-1, 1)}
KNEE = {s: V((s * 0.10, 0.018, 0.515)) for s in (-1, 1)}
ANKLE = {s: V((s * 0.105, -0.01, 0.095)) for s in (-1, 1)}
BALL = {s: V((s * 0.108, 0.115, 0.022)) for s in (-1, 1)}
HEEL_OFF = V((0, -0.085, -0.095))      # sole contact points relative to the ankle (flat foot)
BALL_OFF = V((0, 0.12, -0.095))
TOE_OFF = V((0, 0.192, -0.095))
UA, FA = 0.30, 0.27                    # upper arm / forearm (shoulder->elbow, elbow->wrist)
THIGH, SHIN = (KNEE[1] - HIP[1]).length, (ANKLE[1] - KNEE[1]).length

# rifle, rest = low-ready across the body: stock under the right arm, muzzle forward-down and inboard
BUTT = V((0.135, 0.09, 1.25))
RD = V((-0.30, math.cos(D(28)), -math.sin(D(28)))).normalized()
RU = (V((0, 0, 1)) - RD * RD.z).normalized()
RX = RD.cross(RU).normalized()
RIFLE_REST = Matrix((RX, RD, RU)).transposed().to_4x4()
RIFLE_REST.translation = BUTT


def rifle_pt(y, z=0.0, x=0.0):
    return BUTT + RD * y + RU * z + RX * x


WRIST = {1: rifle_pt(0.215, -0.135, 0.035), -1: rifle_pt(0.405, -0.085, -0.035)}
HANDT = {1: rifle_pt(0.265, -0.075, 0.015), -1: rifle_pt(0.475, -0.035, -0.02)}


def ik(a, target, l1, l2, pole):
    """Two-bone IK: middle joint for root a reaching target, bending toward pole. Returns (joint, reached_target)."""
    d = target - a
    L = min(d.length, l1 + l2 - 1e-4)
    dn = d.normalized()
    x = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = (pole - a); p = (p - dn * p.dot(dn)).normalized()
    return a + dn * x + p * h, a + dn * L


ELB = {s: ik(SH[s], WRIST[s], UA, FA, SH[s] + (V((0.3, -0.2, -0.3)) if s == 1 else V((-0.3, 0.05, -0.4))))[0]
       for s in (-1, 1)}
WRIST = {s: ELB[s] + (WRIST[s] - ELB[s]).normalized() * FA for s in (-1, 1)}   # exact forearm length


def frame(head, tail, zhint):
    """Bone frame (Blender convention): Y along the bone, Z toward zhint, X = Y x Z; translation = head."""
    y = (tail - head).normalized()
    z = zhint - y * zhint.dot(y)
    if z.length < 1e-6:
        z = V((0, 1, 0)) - y * y.y
    z.normalize()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = head
    return m


def bend(a, mid, c):
    """Direction the middle joint bends away from the a->c line (z hint for limb bones)."""
    d = (c - a).normalized()
    v = mid - a
    return v - d * v.dot(d)


REST_DEF = {   # bone: (head, tail, zhint)
    "Hips": (HIPS_H, SPINE_H, V((0, 1, 0))), "Spine": (SPINE_H, CHEST_H, V((0, 1, 0))),
    "Chest": (CHEST_H, NECK_H, V((0, 1, 0))), "Neck": (NECK_H, HEAD_H, V((0, 1, 0))),
    "Head": (HEAD_H, HEAD_T, V((0, 1, 0))),
}
for s, nm in SIDE.items():
    REST_DEF[f"{nm}UpperArm"] = (SH[s], ELB[s], bend(SH[s], ELB[s], WRIST[s]))
    REST_DEF[f"{nm}LowerArm"] = (ELB[s], WRIST[s], bend(SH[s], ELB[s], WRIST[s]))
    REST_DEF[f"{nm}Hand"] = (WRIST[s], HANDT[s], RU)
    REST_DEF[f"{nm}UpperLeg"] = (HIP[s], KNEE[s], V((0, 1, 0)))
    REST_DEF[f"{nm}LowerLeg"] = (KNEE[s], ANKLE[s], V((0, 1, 0)))
    REST_DEF[f"{nm}Foot"] = (ANKLE[s], BALL[s], V((0, 0, 1)))
REST = {b: frame(*REST_DEF[b]) for b in BONES}

# =============================================================================== skinning chains (weight painting)
CHAINS = {"torso": ([V((0, 0, 0.75)), V((0, 0, 1.07)), CHEST_H, NECK_H + V((0, 0, 0.01)), HEAD_H, V((0, 0.04, 1.9))],
                    ["Hips", "Spine", "Chest", "Neck", "Head"], [0.07, 0.08, 0.035, 0.03])}
for s, nm in SIDE.items():
    CHAINS[f"leg{s}"] = ([HIP[s] + V((0, 0, 0.15)), HIP[s], KNEE[s], ANKLE[s], BALL[s] + V((0, 0.08, 0))],
                         ["Hips", f"{nm}UpperLeg", f"{nm}LowerLeg", f"{nm}Foot"], [0.075, 0.065, 0.035])
    CHAINS[f"arm{s}"] = ([SH[s] - V((s * 0.12, 0, 0.02)), SH[s], ELB[s], WRIST[s], HANDT[s] + (HANDT[s] - WRIST[s])],
                         ["Chest", f"{nm}UpperArm", f"{nm}LowerArm", f"{nm}Hand"], [0.05, 0.055, 0.03])


def chain_weights(name, p):
    pts, bones, radii = CHAINS[name]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    best = None
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        ab = b - a
        u = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        d = (a + ab * u - p).length
        if best is None or d < best[0]:
            best = (d, cum[i] + u * ab.length)
    arc = best[1]
    for k in range(1, len(pts) - 1):
        r = radii[k - 1]
        if abs(arc - cum[k]) < r:
            w = (arc - cum[k] + r) / (2 * r)
            w = w * w * (3 - 2 * w)
            return {bones[k - 1]: 1 - w, bones[k]: w}
    for i in range(len(bones)):
        if arc < cum[i + 1] or i == len(bones) - 1:
            return {bones[i]: 1.0}


# =============================================================================== mesh builder with weights
def basis(d, up=V((0, 0, 1))):
    z = V(d).normalized()
    ref = up if abs(z.dot(up)) < 0.95 else V((1, 0, 0))
    x = ref.cross(z).normalized()
    return x, z.cross(x), z


class Builder:
    """One bmesh; each primitive gets a material and a weight spec: bone name (rigid), dict, or 'chain:<name>'."""

    def __init__(self, groups):
        self.bm = bmesh.new()
        self.dl = self.bm.verts.layers.deform.verify()
        self.groups = groups

    def _fin(self, verts, m, w):
        mi = MAT_ORDER.index(m)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = mi
        for v in verts:
            ws = chain_weights(w[6:], v.co) if isinstance(w, str) and w.startswith("chain:") else \
                ({w: 1.0} if isinstance(w, str) else w)
            dv = v[self.dl]
            for b, x in ws.items():
                if x > 1e-4:
                    dv[self.groups.index(b)] = x

    def box(self, m, w, c, size, rot=(0, 0, 0)):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
        self._fin(bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)["verts"], m, w)

    def boxm(self, m, w, M, size):
        self._fin(bmesh.ops.create_cube(self.bm, size=1.0, matrix=M @ Matrix.Diagonal((*size, 1)))["verts"], m, w)

    def cyl(self, m, w, c, r, depth, rot=(0, 0, 0), seg=8, r2=None):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
        vs = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                                   radius2=r if r2 is None else r2, depth=depth, matrix=M)["verts"]
        self._fin(vs, m, w)

    def ell(self, m, w, c, r, rot=(0, 0, 0), u=10, v=6):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*r, 1))
        self._fin(bmesh.ops.create_uvsphere(self.bm, u_segments=u, v_segments=v, radius=1.0, matrix=M)["verts"], m, w)

    def tube(self, m, w, pts, radii, seg=8, up=V((0, 0, 1)), caps=True, phase=0.0):
        bm, rings, vs = self.bm, [], []
        for i, p in enumerate(pts):
            d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            x, y, _ = basis(d, up)
            rx, ry = radii[i]
            ring = [bm.verts.new(V(p) + x * rx * math.cos(a) + y * ry * math.sin(a))
                    for a in [phase + k * 2 * PI / seg for k in range(seg)]]
            rings.append(ring); vs += ring
        for a, b in zip(rings, rings[1:]):
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
        if caps:
            bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
        self._fin(vs, m, w)

    def loftz(self, m, w, secs, seg=12, cx=0.0, caps=True):
        """Vertical loft of super-elliptical sections (z, rx, ry, cy, power)."""
        bm, rings, vs = self.bm, [], []
        for z, rx, ry, cy, pw in secs:
            ring = []
            for k in range(seg):
                a = k * 2 * PI / seg
                c, s_ = math.cos(a), math.sin(a)
                ring.append(bm.verts.new((cx + rx * math.copysign(abs(c) ** pw, c),
                                          cy + ry * math.copysign(abs(s_) ** pw, s_), z)))
            rings.append(ring); vs += ring
        for a, b in zip(rings, rings[1:]):
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
        if caps:
            bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
        self._fin(vs, m, w)

    def to_object(self, name):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:               # box projection in metres -> tiling camo at CAMO_TILE m per repeat
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for lp in f.loops:
                c = lp.vert.co
                u, v = ((c.y, c.z), (c.x, c.z), (c.x, c.y))[ax]
                lp[uv].uv = (u / CAMO_TILE + 0.37 * ax, v / CAMO_TILE + 0.21 * ax)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me); bm.free()
        for m in MAT_ORDER:
            me.materials.append(MATS[m])
        o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
        for g in self.groups:
            o.vertex_groups.new(name=g)
        return o


B = Builder(BONES)
CH_T = "chain:torso"

# ---------------------------------------------------------------- pelvis: trouser seat, battle belt, pouches
B.loftz("SA_Camo", CH_T, [(0.82, 0.13, 0.095, -0.005, 0.8), (0.90, 0.168, 0.115, -0.01, 0.7),
                          (0.99, 0.172, 0.118, 0.0, 0.7), (1.09, 0.158, 0.105, 0.005, 0.75)], seg=12)
B.loftz("SA_Canvas", "Hips", [(0.975, 0.183, 0.128, 0.0, 0.6), (1.045, 0.18, 0.124, 0.003, 0.6)], seg=14)
B.box("SA_Metal", "Hips", (0, 0.128, 1.01), (0.07, 0.012, 0.04))
for s in (-1, 1):
    B.box("SA_CamoGear", "Hips", (s * 0.175, -0.04, 0.985), (0.05, 0.095, 0.11), (0, 0, s * -0.35))
B.cyl("SA_CamoGear", "Hips", (0.0, -0.135, 0.99), 0.035, 0.14, (0, PI / 2, 0), seg=8)       # dump roll
B.box("SA_Rubber", "Hips", (0.165, 0.07, 0.98), (0.03, 0.03, 0.06))                      # holster strap buckle

# ---------------------------------------------------------------- torso: shirt, plate carrier, pouches, pack
B.loftz("SA_Camo", CH_T, [(1.05, 0.152, 0.102, 0.0, 0.75), (1.20, 0.168, 0.112, 0.01, 0.7),
                          (1.33, 0.188, 0.117, 0.02, 0.7), (1.43, 0.183, 0.102, 0.025, 0.65),
                          (1.50, 0.11, 0.08, 0.03, 0.8), (1.55, 0.065, 0.06, 0.035, 1.0)], seg=12)
B.loftz("SA_CamoGear", {"Chest": 0.85, "Spine": 0.15},
        [(1.10, 0.188, 0.138, 0.015, 0.45), (1.30, 0.203, 0.143, 0.02, 0.45), (1.38, 0.172, 0.133, 0.025, 0.55)],
        seg=14)
B.box("SA_CamoGear", "Chest", (0, 0.158, 1.29), (0.27, 0.05, 0.30), (0.05, 0, 0))
B.box("SA_CamoGear", "Chest", (0, -0.123, 1.29), (0.28, 0.05, 0.32), (-0.04, 0, 0))
for s in (-1, 1):
    B.box("SA_CamoGear", "Chest", (s * 0.11, 0.03, 1.462), (0.07, 0.25, 0.03))
    B.box("SA_CamoGear", "Chest", (s * 0.11, 0.137, 1.42), (0.07, 0.03, 0.09), (0.35, 0, 0))
    B.box("SA_CamoGear", "Chest", (s * 0.11, -0.10, 1.42), (0.07, 0.03, 0.09), (-0.35, 0, 0))
for k in (-1, 0, 1):                                                   # triple mag pouch + flaps
    B.box("SA_CamoGear", "Chest", (k * 0.077, 0.195, 1.19), (0.07, 0.058, 0.13))
    B.box("SA_Canvas", "Chest", (k * 0.077, 0.204, 1.258), (0.072, 0.05, 0.028), (0.3, 0, 0))
B.box("SA_CamoGear", "Chest", (0.0, 0.19, 1.345), (0.17, 0.035, 0.09))                 # admin pouch
B.box("SA_Team", "Chest", (0.0, 0.2085, 1.35), (0.09, 0.003, 0.04))                    # ID patch
B.box("SA_CamoGear", "Chest", (-0.205, -0.02, 1.18), (0.07, 0.11, 0.17))               # radio pouch
B.box("SA_Rubber", "Chest", (-0.205, -0.02, 1.28), (0.05, 0.06, 0.04))                 # radio top
B.cyl("SA_Rubber", "Chest", (-0.215, -0.06, 1.47), 0.007, 0.36, seg=4)                # whip antenna
B.box("SA_CamoGear", "Chest", (0.205, -0.01, 1.17), (0.06, 0.1, 0.12))                 # IFAK
# assault pack: body, lid, front pocket, compression straps, team panel on the lid (top-down read)
B.box("SA_Camo", "Chest", (0, -0.232, 1.27), (0.29, 0.16, 0.34), (-0.06, 0, 0))
B.box("SA_Camo", "Chest", (0, -0.245, 1.455), (0.27, 0.15, 0.06), (-0.12, 0, 0))
B.box("SA_Camo", "Chest", (0, -0.33, 1.21), (0.2, 0.05, 0.18), (-0.06, 0, 0))
for s in (-1, 1):
    B.box("SA_Rubber", "Chest", (s * 0.08, -0.322, 1.30), (0.025, 0.012, 0.32), (-0.06, 0, 0))
B.box("SA_Team", "Chest", (0.0, -0.25, 1.489), (0.15, 0.09, 0.006), (-0.12, 0, 0))
B.tube("SA_Rubber", "Chest", [V((0.12, -0.15, 1.47)), V((0.14, 0.02, 1.48)), V((0.11, 0.17, 1.39))],
       [(0.008, 0.008)] * 3, seg=4)

# ---------------------------------------------------------------- head: neck, face, eye-pro, helmet + cover, NVG mount
HC = V((0, 0.045, 1.645))
B.cyl("SA_Skin", CH_T, (0, 0.038, 1.565), 0.05, 0.09, seg=8)
B.ell("SA_Skin", "Head", HC, (0.08, 0.094, 0.104), u=12, v=8)
B.ell("SA_Skin", "Head", HC + V((0, 0.072, -0.058)), (0.06, 0.04, 0.048), u=8, v=5)       # jaw/chin
B.box("SA_Skin", "Head", HC + V((0, 0.097, -0.008)), (0.02, 0.024, 0.036), (0.3, 0, 0))   # nose
B.ell("SA_Canvas", "Head", HC + V((0, 0.07, -0.072)), (0.062, 0.042, 0.03), u=8, v=4)     # beard shadow / chin
for s in (-1, 1):
    B.ell("SA_Skin", "Head", HC + V((s * 0.079, 0.0, -0.005)), (0.014, 0.024, 0.03), u=6, v=4)
B.tube("SA_Glass", "Head", [HC + V((-0.079, 0.04, 0.01)), HC + V((-0.05, 0.088, 0.012)), HC + V((0, 0.1, 0.012)),
                            HC + V((0.05, 0.088, 0.012)), HC + V((0.079, 0.04, 0.01))], [(0.02, 0.007)] * 5, seg=4)
HM = HC + V((0, -0.012, 0.016))
bm, dl = B.bm, B.dl
seg, rows, hv = 16, 4, []
for i in range(rows + 1):
    t = i / rows; el = t * PI / 2
    row = []
    for k in range(seg):
        a = k * 2 * PI / seg
        side = abs(math.cos(a)); back = max(0.0, -math.sin(a)); front = max(0.0, math.sin(a))
        rim_drop = 0.05 * back + 0.012 * (1 - side) - 0.02 * side - 0.012 * front
        r = 0.132 * math.cos(el)
        row.append(bm.verts.new(HM + V((r * math.cos(a), r * math.sin(a) * 1.08,
                                         0.125 * math.sin(el) - rim_drop * (1 - t) ** 2))))
    hv.append(row)
for a, b_ in zip(hv, hv[1:]):
    for k in range(seg):
        bm.faces.new((a[k], a[(k + 1) % seg], b_[(k + 1) % seg], b_[k]))
top = bm.verts.new(HM + V((0, 0, 0.128)))
for k in range(seg):
    bm.faces.new((hv[-1][k], hv[-1][(k + 1) % seg], top))
inner = [bm.verts.new(HM + (v.co - HM) * 0.93) for v in hv[0]]
for k in range(seg):
    bm.faces.new((hv[0][(k + 1) % seg], hv[0][k], inner[k], inner[(k + 1) % seg]))
bm.faces.new(inner)
B._fin([v for r in hv for v in r] + [top] + inner, "SA_Camo", "Head")
B.box("SA_Metal", "Head", HM + V((0, 0.137, 0.06)), (0.058, 0.022, 0.048), (-0.35, 0, 0))      # NVG shroud
B.box("SA_Metal", "Head", HM + V((0, 0.152, 0.035)), (0.034, 0.03, 0.03))
for s in (-1, 1):
    B.box("SA_Metal", "Head", HM + V((s * 0.13, 0.01, 0.035)), (0.012, 0.11, 0.022))           # side rails
    B.ell("SA_Rubber", "Head", HM + V((s * 0.09, 0.005, -0.03)), (0.026, 0.044, 0.05), u=8, v=5)  # headset cups
    B.box("SA_Rubber", "Head", HC + V((s * 0.075, 0.035, -0.06)), (0.008, 0.012, 0.07), (0.5, 0, 0))  # chin strap
B.box("SA_CamoGear", "Head", HM + V((0, -0.128, 0.04)), (0.075, 0.03, 0.045), (0.5, 0, 0))    # counterweight
B.box("SA_Team", "Head", HM + V((0, -0.06, 0.118)), (0.04, 0.05, 0.012), (-0.25, 0, 0))       # IR patch

# ---------------------------------------------------------------- arms: sleeves, flag/ID patch, gloves
for s in (-1, 1):
    sh, el, wr, ht = SH[s], ELB[s], WRIST[s], HANDT[s]
    d1, d2 = (el - sh).normalized(), (wr - el).normalized()
    ch = f"chain:arm{s}"
    B.ell("SA_Camo", ch, sh + V((-s * 0.01, 0, 0.004)), (0.064, 0.068, 0.06),
          u=10, v=6)
    B.tube("SA_Camo", ch, [sh - d1 * 0.02, sh + d1 * 0.12, sh + d1 * 0.24, el + d1 * 0.02],
           [(0.058, 0.061), (0.057, 0.059), (0.048, 0.051), (0.045, 0.047)], seg=8)
    B.ell("SA_Camo", ch, el, (0.047, 0.047, 0.047), u=8, v=5)
    B.tube("SA_Camo", ch, [el - d2 * 0.02, el + d2 * 0.1, wr - d2 * 0.03], [(0.047, 0.05), (0.045, 0.047),
                                                                             (0.037, 0.039)], seg=8)
    B.tube("SA_Team", f"{SIDE[s]}UpperArm", [sh + d1 * 0.08, sh + d1 * 0.14], [(0.0625, 0.0645)] * 2, seg=8,
           caps=False)
    # glove: cuff, palm block, curled fingers, thumb (rigid to the hand)
    hb = f"{SIDE[s]}Hand"
    hd = (ht - wr).normalized()
    hx, hy, hz = basis(hd, RU)
    Mh = Matrix((hx, hy, hz)).transposed().to_4x4()
    B.tube("SA_Canvas", hb, [wr - hd * 0.03, wr + hd * 0.02], [(0.04, 0.042)] * 2, seg=8)
    Mh.translation = wr + hd * 0.055
    B.boxm("SA_Canvas", hb, Mh, (0.075, 0.045, 0.085))
    Mh.translation = wr + hd * 0.095 + hy * 0.015
    B.boxm("SA_Canvas", hb, Mh, (0.072, 0.055, 0.045))
    B.boxm("SA_Rubber", hb, Matrix.Translation(-hx * s * 0.035 + hy * 0.02 + hd * 0.035) @ Matrix.Translation(wr) @
           Mh.to_3x3().to_4x4(), (0.024, 0.026, 0.06))

# ---------------------------------------------------------------- legs: trousers, cargo pocket, knee pads, boots
for s in (-1, 1):
    hp, kn, an = HIP[s], KNEE[s], ANKLE[s]
    d1, d2 = (kn - hp).normalized(), (an - kn).normalized()
    ch, nm = f"chain:leg{s}", SIDE[s]
    B.tube("SA_Camo", ch, [hp + V((0, 0, 0.06)), hp, hp + d1 * 0.15, hp + d1 * 0.31, kn + d1 * 0.03],
           [(0.092, 0.092), (0.096, 0.098), (0.091, 0.093), (0.076, 0.079), (0.064, 0.066)], seg=10)
    B.tube("SA_Camo", ch, [kn - d2 * 0.03, kn + d2 * 0.12, kn + d2 * 0.26, an + V((0, 0, 0.1))],
           [(0.064, 0.066), (0.064, 0.07), (0.054, 0.057), (0.055, 0.058)], seg=10)
    pc = hp + d1 * 0.23 + V((s * 0.083, 0.005, 0))                                   # cargo pocket + flap
    B.box("SA_Camo", f"{nm}UpperLeg", pc, (0.03, 0.12, 0.14))
    B.box("SA_Camo", f"{nm}UpperLeg", pc + V((s * 0.004, 0, 0.07)), (0.034, 0.125, 0.025))
    B.box("SA_CamoGear", f"{nm}UpperLeg", hp + d1 * 0.12 + V((0, 0.093, 0)), (0.1, 0.012, 0.07))  # thigh pocket
    # knee pad: hard cap over soft pad + strap (rigid to the shin so it stays on the knee)
    B.ell("SA_Canvas", f"{nm}LowerLeg", kn + V((0, 0.052, -0.01)), (0.054, 0.033, 0.072), u=8, v=6)
    B.ell("SA_Canvas", f"{nm}LowerLeg", kn + V((0, 0.068, -0.015)), (0.04, 0.022, 0.05), u=8, v=5)
    B.tube("SA_Rubber", f"{nm}LowerLeg", [kn + d2 * 0.05, kn + d2 * 0.072], [(0.063, 0.066)] * 2, seg=10,
           caps=False)
    # boot: shaft, foot, toe cap, sole + heel, laces (rigid to the foot except the shaft top)
    fb = f"{nm}Foot"
    B.loftz("SA_Canvas", {f"{nm}LowerLeg": 0.6, fb: 0.4}, [(an.z + 0.11, 0.053, 0.058, an.y, 1.0),
                                                           (an.z + 0.045, 0.052, 0.062, an.y, 1.0)], seg=10, cx=an.x)
    B.loftz("SA_Canvas", fb, [(0.026, 0.052, 0.138, an.y + 0.052, 0.6), (0.085, 0.047, 0.122, an.y + 0.042, 0.65),
                              (0.115, 0.042, 0.075, an.y + 0.012, 0.85)], seg=12, cx=an.x)
    B.loftz("SA_Rubber", fb, [(0.0, 0.055, 0.143, an.y + 0.052, 0.55), (0.028, 0.056, 0.145, an.y + 0.052, 0.55)],
            seg=12, cx=an.x)
    B.box("SA_Canvas", fb, (an.x, an.y + 0.135, 0.045), (0.086, 0.06, 0.042))
    for k in range(3):
        B.box("SA_Rubber", fb, (an.x, an.y + 0.09 - k * 0.03, 0.098 + k * 0.012), (0.05, 0.008, 0.006))
# drop-leg pistol holster on the right thigh
B.box("SA_Rubber", "RightUpperLeg", HIP[1] + V((0.115, 0.02, -0.17)), (0.035, 0.07, 0.17))
B.box("SA_Rubber", "RightUpperLeg", HIP[1] + V((0.11, 0.04, -0.07)), (0.03, 0.05, 0.06))

body = B.to_object("Rifleman_Body")

# ---------------------------------------------------------------- rifle (generic modern carbine, original), local frame
R = Builder(["Rifle"])
RW = "Rifle"
R.box("SA_Rubber", RW, (0, 0.012, -0.025), (0.042, 0.025, 0.13))
R.box("SA_Metal", RW, (0, 0.07, -0.02), (0.038, 0.1, 0.11))
R.box("SA_Metal", RW, (0, 0.07, 0.04), (0.03, 0.12, 0.03), (0.15, 0, 0))
R.cyl("SA_Metal", RW, (0, 0.15, 0.01), 0.016, 0.14, (-PI / 2, 0, 0), seg=6)
R.box("SA_Metal", RW, (0, 0.32, 0.015), (0.045, 0.22, 0.05))
R.box("SA_Metal", RW, (0, 0.31, -0.03), (0.04, 0.17, 0.045))
R.box("SA_Metal", RW, (0, 0.36, -0.08), (0.036, 0.055, 0.07), (0.15, 0, 0))
R.box("SA_Rubber", RW, (0, 0.255, -0.085), (0.032, 0.035, 0.09), (0.35, 0, 0))
for k in range(4):                                                     # coyote polymer magazine
    R.box("SA_Canvas", RW, (0, 0.375 + k * 0.012, -0.135 - k * 0.04), (0.03, 0.065, 0.046), (0.15 + k * 0.1, 0, 0))
R.cyl("SA_Metal", RW, (0, 0.565, 0.008), 0.03, 0.27, (-PI / 2, 0, 0), seg=8)
R.box("SA_Metal", RW, (0, 0.45, 0.044), (0.022, 0.5, 0.012))
R.cyl("SA_Metal", RW, (0, 0.78, 0.008), 0.009, 0.18, (-PI / 2, 0, 0), seg=6)
R.cyl("SA_Metal", RW, (0, 0.875, 0.008), 0.015, 0.06, (-PI / 2, 0, 0), seg=6)
R.box("SA_Rubber", RW, (0, 0.62, -0.04), (0.022, 0.03, 0.06))
R.box("SA_Metal", RW, (0, 0.335, 0.065), (0.03, 0.06, 0.02))                          # optic
R.box("SA_Metal", RW, (0, 0.335, 0.095), (0.044, 0.11, 0.045))
R.cyl("SA_Metal", RW, (0, 0.40, 0.098), 0.022, 0.035, (-PI / 2, 0, 0), seg=8)
R.cyl("SA_Glass", RW, (0, 0.418, 0.098), 0.018, 0.004, (-PI / 2, 0, 0), seg=8)
R.box("SA_Metal", RW, (0.028, 0.335, 0.095), (0.012, 0.03, 0.02))
R.box("SA_Metal", RW, (0, 0.69, 0.06), (0.012, 0.01, 0.022))
R.box("SA_Metal", RW, (-0.033, 0.66, 0.008), (0.012, 0.04, 0.02))                      # weapon light
rifle = R.to_object("Rifle")
rifle.vertex_groups.clear()
MUZZLE_LOCAL = V((0, 0.905, 0.008))

# =============================================================================== armature
arm_data = bpy.data.armatures.new("Armature")
arm = bpy.data.objects.new("Armature", arm_data); scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for b in BONES:
    h, t, z = REST_DEF[b]
    eb = arm_data.edit_bones.new(b)
    eb.head, eb.tail = h, t
    eb.align_roll(REST[b].col[2].to_3d())
for b in BONES:
    if PARENT[b]:
        arm_data.edit_bones[b].parent = arm_data.edit_bones[PARENT[b]]
        arm_data.edit_bones[b].use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")
err = max(max(abs(x) for row in (arm_data.bones[b].matrix_local - REST[b]) for x in row) for b in BONES)
assert err < 1e-4, f"rest frame mismatch {err}"
REST = {b: arm_data.bones[b].matrix_local.copy() for b in BONES}

body.parent = arm
mod = body.modifiers.new("Armature", "ARMATURE"); mod.object = arm
rifle.parent = arm; rifle.parent_type = "BONE"; rifle.parent_bone = "RightHand"
bpy.context.view_layer.update()
rifle.matrix_world = RIFLE_REST
muzzle = bpy.data.objects.new("Muzzle", None); scene.collection.objects.link(muzzle)
muzzle.empty_display_size = 0.05
muzzle.parent = rifle; muzzle.location = MUZZLE_LOCAL
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
arm.animation_data_create()

# =============================================================================== pose solver
def T(v):
    return Matrix.Translation(v)


def R4(e):
    return Euler(e, "XYZ").to_matrix().to_4x4()


def place_foot(cx, cy, lift, pitch, yaw):
    """Ankle position + rotation so the pivot (heel if toe-up, ball if heel-up) sits at (cx, cy[+offset], lift)."""
    Rz = Matrix.Rotation(yaw, 3, "Z")
    Rm = Rz @ Matrix.Rotation(pitch, 3, "X")
    off = HEEL_OFF if pitch >= 0 else TOE_OFF
    pivot = V((cx, cy, lift + 0.095)) + Rz @ off
    return {"ankle": pivot - Rm @ off, "q": Rm.to_quaternion()}


def base_pose():
    return {
        "hips_pos": V((0, 0.0, 0.958)), "hips_rot": V((0, 0, 0)),
        "spine": V((0, 0, 0)), "chest": V((0, 0, 0)), "neck": V((0, 0, 0)), "head": V((0, 0, 0)),
        "rifle_off": V((0, 0, 0)), "rifle_rot": V((0, 0, 0)),
        "aim": 0.0, "aim_yaw": 0.0, "aim_pitch": 0.0, "aim_pocket": V((0.115, 0.12, 1.47)), "recoil": 0.0,
        "foot": {1: place_foot(0.115, -0.03, 0, 0, D(-9)), -1: place_foot(-0.115, 0.06, 0, 0, D(7))},
        "knee_pole": {1: V((0.12, 1, 0.1)), -1: V((-0.12, 1, 0.1))},
        "elbow_pole": {1: V((0.3, -0.2, -0.3)), -1: V((-0.3, 0.05, -0.4))},
        "lgrip": 1.0, "lfree": V((-0.30, 0.06, 1.02)), "lfree_q": Quaternion(),
        "rw": 0.0, "rifle_wp": V((0, 0, 0)), "rifle_wq": Quaternion(),
    }


def lerp(a, b, t):
    if isinstance(a, dict):
        return {k: lerp(a[k], b[k], t) for k in a}
    if isinstance(a, Quaternion):
        return a.slerp(b, t)
    if isinstance(a, Vector):
        return a.lerp(b, t)
    return a + (b - a) * t


IK_ERR = {}


def solve(p):
    """Pose params -> armature-space matrix per bone, plus the rifle world matrix."""
    M = {}
    M["Hips"] = T(p["hips_pos"]) @ R4(p["hips_rot"]) @ T(-HIPS_H) @ REST["Hips"]
    for b, key in (("Spine", "spine"), ("Chest", "chest"), ("Neck", "neck"), ("Head", "head")):
        pb = PARENT[b]; h = REST[b].translation
        M[b] = M[pb] @ REST[pb].inverted() @ T(h) @ R4(p[key]) @ T(-h) @ REST[b]
    C = M["Chest"] @ REST["Chest"].inverted()        # rest-world -> posed-world, rigid with the chest
    Hx = M["Hips"] @ REST["Hips"].inverted()
    # rifle
    Wr = C @ T(BUTT) @ R4(p["rifle_rot"]) @ T(-BUTT) @ T(p["rifle_off"]) @ RIFLE_REST

    def blend(a, b, t):
        return T(a.translation.lerp(b.translation, t)) @ \
            a.to_quaternion().slerp(b.to_quaternion(), t).to_matrix().to_4x4()
    if p["aim"] > 0:
        aimM = Matrix.Rotation(p["aim_yaw"], 4, "Z") @ Matrix.Rotation(p["aim_pitch"], 4, "X")
        aimM.translation = C @ p["aim_pocket"]
        Wr = blend(Wr, aimM, p["aim"])
    if p["rw"] > 0:
        Wr = blend(Wr, T(p["rifle_wp"]) @ p["rifle_wq"].to_matrix().to_4x4(), p["rw"])
    rc = p["recoil"]
    if rc:
        Wr = Wr @ T(V((0, -0.035 * rc, 0.004 * rc))) @ Matrix.Rotation(D(4.0) * rc, 4, "X")
    toR = Wr @ RIFLE_REST.inverted()
    # arms
    for s, nm in SIDE.items():
        hand = toR @ REST[f"{nm}Hand"]
        if s == -1 and p["lgrip"] < 1.0:
            free = C @ T(p["lfree"]) @ p["lfree_q"].to_matrix().to_4x4() @ T(-WRIST[-1]) @ REST["LeftHand"]
            q = free.to_quaternion().slerp(hand.to_quaternion(), p["lgrip"])
            hand = T(free.translation.lerp(hand.translation, p["lgrip"])) @ q.to_matrix().to_4x4()
        sh = C @ SH[s]
        tgt = hand.translation
        pole = C @ (SH[s] + p["elbow_pole"][s])
        el, reach = ik(sh, tgt, UA, FA, pole)
        IK_ERR[nm + "Arm"] = max(IK_ERR.get(nm + "Arm", 0), (reach - tgt).length)
        bd = bend(sh, el, reach)
        M[f"{nm}UpperArm"] = frame(sh, el, bd)
        M[f"{nm}LowerArm"] = frame(el, reach, bd)
        hand.translation = reach
        M[f"{nm}Hand"] = hand
    # legs
    for s, nm in SIDE.items():
        hp = Hx @ HIP[s]
        f = p["foot"][s]
        qm = f["q"].to_matrix()
        sole = min((qm @ V((sx, sy, -0.095))).z for sx in (-0.05, 0.05) for sy in (-0.09, 0.19))
        tgt = f["ankle"].copy()
        tgt.z = max(tgt.z, -sole)          # sole contact clamp: no part of the boot sole below the ground
        kn, reach = ik(hp, tgt, THIGH, SHIN, hp + p["knee_pole"][s])
        IK_ERR[nm + "Leg"] = max(IK_ERR.get(nm + "Leg", 0), (reach - tgt).length)
        bd = bend(hp, kn, reach)
        M[f"{nm}UpperLeg"] = frame(hp, kn, bd)
        M[f"{nm}LowerLeg"] = frame(kn, reach, bd)
        M[f"{nm}Foot"] = T(reach) @ qm.to_4x4() @ T(-ANKLE[s]) @ REST[f"{nm}Foot"]
    M["_C"] = C
    return M, Wr


def apply_pose(p):
    """Write solved bone transforms into pose-bone channels (matrix_basis); returns the solve result."""
    M, Wr = solve(p)
    out = {}
    for b in BONES:
        par = PARENT[b]
        if par:
            bm_ = (REST[par].inverted() @ REST[b]).inverted() @ (M[par].inverted() @ M[b])
        else:
            bm_ = REST[b].inverted() @ M[b]
        out[b] = bm_.decompose()
    return out, M


GROUP_VERTS = {}


def pose_minz(p, objs=None, group=None):
    """Lowest world Z of the deformed body (and optionally the rifle) for one pose, without keyframes.
    group: only vertices weighted >= 0.5 to that bone."""
    if group and group not in GROUP_VERTS:
        gi = body.vertex_groups[group].index
        GROUP_VERTS[group] = [v.index for v in body.data.vertices if any(g.group == gi and g.weight >= 0.5
                                                                          for g in v.groups)]
    arm.animation_data.action = None
    dec, _ = apply_pose(p)
    for b, (loc, rot, _) in dec.items():
        pb = arm.pose.bones[b]; pb.location = loc; pb.rotation_quaternion = rot; pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    zs = []
    for o in (objs or [body]):
        ev = o.evaluated_get(dg); me = ev.to_mesh(); mw = ev.matrix_world
        vs = me.vertices if not group or o != body else [me.vertices[i] for i in GROUP_VERTS[group]]
        zs.append(min((mw @ v.co).z for v in vs)); ev.to_mesh_clear()
    return min(zs)


# =============================================================================== actions
def smoothstep(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def act_idle(t):
    p = base_pose()
    b = math.sin(2 * PI * t)
    p["chest"] = V((D(1.2) * b, 0, 0)); p["spine"] = V((D(0.4) * b, 0, 0))
    p["head"] = V((D(-1.0) * b, 0, D(3) * math.sin(2 * PI * t + 1.0)))
    p["hips_pos"] = p["hips_pos"] + V((0.008 * math.sin(2 * PI * t + 0.5), 0, 0.003 * b))
    p["rifle_rot"] = V((D(1.5) * math.sin(2 * PI * t + 0.6), 0, 0))
    return p


def gait(p, t, v, Tc, duty, lift, hz, bob, sway, width, heel, toe, shift, yaw_amp, swing_tan=0.25):
    L = v * Tc * duty
    for s, ph in ((1, t % 1.0), (-1, (t + 0.5) % 1.0)):
        if ph < duty:
            u = ph / duty
            y = L / 2 - u * L + shift
            z = 0.0
            pitch = heel * (1 - u / 0.18) if u < 0.18 else (-toe * ((u - 0.62) / 0.38) ** 1.5 if u > 0.62 else 0.0)
        else:
            u = (ph - duty) / (1 - duty)
            m = -L * (1 - duty) / duty * swing_tan        # hermite tangents (partly match the stance speed)
            h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
            y = h00 * (-L / 2) + h10 * m + h01 * (L / 2) + h11 * m + shift
            z = lift * math.sin(PI * u) ** 1.3
            pitch = -toe * (1 - u) ** 2 * (1 - 2 * u if u < 0.5 else 0) + heel * smoothstep((u - 0.55) / 0.45) - \
                toe * 0.5 * math.sin(PI * min(u / 0.6, 1.0))
        p["foot"][s] = place_foot(s * width, y, z, pitch, D(-6) * s)
    p["hips_pos"] = V((sway * math.cos(2 * PI * (t - duty / 2)), 0.0, hz - bob * math.cos(4 * PI * (t - duty / 2))))
    yaw = yaw_amp * math.cos(2 * PI * t)
    p["hips_rot"] = p["hips_rot"] + V((0, D(2.0) * math.cos(2 * PI * (t - duty / 2)), yaw))
    p["spine"] = p["spine"] + V((0, 0, -yaw * 0.6))
    p["chest"] = p["chest"] + V((0, 0, -yaw * 0.5))
    return p


WALK = dict(v=1.4, Tc=1.0, duty=0.6)
RUN = dict(v=4.5, Tc=0.7, duty=0.32)


def act_walk(t):
    p = base_pose()
    gait(p, t, WALK["v"], WALK["Tc"], WALK["duty"], lift=0.085, hz=0.902, bob=0.018, sway=0.018, width=0.105,
         heel=D(16), toe=D(28), shift=-0.03, yaw_amp=D(6))
    p["spine"] += V((D(-3), 0, 0)); p["head"] += V((D(3), 0, 0))
    p["rifle_rot"] = V((D(2.5) * math.sin(4 * PI * t), 0, D(1.5) * math.sin(2 * PI * t)))
    return p


def act_run(t):
    p = base_pose()
    gait(p, t, RUN["v"], RUN["Tc"], RUN["duty"], lift=0.24, hz=0.885, bob=-0.035, sway=0.012, width=0.09,
         heel=D(10), toe=D(42), shift=-0.10, yaw_amp=D(9), swing_tan=0.35)
    p["hips_rot"] += V((D(-9), 0, 0))
    p["spine"] += V((D(-7), 0, 0)); p["chest"] += V((D(-4), 0, 0)); p["neck"] += V((D(8), 0, 0))
    p["head"] += V((D(10), 0, 0))
    p["rifle_rot"] = V((D(8) + D(4) * math.sin(4 * PI * t + 0.8), D(-6), D(-4) + D(3) * math.sin(2 * PI * t)))
    p["rifle_off"] = V((0.0, 0.03, 0.06))
    p["elbow_pole"] = {1: V((0.35, -0.3, -0.25)), -1: V((-0.35, -0.05, -0.35))}
    return p


def aim_pose(p):
    p["hips_rot"] = V((0, 0, D(-18)))
    p["hips_pos"] = V((-0.01, -0.02, 0.94))
    p["spine"] = V((D(-4), 0, D(-8))); p["chest"] = V((D(-4), D(2), D(-9)))
    p["neck"] = V((D(-6), D(4), D(10))); p["head"] = V((D(-10), D(14), D(16)))
    p["aim"] = 1.0
    p["aim_pocket"] = V((0.035, 0.13, 1.50))
    p["foot"] = {1: place_foot(0.16, -0.17, 0, 0, D(-40)), -1: place_foot(-0.12, 0.17, 0, 0, D(-12))}
    p["knee_pole"] = {1: V((0.6, 1, 0.1)), -1: V((0.1, 1, 0.1))}
    p["elbow_pole"] = {1: V((0.45, -0.1, -0.25)), -1: V((-0.15, 0.1, -0.5))}
    return p


def act_aim(t):
    p = aim_pose(base_pose())
    b = math.sin(2 * PI * t)
    p["chest"] += V((D(0.8) * b, 0, 0))
    p["aim_pitch"] = D(0.5) * math.sin(2 * PI * t + 0.4)
    p["aim_yaw"] = D(0.4) * math.sin(4 * PI * t)
    return p


def recoil_curve(t):
    """t in [0,1): fast kick (first 12%), exponential-ish recovery back to 0 at the loop end."""
    if t < 0.12:
        return math.sin(0.5 * PI * t / 0.12)
    u = (t - 0.12) / 0.88
    return (1 - smoothstep(u)) * (1 - u) ** 0.5


def act_fire(t):
    p = aim_pose(base_pose())
    r = recoil_curve(t)
    p["recoil"] = r
    p["chest"] += V((D(1.8) * r, 0, D(0.6) * r)); p["head"] += V((D(1.2) * r, 0, 0))
    p["hips_pos"] = p["hips_pos"] + V((0, -0.004 * r, 0))
    return p


KNEEL_KZ = 0.075        # knee joint height when kneeling; calibrated below so the knee pad rests on the ground


def kneel_pose(p):
    p["hips_rot"] = V((D(4), 0, D(-22)))
    hp = V((0.0, -0.06, 0.5))
    hr = T(hp) @ R4(p["hips_rot"]) @ T(-HIPS_H) @ HIP[1]
    hp.z += KNEEL_KZ + math.sqrt(THIGH ** 2 - 0.10 ** 2) - hr.z
    p["hips_pos"] = hp
    p["spine"] = V((D(-10), 0, D(-6))); p["chest"] = V((D(-6), D(2), D(-8)))
    p["neck"] = V((D(-4), D(4), D(8))); p["head"] = V((D(-8), D(14), D(15)))
    p["aim"] = 1.0
    p["aim_pocket"] = V((0.035, 0.13, 1.50))
    # right knee on the ground, toes behind; left foot planted forward, shin vertical
    hr = T(hp) @ R4(p["hips_rot"]) @ T(-HIPS_H) @ HIP[1]
    K = V((hr.x, hr.y + 0.10, KNEEL_KZ))
    q = (Matrix.Rotation(D(-8), 3, "Z") @ Matrix.Rotation(D(-72), 3, "X")).to_quaternion()
    az = -(q.to_matrix() @ TOE_OFF).z                  # toes tucked under, tip on the ground
    ank = K + V((0.01, -math.sqrt(SHIN ** 2 - (az - K.z) ** 2), az - K.z))
    p["foot"] = {1: {"ankle": ank, "q": q}, -1: place_foot(-0.16, 0.30, 0, 0, D(-14))}
    p["knee_pole"] = {1: V((0.05, 1, -0.6)), -1: V((-0.15, 1, 0.6))}
    p["elbow_pole"] = {1: V((0.45, -0.1, -0.25)), -1: V((-0.1, 0.2, -0.5))}
    return p


def act_crouch_fire(t):
    p = kneel_pose(base_pose())
    r = recoil_curve(t)
    p["recoil"] = r
    p["chest"] += V((D(1.8) * r, 0, D(0.6) * r)); p["head"] += V((D(1.2) * r, 0, 0))
    return p


def die_keys():
    k0 = base_pose()
    k1 = base_pose()                       # hit: torso snaps back, rifle muzzle rises, left hand starts to let go
    k1["hips_pos"] = V((0.0, -0.04, 0.95)); k1["spine"] = V((D(8), 0, D(4))); k1["chest"] = V((D(10), D(-4), D(5)))
    k1["head"] = V((D(18), 0, D(-8))); k1["rifle_rot"] = V((D(15), 0, 0)); k1["lgrip"] = 0.6
    k1["lfree"] = V((-0.32, 0.12, 1.05))
    k2 = base_pose()                       # knees buckle, upper body slumps forward
    k2["hips_pos"] = V((0.02, -0.02, 0.70)); k2["hips_rot"] = V((D(-12), D(4), D(6)))
    k2["spine"] = V((D(-14), 0, D(4))); k2["chest"] = V((D(-12), D(-4), D(4))); k2["head"] = V((D(-20), D(-6), D(10)))
    k2["rifle_rot"] = V((D(20), D(10), D(-10))); k2["lgrip"] = 0.0
    k2["lfree"] = V((-0.34, 0.10, 1.02)); k2["lfree_q"] = Quaternion(V((0, 1, 0)), D(-20))
    k2["foot"] = {1: place_foot(0.12, -0.04, 0, D(-15), D(-12)), -1: place_foot(-0.12, 0.04, 0, 0, D(10))}
    k2["knee_pole"] = {1: V((0.2, 1, -0.1)), -1: V((-0.2, 1, -0.1))}
    k3 = lerp(k2, k2, 0)                   # on the knees, toppling forward
    k3["hips_pos"] = V((0.03, 0.10, 0.46)); k3["hips_rot"] = V((D(-40), D(6), D(8)))
    k3["spine"] = V((D(-12), 0, D(4))); k3["chest"] = V((D(-8), D(-4), D(4))); k3["head"] = V((D(15), D(-6), D(25)))
    k3["rifle_rot"] = V((D(45), D(25), D(-30))); k3["lfree"] = V((-0.40, 0.30, 1.30))
    k3["foot"] = {1: place_foot(0.13, -0.42, 0.0, D(-70), D(-10)), -1: place_foot(-0.13, -0.36, 0.0, D(-70), D(10))}
    k3["knee_pole"] = {1: V((0.1, 1, -0.6)), -1: V((-0.1, 1, -0.6))}
    k4 = lerp(k3, k3, 0)                   # impact: face down, head turned to the side, legs trailing
    k4["hips_pos"] = V((0.04, 0.10, 0.15)); k4["hips_rot"] = V((D(-86), D(10), D(8)))
    k4["spine"] = V((D(4), 0, D(3))); k4["chest"] = V((D(5), D(-3), D(3)))
    k4["neck"] = V((D(10), 0, D(25))); k4["head"] = V((D(10), D(-10), D(45)))
    k4["lfree"] = V((-0.30, -0.02, 1.0)); k4["lfree_q"] = Quaternion(V((0, 1, 0)), D(-60))
    k4["elbow_pole"] = {1: V((0.4, -0.1, -0.1)), -1: V((-0.3, -0.2, -0.2))}
    k4["foot"] = {1: place_foot(0.24, -1.06, 0.0, D(-85), D(-25)), -1: place_foot(-0.14, -1.02, 0.0, D(-80), D(15))}
    k4["knee_pole"] = {1: V((0.3, 0.2, -1.0)), -1: V((-0.2, 0.2, -1.0))}
    k5 = lerp(k4, k4, 0)                   # settle
    k5["hips_pos"] = k4["hips_pos"] + V((0.0, 0.02, 0.0)); k5["head"] = V((D(8), D(-10), D(50)))
    k5["chest"] = V((D(3), D(-3), D(3)))

    def lay_rifle(k):                      # rifle flat on its right side next to the right shoulder, hand on top
        sh = solve(k)[0]["RightUpperArm"].translation
        yd = V((0.45, 1, 0)).normalized(); zd = V((-1, 0.45, 0)).normalized(); xd = yd.cross(zd)
        rq = Matrix((xd, yd, zd)).transposed().to_quaternion()
        g = V((sh.x + 0.24, sh.y + 0.10, 0.0))
        org = g - yd * 0.255 + zd * 0.085
        org.z = 0.036
        k["rw"], k["rifle_wp"], k["rifle_wq"] = 1.0, org, rq

    for k in (k4, k5):                     # alternate rifle placement and ground contact until both settle
        for _ in range(4):
            lay_rifle(k)
            k["hips_pos"].z -= pose_minz(k)
        lay_rifle(k)
    k3["rifle_wp"], k3["rifle_wq"] = k4["rifle_wp"].copy(), k4["rifle_wq"].copy()   # only the blend weight moves
    return [(0.0, k0), (0.12, k1), (0.45, k2), (0.78, k3), (1.02, k4), (1.25, k5), (1.5, k5)]


for _ in range(3):
    KNEEL_KZ -= pose_minz(kneel_pose(base_pose()), group="RightLowerLeg")
DIE_KEYS = die_keys()


def act_die(t):
    s = t * 1.5
    for (ta, a), (tb, b) in zip(DIE_KEYS, DIE_KEYS[1:]):
        if s <= tb:
            u = (s - ta) / (tb - ta)
            u = u * u if ta >= 0.45 and ta < 1.0 else smoothstep(u)    # gravity-like acceleration while falling
            return lerp(a, b, u)
    return DIE_KEYS[-1][1]


ACTIONS = [  # name, function(t in [0,1]), length s, loop
    ("idle", act_idle, 3.0, True), ("walk", act_walk, WALK["Tc"], True), ("run", act_run, RUN["Tc"], True),
    ("aim", act_aim, 2.0, True), ("fire", act_fire, 0.3, True), ("crouch_fire", act_crouch_fire, 0.3, True),
    ("die", act_die, 1.5, False)]

# =============================================================================== bake
REPORT = {}
for name, fn, length, loop in ACTIONS:
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    nf = round(length * FPS)
    prevq = {}
    IK_ERR.clear()
    for f in range(nf + 1):
        t = f / nf
        if loop and f == nf:
            t = 0.0
        p = fn(t)
        if name == "die":                  # ground solver: lift the hips if any part of the body would sink,
            for _ in range(6):             # and swing the muzzle up if the rifle would dig into the ground
                m = pose_minz(p)
                if m > -0.0005:
                    break
                p["hips_pos"].z -= m * 1.1
            for _ in range(12):
                if pose_minz(p, objs=[rifle]) > -0.0005:
                    break
                p["rifle_rot"] = p["rifle_rot"] + V((D(5) * (1 - p["rw"]), 0, 0))
                p["rifle_wp"] = p["rifle_wp"] + V((0, 0, 0.01 * p["rw"]))
        arm.animation_data.action = act
        dec, _ = apply_pose(p)
        for b in BONES:
            pb = arm.pose.bones[b]
            loc, rot, _ = dec[b]
            if b in prevq and prevq[b].dot(rot) < 0:
                rot.negate()
            prevq[b] = rot
            pb.location = loc; pb.rotation_quaternion = rot; pb.scale = (1, 1, 1)
            pb.keyframe_insert("location", frame=f, group=b)
            pb.keyframe_insert("rotation_quaternion", frame=f, group=b)
    act.frame_range = (0, nf)
    act.use_frame_range = True
    act.use_cyclic = loop
    REPORT[name] = {"frames": nf + 1, "length_s": nf / FPS, "loop": loop,
                    "ik_err_mm": {k: round(v * 1000, 1) for k, v in IK_ERR.items()}}
arm.animation_data.action = bpy.data.actions["idle"]
scene.frame_start, scene.frame_end = 0, 90


# =============================================================================== verification (ground contact)
def mesh_minz(frame_no):
    scene.frame_set(frame_no)
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in (body, rifle):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        zs = [(mw @ v.co).z for v in me.vertices]
        ev.to_mesh_clear()
        out.append(min(zs))
    return out


for name, fn, length, loop in ACTIONS:
    arm.animation_data.action = bpy.data.actions[name]
    nf = round(length * FPS)
    mins = [mesh_minz(f) for f in range(0, nf + 1)]
    REPORT[name]["body_min_z_mm"] = [round(min(m[0] for m in mins) * 1000, 1), round(max(m[0] for m in mins) * 1000, 1)]
    REPORT[name]["rifle_min_z_mm"] = round(min(m[1] for m in mins) * 1000, 1)
    if name == "die":
        REPORT[name]["final_body_min_z_mm"] = round(mins[-1][0] * 1000, 1)
REPORT["stride_m"] = {"walk": round(WALK["v"] * WALK["Tc"], 3), "run": round(RUN["v"] * RUN["Tc"], 3)}
REPORT["speed_mps"] = {"walk": WALK["v"], "run": RUN["v"]}
REPORT["triangles"] = {o.name: sum(len(p_.vertices) - 2 for p_ in o.data.polygons) for o in (body, rifle)}
REPORT["triangles"]["total"] = sum(REPORT["triangles"].values())
arm.animation_data.action = bpy.data.actions["idle"]
scene.frame_set(0)

# =============================================================================== smooth shading + export
for o in (body, rifle):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
glb = os.path.join(OUT, "rifleman.glb")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=False, export_animations=True,
                          export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_range=False,
                          export_anim_single_armature=True, export_reset_pose_bones=True)
print(json.dumps(REPORT, indent=1))
with open(os.path.join(OUT, "rifleman_report.json"), "w") as fh:
    json.dump(REPORT, fh, indent=1)


# =============================================================================== previews
def previews(d):
    os.makedirs(d, exist_ok=True)
    from PIL import Image, ImageDraw
    ground = bpy.data.meshes.new("ground")
    bmg = bmesh.new(); bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=60); bmg.to_mesh(ground); bmg.free()
    g = bpy.data.objects.new("ground", ground); scene.collection.objects.link(g)
    gm = mat("ground", (0.36, 0.34, 0.30), 1.0); ground.materials.append(gm)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); scene.collection.objects.link(sun)
    sun.data.energy = 3.2; sun.rotation_euler = (D(40), D(10), D(-35)); sun.data.angle = D(8)
    MATS["SA_Team"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.2, 0.45, 1)
    world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.6, 0.68, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam)
    scene.camera = cam
    scene.view_settings.view_transform = "Standard"

    def look(loc, target):
        cam.location = loc
        cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    def render(path, res):
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)

    arm.animation_data.action = bpy.data.actions["idle"]; scene.frame_set(0)
    scene.render.engine = "CYCLES"; scene.cycles.samples = 24; scene.cycles.device = "CPU"
    scene.cycles.use_denoising = False
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 2.0
    for nm, loc in (("front", (0, 6, 0.95)), ("side", (6, 0, 0.95)), ("back", (0, -6, 0.95))):
        look(loc, (0, 0, 0.95)); render(os.path.join(d, f"pilot3d_rifleman_{nm}.png"), (480, 520))
    cam.data.ortho_scale = 1.3; look((0, 0.0001, 6), (0, 0, 0)); render(os.path.join(d, "pilot3d_rifleman_top.png"),
                                                                       (480, 480))
    cam.data.type = "PERSP"; cam.data.lens = 85
    el, az, dist = D(52), D(35), 5.2
    loc = (dist * math.cos(el) * math.sin(az), dist * math.cos(el) * math.cos(az), 0.85 + dist * math.sin(el))
    look(loc, (0, 0, 0.85)); render(os.path.join(d, "pilot3d_rifleman_rts.png"), (560, 560))
    # animation strip (Cycles, low samples, 3/4 side view)
    scene.cycles.samples = 10
    cam.data.type = "ORTHO"
    tiles, cols = [], 8
    tmp = os.path.join(d, "_strip_tmp.png")
    for name, fn, length, loop in ACTIONS:
        arm.animation_data.action = bpy.data.actions[name]
        nf = round(length * FPS)
        tgt = V((0, 0.3, 0.55)) if name == "die" else V((0, 0, 0.75))
        cam.data.ortho_scale = 2.7 if name == "die" else 2.3
        look(tgt + V((5.0, 3.0, 1.45)), tgt)
        row = []
        for i in range(cols):
            f = round(i * nf / (cols if loop else cols - 1))
            scene.frame_set(f)
            render(tmp, (200, 240))
            row.append((Image.open(tmp).convert("RGB").copy(), f))
        tiles.append((name, row))
    os.remove(tmp)
    W, H, lab = 200, 240, 110
    sheet = Image.new("RGB", (lab + cols * W, len(tiles) * H), (30, 30, 30))
    dr = ImageDraw.Draw(sheet)
    for r, (name, row) in enumerate(tiles):
        dr.text((8, r * H + H // 2 - 6), name, fill=(240, 240, 240))
        for c, (im, f) in enumerate(row):
            sheet.paste(im, (lab + c * W, r * H))
            dr.text((lab + c * W + 4, r * H + 4), f"f{f}", fill=(20, 20, 20))
    sheet.save(os.path.join(d, "pilot3d_rifleman_anims.png"))


if PREV:
    previews(PREV)
print("RIFLEMAN_RIGGED OK", REPORT["triangles"])
