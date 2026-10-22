"""Steel Accord - base flag props: flag_iran.glb and flag_usa.glb (Blender bpy 5.x, procedural, original).

Run:  python3 tools/art/prop_flag_3d.py godot/assets/units3d/props [--previews docs/screens]
Out:  flag_iran.glb, flag_usa.glb (textures embedded; no loose files are written next to them)
      with --previews: docs/screens/flags.png (both GLBs re-imported and rendered at two frames of `wave`)

Each GLB holds:
  `Pole`      8 m tapered mast on a small concrete plinth, ball finial; an `SA_Team` collar on the plinth (team tint)
  `Flag`      cloth: subdivided plane (28 x 12 quads), double-sided material, skinned to `Armature`
  `Armature`  7-bone chain `Flag0`..`Flag6` along the fly (+X); `Flag0` (hoist) only twitches slightly
  action `wave` (2.0 s, 61 frames, loop; first frame == last frame): travelling wave + slight droop + twist
Conventions: metres, +Z up, origin = foot of the pole on the ground. The flag flies toward +X (Blender +X = Godot +X);
rotate the prop about Y in Godot to set the wind direction. Hoist edge at the pole, top edge 0.15 m below the truck.

Flag artwork is drawn procedurally here (numpy, no images / fonts / text):
  Iran: green-white-red horizontal tricolour (7:4). The central emblem is a SIMPLIFIED geometric red figure (two pairs
        of crescents and a central blade with a small diamond) and the white band edging is a row of simple white
        comb motifs - neither reproduces the calligraphy of the real flag (no text is drawn).
  USA:  13 stripes, blue canton over 7 stripes, 50 stars drawn as white dots in the 9-row staggered layout (19:10).
`flag_image(kind, w)` is also used by inf_iran_3d.py for the small uniform shoulder patches.
"""
import os, sys, math
if __name__ == "__main__" and os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)
import numpy as np

PI = math.pi
D = math.radians

IR_GREEN, IR_WHITE, IR_RED = (35, 159, 64), (255, 255, 255), (218, 0, 0)
US_RED, US_WHITE, US_BLUE = (178, 34, 52), (255, 255, 255), (60, 59, 110)
ASPECT = {"iran": 7 / 4, "usa": 1.9}


# =============================================================================== flag artwork (procedural)
def _draw_iran(W, H):
    img = np.zeros((H, W, 3), float)
    y, x = np.mgrid[0:H, 0:W] + 0.5
    b = H / 3.0
    img[:] = IR_WHITE
    img[y < b] = IR_GREEN
    img[y >= 2 * b] = IR_RED
    # simplified white band edging: 11 comb motifs along the inner edge of the green band and of the red band
    n = 11
    sp = W / n
    for k in range(n):
        cx = (k + 0.5) * sp
        for top, sgn in ((b, -1), (2 * b, 1)):           # green band: motif above the edge; red band: below
            e0 = top + sgn * 0.045 * b                    # motif base line (closest to the white band)
            bar = (np.abs(x - cx) < 0.28 * sp) & (np.abs(y - e0) < 0.016 * b)
            m = bar
            for t in (-0.22, 0.0, 0.22):                  # three short ticks pointing away from the white band
                y0, y1 = sorted((e0, e0 + sgn * 0.13 * b))
                m = m | ((np.abs(x - (cx + t * sp)) < 0.025 * sp) & (y > y0) & (y < y1))
            img[m] = IR_WHITE
    # simplified central emblem (red, geometric): crescents + blade + diamond, fits inside the white band
    S = b * 0.93
    u = (x - W / 2) / S
    v = (H / 2 - y) / S
    vs = v * 0.80                                    # crescents taller than wide (tulip-like outline)
    r = np.hypot(u, vs)
    em = np.zeros_like(u, bool)
    for s in (-1, 1):
        outer = (r < 0.40) & (np.hypot(u + s * 0.075, vs + 0.01) > 0.385) & (s * u > 0.03) & (v < 0.43)
        inner = (r < 0.255) & (np.hypot(u + s * 0.06, vs + 0.01) > 0.24) & (s * u > 0.045) & (v < 0.27)
        em |= outer | inner
    w = np.where(v > -0.30, 0.026, 0.026 * np.clip((v + 0.46) / 0.16, 0, 1))
    em |= (np.abs(u) < w) & (v > -0.46) & (v < 0.30)                     # blade
    em |= (np.abs(u) / 0.05 + np.abs(v - 0.37) / 0.045) < 1.0            # diamond above the blade
    img[em] = IR_RED
    return img


