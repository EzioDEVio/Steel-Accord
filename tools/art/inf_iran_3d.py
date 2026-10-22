"""Steel Accord - Iranian infantry roster in 3D, on the SAME shared infantry kit as the U.S. roster (inf_kit.py).

Run:  python3 tools/art/inf_iran_3d.py <role> godot/assets/units3d/<role> [--previews docs/screens] [--faces <tiles dir>]
      python3 tools/art/inf_iran_3d.py faces_sheet <tiles dir> docs/screens/ir_faces.png      (combine face tiles)
Roles: ir_rifleman ir_rpg ir_mg ir_sniper ir_engineer ir_medic irgc_sf ir_paratrooper

Same as the U.S. roster: the 17-bone SkeletonProfileHumanoid skeleton and rest pose, the gait / aim / kneel / die
solvers, action names (+ role extras), 30 fps, metres, origin on the ground between the feet, Blender +Y forward
(Godot -Z), hand item rigid on RightHand with a `Muzzle` empty, `SA_Team` neutral grey patches for team tint.
inf_kit.py is NOT modified: this script only uses its public hooks (Role, body_extra, extra_objects, after_bake,
POSE_EXTRA / AIM_EXTRA / DIE_HOOK / GROUND_SOLVE) and swaps the camouflage generator (K.make_camo) for its own builds.

Face variants (all roles): the body has a clean-shaven face (eyes, brows, lip line). Two SEPARATE skinned meshes,
weighted 100 % to `Head`, sit on it:  `Beard` (short full or trimmed, per role) and `Moustache`.
   bearded = Beard + Moustache visible | moustache only = hide Beard | clean-shaven = hide both.
Flags: a small Iranian-flag shoulder patch (own texture `SA_FlagIR`, drawn by prop_flag_3d.flag_image) on the left
upper sleeve. Camouflage is generated from colours only (no photos): regular army = disruptive woodland/desert
blotches; IRGC = a digital (pixel) pattern. All weapons are generic procedural silhouettes (AK-, G3-, PKM-, SVD-,
RPG-7-family shapes), not copies of any specific product design.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inf_kit as K                  # import FIRST (pins PYTHONHASHSEED via re-exec)
import numpy as np

MODE = sys.argv.pop(1)


# =============================================================================== faces sheet (no bpy work)
def faces_sheet(tiles, out):
    from PIL import Image, ImageDraw
    rows = [r for r in ROLE_ORDER if os.path.exists(os.path.join(tiles, f"face_{r}_full.png"))]
    cols = ("full", "moustache", "shaven")
    t0 = Image.open(os.path.join(tiles, f"face_{rows[0]}_full.png"))
    W, H = t0.size
    lab = 120
    sheet = Image.new("RGB", (lab + 3 * W, 22 + len(rows) * H), (30, 30, 30))
    dr = ImageDraw.Draw(sheet)
    for c, nm in enumerate(("Beard + Moustache", "Moustache only", "clean-shaven (both hidden)")):
        dr.text((lab + c * W + 6, 5), nm, fill=(235, 235, 235))
    for r, role in enumerate(rows):
        dr.text((8, 22 + r * H + H // 2 - 6), role, fill=(235, 235, 235))
        for c, v in enumerate(cols):
            sheet.paste(Image.open(os.path.join(tiles, f"face_{role}_{v}.png")).convert("RGB"), (lab + c * W, 22 + r * H))
    sheet.save(out)
    print("FACES SHEET", out, rows)


ROLE_ORDER = ["ir_rifleman", "ir_rpg", "ir_mg", "ir_sniper", "ir_engineer", "ir_medic", "irgc_sf", "ir_paratrooper"]
if MODE == "faces_sheet":
    faces_sheet(sys.argv[1], sys.argv[2])
    sys.exit(0)

FACES = None
if "--faces" in sys.argv:
    _i = sys.argv.index("--faces"); FACES = sys.argv[_i + 1]; del sys.argv[_i:_i + 2]
OUT, PREV, ONLY_ANIMS = K.parse_args()
ROLE = MODE

import bpy, bmesh
from mathutils import Matrix, Vector as V, Quaternion, Euler
import prop_flag_3d as FL

D = math.radians
PI = math.pi
AXIS = (-PI / 2, 0, 0)                 # cylinder axis along +Y
GRIP = (0, 0.255, -0.085)              # shared pistol-grip position (carbine local frame)

# =============================================================================== palettes (sRGB, chosen by hand)
PAL_ARMY = {"base": (160, 143, 106), "light": (192, 178, 142), "green": (92, 97, 63), "brown": (114, 86, 60),
            "dark": (44, 40, 33)}
PAL_IRGC = {"base": (122, 116, 86), "light": (158, 150, 114), "green": (80, 89, 59), "brown": (107, 85, 60),
            "dark": (50, 48, 39)}


def camo_woodland(path, pal, seed, n=512):
    """Disruptive woodland/desert pattern: large hard-edged, slightly horizontal blotches + small dark branches."""
    rng = np.random.default_rng(seed)
    N, sm = K.periodic_noise, K.smooth
    img = np.zeros((n, n, 3)) + np.array(pal["base"], float)

    def lay(col, mask):
        nonlocal img
        img = img * (1 - mask[..., None]) + np.array(pal[col], float) * mask[..., None]
    lay("light", sm(0.95, 1.01, N(n, 62, 40, rng) + 0.45 * N(n, 16, 11, rng)))
    lay("green", sm(0.26, 0.31, N(n, 92, 56, rng) + 0.5 * N(n, 22, 15, rng)))
    lay("brown", sm(0.58, 0.63, N(n, 80, 48, rng) + 0.5 * N(n, 20, 13, rng)))
    lay("dark", sm(1.18, 1.23, N(n, 44, 18, rng) + 0.55 * N(n, 12, 7, rng)))
    weave = N(n, 0.7, 0.7, rng) * 4.0 + N(n, 3, 3, rng) * 3.0
    img = np.clip(img + weave[..., None], 0, 255).astype(np.uint8)
    from PIL import Image
    Image.fromarray(img, "RGB").save(path)
    return path


def camo_digital(path, pal, seed, n=512, cell=8):
    """IRGC-style digital pattern: blotches quantised to ~0.9 cm square cells, two scales."""
    rng = np.random.default_rng(seed)
    N, sm = K.periodic_noise, K.smooth
    m = n // cell
    img = np.zeros((m, m, 3)) + np.array(pal["base"], float)

    def lay(col, mask):
        nonlocal img
        mask = (mask > 0.5).astype(float)
        img = img * (1 - mask[..., None]) + np.array(pal[col], float) * mask[..., None]
    lay("light", sm(0.9, 1.0, N(m, 4.5, 3.5, rng) + 0.6 * N(m, 1.2, 1.0, rng)))
    lay("green", sm(0.15, 0.25, N(m, 6.0, 4.5, rng) + 0.6 * N(m, 1.5, 1.2, rng)))
    lay("brown", sm(0.55, 0.65, N(m, 5.0, 4.0, rng) + 0.6 * N(m, 1.3, 1.1, rng)))
    lay("dark", sm(1.05, 1.15, N(m, 3.0, 2.0, rng) + 0.7 * N(m, 1.0, 0.8, rng)))
    img = np.kron(img, np.ones((cell, cell, 1)))
    weave = N(n, 0.7, 0.7, rng) * 4.0 + N(n, 3, 3, rng) * 2.5
    img = np.clip(img + weave[..., None], 0, 255).astype(np.uint8)
    from PIL import Image
    Image.fromarray(img, "RGB").save(path)
    return path


CAMO_FN = [camo_woodland]
K.make_camo = lambda path, pal, seed=1977, n=512: CAMO_FN[0](path, pal, seed, n)   # used by K.build


def hair_texture(path, seed=7, n=256):
    """Dark hair albedo: fine vertical strands with a few lighter grey-brown hairs (tiles)."""
    rng = np.random.default_rng(seed)
    N = K.periodic_noise
    s = N(n, 0.6, 9, rng) + 0.5 * N(n, 1.5, 3, rng)
    base = np.array((64, 50, 40), float); hi = np.array((112, 94, 75), float); lo = np.array((30, 23, 18), float)
    t = K.smooth(-1.0, 2.2, s)
    img = lo[None, None] * (1 - t[..., None]) + base * t[..., None]
    g = K.smooth(1.7, 2.3, N(n, 0.5, 6, rng))
    img = img * (1 - g[..., None]) + hi * g[..., None]
    from PIL import Image
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(path)
    return path


def shemagh_texture(path, n=512):
    """Sand cloth with a fine olive check (1.4 cm pitch at the 0.55 m box-projection tile)."""
    y, x = np.mgrid[0:n, 0:n]
    p = 13
    a = ((x % p) < 2) | ((y % p) < 2)
    b = ((x % (p * 4)) < 3) | ((y % (p * 4)) < 3)
    img = np.zeros((n, n, 3)) + np.array((170, 160, 128), float)
    img[a] = (146, 140, 108); img[b] = (118, 116, 88)
    rng = np.random.default_rng(3)
    img += rng.standard_normal((n, n, 1)) * 3
    from PIL import Image
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(path)
    return path


# =============================================================================== materials shared by all roles
COMMON_MATS = {
    "SA_Rig": ((0.15, 0.15, 0.095), 0.9, 0.0),          # olive-drab canvas chest rig / belt pouches (regular army)
    "SA_Wood": ((0.20, 0.085, 0.035), 0.55, 0.0),       # rifle furniture
    "SA_Olive": ((0.13, 0.15, 0.085), 0.7, 0.0),        # launcher warheads, ammo boxes, packs
    "SA_Lip": ((0.30, 0.15, 0.12), 0.6, 0.0),
    "SA_Eye": ((0.03, 0.022, 0.017), 0.25, 0.0),
    "SA_Coyote": ((0.33, 0.27, 0.18), 0.9, 0.0),        # IRGC carrier / gear
    "SA_Brass": ((0.50, 0.33, 0.09), 0.35, 0.9),        # MG belt
    "SA_Webbing": ((0.17, 0.16, 0.11), 0.9, 0.0),       # parachute harness
    "SA_Marking": ((0.55, 0.45, 0.12), 0.6, 0.0),
}
ARMY_OVERRIDES = {"SA_Canvas": ((0.13, 0.095, 0.07), 0.75, 0.0),     # dark brown leather boots / gloves / belt
                  "SA_Skin": ((0.56, 0.38, 0.27), 0.6, 0.0)}
IRGC_OVERRIDES = {"SA_Skin": ((0.56, 0.38, 0.27), 0.6, 0.0)}


def add_textured_mats():
    """Textured materials appended to the kit's material list (called at the start of body_extra)."""
    tmp = OUT
    if "SA_FlagIR" not in K.MATS:
        p = os.path.join(tmp, f"{ROLE}_flagpatch.png")
        from PIL import Image
        Image.fromarray(FL.flag_image("iran", 140, ss=4), "RGB").save(p)
        K.MATS["SA_FlagIR"] = K.mat("SA_FlagIR", (1, 1, 1), 0.8, tex=p)
        K.MATS["SA_Beard"] = K.mat("SA_Beard", (1, 1, 1), 0.8, tex=hair_texture(os.path.join(tmp, f"{ROLE}_hair.png")))
        K.MAT_ORDER[:] = list(K.MATS)


