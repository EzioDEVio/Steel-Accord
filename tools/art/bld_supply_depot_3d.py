"""Steel Accord - PILOT 3D structure: US 'Supply Depot' (procedurally modelled + texture-baked in Blender, bpy 5.x).

Run:  python3 -I bld_supply_depot_3d.py <out_dir> [--previews <dir>] [--concept <overhead.png>]
Out:  <out_dir>/supply_depot.glb with two mesh nodes:
        Building - slab, warehouse, docks, canopy, roof hardware   (materials SD_SupplyDepot + SA_Team)
        Props    - crates, pallets, containers, barriers, fence, light poles (SD_SupplyDepot + SD_Fence)
      --previews renders front/side/rear/top/rts PNGs of the *exported* GLB (re-imported) with Cycles CPU, and
      --concept additionally writes pilot3d_depot_vs_concept.png (RTS render beside the concept image).

Conventions: metres; origin = centre of the slab's bottom face (ground); slab 22 (X) x 18 (Y) m, top at 0.25 m;
front (loading bays) faces Blender -Y = Godot +Z. Original design built from the client's concept sheet.

Texturing pipeline (deterministic):
  1. every primitive is tagged with a source surface (concrete, olive ribbed roof, door slats, crate, hazard ...);
     each source surface is a tileable numpy texture mapped by a world-space planar 'tile' UV (constant texel size);
  2. a non-overlapping 'atlas' UV is generated over Building + Props together (smart project);
  3. Cycles bakes the source colour into one atlas, then ambient occlusion (with a ground plane);
  4. albedo x AO is composited in numpy -> one JPEG atlas -> a single Principled BSDF material (glTF-safe).
  The chain-link fence keeps its own small tiling RGBA texture (alpha blend), and SA_Team stays a plain
  material so the game's team tint can still find it.
"""
import bpy, bmesh, math, sys, os, tempfile
import numpy as np
from mathutils import Matrix, Euler, Vector
from PIL import Image

# ------------------------------------------------------------------ args
argv = sys.argv[1:]
def _opt(name):
    if name in argv:
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
    return None
PREVIEWS = _opt("--previews")
CONCEPT = _opt("--concept")
ONLY = _opt("--only")                    # e.g. --only rts,front : render just these preview shots
SKIP_BUILD = "--previews-only" in argv
if SKIP_BUILD:
    argv.remove("--previews-only")
OUT = argv[0] if argv else "."
os.makedirs(OUT, exist_ok=True)
TMP = tempfile.mkdtemp(prefix="sd3d_")
ATLAS = 4096          # final albedo atlas
AO_RES = 2048         # AO bake (low frequency; upscaled)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
PI = math.pi
V = Vector