def _draw_usa(W, H):
    img = np.zeros((H, W, 3), float)
    y, x = np.mgrid[0:H, 0:W] + 0.5
    s = H / 13.0
    stripe = (y // s).astype(int)
    img[:] = US_WHITE
    img[stripe % 2 == 0] = US_RED
    cw, ch = 0.76 * H, 7 * s
    can = (x < cw) & (y < ch)
    img[can] = US_BLUE
    rad = 0.0616 * H * 0.30                          # simplified star = dot (smaller than the star's span)
    for row in range(9):
        cy = ch * (row + 1) / 10
        cols = range(6) if row % 2 == 0 else range(5)
        for c in cols:
            cx = cw * ((2 * c + 1) if row % 2 == 0 else (2 * c + 2)) / 12
            img[(x - cx) ** 2 + (y - cy) ** 2 < rad * rad] = US_WHITE
    return img


def flag_image(kind, w=700, ss=3):
    """RGB uint8 array (h, w, 3) of the flag artwork, supersampled ss x for clean edges."""
    from PIL import Image
    h = int(round(w / ASPECT[kind]))
    big = (_draw_iran if kind == "iran" else _draw_usa)(w * ss, h * ss)
    im = Image.fromarray(np.clip(big, 0, 255).astype(np.uint8), "RGB").resize((w, h), Image.LANCZOS)
    return np.asarray(im)


def save_flag_png(kind, path, w=700):
    from PIL import Image
    Image.fromarray(flag_image(kind, w), "RGB").save(path)
    return path


# =============================================================================== 3D prop
POLE_H = 8.0
FLAG_H = {"iran": 1.40, "usa": 1.30}
NB = 7                        # bones along the fly
NX, NZ = 28, 12               # cloth quads


def build_flag(kind, out, tmpdir):
    import bpy, bmesh
    from mathutils import Matrix, Vector as V, Quaternion, Euler
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 30
    tex = save_flag_png(kind, os.path.join(tmpdir, f"flag_{kind}_tex.png"), 700 if kind == "iran" else 760)

    def mat(name, rgb, rough, metal=0.0, tex_=None, double=False):
        m = bpy.data.materials.new(name); m.use_nodes = True
        bs = m.node_tree.nodes["Principled BSDF"]
        bs.inputs["Base Color"].default_value = (*rgb, 1)
        bs.inputs["Roughness"].default_value = rough; bs.inputs["Metallic"].default_value = metal
        if tex_:
            t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex_); t.image.pack()
            t.extension = "EXTEND"
            m.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
        m.use_backface_culling = not double
        return m

    m_flag = mat("SA_FlagIR" if kind == "iran" else "SA_FlagUS", (1, 1, 1), 0.8, tex_=tex, double=True)
    m_pole = mat("SA_Pole", (0.55, 0.56, 0.58), 0.35, 0.8)
    m_gold = mat("SA_Finial", (0.72, 0.56, 0.25), 0.3, 1.0)
    m_conc = mat("SA_Concrete", (0.42, 0.41, 0.38), 0.95)
    m_team = mat("SA_Team", (0.75, 0.75, 0.75), 0.7)

    # ---------------------------------------------------------------- pole + plinth + finial
    bm = bmesh.new()
    mats = [m_pole, m_gold, m_conc, m_team]

    def tag(vs, mi):
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = mi

    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.055, radius2=0.035, depth=POLE_H - 0.25,
                               matrix=Matrix.Translation((0, 0, 0.25 + (POLE_H - 0.25) / 2)))["verts"]
    tag(vs, 0)
    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.05, radius2=0.05, depth=0.05,
                               matrix=Matrix.Translation((0, 0, POLE_H - 0.02)))["verts"]          # truck
    tag(vs, 0)
    vs = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.07,
                                   matrix=Matrix.Translation((0, 0, POLE_H + 0.07)))["verts"]
    tag(vs, 1)
    vs = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.11)) @
                               Matrix.Diagonal((0.62, 0.62, 0.22, 1)))["verts"]
    tag(vs, 2)
    vs = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.245)) @
                               Matrix.Diagonal((0.42, 0.42, 0.05, 1)))["verts"]
    tag(vs, 2)
    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.085, radius2=0.085, depth=0.12,
                               matrix=Matrix.Translation((0, 0, 0.33)))["verts"]                  # team collar
    tag(vs, 3)
    for z in (1.2, POLE_H - 0.5):                                                                 # halyard cleats
        vs = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.045, 0, z)) @
                                   Matrix.Diagonal((0.02, 0.03, 0.12, 1)))["verts"]
        tag(vs, 0)
    me = bpy.data.meshes.new("Pole"); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    pole = bpy.data.objects.new("Pole", me); sc.collection.objects.link(pole)
    for p in me.polygons:
        p.use_smooth = abs(p.normal.z) < 0.5

    # ---------------------------------------------------------------- cloth
    L, Hh = FLAG_H[kind] * ASPECT[kind], FLAG_H[kind]
    X0 = 0.065                                     # hoist edge just clear of the pole
    ZT = POLE_H - 0.15
    ZC = ZT - Hh / 2
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    grid = [[bm.verts.new((X0 + L * i / NX, 0.0, ZT - Hh * j / NZ)) for j in range(NZ + 1)] for i in range(NX + 1)]
    for i in range(NX):
        for j in range(NZ):
            f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            for lp in f.loops:
                c = lp.vert.co
                lp[uvl].uv = ((c.x - X0) / L, (c.z - (ZT - Hh)) / Hh)
    me = bpy.data.meshes.new("Flag"); bm.to_mesh(me); bm.free()
    me.materials.append(m_flag)
    for p in me.polygons:
        p.use_smooth = True
    flag = bpy.data.objects.new("Flag", me); sc.collection.objects.link(flag)

    # ---------------------------------------------------------------- armature: chain along +X at mid-height
    ad = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", ad); sc.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    seg = L / NB
    prev = None
    for k in range(NB):
        eb = ad.edit_bones.new(f"Flag{k}")
        eb.head = (X0 + k * seg, 0, ZC); eb.tail = (X0 + (k + 1) * seg, 0, ZC)
        eb.roll = 0.0
        if prev:
            eb.parent = prev; eb.use_connect = True
        prev = eb
    bpy.ops.object.mode_set(mode="OBJECT")
    for k in range(NB):
        flag.vertex_groups.new(name=f"Flag{k}")
    for v in me.vertices:                          # linear blend between neighbouring bone centres
        f_ = (v.co.x - X0) / seg - 0.5
        k0 = max(0, min(NB - 1, math.floor(f_)))
        t = min(max(f_ - k0, 0.0), 1.0) if f_ >= 0 else 0.0
        k1 = min(NB - 1, k0 + 1)
        flag.vertex_groups[f"Flag{k0}"].add([v.index], 1 - t if k1 != k0 else 1.0, "REPLACE")
        if k1 != k0 and t > 1e-4:
            flag.vertex_groups[f"Flag{k1}"].add([v.index], t, "REPLACE")
    flag.parent = arm
    mod = flag.modifiers.new("Armature", "ARMATURE"); mod.object = arm

    # ---------------------------------------------------------------- wave: 2 s loop
    arm.animation_data_create()
    act = bpy.data.actions.new("wave"); act.use_fake_user = True
    arm.animation_data.action = act
    rest = {k: ad.bones[f"Flag{k}"].matrix_local.to_3x3() for k in range(NB)}
    NF = 60
    for f in range(NF + 1):
        t = (f % NF) / NF
        for k in range(NB):
            pb = arm.pose.bones[f"Flag{k}"]
            pb.rotation_mode = "QUATERNION"
            ph = 2 * PI * t - 0.95 * k
            amp = D(3.0) if k == 0 else D(8.0 + 2.0 * k)
            yaw = amp * math.sin(ph)                                    # about world Z: the travelling wave
            droop = D(1.2 + 0.25 * k) * (1 + 0.3 * math.sin(ph + 1.3))  # about world Y: fly end sags a little
            twist = D(3.0 + 2.0 * k) * math.sin(ph + 1.9)               # about the bone axis (world X): ripples
            qw = (Quaternion((0, 0, 1), yaw) @ Quaternion((0, 1, 0), droop) @ Quaternion((1, 0, 0), twist))
            R = rest[k]
            ql = (R.inverted() @ qw.to_matrix() @ R).to_quaternion()   # world-axis rotation in the bone frame
            pb.rotation_quaternion = ql
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    act.frame_range = (0, NF); act.use_frame_range = True; act.use_cyclic = True
    sc.frame_start, sc.frame_end = 0, NF
    sc.frame_set(0)

    glb = os.path.join(out, f"flag_{kind}.glb")
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=False, export_animations=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_range=False,
                              export_anim_single_armature=True, export_reset_pose_bones=True)
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in (pole, flag)}
    print(f"FLAG {kind} OK", tris, f"cloth {L:.2f} x {Hh:.2f} m")
    return tris