# =============================================================================== head: face features (shaven base)
HC = K.HC_HEAD
CB = V((0.0, 0.065, 1.615))                       # ray centre for the face-hair shells
FACE_ELL = [(HC, V((0.08, 0.094, 0.104))), (HC + V((0, 0.072, -0.058)), V((0.06, 0.04, 0.048)))]


def face_features(B):
    """Eyes, brows, lip line on the clean-shaven base head (all part of the body mesh, rigid to Head)."""
    for s in (-1, 1):
        B.ell("SA_Eye", "Head", V((s * 0.031, 0.1268, 1.6525)), (0.0088, 0.0042, 0.0042), u=8, v=4)   # eye
        B.ell("SA_Lip", "Head", V((s * 0.031, 0.1262, 1.6575)), (0.0105, 0.0042, 0.0028), u=8, v=4)   # upper lid
        B.box("SA_Beard", "Head", V((s * 0.033, 0.1295, 1.667)), (0.027, 0.006, 0.0042), (0.2, 0, s * -0.10))  # brow
    B.box("SA_Lip", "Head", V((0, 0.1525, 1.597)), (0.034, 0.008, 0.0045))                                # lip line


def face_surface(az, el):
    """Point + outward normal where the ray from CB (azimuth from +Y toward +X, elevation) leaves the head/jaw."""
    d = V((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))

    def f(p):
        return min((sum(((p[i] - c[i]) / r[i]) ** 2 for i in range(3)), k) for k, (c, r) in enumerate(FACE_ELL))
    lo, hi = 0.0, 0.25
    for _ in range(40):
        mid = (lo + hi) / 2
        if f(CB + d * mid)[0] < 1.0:
            lo = mid
        else:
            hi = mid
    p = CB + d * lo
    c, r = FACE_ELL[f(p)[1]]
    n = V(((p.x - c.x) / r.x ** 2, (p.y - c.y) / r.y ** 2, (p.z - c.z) / r.z ** 2)).normalized()
    return p, n


def interp(pts, x):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


BEARD_STYLES = {   # thickness (m): chin, cheek, under the chin; chin drop (m)
    "full": dict(chin=0.0078, cheek=0.0042, under=0.0050, drop=0.0035, bot=0, top=0),
    "trim": dict(chin=0.0042, cheek=0.0026, under=0.0030, drop=0.0010, bot=12, top=-5),   # less coverage too
}


def hair_shell(name, region, thick, ni, nj):
    """Skinned shell over the face (rigid to Head). region(a) -> (el_bot, el_top) in degrees for azimuth a (deg);
    thick(a, h) -> offset (m) along the normal; h = 0 bottom .. 1 top of the band. Edges taper into the skin."""
    B = K.Builder(K.BONES)
    az_max = region["az"]
    grid = []
    for i in range(ni):
        a = -az_max + 2 * az_max * i / (ni - 1)
        eb, et = region["el"](a)
        row = []
        for j in range(nj):
            h = j / (nj - 1)
            el = eb + (et - eb) * h
            p, n = face_surface(D(a), D(el))
            p = p + n * thick(a, h) + region.get("shift", lambda a, h: V((0, 0, 0)))(a, h)
            row.append(B.bm.verts.new(p))
        grid.append(row)
    for i in range(ni - 1):
        for j in range(nj - 1):
            B.bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    B._fin([v for r in grid for v in r], "SA_Beard", "Head")
    o = B.to_object(name)
    me = o.data
    out = sum((p.center - CB).normalized().dot(p.normal) for p in me.polygons)
    if out < 0:                                    # open shell: make every face point away from the head
        me.flip_normals()
    for p in me.polygons:
        p.use_smooth = True                        # hair UVs: azimuth / elevation, ~3 cm per texture repeat
    uv = me.uv_layers["UVMap"]
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            c = me.vertices[me.loops[li].vertex_index].co - CB
            uv.data[li].uv = (math.degrees(math.atan2(c.x, c.y)) / 14.0, math.degrees(math.atan2(c.z, math.hypot(c.x, c.y))) / 14.0)
    return o


def taper(x, w):
    return K.smooth(0.0, w, x)


def make_beard(style):
    st = BEARD_STYLES[style]
    top = [(0, -16), (18, -15.5), (28, -9), (42, 0), (58, 5), (72, 10), (84, 30)]
    bot = [(0, -58), (40, -57), (70, -52), (84, -48)]
    tl = lambda a: interp(top, abs(a)) + st["top"] * K.smooth(20, 45, abs(a))   # lower cheek line (trim)
    reg = {"az": 84, "el": lambda a: (interp(bot, abs(a)) + st["bot"], tl(a))}

    def thick(a, h):
        front = math.exp(-(a / 34.0) ** 2)
        t = st["cheek"] + (st["chin"] - st["cheek"]) * front * (1 - K.smooth(0.55, 1.0, h))
        t = t * (1 - 0.5 * K.smooth(0.3, 0.0, h)) + st["under"] * 0.5 * K.smooth(0.3, 0.0, h)
        e = taper(1 - abs(a) / 84.0, 0.16) * taper(1 - h, 0.30) * (0.30 + 0.70 * taper(h, 0.25))
        return t * e - 0.0006

    def shift(a, h):                               # the chin hair hangs a little lower and forward
        front = math.exp(-(a / 30.0) ** 2) * K.smooth(0.65, 0.15, h)
        return V((0, 0.35 * st["drop"], -st["drop"])) * front
    reg["shift"] = shift
    return hair_shell("Beard", reg, thick, 19, 10)


def make_moustache():
    reg = {"az": 20, "el": lambda a: (-6.5 - 4.5 * (a / 20) ** 2, 0.3 - 2.5 * (a / 20) ** 2)}

    def thick(a, h):
        e = taper(1 - abs(a) / 20.0, 0.25) * taper(1 - h, 0.45) * taper(h, 0.35)
        return 0.0036 * e - 0.0004

    def shift(a, h):
        return V((0, 0.0015, -0.001)) * (1 - h)
    reg["shift"] = shift
    return hair_shell("Moustache", reg, thick, 9, 5)


def skin_to_head(o, arm):
    o.parent = arm
    m = o.modifiers.new("Armature", "ARMATURE"); m.object = arm


# =============================================================================== uniform: flag shoulder patch
PATCHES = []


def flag_patch(B, s=-1, at=0.19, w=0.056, h=0.032):
    sh, el = K.SH[s], K.ELB[s]
    d1 = (el - sh).normalized()
    out = V((s, 0, 0)); out = (out - d1 * out.dot(d1)).normalized()
    up = -d1
    right = (-out).cross(up).normalized()
    c = sh + d1 * at + out * 0.053
    M = Matrix((right, out, up)).transposed().to_4x4(); M.translation = c
    B.boxm("SA_FlagIR", f"{K.SIDE[s]}UpperArm", M, (w, 0.004, h))
    PATCHES.append((c, right, up, w, h))


def patch_uvs(body):
    me = body.data
    mi = [m.name for m in me.materials].index("SA_FlagIR")
    uv = me.uv_layers["UVMap"]
    for poly in me.polygons:
        if poly.material_index != mi:
            continue
        pc = poly.center
        c, r, u, w, h = min(PATCHES, key=lambda P: (P[0] - pc).length)
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co - c
            uv.data[li].uv = (min(max(p.dot(r) / w + 0.5, 0.0), 1.0), min(max(p.dot(u) / h + 0.5, 0.0), 1.0))


# =============================================================================== gear builders
def ir_helmet(B, mat="SA_Camo"):
    """Older-style steel helmet with a cloth cover + elastic band (no rails / NVG mount); team patch on top."""
    HM = HC + V((0, -0.008, 0.018))
    K.helmet_shell(B, HM, mat, r=0.136, h=0.128, back_drop=0.03, top_h=0.13)
    B.loftz("SA_Rubber", "Head", [(HM.z + 0.028, 0.1355, 0.1465, HM.y, 1.0), (HM.z + 0.05, 0.1295, 0.140, HM.y, 1.0)],
            seg=16, caps=False)
    B.box("SA_Team", "Head", HM + V((0, -0.05, 0.121)), (0.05, 0.06, 0.012), (-0.22, 0, 0))
    for s in (-1, 1):                                                      # chin/nape strap behind the ears
        B.box("SA_Canvas", "Head", HC + V((s * 0.083, 0.0, -0.035)), (0.006, 0.012, 0.075), (-0.2, 0, 0))