def build_asset():
    global scene
    # ================================================================== tileable source textures (numpy, sRGB 0..1)
    N = 512
    UU = ((np.arange(N) + 0.5) / N)[None, :].repeat(N, 0)      # u across columns
    VV = ((np.arange(N) + 0.5) / N)[:, None].repeat(N, 1)      # v across rows (row 0 = bottom in Blender)


    def noise(sx, sy, seed):
        """Tileable gaussian-filtered noise, unit std; sx/sy ~ feature size in px along u/v."""
        w = np.random.default_rng(seed).standard_normal((N, N))
        fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.fftfreq(N)[None, :]
        r = np.real(np.fft.ifft2(np.fft.fft2(w) * np.exp(-((fx * sx) ** 2 + (fy * sy) ** 2))))
        return r / (r.std() + 1e-9)


    def frac(a):
        return a - np.floor(a)


    def col(r, g, b):
        return np.array([r, g, b], np.float32) / 255.0


    def shade(base, k):
        return base[None, None, :] * k[..., None]


    def lines(coord, count, width):
        """1 where a line (fractional width of a period) sits, else 0."""
        return (frac(coord * count) < width).astype(np.float32)


    def t_conc():          # tan cast concrete walls / pilasters / parapets  (S = 4 m)
        k = 1 + 0.025 * noise(70, 70, 1) + 0.03 * noise(3, 3, 2) - 0.04 * np.clip(noise(2, 90, 3), 0, None)
        k *= 1 - 0.12 * lines(VV, 3, 0.006)
        k *= 1 - 0.06 * lines(UU, 2, 0.004)
        return shade(col(176, 162, 140), k)


    def t_slab():          # pavement slab with 3 m joints  (S = 6 m)
        k = 1 + 0.025 * noise(90, 90, 4) + 0.03 * noise(3, 3, 5) - 0.05 * np.clip(noise(25, 25, 6) - 1.2, 0, None)
        k *= 1 - 0.35 * np.maximum(lines(UU, 2, 0.004), lines(VV, 2, 0.004))
        return shade(col(156, 146, 131), k)


    def t_roof():          # olive standing-seam roof (S = 4 m, 8 ribs)
        f = frac(UU * 8)
        k = np.where(f < 0.1, 1.22, np.where(f < 0.2, 0.74, 1.0 - 0.08 * (f - 0.2)))
        k = k * (1 + 0.02 * noise(80, 80, 7) + 0.025 * noise(2, 2, 8) - 0.05 * np.clip(noise(2, 70, 9), 0, None))
        k *= 1 - 0.18 * lines(VV, 1, 0.004)
        return shade(col(102, 103, 82), k)


    def t_clad():          # olive vertical-ribbed wall cladding (S = 3 m, 12 ribs)
        f = frac(UU * 10)
        k = np.where(f < 0.25, 1.16, np.where((f > 0.5) & (f < 0.68), 0.76, 1.0))
        k = k * (1 + 0.025 * noise(80, 80, 10) + 0.02 * noise(2, 2, 11) - 0.06 * np.clip(noise(2, 60, 12), 0, None))
        return shade(col(90, 92, 72), k)


    def t_door():          # grey roll-up door slats (S = 2 m, 20 slats)
        f = frac(VV * 14)
        k = np.where(f < 0.14, 0.62, np.where(f < 0.3, 1.14, 1.0)) * (1 + 0.04 * noise(40, 40, 13) + 0.02 * noise(2, 2, 14))
        return shade(col(146, 146, 140), k)


    def t_container():     # green corrugated container (S = 3 m)
        s = np.sin(UU * 2 * PI * 10)
        k = (1 + 0.14 * np.tanh(3 * s)) * (1 + 0.03 * noise(50, 50, 15) + 0.02 * noise(2, 2, 16))
        k *= 1 - 0.1 * np.clip(noise(2, 50, 17), 0, None)
        return shade(col(78, 84, 62), k)


    def t_tarp():          # tan canvas tarp (S = 2 m)
        k = 1 + 0.07 * noise(30, 6, 18) + 0.05 * noise(6, 30, 19) + 0.02 * noise(2, 2, 20)
        k *= 1 - 0.15 * lines(UU + 0.25, 2, 0.006)
        return shade(col(176, 153, 115), k)


    def t_crate():         # olive ammo crates, plank lines, stencil marks (S = 1.2 m)
        k = 1 + 0.05 * noise(20, 4, 21) + 0.02 * noise(2, 2, 22)
        k *= 1 - 0.25 * lines(VV, 8, 0.03)
        k *= 1 - 0.55 * lines(UU, 2, 0.02)
        img = shade(col(98, 101, 66), k)
        fu, fv = frac(UU * 2), frac(VV * 2)
        st = (fu > 0.3) & (fu < 0.7) & (fv > 0.45) & (fv < 0.55)
        img[st] = col(190, 178, 120)
        return img


    def t_pallet():        # pallet wood (S = 1.2 m)
        k = (1 + 0.08 * noise(3, 40, 23) + 0.03 * noise(2, 2, 24)) * (1 - 0.5 * lines(UU, 6, 0.06))
        return shade(col(138, 112, 76), k)


    def t_hazard():        # yellow/black diagonal stripes (S = 1.6 m, 0.2 m bands)
        yel = (frac((UU + VV) * 4) < 0.5)
        img = np.where(yel[..., None], col(216, 172, 34)[None, None], col(32, 31, 28)[None, None])
        return img * (1 + 0.06 * noise(10, 10, 25))[..., None] * (1 - 0.15 * np.clip(noise(4, 4, 26) - 1.0, 0, None))[..., None]


    def t_flat(rgb, amp, seed, size=40):
        def f():
            return shade(col(*rgb), 1 + amp * noise(size, size, seed) + 0.5 * amp * noise(2, 2, seed + 1))
        return f


    def t_hvac():          # light grey HVAC / penthouse panels (S = 2 m)
        k = (1 + 0.03 * noise(40, 40, 27)) * (1 - 0.3 * np.maximum(lines(UU, 4, 0.01), lines(VV, 2, 0.01)))
        k *= 1 - 0.2 * lines(VV * 1.0, 24, 0.25) * (frac(UU * 4) > 0.5)        # grille fins on half the panels
        return shade(col(170, 168, 162), k)


    def t_glass():         # skylight glazing with frames (S = 2 m)
        frame = np.maximum(lines(UU, 4, 0.05), lines(VV, 2, 0.06))
        g = shade(col(58, 70, 88), 1 + 0.25 * (UU - VV) + 0.04 * noise(30, 30, 28))
        return np.where(frame[..., None] > 0, col(150, 152, 150)[None, None], g)


    def t_jersey():
        k = 1 + 0.05 * noise(50, 50, 29) + 0.03 * noise(2, 2, 30) - 0.05 * np.clip(noise(3, 3, 31) - 1.5, 0, None)
        return shade(col(150, 140, 123), k)


    SURF = {  # name: (texture fn, world size of one tile in metres)
        "conc": (t_conc, 4.0), "slab": (t_slab, 6.0), "roof": (t_roof, 4.0), "clad": (t_clad, 3.0),
        "door": (t_door, 2.0), "cont": (t_container, 3.0), "tarp": (t_tarp, 2.0), "crate": (t_crate, 1.2),
        "pallet": (t_pallet, 1.2), "hazard": (t_hazard, 1.6), "hvac": (t_hvac, 2.0), "glass": (t_glass, 2.0),
        "jersey": (t_jersey, 3.0),
        "metal": (t_flat((84, 86, 84), 0.05, 40), 2.0), "dark": (t_flat((30, 30, 28), 0.05, 42), 1.0),
        "yellow": (t_flat((214, 172, 42), 0.05, 44), 2.0), "lamp": (t_flat((255, 238, 186), 0.02, 46), 1.0),
        "rubber": (t_flat((26, 26, 25), 0.05, 48), 1.0), "olive": (t_flat((86, 92, 60), 0.06, 50), 2.0),
        "team": (t_flat((235, 235, 235), 0.0, 52), 1.0),
    }


    def np_to_image(name, arr, alpha=None, colorspace="sRGB"):
        """Save a (bottom-up) numpy RGB(+alpha) array as PNG in TMP and load it (generated images lose pixels on pack)."""
        a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
        if alpha is not None:
            a8 = np.concatenate([a8, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)[..., None]], 2)
        path = os.path.join(TMP, name + ".png")
        Image.fromarray(a8[::-1]).save(path)
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = colorspace
        return img


    def src_material(sname):
        fn, _ = SURF[sname]
        m = bpy.data.materials.new("SA_Team" if sname == "team" else "SRC_" + sname)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.85
        if sname == "team":
            bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = np_to_image("tile_" + sname, fn()); tex.interpolation = "Cubic"
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "tile"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        return m


    MATS = {s: src_material(s) for s in SURF}


    # ================================================================== geometry accumulator
    class Part:
        """Accumulates primitives per (surface, bevel) into bmeshes; build() makes one joined object."""

        def __init__(self, name):
            self.name, self.bms = name, {}

        def bm(self, m, bev=False):
            return self.bms.setdefault((m, bev), bmesh.new())

        def _drop_bottom(self, bm, verts):
            faces = {f for v in verts for f in v.link_faces}
            dead = []
            for f in faces:
                f.normal_update()
                if f.normal.z < -0.999:
                    dead.append(f)
            bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")

        def box(self, m, c, size, rot=(0, 0, 0), bottom=False, bev=False):
            bm = self.bm(m, bev)
            M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
            r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
            if not bottom:
                self._drop_bottom(bm, r["verts"])

        def span(self, m, x0, x1, y0, y1, z0, z1, bottom=False, bev=False):
            self.box(m, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)),
                     bottom=bottom, bev=bev)

        def cyl(self, m, c, r, depth, rot=(0, 0, 0), seg=10, r2=None, bottom=False):
            bm = self.bm(m)
            M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4()
            res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                                        radius2=r if r2 is None else r2, depth=depth, matrix=M)
            if not bottom:
                self._drop_bottom(bm, res["verts"])

        def strut(self, m, a, b, r, seg=6):
            a, b = V(a), V(b)
            d = b - a
            M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r,
                                  depth=d.length, matrix=M)

        def prism(self, m, pts, axis, a0, a1, bev=False):
            """Extrude a closed 2D profile. axis 'x': pts are (y, z), extruded over x in [a0, a1];
            axis 'y': pts are (x, z), extruded over y."""
            bm = self.bm(m, bev)
            if axis == "x":
                A = [bm.verts.new((a0, p, q)) for p, q in pts]; B = [bm.verts.new((a1, p, q)) for p, q in pts]
            else:
                A = [bm.verts.new((p, a0, q)) for p, q in pts]; B = [bm.verts.new((p, a1, q)) for p, q in pts]
            n = len(A)
            fs = [bm.faces.new(A[::-1]), bm.faces.new(B)]
            for i in range(n):
                fs.append(bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i])))
            bmesh.ops.recalc_face_normals(bm, faces=fs)
            self._drop_bottom(bm, A + B)

        def frustum(self, m, x0, x1, y0, y1, z0, z1, inset, bev=False):
            bm = self.bm(m, bev)
            A = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
            B = [bm.verts.new(p) for p in ((x0 + inset, y0 + inset, z1), (x1 - inset, y0 + inset, z1),
                                           (x1 - inset, y1 - inset, z1), (x0 + inset, y1 - inset, z1))]
            bm.faces.new(B)
            for i in range(4):
                bm.faces.new((A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]))

        def build(self):
            objs = []
            for (sname, bev), bm in sorted(self.bms.items()):
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                S = SURF[sname][1]
                uv = bm.loops.layers.uv.new("tile")
                for f in bm.faces:                       # world planar projection by dominant normal axis
                    n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
                    for lp in f.loops:
                        p = lp.vert.co
                        lp[uv].uv = ((p.x, p.y) if ax == 2 else (p.y, p.z) if ax == 0 else (p.x, p.z))
                        lp[uv].uv = (lp[uv].uv[0] / S, lp[uv].uv[1] / S)
                me = bpy.data.meshes.new(f"{self.name}_{sname}")
                bm.to_mesh(me); bm.free()
                o = bpy.data.objects.new(me.name, me); scene.collection.objects.link(o)
                me.materials.append(MATS[sname])
                if bev:
                    b = o.modifiers.new("bv", "BEVEL")
                    b.width = 0.035; b.segments = 1; b.limit_method = "ANGLE"; b.angle_limit = math.radians(40)
                    b.harden_normals = True; b.use_clamp_overlap = True
                objs.append(o)
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                bpy.context.view_layer.objects.active = o
                for md in list(o.modifiers):
                    bpy.ops.object.modifier_apply(modifier=md.name)
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            bpy.ops.object.join()
            j = bpy.context.active_object; j.name = self.name; j.data.name = self.name
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
            return j


    # ================================================================== layout constants
    SL = 0.25                                   # slab top
    BX0, BX1, BY0, BY1 = -6.1, 6.1, -4.0, 6.0   # warehouse walls (front = BY0, faces -Y)
    WH, RZ, PZ = 6.2, 6.3, 6.75                 # wall top, roof deck, parapet top
    DZ = SL + 1.0                               # loading dock top
    DOOR_X = (-3.85, 0.0, 3.85); DW = 2.9       # roll-up doors (centres, width)
    DTOP = 4.15
    B = Part("Building")
    P = Part("Props")

    # ------------------------------------------------------------------ slab
    B.frustum("slab", -11.0, 11.0, -9.0, 9.0, 0.0, SL, 0.12)
    B.span("slab", BX0 - 0.6, BX1 + 0.6, BY0 + 0.2, BY1 + 0.6, SL - 0.05, SL + 0.06)        # building pad (subtle step)

    # ------------------------------------------------------------------ walls: olive cladding shell
    T = 0.3
    B.span("clad", BX0, BX0 + T, BY0, BY1, SL, WH)
    B.span("clad", BX1 - T, BX1, BY0, BY1, SL, WH)
    B.span("clad", BX0, BX1, BY1 - T, BY1, SL, WH)
    B.span("clad", BX0, BX1, BY0 + 0.2, BY0 + 0.2 + T, SL, WH)
    # base plinth on sides + rear, panel joint strips, downpipes
    B.span("conc", BX0 - 0.08, BX0 + 0.1, BY0, BY1, SL, SL + 0.7, bev=True)
    B.span("conc", BX1 - 0.1, BX1 + 0.08, BY0, BY1, SL, SL + 0.7, bev=True)
    B.span("conc", BX0, BX1, BY1 - 0.1, BY1 + 0.08, SL, SL + 0.7, bev=True)
    for y in np.arange(BY0 + 2.6, BY1 - 1.0, 2.4):
        for x0, x1 in ((BX0 - 0.05, BX0), (BX1, BX1 + 0.05)):
            B.span("metal", x0, x1, y - 0.04, y + 0.04, SL + 0.7, WH)
    for x in np.arange(-3.6, 4.0, 2.4):
        B.span("metal", x - 0.04, x + 0.04, BY1, BY1 + 0.05, SL + 0.7, WH)
    for x, y in ((BX0 - 0.12, BY1 - 1.6), (BX1 + 0.04, BY1 - 1.6)):
        B.span("metal", x, x + 0.08, y - 0.06, y + 0.06, SL + 0.7, WH + 0.1)

    # ------------------------------------------------------------------ corner pilasters / rear stair towers (tan concrete)
    for sx in (-1, 1):
        xo = BX0 if sx < 0 else BX1
        # front corner pilasters
        x0, x1 = sorted((xo - sx * 0.15, xo + sx * 0.9))
        B.span("conc", x0, x1, BY0 - 0.15, BY0 + 0.9, SL, PZ + 0.25, bev=True)
        B.span("conc", x0 - 0.05, x1 + 0.05, BY0 - 0.2, BY0 + 0.95, PZ + 0.25, PZ + 0.35, bev=True)   # cap
        # rear towers (bigger, taller)
        x0, x1 = sorted((xo - sx * 0.15, xo + sx * 1.7))
        B.span("conc", x0, x1, BY1 - 1.7, BY1 + 0.15, SL, PZ + 0.55, bev=True)
        B.span("conc", x0 - 0.05, x1 + 0.05, BY1 - 1.75, BY1 + 0.2, PZ + 0.55, PZ + 0.65, bev=True)
        # small square window on each tower (side face)
        B.span("metal", xo + sx * 0.15 - 0.02, xo + sx * 0.15 + 0.02, BY1 - 1.1, BY1 - 0.5, 5.0, 5.6)
        B.span("dark", xo + sx * 0.15 - 0.03, xo + sx * 0.15 + 0.03, BY1 - 1.02, BY1 - 0.58, 5.08, 5.52)

    # ------------------------------------------------------------------ parapet (tan) + roof deck (olive ribbed)
    B.span("conc", BX0 - 0.06, BX0 + 0.32, BY0, BY1, WH - 0.15, PZ, bev=True)
    B.span("conc", BX1 - 0.32, BX1 + 0.06, BY0, BY1, WH - 0.15, PZ, bev=True)
    B.span("conc", BX0, BX1, BY1 - 0.32, BY1 + 0.06, WH - 0.15, PZ, bev=True)
    B.span("conc", BX0, BX1, BY0 - 0.15, BY0 + 0.35, 5.95, PZ, bev=True)                  # front parapet band
    B.span("roof", BX0 + 0.3, BX1 - 0.3, BY0 + 0.3, BY1 - 0.3, WH - 0.1, RZ)
    for x in (BX0 + 0.32, BX1 - 0.32):                                                     # coping flashing
        B.span("metal", x - 0.02, x + 0.02, BY0 + 0.35, BY1 - 0.32, RZ, RZ + 0.25)

    # ------------------------------------------------------------------ front facade: piers, lintel, recessed doors
    FY = BY0 - 0.12                                   # proud face of the tan front wall
    for x0, x1 in ((-2.4, -1.45), (1.45, 2.4)):
        B.span("conc", x0, x1, FY, BY0 + 0.2, SL, 4.65, bev=True)
    B.span("conc", BX0 + 0.75, BX1 - 0.75, FY, BY0 + 0.2, DTOP, 4.65, bev=True)            # lintel
    B.span("conc", BX0 + 0.75, BX1 - 0.75, FY - 0.05, BY0 + 0.2, 4.6, 4.7, bev=True)       # drip band
    for cx in DOOR_X:
        x0, x1 = cx - DW / 2, cx + DW / 2
        B.span("door", x0 + 0.08, x1 - 0.08, BY0 + 0.13, BY0 + 0.2, DZ, DTOP)                 # slat curtain (recessed)
        B.span("metal", x0 + 0.08, x1 - 0.08, BY0 + 0.06, BY0 + 0.14, DZ, DZ + 0.12)          # bottom bar
        for x in (x0 + 0.04, x1 - 0.04):                                                     # guide rails
            B.span("metal", x - 0.05, x + 0.05, BY0 + 0.02, BY0 + 0.16, DZ, DTOP)
        B.span("metal", x0, x1, BY0 - 0.02, BY0 + 0.14, DTOP - 0.18, DTOP)                   # head housing
        B.span("metal", cx - 0.18, cx + 0.18, FY - 0.12, FY, 4.3, 4.5, bottom=True)          # wall lamp
        B.span("lamp", cx - 0.14, cx + 0.14, FY - 0.13, FY - 0.03, 4.28, 4.31, bottom=True)

    # ------------------------------------------------------------------ loading canopy (olive ribbed) + tension rods + team fascia
    CY1 = BY0 - 2.45
    B.prism("roof", [(FY, 5.3), (FY, 5.15), (CY1, 4.66), (CY1, 4.82)], "x", BX0 - 0.2, BX1 + 0.2)
    B.span("metal", BX0 - 0.22, BX1 + 0.22, CY1 - 0.1, CY1 + 0.02, 4.6, 4.86, bottom=True)  # fascia beam
    B.span("team", BX0 - 0.2, BX1 + 0.2, CY1 - 0.12, CY1 - 0.1, 4.64, 4.78, bottom=True)
    for x in (-5.4, -1.9, 1.9, 5.4):
        B.strut("metal", (x, FY, 6.05), (x, CY1 + 0.12, 4.9), 0.045)
        B.span("metal", x - 0.08, x + 0.08, FY - 0.08, FY, 5.95, 6.15, bottom=True)
        B.span("metal", x - 0.05, x + 0.05, CY1, CY1 + 0.7, 4.72, 4.9, bottom=True)

    # ------------------------------------------------------------------ loading dock platforms, centre ramp, hazard bands
    DY1 = -7.0
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 1.4, sx * (BX1 + 0.05)))
        B.span("slab", x0, x1, DY1, BY0, SL, DZ, bev=True)
        B.span("hazard", x0 + 0.05, x1 - 0.05, DY1 - 0.02, DY1, DZ - 0.38, DZ - 0.06)
        B.span("yellow", x0 + 0.05, x1 - 0.05, DY1 + 0.04, DY1 + 0.18, DZ, DZ + 0.008)      # edge line
        B.span("yellow", sx * 1.48 - 0.07, sx * 1.48 + 0.07, DY1 + 0.04, BY0 - 0.15, DZ, DZ + 0.008)
        xi = sx * 1.4                                                                       # ramp-side hazard band
        B.span("hazard", xi - 0.01, xi + 0.01, DY1 + 0.02, -5.9, DZ - 0.38, DZ - 0.06)
        for cx in (sx * 3.85 - 0.9, sx * 3.85 + 0.9):                                        # dock bumpers
            B.span("rubber", cx - 0.18, cx + 0.18, DY1 - 0.14, DY1, SL + 0.15, DZ - 0.45)
        B.span("yellow", sx * (BX1 + 0.05) - 0.08, sx * (BX1 + 0.05) + 0.08, DY1 - 0.02, BY0, DZ - 0.04, DZ + 0.01)
    # centre: short level landing then a ramp down to the apron
    B.prism("slab", [(BY0, SL), (BY0, DZ), (-5.4, DZ), (-8.8, SL + 0.01)], "x", -1.4, 1.4)
    ang = math.atan2(DZ - SL, 8.8 - 5.4)
    for x in (-1.2, 1.2):
        B.span("yellow", x - 0.06, x + 0.06, -5.4, BY0 - 0.15, DZ, DZ + 0.008)
        L = math.hypot(3.4, DZ - SL)
        B.box("yellow", (x, -7.1, (DZ + SL) / 2 + 0.008), (0.12, L, 0.01), (ang, 0, 0), bottom=True)
    B.span("yellow", -1.2, 1.2, -8.85, -8.75, SL, SL + 0.01)
    # apron lane lines continuing to the slab edge in front of the side docks
    for x in (-6.0, -1.6, 1.6, 6.0):
        B.span("yellow", x - 0.06, x + 0.06, -8.85, DY1 - 0.05, SL, SL + 0.008)
    # steps at the right end of the dock
    for k in range(3):
        x0 = BX1 + 0.05 + k * 0.35
        B.span("slab", x0, x0 + 0.35, -6.6, -4.6, SL, DZ - (k + 1) * (DZ - SL) / 4, bev=True)
    # bollards at door jambs
    for cx in DOOR_X:
        for x in (cx - DW / 2 - 0.25, cx + DW / 2 + 0.25):
            if abs(x) > 6.2:
                continue
            zb = DZ
            B.cyl("yellow", (x, BY0 - 0.45, zb + 0.5), 0.11, 1.0, seg=10)
            B.cyl("dark", (x, BY0 - 0.45, zb + 1.01), 0.115, 0.03, seg=10, bottom=True)

    # ------------------------------------------------------------------ side + rear facade details
    def louvre(axis, fixed, a, z, out, w=2.0, h=0.55):
        """Louvred window on a wall; axis 'x' = wall normal along x."""
        if axis == "x":
            B.span("metal", fixed, fixed + out * 0.08, a - w / 2 - 0.08, a + w / 2 + 0.08, z - h / 2 - 0.08, z + h / 2 + 0.08)
            B.span("dark", fixed + out * 0.08, fixed + out * 0.09, a - w / 2, a + w / 2, z - h / 2, z + h / 2)
            for k in range(4):
                zz = z - h / 2 + (k + 0.5) * h / 4
                B.span("metal", fixed + out * 0.08, fixed + out * 0.12, a - w / 2, a + w / 2, zz - 0.03, zz + 0.03)
        else:
            B.span("metal", a - w / 2 - 0.08, a + w / 2 + 0.08, fixed, fixed + out * 0.08, z - h / 2 - 0.08, z + h / 2 + 0.08)
            B.span("dark", a - w / 2, a + w / 2, fixed + out * 0.08, fixed + out * 0.09, z - h / 2, z + h / 2)
            for k in range(4):
                zz = z - h / 2 + (k + 0.5) * h / 4
                B.span("metal", a - w / 2, a + w / 2, fixed + out * 0.08, fixed + out * 0.12, zz - 0.03, zz + 0.03)


    for y in (-1.2, 1.4, 4.0 - 0.6):
        louvre("x", BX0 - 0.05, y, 5.1, -1)
        louvre("x", BX1 + 0.05, y, 5.1, 1)
    for x in (-3.4, 0.2):
        louvre("y", BY1 + 0.05, x, 5.1, 1)
    # personnel doors with awnings (right side near the rear, rear wall left)
    def pdoor(axis, fixed, a, out):
        if axis == "x":
            B.span("conc", fixed, fixed + out * 0.12, a - 0.65, a + 0.65, SL, 2.75, bev=True)
            B.span("metal", fixed + out * 0.12, fixed + out * 0.16, a - 0.48, a + 0.48, SL, 2.4)
            B.span("metal", fixed, fixed + out * 0.9, a - 0.8, a + 0.8, 2.85, 2.95, bottom=True)
            B.span("lamp", fixed + out * 0.16, fixed + out * 0.2, a + 0.3, a + 0.4, 1.2, 1.35)
        else:
            B.span("conc", a - 0.65, a + 0.65, fixed, fixed + out * 0.12, SL, 2.75, bev=True)
            B.span("metal", a - 0.48, a + 0.48, fixed + out * 0.12, fixed + out * 0.16, SL, 2.4)
            B.span("metal", a - 0.8, a + 0.8, fixed, fixed + out * 0.9, 2.85, 2.95, bottom=True)
    pdoor("x", BX1 + 0.05, 3.2, 1)
    pdoor("y", BY1 + 0.05, -2.0, 1)
    # rear roll-up door with housing + awning + bollards
    RX0, RX1 = 0.9, 3.7
    B.span("conc", RX0 - 0.3, RX1 + 0.3, BY1, BY1 + 0.14, SL, 3.9, bev=True)
    B.span("door", RX0, RX1, BY1 + 0.14, BY1 + 0.17, SL, 3.4)
    B.span("metal", RX0 - 0.1, RX1 + 0.1, BY1 + 0.14, BY1 + 0.5, 3.4, 3.85, bottom=True)
    B.prism("metal", [(BY1 + 0.14, 4.0), (BY1 + 1.1, 3.8), (BY1 + 1.1, 3.72), (BY1 + 0.14, 3.92)], "x", RX0 - 0.3, RX1 + 0.3)
    for x in (RX0 - 0.45, RX1 + 0.45):
        B.cyl("yellow", (x, BY1 + 0.5, SL + 0.5), 0.1, 1.0, seg=10)
    # ladder on the front-left pilaster (side face) and the rear-right tower (rear face)
    def ladder(p0, along, n_rungs, height, out):
        p0 = V(p0); along = V(along); out = V(out)
        for s in (-0.22, 0.22):
            a = p0 + along * s
            B.strut("metal", a + out * 0.12, a + out * 0.12 + V((0, 0, height)), 0.025, seg=4)
        for k in range(n_rungs):
            z = 0.35 + k * (height - 0.4) / (n_rungs - 1)
            B.strut("metal", p0 + along * -0.22 + out * 0.12 + V((0, 0, z)), p0 + along * 0.22 + out * 0.12 + V((0, 0, z)), 0.015, seg=4)
    ladder((BX0 - 0.15, BY0 + 0.4, SL), (0, 1, 0), 18, PZ + 0.25 - SL + 0.6, (-1, 0, 0))
    ladder((BX1 - 0.6, BY1 + 0.15, SL), (1, 0, 0), 18, PZ + 0.55 - SL + 0.6, (0, 1, 0))

    # ------------------------------------------------------------------ roof hardware
    for y in (4.6, 3.1, 1.6, 0.1, -1.4):                                   # 5 skylights (left-centre column)
        B.span("metal", -2.7, -0.5, y - 0.38, y + 0.38, RZ, RZ + 0.2, bev=True)
        B.prism("glass", [(y - 0.29, RZ + 0.2), (y + 0.29, RZ + 0.2), (y + 0.29, RZ + 0.29), (y - 0.29, RZ + 0.25)], "x", -2.6, -0.6)
    for y in (4.0, 2.2, 0.4, -1.4):                                        # mushroom vents (right-centre column)
        B.cyl("metal", (2.3, y, RZ + 0.25), 0.16, 0.5, seg=10)
        B.cyl("hvac", (2.3, y, RZ + 0.55), 0.32, 0.12, seg=12, r2=0.2, bottom=True)
    def hvac(x, y, sx=1.5, sy=1.15, h=0.85, z=RZ):
        B.span("metal", x - sx / 2 - 0.08, x + sx / 2 + 0.08, y - sy / 2 - 0.08, y + sy / 2 + 0.08, z, z + 0.12)
        B.span("hvac", x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, z + 0.12, z + h, bev=True)
        B.cyl("dark", (x + sx * 0.18, y, z + h + 0.01), min(sx, sy) * 0.33, 0.04, seg=16)
        B.cyl("metal", (x + sx * 0.18, y, z + h + 0.035), min(sx, sy) * 0.1, 0.05, seg=8)
    hvac(-4.55, -2.3)
    hvac(-4.4, 3.9, 1.3, 1.1)
    hvac(4.5, -2.6, 1.5, 1.2)
    B.span("hvac", 4.4, 5.2, 1.0, 2.6, RZ, RZ + 0.75, bev=True)                       # duct cabinet
    B.strut("metal", (4.8, 1.0, RZ + 0.45), (4.8, -1.9, RZ + 0.45), 0.12, seg=8)       # duct to the front unit
    B.span("hvac", -4.9, -4.1, 1.0, 1.8, RZ, RZ + 0.45, bev=True)                     # roof hatch
    B.span("metal", -4.95, -4.05, 0.95, 1.85, RZ + 0.45, RZ + 0.5)
    B.strut("metal", (BX1 - 0.55, -3.3, RZ + 0.15), (BX1 - 0.55, 4.2, RZ + 0.15), 0.06, seg=6)   # conduit run
    B.strut("metal", (BX0 + 0.55, -3.0, RZ + 0.12), (BX0 + 0.55, 3.0, RZ + 0.12), 0.05, seg=6)
    for y in (-2.0, 0.0, 2.0):
        B.span("metal", BX1 - 0.65, BX1 - 0.45, y - 0.08, y + 0.08, RZ, RZ + 0.1)
    # rear-right tower: penthouse + fan; rear-left tower: antenna mast
    TZ = PZ + 0.65
    B.span("hvac", 4.6, 6.0, BY1 - 1.55, BY1 - 0.15, TZ, TZ + 0.75, bev=True)
    B.cyl("dark", (5.3, BY1 - 0.85, TZ + 0.76), 0.42, 0.04, seg=16)
    B.cyl("metal", (-5.3, BY1 - 0.85, TZ + 0.15), 0.25, 0.3, seg=8)
    B.cyl("metal", (-5.3, BY1 - 0.85, TZ + 1.6), 0.05, 2.6, seg=6)
    B.strut("metal", (-5.75, BY1 - 0.85, TZ + 2.4), (-4.85, BY1 - 0.85, TZ + 2.4), 0.03, seg=4)
    B.box("metal", (-5.3, BY1 - 0.85, TZ + 2.75), (0.3, 0.12, 0.22), bottom=True)
    B.span("metal", -6.0, -5.5, BY1 - 1.6, BY1 - 1.0, TZ, TZ + 0.5)                # junction box
    for sx in (-1, 1):                                                              # tower roof lamps
        B.span("metal", sx * 5.3 - 0.1, sx * 5.3 + 0.1, BY1 - 1.75, BY1 - 1.6, PZ + 0.2, PZ + 0.4, bottom=True)

    building = B.build()


    # ================================================================== PROPS
    def pallet(cx, cy, base=SL, sx=1.2, sy=1.0):
        P.span("pallet", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, base, base + 0.14)
        return base + 0.14


    def ammo_pallet(cx, cy, layers=2, base=SL):
        z = pallet(cx, cy, base)
        cw, cd, ch = 0.57, 0.47, 0.36
        for l in range(layers):
            for i in (-1, 1):
                for j in (-1, 1):
                    c = (cx + i * (cw / 2 + 0.01), cy + j * (cd / 2 + 0.01), z + l * (ch + 0.01) + ch / 2)
                    P.box("crate", c, (cw, cd, ch))
        P.span("rubber", cx - 0.6, cx + 0.6, cy - 0.04, cy + 0.04, base + 0.14, z + layers * (ch + 0.01) + 0.015)   # strap
        return z + layers * (ch + 0.01)


    def tarp_stack(cx, cy, sx, sy, h):
        z = SL + 0.14
        P.span("pallet", cx - sx / 2 + 0.05, cx + sx / 2 - 0.05, cy - sy / 2 + 0.05, cy + sy / 2 - 0.05, SL, z)
        P.span("tarp", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z, z + h - 0.15, bev=True)
        P.frustum("tarp", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z + h - 0.15, z + h, 0.12)
        for t in (-0.28, 0.28):                                                        # straps over the top
            if sx >= sy:
                x = cx + t * sx
                P.span("rubber", x - 0.04, x + 0.04, cy - sy / 2 - 0.02, cy + sy / 2 + 0.02, z, z + h + 0.015)
            else:
                y = cy + t * sy
                P.span("rubber", cx - sx / 2 - 0.02, cx + sx / 2 + 0.02, y - 0.04, y + 0.04, z, z + h + 0.015)


    def container(cx, cy, length, along_y=True, w=2.2, h=2.3):
        sx, sy = (w, length) if along_y else (length, w)
        P.span("cont", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, SL + 0.1, SL + h, bev=True)
        P.span("metal", cx - sx / 2 + 0.1, cx + sx / 2 - 0.1, cy - sy / 2 + 0.1, cy + sy / 2 - 0.1, SL, SL + 0.1)
        # end doors (frame + lock bars) at the end facing the yard centre-line
        if along_y:
            for e in (-1, 1):
                y = cy + e * sy / 2
                P.span("olive", cx - sx / 2 + 0.06, cx + sx / 2 - 0.06, y - 0.03 if e > 0 else y - 0.02, y + 0.02 if e < 0 else y + 0.03, SL + 0.15, SL + h - 0.06)
            for t in (-0.35, -0.12, 0.12, 0.35):
                P.span("metal", cx + t * sx - 0.025, cx + t * sx + 0.025, cy - sy / 2 - 0.06, cy - sy / 2, SL + 0.2, SL + h - 0.1)
        else:
            for e in (-1, 1):
                x = cx + e * sx / 2
                P.span("olive", x - 0.03 if e > 0 else x - 0.02, x + 0.02 if e < 0 else x + 0.03, cy - sy / 2 + 0.06, cy + sy / 2 - 0.06, SL + 0.15, SL + h - 0.06)
        # roof edge rails (top-down read)
        P.span("olive", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, SL + h, SL + h + 0.04)


    # west yard (x < 0), back to front
    ammo_pallet(-9.0, 7.0); ammo_pallet(-7.6, 7.0, 3)
    tarp_stack(-8.3, 5.2, 2.2, 2.0, 1.9)
    tarp_stack(-8.3, 2.9, 2.2, 1.8, 1.55)
    container(-8.3, 0.1, 3.6)
    container(-8.3, -3.6, 3.0)
    tarp_stack(-8.9, -6.2, 1.5, 1.5, 1.4)
    ammo_pallet(-7.4, -6.6, 2)
    ammo_pallet(-7.4, -5.4, 1)
    # east yard
    container(8.3, 6.6, 2.6)
    tarp_stack(8.3, 4.15, 2.2, 2.0, 2.0)
    ammo_pallet(7.6, 2.3, 2); ammo_pallet(9.0, 2.3, 3)
    tarp_stack(8.3, 0.4, 2.2, 1.8, 1.6)
    container(8.4, -2.6, 3.2)
    ammo_pallet(7.6, -5.2, 2); ammo_pallet(9.0, -5.2, 2); ammo_pallet(8.3, -6.6, 1)
    # rear strip (behind the warehouse, clear of the rear door)
    ammo_pallet(-4.4, 7.2, 2); ammo_pallet(-3.0, 7.2, 1)
    tarp_stack(5.6, 7.15, 1.6, 1.2, 1.2)
    # on the docks (as in the concept): tarp-covered pallet left, crate stack right
    P.span("pallet", -4.5, -3.3, -6.4, -5.4, DZ, DZ + 0.14)
    P.span("tarp", -4.55, -3.25, -6.45, -5.35, DZ + 0.14, DZ + 1.1, bev=True)
    P.span("rubber", -3.94, -3.86, -6.47, -5.33, DZ + 0.14, DZ + 1.115)
    ammo_pallet(3.3, -5.9, 2, base=DZ); ammo_pallet(4.6, -5.9, 1, base=DZ)
    # fuel drums by the east yard
    for i, (x, y) in enumerate(((9.5, -3.9), (9.5, -4.5), (8.9, -4.2))):
        P.cyl("olive" if i != 2 else "yellow", (x, y, SL + 0.45), 0.29, 0.9, seg=12)
        P.cyl("metal", (x, y, SL + 0.91), 0.3, 0.03, seg=12, bottom=True)

    # jersey barriers along sides and rear, short runs at the front corners
    JP = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.12, 0.3), (0.08, 0.81), (-0.08, 0.81), (-0.12, 0.3), (-0.3, 0.08)]
    def jersey_run(a, b, fixed, axis, seglen=2.8, gap=0.12):
        """Barrier segments between a..b along `axis`; profile offset across the run by `fixed`."""
        L = abs(b - a); n = max(1, int(round(L / (seglen + gap)))); s = L / n
        ext = "y" if axis == "y" else "x"
        for k in range(n):
            t0 = min(a, b) + k * s + gap / 2; t1 = t0 + s - gap
            P.prism("jersey", [(fixed + px, SL + pz) for px, pz in JP], ext, t0, t1)
    jersey_run(-8.7, 8.7, -10.62, "y")
    jersey_run(-8.7, 8.7, 10.62, "y")
    jersey_run(-10.2, 10.2, 8.62, "x")
    jersey_run(-10.3, -7.4, -8.62, "x")
    jersey_run(7.4, 10.3, -8.62, "x")

    # fence posts / rails (Props) + chain-link panels (separate 'Fence' object, joined into Props after baking)
    FX, FYB, FYF = 10.05, 8.1, -7.75
    FH = 2.35
    fence_runs = [((-FX, FYF), (-FX, FYB)), ((-FX, FYB), (FX, FYB)), ((FX, FYB), (FX, FYF)),
                  ((-FX, FYF), (-7.1, FYF)), ((7.1, FYF), (FX, FYF))]
    fence_quads = []
    for (x0, y0), (x1, y1) in fence_runs:
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / 3.0)))
        for k in range(n + 1):
            t = k / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            P.cyl("metal", (x, y, SL + FH / 2 + 0.05), 0.045, FH + 0.1, seg=6)
        P.strut("metal", (x0, y0, SL + FH), (x1, y1, SL + FH), 0.025, seg=4)
        P.strut("metal", (x0, y0, SL + 0.12), (x1, y1, SL + 0.12), 0.018, seg=4)
        fence_quads.append(((x0, y0), (x1, y1)))
    # corner light poles with twin flood heads aimed at the yard
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = sx * 9.55, sy * (7.25 if sy < 0 else 7.6)
        P.span("conc", x - 0.25, x + 0.25, y - 0.25, y + 0.25, SL, SL + 0.35, bev=True)
        P.cyl("metal", (x, y, SL + 0.35 + 3.6), 0.09, 7.2, seg=8, r2=0.06)
        yaw = math.atan2(-y, -x)
        P.box("metal", (x, y, SL + 7.45), (0.9, 0.08, 0.08), (0, 0, yaw + PI / 2), bottom=True)
        for s in (-1, 1):
            hx = x + s * 0.38 * math.cos(yaw + PI / 2); hy = y + s * 0.38 * math.sin(yaw + PI / 2)
            P.box("metal", (hx, hy, SL + 7.35), (0.38, 0.22, 0.28), (0, math.radians(30), yaw), bottom=True)
            P.box("lamp", (hx + 0.12 * math.cos(yaw), hy + 0.12 * math.sin(yaw), SL + 7.28), (0.04, 0.18, 0.22),
                  (0, math.radians(30), yaw), bottom=True)
    props = P.build()


    # ================================================================== chain-link fence object
    def chainlink():
        n = 256
        u = (np.arange(n) + 0.5)[None, :].repeat(n, 0); v = (np.arange(n) + 0.5)[:, None].repeat(n, 1)
        per = 32.0
        d1 = np.abs(frac((u + v) / per) - 0.5) * per; d2 = np.abs(frac((u - v) / per) - 0.5) * per
        a = np.clip(1.9 - np.minimum(d1, d2), 0, 1)
        return np.full((n, n, 3), 0.62, np.float32), a


    fbm = bmesh.new(); fuv = fbm.loops.layers.uv.new("UVMap")
    for (x0, y0), (x1, y1) in fence_quads:
        L = math.hypot(x1 - x0, y1 - y0)
        vs = [fbm.verts.new(p) for p in ((x0, y0, SL + 0.05), (x1, y1, SL + 0.05), (x1, y1, SL + FH), (x0, y0, SL + FH))]
        f = fbm.faces.new(vs)
        for lp, (uu, vv) in zip(f.loops, ((0, 0), (L, 0), (L, FH - 0.05), (0, FH - 0.05))):
            lp[fuv].uv = (uu, vv)
    fme = bpy.data.meshes.new("Fence"); fbm.to_mesh(fme); fbm.free()
    fence = bpy.data.objects.new("Fence", fme); scene.collection.objects.link(fence)
    fm = bpy.data.materials.new("SD_Fence"); fm.use_nodes = True; fm.use_backface_culling = False
    fb = fm.node_tree.nodes["Principled BSDF"]; fb.inputs["Roughness"].default_value = 0.6
    fb.inputs["Metallic"].default_value = 0.3
    crgb, ca = chainlink()
    ftex = fm.node_tree.nodes.new("ShaderNodeTexImage")
    ftex.image = np_to_image("supply_depot_chainlink", crgb, ca)
    fm.node_tree.links.new(ftex.outputs["Color"], fb.inputs["Base Color"])
    fm.node_tree.links.new(ftex.outputs["Alpha"], fb.inputs["Alpha"])
    fme.materials.append(fm)


    # ================================================================== atlas UVs over Building + Props
    for o in (building, props):
        o.data.uv_layers.new(name="atlas")
        o.data.uv_layers.active = o.data.uv_layers["atlas"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in (building, props):
        o.select_set(True)
    bpy.context.view_layer.objects.active = building
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0015, area_weight=0.0)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0015, shape_method="AABB")
    bpy.ops.object.mode_set(mode="OBJECT")

    # ================================================================== bake colour, then AO
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.seed = 7
    scene.render.bake.margin = 8
    col_img = bpy.data.images.new("bake_col", ATLAS, ATLAS)
    ao_img = bpy.data.images.new("bake_ao", AO_RES, AO_RES); ao_img.colorspace_settings.name = "Non-Color"
    src_mats = {m for o in (building, props) for m in o.data.materials}
    targets = {}
    for m in src_mats:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = col_img
        m.node_tree.nodes.active = n; targets[m] = n
    fence.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    for o in (building, props):
        o.select_set(True)
    bpy.context.view_layer.objects.active = building
    scene.cycles.samples = 8
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=8, use_clear=True)
    for m, n in targets.items():
        n.image = ao_img
    world = bpy.data.worlds.new("bakeworld"); scene.world = world
    world.light_settings.distance = 4.0
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.001)); ground = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    for o in (building, props):
        o.select_set(True)
    bpy.context.view_layer.objects.active = building
    scene.cycles.samples = 24
    bpy.ops.object.bake(type="AO", margin=8, use_clear=True)
    bpy.data.objects.remove(ground)


    def img_np(img):
        a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
        return a.reshape(img.size[1], img.size[0], 4)[..., :3]


    c = img_np(col_img)                       # sRGB-encoded values
    ao = img_np(ao_img)[..., 0]
    ao = np.asarray(Image.fromarray((ao * 255).astype(np.uint8)).resize((ATLAS, ATLAS), Image.BILINEAR), np.float32) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    lin *= (0.28 + 0.72 * ao ** 1.1)[..., None]
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    out8 = (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]          # Blender rows are bottom-up
    atlas_path = os.path.join(TMP, "supply_depot_albedo.jpg")
    Image.fromarray(out8).save(atlas_path, quality=90, optimize=True)

    # ================================================================== final materials, UV cleanup, join fence
    fin = bpy.data.materials.new("SD_SupplyDepot"); fin.use_nodes = True; fin.use_backface_culling = True
    MATS["team"].use_backface_culling = True
    bs = fin.node_tree.nodes["Principled BSDF"]
    bs.inputs["Roughness"].default_value = 0.82; bs.inputs["Metallic"].default_value = 0.0
    at = fin.node_tree.nodes.new("ShaderNodeTexImage"); at.image = bpy.data.images.load(atlas_path)
    fin.node_tree.links.new(at.outputs["Color"], bs.inputs["Base Color"])
    team = MATS["team"]
    for n in [n for n in team.node_tree.nodes if n.type in ("TEX_IMAGE", "UVMAP")]:
        team.node_tree.nodes.remove(n)
    team.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)

    for o in (building, props):
        me = o.data
        idx = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("material_index", idx)
        is_team = np.array([m.name == "SA_Team" for m in me.materials])
        new_idx = np.where(is_team[idx], 1, 0).astype(np.int32)
        me.materials.clear(); me.materials.append(fin); me.materials.append(team)
        me.polygons.foreach_set("material_index", new_idx)
        if not is_team.any():
            me.materials.pop(index=1)
        me.uv_layers.remove(me.uv_layers["tile"])
        me.uv_layers["atlas"].name = "UVMap"
    fence.hide_render = False
    bpy.ops.object.select_all(action="DESELECT")
    props.select_set(True); fence.select_set(True); bpy.context.view_layer.objects.active = props
    bpy.ops.object.join()
    props = bpy.context.active_object; props.name = "Props"; props.data.name = "Props"

    ntris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in (building, props)}
    bpy.ops.object.select_all(action="DESELECT"); building.select_set(True); props.select_set(True)
    glb = os.path.join(OUT, "supply_depot.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True, use_selection=True,
                              export_image_format="AUTO")
    dims = [round(v, 2) for v in building.dimensions]
    print("SUPPLY_DEPOT OK tris", ntris, "total", sum(ntris.values()), "building dims", dims,
          "glb bytes", os.path.getsize(glb))