def preview(out, prev):
    """Re-import both GLBs and render them at two frames of `wave` -> prev/flags.png."""
    import bpy, bmesh
    from mathutils import Vector as V
    from PIL import Image
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    arms = []
    for kind, x in (("iran", -1.9), ("usa", 1.9)):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(out, f"flag_{kind}.glb"))
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.parent is None:
                o.location.x += x
        a = [o for o in new if o.type == "ARMATURE"][0]
        names = sorted(o.name for o in new)
        acts = [s.action for tr in (a.animation_data.nla_tracks if a.animation_data else []) for s in tr.strips]
        act = acts[0] if acts else a.animation_data.action
        a.animation_data.action = act
        for tr in a.animation_data.nla_tracks:
            tr.mute = True
        arms.append((kind, a, act, names))
    g = bpy.data.meshes.new("ground"); b = bmesh.new()
    bmesh.ops.create_grid(b, x_segments=1, y_segments=1, size=40); b.to_mesh(g); b.free()
    go = bpy.data.objects.new("ground", g); sc.collection.objects.link(go)
    gm = bpy.data.materials.new("g"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.36, 0.34, 0.30, 1)
    g.materials.append(gm)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3.2; sun.rotation_euler = (D(40), D(10), D(-35))
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.6, 0.68, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.lens = 38
    cam.location = (0.8, -13.5, 5.0)
    cam.rotation_euler = (V((0.8, 0, 4.1)) - V(cam.location)).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "Standard"
    sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"; sc.cycles.use_denoising = False
    sc.render.threads_mode = "FIXED"; sc.render.threads = 2
    sc.render.resolution_x, sc.render.resolution_y = 560, 440
    tiles = []
    tmp = os.path.join(prev, "_flags_tmp.png")
    for f in (0, 30):
        sc.frame_set(f)
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        tiles.append(Image.open(tmp).convert("RGB").copy())
    os.remove(tmp)
    sheet = Image.new("RGB", (560 * 2, 440), (30, 30, 30))
    for i, im in enumerate(tiles):
        sheet.paste(im, (560 * i, 0))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    dr.text((8, 6), "flag_iran.glb / flag_usa.glb  -  wave f0", fill=(20, 20, 20))
    dr.text((568, 6), "wave f30", fill=(20, 20, 20))
    sheet.save(os.path.join(prev, "flags.png"))
    print("FLAGS PREVIEW", [a[3] for a in arms])


if __name__ == "__main__":
    argv = sys.argv[1:]
    prev = None
    if "--previews" in argv:
        i = argv.index("--previews"); prev = argv[i + 1]; del argv[i:i + 2]
    out = argv[0] if argv else "."
    os.makedirs(out, exist_ok=True)
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="sa_flag_")
    for kind in ("iran", "usa"):
        build_flag(kind, out, tmpdir)          # the artwork PNG is packed into the GLB, then the temp dir goes
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    if prev:
        preview(out, prev)