def boonie_hat(B):
    z0 = HC.z + 0.03
    B.loftz("SA_Camo", "Head", [(z0, 0.092, 0.104, HC.y - 0.004, 0.85), (z0 + 0.06, 0.09, 0.101, HC.y - 0.004, 0.85),
                                (z0 + 0.105, 0.078, 0.088, HC.y - 0.004, 0.9), (z0 + 0.118, 0.05, 0.06, HC.y - 0.004, 1.0)],
            seg=14, caps=True)
    B.loftz("SA_Camo", "Head", [(z0 + 0.012, 0.094, 0.106, HC.y - 0.004, 0.9), (z0 - 0.004, 0.158, 0.168, HC.y - 0.004, 0.9),
                                (z0 - 0.012, 0.158, 0.168, HC.y - 0.004, 0.9), (z0 + 0.002, 0.094, 0.106, HC.y - 0.004, 0.9)],
            seg=16, caps=False)
    B.loftz("SA_Rig", "Head", [(z0 + 0.012, 0.093, 0.105, HC.y - 0.004, 0.85), (z0 + 0.03, 0.0925, 0.1045, HC.y - 0.004, 0.85)],
            seg=14, caps=False)
    B.box("SA_Team", "Head", V((0, HC.y - 0.004, z0 + 0.119)), (0.06, 0.07, 0.004))


def shemagh(B, drape=True):
    if "SA_Shemagh" not in K.MATS:                 # textured material, created only for roles that wear one
        K.MATS["SA_Shemagh"] = K.mat("SA_Shemagh", (1, 1, 1), 0.95,
                                     tex=shemagh_texture(os.path.join(OUT, f"{ROLE}_shemagh.png")))
        K.MAT_ORDER[:] = list(K.MATS)
    B.loftz("SA_Shemagh", "chain:torso", [(1.455, 0.165, 0.115, 0.022, 0.8), (1.50, 0.122, 0.092, 0.03, 0.85),
                                           (1.535, 0.088, 0.078, 0.035, 1.0), (1.556, 0.07, 0.068, 0.038, 1.0)],
            seg=12, caps=False)
    if drape:
        B.box("SA_Shemagh", "Chest", (0.0, 0.122, 1.43), (0.11, 0.02, 0.09), (0.35, 0, 0.0))
        B.box("SA_Shemagh", "Chest", (0.025, 0.128, 1.375), (0.06, 0.015, 0.06), (0.25, 0, 0.5))


def chest_rig(B, mags=4, mat="SA_Rig", team=True, side=True):
    W = {"Chest": 0.75, "Spine": 0.25}
    B.box(mat, W, (0, 0.128, 1.165), (0.30, 0.035, 0.17))
    xs = {4: (-0.105, -0.035, 0.035, 0.105), 3: (-0.07, 0.0, 0.07), 2: (-0.04, 0.04)}[mags]
    for x in xs:
        B.box(mat, W, (x, 0.158, 1.155), (0.064, 0.042, 0.13))
        B.box(mat, W, (x, 0.163, 1.218), (0.067, 0.048, 0.02), (0.12, 0, 0))
    if side:
        for s in (-1, 1):
            B.box(mat, W, (s * 0.178, 0.10, 1.15), (0.055, 0.06, 0.085), (0, 0, s * 0.35))
    for s in (-1, 1):
        B.tube(mat, "Chest", [V((s * 0.12, 0.135, 1.245)), V((s * 0.118, 0.10, 1.40)), V((s * 0.11, 0.01, 1.477)),
                              V((s * 0.10, -0.10, 1.42)), V((-s * 0.03, -0.128, 1.28)), V((-s * 0.13, -0.118, 1.15))],
               [(0.024, 0.005)] * 6, seg=4)
    B.loftz(mat, W, [(1.088, 0.168, 0.12, 0.0, 0.7), (1.112, 0.168, 0.12, 0.0, 0.7)], seg=12, caps=False)
    if team:
        B.box("SA_Team", "Chest", (0, 0.1465, 1.238), (0.09, 0.004, 0.02))


def bedroll(B):
    B.cyl("SA_Rig", "Chest", (0, -0.205, 1.07), 0.042, 0.33, (0, PI / 2, 0), seg=8)
    for s in (-1, 1):                                                    # tie-down straps
        B.cyl("SA_Canvas", "Chest", (s * 0.10, -0.205, 1.07), 0.045, 0.02, (0, PI / 2, 0), seg=8)


def army_head(B):
    face_features(B)
    flag_patch(B, -1)


# =============================================================================== weapons (carbine local frame)
def _ak_core(R, w, furn="SA_Wood", mag="SA_Metal"):
    M = "SA_Metal"
    R.box(M, w, (0, 0.33, 0.0), (0.044, 0.22, 0.058))                             # receiver
    R.cyl(M, w, (0, 0.33, 0.026), 0.021, 0.22, AXIS, seg=8)                     # dust cover
    R.box(M, w, (0.025, 0.31, 0.012), (0.012, 0.05, 0.012))                      # charging handle
    R.box(furn, w, GRIP, (0.03, 0.036, 0.09), (0.35, 0, 0))                       # pistol grip
    R.box(M, w, (0, 0.30, -0.055), (0.012, 0.06, 0.008))                         # trigger guard
    for k in range(5):                                                         # curved magazine
        R.box(mag, w, (0, 0.385 + k * 0.019, -0.068 - k * 0.036), (0.028, 0.062, 0.044), (0.22 + k * 0.13, 0, 0))
    R.box(M, w, (0, 0.452, 0.042), (0.024, 0.04, 0.014))                         # rear sight block


def build_ak(R, w):
    """AK-family rifle (generic): wooden stock / handguards, curved magazine, gas tube, slanted front sight."""
    M, Wd = "SA_Metal", "SA_Wood"
    R.box(M, w, (0, 0.008, -0.048), (0.04, 0.016, 0.125))                       # butt plate
    R.box(Wd, w, (0, 0.115, -0.03), (0.038, 0.20, 0.07), (-0.12, 0, 0))         # stock
    R.box(Wd, w, (0, 0.075, -0.075), (0.034, 0.13, 0.04), (-0.32, 0, 0))
    _ak_core(R, w)
    R.box(Wd, w, (0, 0.512, -0.012), (0.05, 0.15, 0.048))                       # lower handguard
    R.box(Wd, w, (0, 0.53, 0.033), (0.036, 0.13, 0.026))                        # upper handguard (over gas tube)
    R.cyl(M, w, (0, 0.625, 0.034), 0.011, 0.08, AXIS, seg=6)                    # gas tube
    R.box(M, w, (0, 0.67, 0.022), (0.03, 0.03, 0.045))                          # gas block
    R.cyl(M, w, (0, 0.64, 0.0), 0.011, 0.40, AXIS, seg=8)                       # barrel
    R.box(M, w, (0, 0.80, 0.03), (0.012, 0.02, 0.05), (-0.35, 0, 0))            # slanted front sight
    R.cyl(M, w, (0, 0.865, 0.0), 0.015, 0.05, AXIS, seg=8)                      # muzzle brake
    R.cyl(M, w, (0, 0.70, -0.018), 0.004, 0.20, AXIS, seg=4)                    # cleaning rod


def build_ak_fold(R, w):
    """AK-family with an under-folding skeleton stock (paratrooper / medic)."""
    M, Wd = "SA_Metal", "SA_Wood"
    for s in (-1, 1):
        R.box(M, w, (s * 0.017, 0.115, -0.03), (0.008, 0.22, 0.012), (-0.10, 0, 0))
    R.box(M, w, (0, 0.012, -0.05), (0.045, 0.014, 0.09))                         # butt plate
    _ak_core(R, w)
    R.box(Wd, w, (0, 0.512, -0.012), (0.05, 0.15, 0.048))
    R.box(Wd, w, (0, 0.53, 0.033), (0.036, 0.13, 0.026))
    R.cyl(M, w, (0, 0.625, 0.034), 0.011, 0.08, AXIS, seg=6)
    R.box(M, w, (0, 0.67, 0.022), (0.03, 0.03, 0.045))
    R.cyl(M, w, (0, 0.64, 0.0), 0.011, 0.40, AXIS, seg=8)
    R.box(M, w, (0, 0.80, 0.03), (0.012, 0.02, 0.05), (-0.35, 0, 0))
    R.cyl(M, w, (0, 0.865, 0.0), 0.015, 0.05, AXIS, seg=8)


def build_ak_mod(R, w):
    """Modernised AK-family (IRGC SF): adjustable polymer stock, rail handguard, magnified optic, suppressor."""
    M, Rb = "SA_Metal", "SA_Rubber"
    R.box(Rb, w, (0, 0.03, -0.035), (0.042, 0.05, 0.12))                         # stock body
    R.box(Rb, w, (0, 0.055, 0.02), (0.036, 0.09, 0.025))                         # cheek riser
    R.cyl(M, w, (0, 0.14, 0.0), 0.014, 0.18, AXIS, seg=6)                       # buffer tube
    R.box(M, w, (0, 0.33, 0.0), (0.044, 0.22, 0.058))
    R.box(M, w, (0.025, 0.31, 0.012), (0.012, 0.05, 0.012))
    R.box(Rb, w, GRIP, (0.032, 0.036, 0.095), (0.35, 0, 0))
    R.box(M, w, (0, 0.30, -0.055), (0.012, 0.06, 0.008))
    for k in range(5):
        R.box(Rb, w, (0, 0.385 + k * 0.019, -0.068 - k * 0.036), (0.029, 0.062, 0.044), (0.22 + k * 0.13, 0, 0))
    R.box(Rb, w, (0, 0.53, 0.0), (0.054, 0.17, 0.062))                           # rail handguard
    R.box(M, w, (0, 0.44, 0.042), (0.022, 0.38, 0.012))                          # top rail
    R.box(Rb, w, (0, 0.585, -0.05), (0.022, 0.035, 0.045), (0.25, 0, 0))         # hand stop
    R.cyl(M, w, (0, 0.335, 0.088), 0.017, 0.15, AXIS, seg=8)                    # optic tube
    R.cyl(M, w, (0, 0.42, 0.088), 0.022, 0.04, AXIS, seg=8)                     # objective
    R.cyl("SA_Glass", w, (0, 0.441, 0.088), 0.019, 0.004, AXIS, seg=8)
    R.box(M, w, (0, 0.335, 0.06), (0.03, 0.08, 0.025))                           # mount
    R.cyl(M, w, (0, 0.335, 0.11), 0.008, 0.015, seg=6)                          # turret
    R.cyl(M, w, (0, 0.655, 0.0), 0.011, 0.06, AXIS, seg=8)
    R.cyl(M, w, (0, 0.765, 0.0), 0.021, 0.18, AXIS, seg=10)                     # suppressor
    R.box(Rb, w, (-0.034, 0.56, 0.01), (0.012, 0.05, 0.022))                     # laser / light box