glb = os.path.join(OUT, "supply_depot.glb")
if not SKIP_BUILD:
    build_asset()

# ================================================================== previews (render the exported GLB)
if PREVIEWS:
    os.makedirs(PREVIEWS, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=glb)
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 20
    scene.cycles.use_denoising = True; scene.cycles.max_bounces = 3
    scene.render.resolution_x, scene.render.resolution_y = 1152, 768
    scene.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.32, 0.33, 0.36, 1); bg.inputs["Strength"].default_value = 0.6
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.2; sun.angle = math.radians(3)
    so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
    so.rotation_euler = Euler((math.radians(42), 0, math.radians(-38)))
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.11, 0.10, 0.075, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    bpy.ops.mesh.primitive_plane_add(size=300, location=(0, 0, -0.002)); bpy.context.active_object.data.materials.append(gm)
    cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam

    def shot(name, az_deg, el_deg, dist=46.0, lens=50, ortho=None, target=(0, 0, 2.2)):
        tgt = V(target); az, el = math.radians(az_deg), math.radians(el_deg)
        d = V((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        cam.location = tgt + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam_d.type = "ORTHO"; cam_d.ortho_scale = ortho
        else:
            cam_d.type = "PERSP"; cam_d.lens = lens
        scene.render.filepath = os.path.join(PREVIEWS, f"pilot3d_depot_{name}.png")
        if ONLY and name not in ONLY.split(","):
            return
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)

    # azimuth 0 = camera south of the building (looking at the loading bays), positive = towards +X (east)
    shot("rts", -38, 52)
    shot("front", 0, 22)
    shot("side", -90, 14)
    shot("rear", 150, 35)
    shot("top", 0, 89.9, dist=60, ortho=30, target=(0, 0, 0))

    if CONCEPT:
        a = Image.open(os.path.join(PREVIEWS, "pilot3d_depot_rts.png")).convert("RGB")
        b = Image.open(CONCEPT).convert("RGB")
        b = b.resize((int(b.width * a.height / b.height), a.height), Image.LANCZOS)
        sbs = Image.new("RGB", (a.width + b.width + 16, a.height), (20, 20, 20))
        sbs.paste(a, (0, 0)); sbs.paste(b, (a.width + 16, 0))
        sbs.save(os.path.join(PREVIEWS, "pilot3d_depot_vs_concept.png"))
        print("wrote side-by-side")