def build_g3(R, w):
    """G3-family battle rifle (generic): straight polymer stock, long receiver, cocking tube over the barrel,
    straight magazine, drum rear sight, hooded front sight."""
    M, Rb = "SA_Metal", "SA_Rubber"
    R.box(Rb, w, (0, 0.012, -0.03), (0.044, 0.024, 0.13))
    R.box(Rb, w, (0, 0.12, -0.025), (0.044, 0.20, 0.085), (-0.06, 0, 0))         # stock
    R.box(M, w, (0, 0.335, 0.003), (0.042, 0.23, 0.055))                         # receiver
    R.cyl(M, w, (0, 0.335, 0.022), 0.022, 0.23, AXIS, seg=8)
    R.cyl(M, w, (0, 0.25, 0.058), 0.013, 0.03, (0, PI / 2, 0), seg=8)           # drum rear sight
    R.box(Rb, w, GRIP, (0.032, 0.036, 0.095), (0.35, 0, 0))
    R.box(M, w, (0, 0.30, -0.055), (0.012, 0.06, 0.008))
    R.box(M, w, (0, 0.40, -0.095), (0.030, 0.06, 0.13), (0.10, 0, 0))            # straight magazine
    R.box(Rb, w, (0, 0.545, -0.008), (0.055, 0.19, 0.055))                       # handguard
    R.cyl(M, w, (0, 0.59, 0.032), 0.013, 0.30, AXIS, seg=8)                     # cocking tube
    R.box(M, w, (0, 0.47, 0.045), (0.012, 0.03, 0.02))                           # cocking handle
    R.cyl(M, w, (0, 0.70, 0.0), 0.012, 0.48, AXIS, seg=8)                       # barrel
    R.box(M, w, (0, 0.745, 0.035), (0.03, 0.02, 0.045))                          # front sight hood
    R.cyl(M, w, (0, 0.955, 0.0), 0.015, 0.06, AXIS, seg=8)                      # flash hider


def build_pkm(R, w):
    """PKM-family general-purpose MG (generic): skeleton stock, long barrel with carry handle, gas tube below,
    ammunition box under the receiver (right side), folded bipod."""
    M, Wd = "SA_Metal", "SA_Wood"
    R.box(M, w, (0, 0.012, -0.045), (0.04, 0.024, 0.13))                         # butt plate
    R.box(Wd, w, (0, 0.11, 0.0), (0.034, 0.18, 0.026))                           # stock top bar
    R.box(Wd, w, (0, 0.11, -0.09), (0.03, 0.18, 0.024), (-0.12, 0, 0))           # stock lower bar (thumbhole)
    R.box(Wd, w, (0, 0.20, -0.04), (0.032, 0.03, 0.10))
    R.box(M, w, (0, 0.31, 0.0), (0.05, 0.24, 0.075))                             # receiver
    R.box(M, w, (0, 0.30, 0.048), (0.048, 0.17, 0.02))                           # feed cover
    R.box(M, w, (0, 0.235, 0.07), (0.012, 0.02, 0.03))                            # rear sight
    R.box(Wd, w, GRIP, (0.03, 0.036, 0.09), (0.35, 0, 0))
    R.box(M, w, (0, 0.30, -0.06), (0.012, 0.06, 0.008))
    R.box("SA_Olive", w, (0.03, 0.36, -0.10), (0.07, 0.11, 0.11))                # ammunition box
    R.box(M, w, (0.03, 0.36, -0.04), (0.05, 0.03, 0.012))
    R.box("SA_Brass", w, (0.032, 0.36, -0.03), (0.02, 0.04, 0.03), (0, 0.3, 0))   # belt into the feed
    R.cyl(M, w, (0, 0.77, 0.0), 0.014, 0.70, AXIS, seg=8)                       # barrel
    R.cyl(M, w, (0, 0.62, -0.03), 0.011, 0.40, AXIS, seg=6)                     # gas tube
    R.box(M, w, (0, 0.83, -0.02), (0.03, 0.04, 0.04))                            # gas block
    R.box(M, w, (0, 0.52, 0.04), (0.014, 0.025, 0.06)); R.box(Wd, w, (0, 0.52, 0.075), (0.016, 0.10, 0.018))  # handle
    R.box(M, w, (0, 1.06, 0.035), (0.01, 0.015, 0.04))                           # front sight
    R.cyl(M, w, (0, 1.14, 0.0), 0.02, 0.07, AXIS, seg=8, r2=0.016)              # flash hider
    for s in (-1, 1):                                                          # bipod folded under the barrel
        R.box(M, w, (s * 0.014, 0.95, -0.035), (0.008, 0.24, 0.008))


def build_svd(R, w):
    """SVD-family designated marksman rifle (generic): thumbhole skeleton stock with cheek rest, long slender
    barrel, slotted flash hider, side-mounted optic on the LEFT, 10-round magazine."""
    M, Wd = "SA_Metal", "SA_Wood"
    R.box(M, w, (0, 0.012, -0.05), (0.038, 0.024, 0.14))                         # butt plate
    R.box(Wd, w, (0, 0.11, 0.005), (0.034, 0.19, 0.03))                          # comb
    R.box(Wd, w, (0, 0.085, 0.03), (0.03, 0.10, 0.025))                          # cheek rest
    R.box(Wd, w, (0, 0.12, -0.105), (0.03, 0.22, 0.026), (-0.10, 0, 0))          # lower bar
    R.box(Wd, w, (0, 0.025, -0.05), (0.036, 0.04, 0.12))
    R.box(Wd, w, GRIP, (0.03, 0.038, 0.10), (0.30, 0, 0))                       # grip (front of the thumbhole)
    R.box(M, w, (0, 0.34, 0.0), (0.042, 0.21, 0.052))                            # receiver
    R.box(M, w, (0, 0.30, -0.055), (0.012, 0.06, 0.008))
    R.box(M, w, (0, 0.385, -0.07), (0.028, 0.058, 0.07), (0.18, 0, 0))           # magazine
    R.box(Wd, w, (0, 0.545, -0.004), (0.048, 0.20, 0.052))                       # handguard
    R.cyl(M, w, (0, 0.85, 0.0), 0.0105, 0.62, AXIS, seg=8)                      # barrel
    R.box(M, w, (0, 1.10, 0.03), (0.01, 0.015, 0.035))                           # front sight
    R.cyl(M, w, (0, 1.20, 0.0), 0.014, 0.08, AXIS, seg=8)                       # slotted flash hider
    R.box(M, w, (-0.024, 0.33, 0.04), (0.012, 0.09, 0.03))                       # side mount (left)
    R.cyl(M, w, (-0.022, 0.36, 0.085), 0.016, 0.26, AXIS, seg=8)                # optic tube
    R.cyl(M, w, (-0.022, 0.505, 0.085), 0.022, 0.05, AXIS, seg=8)               # objective
    R.cyl("SA_Glass", w, (-0.022, 0.531, 0.085), 0.019, 0.004, AXIS, seg=8)
    R.cyl("SA_Rubber", w, (-0.022, 0.215, 0.085), 0.019, 0.04, AXIS, seg=8)     # eye cup
    R.cyl(M, w, (-0.022, 0.37, 0.108), 0.008, 0.02, seg=6)                      # turrets
    R.cyl(M, w, (-0.045, 0.37, 0.085), 0.008, 0.02, (0, PI / 2, 0), seg=6)


def gun(name, build, muzzle, **kw):
    kw.setdefault("grip_local", GRIP)
    return K.Weapon(name, build, K.RIFLE_REST, K.BUTT, V(muzzle), **kw)


# ------------------------------------------------------------------ RPG-7-family launcher (AT4 conventions)
RPG_GRIP = V((0, 0.20, -0.105))
RPG_REAR, RPG_TUBE_FRONT, RPG_TIP = -0.58, 0.37, 0.86


def build_rpg(R, w):
    """Reusable shoulder-fired launcher (generic RPG-7-family silhouette). Local frame: origin = shoulder contact on
    the tube axis, +Y toward the muzzle; optic on the LEFT (-X). Rocket loaded with its warhead outside the tube."""
    M, Wd, O = "SA_Metal", "SA_Wood", "SA_Olive"
    cy = lambda y0, y1: ((y0 + y1) / 2, y1 - y0)
    c, d = cy(-0.47, RPG_TUBE_FRONT)
    R.cyl(M, w, (0, c, 0), 0.021, d, AXIS, seg=10)                                # tube
    c, d = cy(RPG_REAR, -0.47)
    R.cyl(M, w, (0, c, 0), 0.052, d, AXIS, seg=12, r2=0.024)                      # flared venturi (rear)
    R.cyl("SA_Rubber", w, (0, RPG_REAR - 0.002, 0), 0.045, 0.004, AXIS, seg=10)
    c, d = cy(-0.13, 0.13)
    R.cyl(Wd, w, (0, c, 0), 0.031, d, AXIS, seg=10)                               # wooden heat guard
    R.cyl(M, w, (0, 0.0, 0), 0.0325, 0.012, AXIS, seg=10)                         # guard clamp
    R.box(Wd, w, RPG_GRIP + V((0, 0, 0.005)), (0.03, 0.036, 0.10), (0.30, 0, 0))   # pistol grip
    R.box(M, w, (0, 0.20, -0.035), (0.03, 0.08, 0.035))                           # trigger housing
    R.box(M, w, (0, 0.33, 0.03), (0.008, 0.012, 0.022))                           # front sight
    R.box(M, w, (0, 0.15, 0.03), (0.016, 0.012, 0.018))                           # rear sight
    R.box(M, w, (-0.03, 0.10, 0.025), (0.02, 0.06, 0.025))                        # optic mount (left)
    R.cyl(M, w, (-0.045, 0.10, 0.05), 0.014, 0.14, AXIS, seg=8)                   # optic
    R.cyl("SA_Rubber", w, (-0.045, 0.015, 0.05), 0.016, 0.035, AXIS, seg=8)        # eye cup
    R.cyl("SA_Glass", w, (-0.045, 0.171, 0.05), 0.012, 0.004, AXIS, seg=8)
    # rocket: booster neck, ogive warhead, nose probe
    c, d = cy(RPG_TUBE_FRONT, 0.42)
    R.cyl(O, w, (0, c, 0), 0.022, d, AXIS, seg=10, r2=0.024)
    c, d = cy(0.42, 0.50)
    R.cyl(O, w, (0, c, 0), 0.024, d, AXIS, seg=12, r2=0.043)
    c, d = cy(0.50, 0.60)
    R.cyl(O, w, (0, c, 0), 0.043, d, AXIS, seg=12)
    R.cyl("SA_Marking", w, (0, 0.585, 0), 0.0435, 0.012, AXIS, seg=12)
    c, d = cy(0.60, 0.80)
    R.cyl(O, w, (0, c, 0), 0.043, d, AXIS, seg=12, r2=0.012)
    c, d = cy(0.80, RPG_TIP)
    R.cyl(M, w, (0, c, 0), 0.009, d, AXIS, seg=6, r2=0.006)


RPG_REST = K.RIFLE_REST @ Matrix.Translation(V(GRIP) - RPG_GRIP)


# =============================================================================== shared pose helpers (as roster)
def carry(P, d, zhint):
    return V(P), K.axes_matrix(d, zhint, (0, 0, 0)).to_quaternion()


def left_free(p, pos, fingers=(0.05, 0.25, -1), back=(-1, 0, 0.1)):
    p["lgrip"] = 0.0; p["lfree"] = V(pos); p["lfree_q"] = K.hand_q(fingers, back)


def left_swing(p, t):
    c = math.cos(2 * PI * t)
    left_free(p, (-0.235, 0.05 + 0.13 * c, 0.90 + 0.03 * c * c), (0.0, 0.25 + 0.35 * c, -1))


def left_pump(p, t):
    c = math.cos(2 * PI * t)
    left_free(p, (-0.22, 0.10 + 0.17 * c, 1.08 + 0.07 * c), (0.25, 1.0 - 0.2 * c, 0.4 + 0.5 * c), (-1, 0.1, 0.4))
    p["elbow_pole"][-1] = V((-0.2, -1.0, -0.2))


def burst(n):
    return lambda t: K.recoil_curve((t * n) % 1.0)


def fire_with(curve, kneel=False, chest=1.8):
    def act(t):
        p = K.kneel_pose(K.base_pose()) if kneel else K.aim_pose(K.base_pose())
        r = curve(t)
        p["recoil"] = r
        p["chest"] += V((D(chest) * r, 0, D(0.6) * r)); p["head"] += V((D(1.2) * r, 0, 0))
        if not kneel:
            p["hips_pos"] = p["hips_pos"] + V((0, -0.004 * r, 0))
        return p
    return act


def slow_curve(t):
    if t < 0.06:
        return math.sin(0.5 * PI * t / 0.06)
    u = (t - 0.06) / 0.94
    return (1 - K.smoothstep(u)) * (1 - u) ** 0.8


def std_actions(fire_fn=None, fire_len=0.3, crouch_fn=None, extra=()):
    return [("idle", K.act_idle, 3.0, True), ("walk", K.act_walk, K.WALK["Tc"], True),
            ("run", K.act_run, K.RUN["Tc"], True), ("aim", K.act_aim, 2.0, True),
            ("fire", fire_fn or K.act_fire, fire_len, True),
            ("crouch_fire", crouch_fn or K.act_crouch_fire, fire_len, True), ("die", K.act_die, 1.5, False)] + \
        list(extra)


def kneel_relaxed(p):
    a = K.AIM_EXTRA; K.AIM_EXTRA = None
    p = K.kneel_pose(p)
    K.AIM_EXTRA = a
    p["aim"] = 0.0
    p["hips_rot"] = V((D(4), 0, D(-10)))
    p["spine"] = V((D(-14), 0, 0)); p["chest"] = V((D(-8), 0, 0)); p["neck"] = V((D(-8), 0, 0))
    p["head"] = V((D(-14), 0, 0))
    p["elbow_pole"] = {1: V((0.3, -0.2, -0.3)), -1: V((-0.3, 0.05, -0.4))}
    return p


# =============================================================================== role assembly
REG_BODY = dict(pack="small", radio=False, helmet=None, nvg=False, holster=False, mag_pouches=False, armband=True,
                hydration=False, carrier="none", knee_pads=False, eyepro=False, beard=False,
                remap={"SA_CamoGear": "SA_Rig"})
FACE_STYLE = {"ir_rifleman": "full", "ir_rpg": "trim", "ir_mg": "full", "ir_sniper": "full", "ir_engineer": "trim",
              "ir_medic": "trim", "irgc_sf": "full", "ir_paratrooper": "trim"}
EXTRA_OBJS = []          # role-specific extra objects (e.g. ChuteAttach)


def extras(arm):
    patch_uvs(K.BODY)
    objs = []
    for o in (make_beard(FACE_STYLE[ROLE]), make_moustache()):
        skin_to_head(o, arm)
        objs.append(o)
    for fn in EXTRA_OBJS:
        objs += fn(arm)
    FACE_OBJS[:] = objs[:2]
    return objs


FACE_OBJS = []


def after_bake(report):
    tr = report["triangles"]
    for o in FACE_OBJS:
        tr[o.name] = sum(len(p.vertices) - 2 for p in o.data.polygons)
    tr["total"] = sum(v for k, v in tr.items() if k != "total")
    report["face_variants"] = {
        "objects": [o.name for o in FACE_OBJS], "beard_style": FACE_STYLE[ROLE],
        "looks": {"bearded": "Beard + Moustache visible", "moustache": "hide Beard",
                  "clean_shaven": "hide Beard and Moustache"},
        "skinning": "100 % Head (separate skinned meshes on the same Skeleton3D)"}
    report["flag_patch"] = "left upper sleeve, material SA_FlagIR (texture <role>_flagpatch.png, embedded)"


def make_role(name, body_name, weapon, body_extra, actions, palette=PAL_ARMY, camo_seed=2101, body_opts=None,
              overrides=ARMY_OVERRIDES, notes="", report_extra=None, camo=camo_woodland):
    CAMO_FN[0] = camo

    def bx(B):
        add_textured_mats()
        body_extra(B)
    rx = dict(report_extra or {}); rx["notes"] = notes
    rx["camo"] = camo.__name__
    return K.Role(name, body_name=body_name, palette=palette, camo_seed=camo_seed, weapon=weapon,
                  extra_mats=COMMON_MATS, mat_overrides=overrides,
                  body_opts=dict(REG_BODY, **(body_opts or {})), body_extra=bx, actions=actions,
                  prev_prefix=name if name.startswith("ir_") else f"ir_{name}", prev_views=("front", "rts"),
                  extra_objects=extras, after_bake=after_bake, report_extra=rx)


# ------------------------------------------------------------------ 1. rifleman
def role_rifleman():
    def bx(B):
        army_head(B); ir_helmet(B); chest_rig(B, 4); bedroll(B)
    return make_role("ir_rifleman", "IR_Rifleman_Body", gun("Rifle", build_ak, (0, 0.89, 0.0)), bx, lambda: std_actions(),
                     camo_seed=2101,
                     notes="Rifleman actions. AK-family rifle (wood furniture), older cloth-covered helmet, olive "
                           "chest rig with 4 magazine pouches, small pack + bedroll.")


# ------------------------------------------------------------------ 2. RPG gunner (AT4 conventions)
def role_rpg():
    W_REST = RPG_REST
    weapon = K.Weapon("Launcher", build_rpg, W_REST, W_REST.translation.copy(), V((0, RPG_TIP, 0)),
                      empties={"Backblast": (V((0, RPG_REAR, 0)), (0, 0, PI))},
                      aim_pocket=(0.205, 0.035, 1.55), kick=0.05, lift=0.012, rise=5.0,
                      lay=dict(gx=0.20, gy=0.12, grip=0.20, side=0.10, h=0.07), grip_local=RPG_GRIP)

    def bx(B):
        army_head(B); ir_helmet(B); chest_rig(B, 3, side=False)
        # rocket carrier on the back: canvas pack with two spare rockets, warheads up
        B.box("SA_Rig", "Chest", (0, -0.215, 1.22), (0.30, 0.12, 0.32), (-0.05, 0, 0))
        B.box("SA_Team", "Chest", (0, -0.278, 1.22), (0.14, 0.006, 0.10), (-0.05, 0, 0))
        for s in (-1, 1):
            x = s * 0.075
            B.cyl("SA_Olive", "Chest", (x, -0.225, 1.43), 0.024, 0.08, seg=10, r2=0.043)
            B.cyl("SA_Olive", "Chest", (x, -0.225, 1.51), 0.043, 0.08, seg=10)
            B.cyl("SA_Olive", "Chest", (x, -0.225, 1.62), 0.043, 0.14, seg=10, r2=0.012)
            B.cyl("SA_Marking", "Chest", (x, -0.225, 1.545), 0.0435, 0.012, seg=10)
        B.box("SA_Rig", "Hips", (-0.19, 0.04, 0.985), (0.045, 0.06, 0.09), (0, 0, 0.3))

    CARRY = carry((0.255, 0.11, 0.93), (-0.06, 0.86, -0.50), (0.85, 0.0, 0.55))

    def pose_extra(p):
        p["w_loc"], p["w_q"] = CARRY[0].copy(), CARRY[1].copy()
        p["lslide"], p["lroll"], p["ldrop"] = 0.0, 0.0, 0.0
        p["lgrip"] = 0.0
        p["lfree"] = V((-0.235, 0.05, 0.89)); p["lfree_q"] = K.hand_q((0.05, 0.25, -1), (-1, 0, 0.1))
        p["elbow_pole"] = {1: V((0.3, -0.4, -0.1)), -1: V((-0.3, -0.3, -0.2))}

    def aim_extra(p, kneel):
        p["lgrip"] = 1.0
        p["lslide"], p["lroll"], p["ldrop"] = RPG_LSLIDE[0], 0.0, RPG_LDROP[0]
        p["head"] = V((D(-6), D(7), D(14))) if not kneel else V((D(-4), D(7), D(14)))
        p["neck"] = V((D(-4), D(4), D(9)))
        p["elbow_pole"] = {1: V((0.5, -0.1, -0.35)), -1: V((-0.2, 0.1, -0.5))}

    def die_hook(keys):
        k0, k1, k2, k3, k4, k5 = keys
        k1["rifle_rot"] = V((D(-10), 0, 0)); k2["rifle_rot"] = V((D(5), 0, 0)); k3["rifle_rot"] = V((D(40), 0, D(35)))
        k2["rifle_off"] = V((0.09, 0, 0)); k3["rifle_off"] = V((0.10, 0, 0))

    K.POSE_EXTRA, K.AIM_EXTRA, K.DIE_HOOK = pose_extra, aim_extra, die_hook
    K.WEAPON_SOLVE_ITERS = 40

    def act_idle(t):
        p = K.base_pose(); b = math.sin(2 * PI * t)
        p["chest"] = V((D(1.2) * b, 0, 0)); p["spine"] = V((D(0.4) * b, 0, 0))
        p["head"] = V((D(-1.0) * b, 0, D(4) * math.sin(2 * PI * t + 1.0)))
        p["hips_pos"] = p["hips_pos"] + V((0.008 * math.sin(2 * PI * t + 0.5), 0, 0.003 * b))
        p["rifle_rot"] = V((D(1.2) * math.sin(2 * PI * t + 0.6), 0, 0))
        return p

    def act_walk(t):
        p = K.base_pose(); K.walk_legs(p, t)
        p["spine"] += V((D(-3), 0, 0)); p["head"] += V((D(3), 0, 0))
        p["rifle_rot"] = V((D(2.0) * math.sin(4 * PI * t), 0, D(1.5) * math.sin(2 * PI * t)))
        p["rifle_off"] = V((0, 0, 0.006 * math.sin(4 * PI * t)))
        left_swing(p, t)
        return p

    def act_run(t):
        p = K.base_pose(); K.run_legs(p, t); K.run_torso(p)
        p["rifle_rot"] = V((D(20) + D(4) * math.sin(4 * PI * t + 0.8), D(-3), D(-4) + D(3) * math.sin(2 * PI * t)))
        p["rifle_off"] = V((0.035, 0.02, 0.05))
        left_pump(p, t)
        p["elbow_pole"][1] = V((0.3, -0.4, -0.1))
        return p

    def act_aim(t):
        p = K.aim_pose(K.base_pose()); b = math.sin(2 * PI * t)
        p["chest"] += V((D(0.8) * b, 0, 0))
        p["aim_pitch"] = D(0.4) * math.sin(2 * PI * t + 0.4); p["aim_yaw"] = D(0.3) * math.sin(4 * PI * t)
        return p

    def launch_curve(t):
        if t < 0.07:
            return math.sin(0.5 * PI * t / 0.07)
        if t < 0.2:
            return 1.0 - 0.25 * K.smoothstep((t - 0.07) / 0.13)
        return 0.75 * (1 - K.smoothstep((t - 0.2) / 0.8))

    def launch(p, t, kneel=False):
        r = launch_curve(t); r2 = launch_curve(max(0.0, t - 0.05)) if t > 0.05 else 0.0
        p["recoil"] = r
        p["chest"] += V((D(3.5) * r2, D(-1.0) * r2, D(1.0) * r2)); p["spine"] += V((D(1.5) * r2, 0, 0))
        p["head"] += V((D(2.5) * r, 0, 0))
        if not kneel:
            p["hips_pos"] = p["hips_pos"] + V((0, -0.015 * r2, -0.008 * r2))
        return p

    acts = lambda: [("idle", act_idle, 3.0, True), ("walk", act_walk, K.WALK["Tc"], True), ("run", act_run, K.RUN["Tc"], True),
                    ("aim", act_aim, 2.0, True), ("fire", lambda t: launch(K.aim_pose(K.base_pose()), t), 0.6, True),
                    ("crouch_fire", lambda t: launch(K.kneel_pose(K.base_pose()), t, True), 0.6, True),
                    ("die", K.act_die, 1.5, False)]
    return make_role("ir_rpg", "IR_RPG_Body", weapon, bx, acts, camo_seed=2102,
                     body_opts=dict(pack=None),
                     notes="AT4 conventions: one-handed side carry (idle/walk/run), shouldered aim, fire/crouch_fire = "
                           "0.6 s launch (kick 50 mm + 5 deg rise, starts/ends in the aim pose). Launcher = generic "
                           "RPG-7-family tube with the warhead loaded; Muzzle at the warhead tip, Backblast at the "
                           "venturi (rotated 180 deg so +Y points out of the rear). Two spare rockets on the back.")


RPG_LSLIDE, RPG_LDROP = [-0.10], [0.0]


# ------------------------------------------------------------------ 3. MG gunner
def role_mg():
    def bx(B):
        army_head(B); ir_helmet(B); chest_rig(B, 2)
        # ammunition belt worn across the chest (left shoulder -> right hip), brass with dark links
        pts = [V((-0.13, 0.08, 1.47)), V((-0.06, 0.165, 1.37)), V((0.05, 0.19, 1.24)), V((0.15, 0.15, 1.10)),
               V((0.19, 0.06, 1.02)), V((0.17, -0.06, 1.04)), V((0.05, -0.135, 1.22)), V((-0.10, -0.12, 1.40)),
               V((-0.13, 0.08, 1.47))]
        W = {"Chest": 0.8, "Spine": 0.2}
        B.tube("SA_Brass", W, pts[:5], [(0.026, 0.010)] * 5, seg=4, up=V((0, 1, 0)))
        B.tube("SA_Rubber", W, pts[4:], [(0.022, 0.006)] * 5, seg=4, up=V((0, 1, 0)))
        B.box("SA_Olive", "Hips", (0.20, -0.02, 0.97), (0.07, 0.12, 0.10), (0, 0, -0.3))         # spare ammo box
    return make_role("ir_mg", "IR_MG_Body", gun("MMG", build_pkm, (0, 1.175, 0.0), kick=0.04, lift=0.004, rise=3.5,
                                                lay=dict(gx=0.24, gy=0.10, grip=0.255, side=0.085, h=0.10)),
                     bx, lambda: std_actions(fire_with(burst(3), chest=2.6), 0.35, fire_with(burst(3), kneel=True, chest=2.6)),
                     camo_seed=2103,
                     notes="fire/crouch_fire = 3-round burst cycle in 0.35 s (loop). PKM-family GPMG with ammo box; "
                           "an ammunition belt is worn across the chest; spare ammo box on the right hip.")


# ------------------------------------------------------------------ 4. sniper
def role_sniper():
    def bx(B):
        face_features(B); flag_patch(B, -1); boonie_hat(B); shemagh(B); chest_rig(B, 2, side=False)
        B.box("SA_Rig", "Chest", (0.10, 0.15, 1.27), (0.07, 0.05, 0.08))                           # binocular pouch
        B.box("SA_Rubber", "Hips", (-0.19, 0.0, 0.98), (0.05, 0.08, 0.10), (0, 0, 0.3))
    K.WEAPON_SOLVE_ITERS = 40
    return make_role("ir_sniper", "IR_Sniper_Body",
                     gun("SniperRifle", build_svd, (0, 1.245, 0.0), kick=0.05, lift=0.006, rise=5.0,
                         lay=dict(gx=0.24, gy=0.10, grip=0.255, side=0.085, h=0.085)),
                     bx, lambda: std_actions(fire_with(slow_curve, chest=2.5), 0.8, fire_with(slow_curve, kneel=True, chest=2.5)),
                     camo_seed=2104, body_opts=dict(pack="small"),
                     notes="fire/crouch_fire = one heavy shot, 0.8 s (kick + settle); crouch_fire is kneeling. "
                           "SVD-family DMR with a left side-mounted optic; boonie hat (team patch on the crown) and "
                           "shemagh instead of a helmet.")


# ------------------------------------------------------------------ 5. engineer
def role_engineer():
    def bx(B):
        army_head(B); ir_helmet(B); chest_rig(B, 3, side=False)
        # tool pack: box pack with an entrenching shovel and a large wrench strapped on, team panel on the lid
        B.box("SA_Rig", "Chest", (0, -0.215, 1.24), (0.30, 0.13, 0.34), (-0.05, 0, 0))
        B.box("SA_Rig", "Chest", (0, -0.222, 1.42), (0.28, 0.12, 0.05), (-0.1, 0, 0))
        B.box("SA_Team", "Chest", (0, -0.226, 1.447), (0.15, 0.08, 0.006), (-0.1, 0, 0))
        B.cyl("SA_Wood", "Chest", (0.06, -0.29, 1.36), 0.014, 0.52, (0.05, 0, 0), seg=6)            # shovel handle
        B.box("SA_Wood", "Chest", (0.06, -0.294, 1.625), (0.09, 0.024, 0.024), (0.05, 0, 0))        # T-grip
        B.box("SA_Metal", "Chest", (0.06, -0.293, 1.06), (0.13, 0.012, 0.16), (0.05, 0, 0))         # shovel blade
        B.box("SA_Metal", "Chest", (-0.08, -0.285, 1.25), (0.022, 0.012, 0.28), (0.05, 0, 0.15))    # wrench
        B.box("SA_Metal", "Chest", (-0.06, -0.285, 1.395), (0.06, 0.014, 0.04), (0.05, 0, 0.15))
        for z in (1.15, 1.32):
            B.box("SA_Rubber", "Chest", (0, -0.282, z), (0.31, 0.012, 0.022), (-0.05, 0, 0))
        # hip tool pouch with a hammer handle and pliers sticking out
        B.box("SA_Rig", "Hips", (-0.20, 0.03, 0.97), (0.06, 0.13, 0.13), (0, 0, 0.25))
        B.cyl("SA_Wood", "Hips", (-0.20, 0.0, 1.06), 0.011, 0.10, seg=6)
        B.box("SA_Metal", "Hips", (-0.20, 0.0, 1.11), (0.02, 0.07, 0.02))
        B.box("SA_Rubber", "Hips", (-0.205, 0.06, 1.05), (0.012, 0.012, 0.07), (0.2, 0, 0))
        B.box("SA_Olive", "Hips", (0.20, -0.02, 0.97), (0.06, 0.11, 0.10), (0, 0, -0.3))           # wire / det box

    def work(t):                                   # kneeling repair loop: hammering / turning with the left hand
        p = kneel_relaxed(K.base_pose())
        b = math.sin(2 * PI * t); h = max(0.0, math.sin(4 * PI * t))
        p["spine"] = V((D(-24), 0, D(4))); p["chest"] = V((D(-12) + D(2) * h, 0, D(4))); p["head"] = V((D(-22), 0, D(6)))
        p["w_loc"], p["w_q"] = carry((0.24, 0.20, 1.00), (0.25, 0.45, -0.86), (0.9, 0.0, 0.3))
        left_free(p, (-0.03 + 0.04 * b, 0.36, 1.06 + 0.07 * h), (0.4, 0.8, -0.6 + 0.4 * h), (0.1, 0.4, 1.0))
        p["elbow_pole"] = {1: V((0.4, -0.3, 0.0)), -1: V((-0.5, 0.0, -0.3))}
        return p

    K.GROUND_SOLVE = {"die", "work"}
    return make_role("ir_engineer", "IR_Engineer_Body",
                     gun("Rifle", build_g3, (0, 0.985, 0.0), lay=dict(gx=0.24, gy=0.10, grip=0.255, side=0.085, h=0.05)),
                     bx, lambda: std_actions(extra=[("work", work, 2.0, True)]), camo_seed=2105,
                     body_opts=dict(pack=None),
                     notes="Rifleman actions + work (2 s loop: kneeling, left hand hammering/turning, rifle held "
                           "muzzle-down in the right hand). G3-family rifle. Tool kit = tool pack with shovel + wrench "
                           "and a hip tool pouch (hammer, pliers); no hand-held tool prop.")


# ------------------------------------------------------------------ 6. medic
def role_medic():
    def bx(B):
        army_head(B); ir_helmet(B); chest_rig(B, 2, side=False)
        # aid bag on the back with a neutral team panel. NO red crescent / red cross is modelled.
        B.box("SA_Rig", "Chest", (0, -0.245, 1.25), (0.32, 0.19, 0.40), (-0.06, 0, 0))
        B.box("SA_Rig", "Chest", (0, -0.25, 1.46), (0.30, 0.17, 0.05), (-0.12, 0, 0))
        B.box("SA_Team", "Chest", (0, -0.343, 1.25), (0.14, 0.006, 0.14), (-0.06, 0, 0))
        B.box("SA_Team", "Chest", (0, -0.25, 1.49), (0.14, 0.09, 0.006), (-0.12, 0, 0))
        for s in (-1, 1):
            B.box("SA_Rubber", "Chest", (s * 0.15, -0.20, 1.25), (0.012, 0.15, 0.36), (-0.06, 0, 0))
        B.box("SA_Rig", "Hips", (-0.20, 0.03, 0.97), (0.06, 0.13, 0.13), (0, 0, 0.25))
        B.box("SA_Team", "Hips", (-0.232, 0.03, 0.97), (0.004, 0.06, 0.06), (0, 0, 0.25))
        sh, el = K.SH[1], K.ELB[1]
        d1 = (el - sh).normalized()
        B.tube("SA_Team", "RightUpperArm", [sh + d1 * 0.05, sh + d1 * 0.17], [(0.066, 0.068)] * 2, seg=8, caps=False)

    def heal(t):
        p = kneel_relaxed(K.base_pose())
        b = math.sin(4 * PI * t)
        p["spine"] = V((D(-26), 0, D(-4))); p["chest"] = V((D(-14) + D(3) * b, 0, 0))
        p["neck"] = V((D(-10), 0, 0)); p["head"] = V((D(-18), 0, D(6) * math.sin(2 * PI * t)))
        p["w_loc"], p["w_q"] = carry((0.24, 0.20, 1.00), (0.25, 0.45, -0.86), (0.9, 0.0, 0.3))
        left_free(p, (-0.06, 0.38, 1.07 - 0.03 * max(0.0, b)), (0.3, 0.9, -0.5), (0.0, 0.3, 1.0))
        p["elbow_pole"] = {1: V((0.4, -0.3, 0.0)), -1: V((-0.5, 0.0, -0.3))}
        return p

    K.GROUND_SOLVE = {"die", "heal"}
    return make_role("ir_medic", "IR_Medic_Body", gun("Rifle", build_ak_fold, (0, 0.89, 0.0)), bx,
                     lambda: std_actions(extra=[("heal", heal, 2.0, True)]), camo_seed=2106, body_opts=dict(pack=None),
                     notes="Rifleman actions + heal (2 s kneeling treatment loop). Aid bag, hip pouch and the wide "
                           "right armband are SA_Team neutral patches; NO red crescent / red cross emblem is modelled "
                           "(the client must supply an approved emblem before release). AK with folding stock.")


# ------------------------------------------------------------------ 7. IRGC special forces
def role_irgc():
    def bx(B):
        face_features(B); flag_patch(B, -1); shemagh(B, drape=False)
        B.box("SA_Rubber", "Head", K.HM_HELMET + V((0.10, 0.10, -0.05)), (0.01, 0.07, 0.01), (0, 0, 0.6))  # boom mic
        B.box("SA_Coyote", "Chest", (0.0, -0.17, 1.22), (0.22, 0.07, 0.24))                              # back panel
        B.box("SA_Team", "Chest", (0.0, -0.206, 1.30), (0.10, 0.004, 0.05))
        B.cyl("SA_Rubber", "Chest", (0.19, -0.08, 1.52), 0.006, 0.36, seg=4)                              # antenna
        for k in (-1, 1):
            B.box("SA_Coyote", "Chest", (k * 0.12, 0.215, 1.08), (0.07, 0.05, 0.10))
    return make_role("irgc_sf", "IRGC_SF_Body", gun("Rifle", build_ak_mod, (0, 0.855, 0.0)), bx, lambda: std_actions(),
                     palette=PAL_IRGC, camo_seed=2107, camo=camo_digital, overrides=IRGC_OVERRIDES,
                     body_opts=dict(pack=None, radio=True, helmet="combat", nvg=False, holster=True, mag_pouches=True,
                                    carrier="plate", knee_pads=True, helmet_mat="SA_Coyote",
                                    remap={"SA_CamoGear": "SA_Coyote"}),
                     notes="Rifleman actions. Distinct from the regular army: digital (pixel) camouflage, coyote "
                           "plate carrier + modern helmet with rails/headset, knee pads, shemagh, modernised AK with "
                           "magnified optic and suppressor, tan boots/gloves.")


# ------------------------------------------------------------------ 8. paratrooper
ATTACH = V((0.0, 0.0, 1.49))
CONN_X = 0.12
DESC_LIFT = [0.06]
LAND_KEYS = []


def role_para():
    def bx(B):
        army_head(B); ir_helmet(B); chest_rig(B, 3, side=False, team=False)
        O, Wb = "SA_Olive", "SA_Webbing"
        B.box(O, "Chest", (0, -0.215, 1.24), (0.30, 0.13, 0.40), (-0.05, 0, 0))
        B.box(O, "Chest", (0, -0.222, 1.45), (0.28, 0.12, 0.05), (-0.10, 0, 0))
        B.box("SA_Team", "Chest", (0, -0.226, 1.478), (0.15, 0.08, 0.006), (-0.10, 0, 0))
        for s in (-1, 1):
            x = s * CONN_X
            B.tube(Wb, "Chest", [V((x, -0.15, 1.12)), V((x, -0.10, 1.44)), V((x, 0.0, 1.515)), V((x, 0.13, 1.47)),
                                 V((s * 0.11, 0.19, 1.30)), V((s * 0.10, 0.19, 1.10))], [(0.024, 0.006)] * 6, seg=4)
            B.box("SA_Metal", "Chest", (x, 0.02, 1.522), (0.04, 0.05, 0.02))
            hp, kn = K.HIP[s], K.KNEE[s]
            d1 = (kn - hp).normalized()
            B.tube(Wb, f"{K.SIDE[s]}UpperLeg", [hp + d1 * 0.13, hp + d1 * 0.17], [(0.099, 0.101)] * 2, seg=10, caps=False)
            B.tube(Wb, "Hips", [V((s * 0.10, 0.13, 1.04)), V((s * 0.105, 0.115, 0.93)), hp + d1 * 0.15 + V((0, 0.09, 0))],
                   [(0.022, 0.006)] * 3, seg=4)
        B.tube(Wb, "Chest", [V((-0.12, 0.196, 1.30)), V((0.12, 0.196, 1.30))], [(0.006, 0.02)] * 2, seg=4)
        B.box("SA_Metal", "Chest", (0, 0.20, 1.30), (0.05, 0.012, 0.03))
        B.box("SA_Team", "Chest", (0, 0.205, 1.30), (0.03, 0.004, 0.018))
        B.box(O, "Hips", (-0.02, 0.215, 0.975), (0.28, 0.095, 0.15))
        B.box(O, "Hips", (-0.02, 0.265, 0.975), (0.24, 0.012, 0.12))
        B.box("SA_Metal", "Hips", (0.10, 0.27, 0.99), (0.02, 0.02, 0.05))

    EXTRA_OBJS.append(lambda arm: [K.bone_empty("ChuteAttach", "Chest", ATTACH)])

    def descend_pose(t):
        p = K.base_pose()
        sw = math.sin(2 * PI * t)
        p["hips_pos"] = V((0.0, 0.0, 0.958 + DESC_LIFT[0]))
        p["hips_rot"] = V((D(3) * sw, D(2.5) * math.sin(2 * PI * t + 0.7), 0))
        p["spine"] = V((D(-2), 0, 0)); p["chest"] = V((D(-1.5) * sw, 0, 0))
        p["neck"] = V((D(6), 0, 0)); p["head"] = V((D(14), 0, D(6) * math.sin(2 * PI * t + 1.4)))
        hz = p["hips_pos"].z
        for s in (-1, 1):
            lag = D(4) * math.sin(2 * PI * t - 0.9)
            q = (Matrix.Rotation(D(4) * s, 3, "Z") @ Matrix.Rotation(D(-42) + lag, 3, "X")).to_quaternion()
            p["foot"][s] = {"ankle": V((s * 0.075, 0.05 + 0.03 * math.sin(2 * PI * t - 0.9), hz - 0.80)), "q": q}
        p["knee_pole"] = {1: V((0.05, 1, 0.0)), -1: V((-0.05, 1, 0.0))}
        p["lgrip"] = 0.0
        p["lfree"] = V((-0.21, 0.03, 1.80 + 0.01 * sw))
        p["lfree_q"] = K.hand_q((0.7, 0.3, 0.6), (-0.6, 0.6, -0.2))
        p["elbow_pole"] = {1: V((0.3, -0.2, -0.3)), -1: V((-0.6, 0.0, 0.1))}
        p["rifle_rot"] = V((D(-12), 0, D(4)))
        return p

    def kneel_up(p):
        p = K.kneel_pose(p)
        p["aim"] = 0.0
        p["spine"] = V((D(-12), 0, 0)); p["chest"] = V((D(-4), 0, 0)); p["neck"] = V((0, 0, 0)); p["head"] = V((D(6), 0, 0))
        p["hips_rot"] = V((D(4), 0, D(-10)))
        p["elbow_pole"] = {1: V((0.3, -0.2, -0.3)), -1: V((-0.3, 0.05, -0.4))}
        return p

    def land_keys():
        k0 = descend_pose(0.0)
        k1 = K.base_pose()
        k1["hips_pos"] = V((0.0, -0.03, 0.78)); k1["spine"] = V((D(-14), 0, 0)); k1["chest"] = V((D(-8), 0, 0))
        k1["head"] = V((D(6), 0, 0))
        k1["foot"] = {1: K.place_foot(0.07, 0.05, 0, 0, D(-3)), -1: K.place_foot(-0.07, 0.05, 0, 0, D(3))}
        k1["knee_pole"] = {1: V((0.05, 1, 0.0)), -1: V((-0.05, 1, 0.0))}
        k1["lgrip"] = 0.0; k1["lfree"] = V((-0.16, 0.12, 1.45)); k1["lfree_q"] = K.hand_q((0.6, 0.6, 0.3), (-0.5, 0.2, 0.8))
        k1["rifle_rot"] = V((D(-10), 0, D(4)))
        k2 = K.lerp(k1, k1, 0)
        k2["hips_pos"] = V((0.14, -0.08, 0.40)); k2["hips_rot"] = V((D(-10), D(55), D(-10)))
        k2["spine"] = V((D(-18), D(10), 0)); k2["chest"] = V((D(-14), D(8), 0)); k2["head"] = V((D(-10), D(-20), 0))
        k2["foot"] = {1: K.place_foot(0.24, 0.10, 0.02, D(10), D(-20)), -1: K.place_foot(0.10, 0.12, 0.10, D(20), D(-15))}
        k2["knee_pole"] = {1: V((0.6, 1, 0.3)), -1: V((0.5, 1, 0.4))}
        k3 = K.lerp(k2, k2, 0)
        k3["hips_pos"] = V((0.30, -0.18, 0.20)); k3["hips_rot"] = V((D(20), D(80), D(-15)))
        k3["spine"] = V((D(-25), 0, 0)); k3["chest"] = V((D(-15), 0, 0)); k3["head"] = V((D(-25), D(-25), 0))
        k3["foot"] = {1: K.place_foot(0.55, 0.25, 0.25, D(20), D(-60)), -1: K.place_foot(0.45, 0.30, 0.35, D(20), D(-60))}
        k3["knee_pole"] = {1: V((0.3, 1, 0.8)), -1: V((0.3, 1, 0.8))}
        k4 = kneel_up(K.base_pose())
        k4["lgrip"] = 0.4; k4["lfree"] = V((-0.25, 0.15, 1.05))
        k5 = K.base_pose()
        k5["hips_pos"] = V((0.0, -0.02, 0.86)); k5["spine"] = V((D(-10), 0, 0)); k5["chest"] = V((D(-3), 0, 0))
        k5["foot"] = {1: K.place_foot(0.12, -0.05, 0, 0, D(-9)), -1: K.place_foot(-0.12, 0.10, 0, 0, D(7))}
        k6 = K.act_idle(0.0)
        return [(0.0, k0), (0.12, k1), (0.45, k2), (0.8, k3), (1.3, k4), (1.85, k5), (2.25, k6), (2.4, k6)]

    def act_land(t):
        s = t * 2.4
        for (ta, a), (tb, b) in zip(LAND_KEYS, LAND_KEYS[1:]):
            if s <= tb:
                return K.lerp(a, b, K.smoothstep((s - ta) / (tb - ta)))
        return LAND_KEYS[-1][1]

    def actions():
        for _ in range(3):
            DESC_LIFT[0] -= K.pose_minz(descend_pose(0.0))
        LAND_KEYS[:] = land_keys()
        return std_actions() + [("para_descend", descend_pose, 2.0, True), ("para_land", act_land, 2.4, False)]

    K.GROUND_SOLVE = {"die", "para_land"}
    return make_role("ir_paratrooper", "IR_Paratrooper_Body", gun("Rifle", build_ak_fold, (0, 0.89, 0.0)), bx, actions,
                     camo_seed=2108, body_opts=dict(pack=None),
                     report_extra={"chute_attach_rest": list(ATTACH), "parachute_glb":
                                   "reuse godot/assets/units3d/paratrooper/parachute_personnel.glb"},
                     notes="Same harness / para actions as the U.S. paratrooper: para_descend (2 s loop), para_land "
                           "(2.4 s one-shot, last frame = idle frame 0). ChuteAttach empty on Chest at the riser "
                           "point. Reuses the existing parachute_personnel.glb. AK with folding stock.")


# =============================================================================== face close-ups (after the build)
def render_faces(tiles):
    os.makedirs(tiles, exist_ok=True)
    sc = bpy.context.scene
    arm = bpy.data.objects["Armature"]
    arm.animation_data.action = bpy.data.actions["idle"]; sc.frame_set(0)
    cam = sc.camera
    cam.data.type = "PERSP"; cam.data.lens = 85
    tgt = V((0, 0.08, 1.625))
    cam.location = tgt + V((0.30, 0.74, 0.07))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.cycles.samples = 24
    sc.render.resolution_x, sc.render.resolution_y = 240, 260
    beard, mous = bpy.data.objects["Beard"], bpy.data.objects["Moustache"]
    for nm, hb, hm in (("full", False, False), ("moustache", True, False), ("shaven", True, True)):
        beard.hide_render, mous.hide_render = hb, hm
        sc.render.filepath = os.path.join(tiles, f"face_{ROLE}_{nm}.png")
        bpy.ops.render.render(write_still=True)
    beard.hide_render = mous.hide_render = False


ROLES = {"ir_rifleman": role_rifleman, "ir_rpg": role_rpg, "ir_mg": role_mg, "ir_sniper": role_sniper,
         "ir_engineer": role_engineer, "ir_medic": role_medic, "irgc_sf": role_irgc, "ir_paratrooper": role_para}
if ROLE not in ROLES:
    sys.exit(f"unknown role {ROLE}; one of {list(ROLES)}")
os.makedirs(OUT, exist_ok=True)
rep = K.build(ROLES[ROLE](), OUT, PREV, ONLY_ANIMS)
if FACES:
    if not PREV:
        sys.exit("--faces needs --previews (it reuses the preview lights)")
    render_faces(FACES)
print(f"INF_IRAN {ROLE} OK", rep["triangles"])
