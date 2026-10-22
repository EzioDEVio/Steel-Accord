"""Steel Accord - shared kit for code-built 3D base structures (Blender bpy 5.x as a Python module).

Derived from the approved pilot tools/art/bld_supply_depot_3d.py (same method, generalised; the pilot itself is
unchanged). Used by tools/art/bld_{command_center,power_plant,barracks,war_factory}_3d.py.

Method (deterministic):
  1. geometry = code-placed primitives accumulated per (source surface, bevel) in a Part; each source surface is a
     tileable numpy texture (colours sampled from the concept sheet) mapped by a world-planar 'tile' UV;
  2. one non-overlapping 'atlas' UV over Building + Props (smart project + pack);
  3. Cycles CPU bakes source colour, then AO (with a ground plane) -> colour x AO composited to one JPEG atlas;
  4. single Principled BSDF atlas material + plain `SA_Team` + optional chain-link `<P>_Fence`; GLB export.
Extras over the pilot: emissive light objects (`Light_Status*`, `Light_Beacon*`, `Light_Flood*`, each with its own
material `SA_Light_<objectname>`), named empties (`Exit`, `RepairBay`), lathe/dish/tank/stair/railing helpers.

Conventions: metres; origin = centre of the slab's bottom face; front faces Blender -Y = Godot +Z.
"""
import bpy, bmesh, math, os, tempfile
import numpy as np
from mathutils import Matrix, Euler, Vector
from PIL import Image

PI = math.pi
V = Vector


# ====================================================================== tileable source textures (numpy, sRGB 0..1)
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
    return (frac(coord * count) < width).astype(np.float32)


def grime(seed, amt=0.05):
    """vertical streaks + broad mottling multiplier."""
    return 1 + 0.025 * noise(70, 70, seed) + 0.03 * noise(3, 3, seed + 1) - amt * np.clip(noise(2, 90, seed + 2), 0, None)


# ---- pilot surfaces (identical recipes)
def t_conc():
    k = grime(1, 0.04)
    k *= 1 - 0.12 * lines(VV, 3, 0.006)
    k *= 1 - 0.06 * lines(UU, 2, 0.004)
    return shade(col(176, 162, 140), k)


def t_slab():
    k = 1 + 0.025 * noise(90, 90, 4) + 0.03 * noise(3, 3, 5) - 0.05 * np.clip(noise(25, 25, 6) - 1.2, 0, None)
    k *= 1 - 0.35 * np.maximum(lines(UU, 2, 0.004), lines(VV, 2, 0.004))
    return shade(col(156, 146, 131), k)


def t_roof():          # olive standing-seam roof (S = 4 m, 8 ribs along v)
    f = frac(UU * 8)
    k = np.where(f < 0.1, 1.22, np.where(f < 0.2, 0.74, 1.0 - 0.08 * (f - 0.2)))
    k = k * (1 + 0.02 * noise(80, 80, 7) + 0.025 * noise(2, 2, 8) - 0.05 * np.clip(noise(2, 70, 9), 0, None))
    k *= 1 - 0.18 * lines(VV, 1, 0.004)
    return shade(col(102, 106, 80), k)


def t_clad():
    f = frac(UU * 10)
    k = np.where(f < 0.25, 1.16, np.where((f > 0.5) & (f < 0.68), 0.76, 1.0))
    k = k * (1 + 0.025 * noise(80, 80, 10) + 0.02 * noise(2, 2, 11) - 0.06 * np.clip(noise(2, 60, 12), 0, None))
    return shade(col(90, 92, 70), k)


def t_door():
    f = frac(VV * 14)
    k = np.where(f < 0.14, 0.62, np.where(f < 0.3, 1.14, 1.0)) * (1 + 0.04 * noise(40, 40, 13) + 0.02 * noise(2, 2, 14))
    return shade(col(146, 146, 140), k)


def t_container():
    s = np.sin(UU * 2 * PI * 10)
    k = (1 + 0.14 * np.tanh(3 * s)) * (1 + 0.03 * noise(50, 50, 15) + 0.02 * noise(2, 2, 16))
    k *= 1 - 0.1 * np.clip(noise(2, 50, 17), 0, None)
    return shade(col(80, 88, 62), k)


def t_tarp():
    k = 1 + 0.07 * noise(30, 6, 18) + 0.05 * noise(6, 30, 19) + 0.02 * noise(2, 2, 20)
    k *= 1 - 0.15 * lines(UU + 0.25, 2, 0.006)
    return shade(col(176, 153, 115), k)


def t_crate():
    k = 1 + 0.05 * noise(20, 4, 21) + 0.02 * noise(2, 2, 22)
    k *= 1 - 0.25 * lines(VV, 8, 0.03)
    k *= 1 - 0.55 * lines(UU, 2, 0.02)
    img = shade(col(98, 101, 66), k)
    fu, fv = frac(UU * 2), frac(VV * 2)
    img[(fu > 0.3) & (fu < 0.7) & (fv > 0.45) & (fv < 0.55)] = col(190, 178, 120)
    return img


def t_pallet():
    k = (1 + 0.08 * noise(3, 40, 23) + 0.03 * noise(2, 2, 24)) * (1 - 0.5 * lines(UU, 6, 0.06))
    return shade(col(138, 112, 76), k)


def t_hazard():
    yel = (frac((UU + VV) * 4) < 0.5)
    img = np.where(yel[..., None], col(216, 172, 34)[None, None], col(32, 31, 28)[None, None])
    return img * (1 + 0.06 * noise(10, 10, 25))[..., None] * (1 - 0.15 * np.clip(noise(4, 4, 26) - 1.0, 0, None))[..., None]


def t_flat(rgb, amp, seed, size=40):
    def f():
        return shade(col(*rgb), 1 + amp * noise(size, size, seed) + 0.5 * amp * noise(2, 2, seed + 1))
    return f


def t_hvac():
    k = (1 + 0.03 * noise(40, 40, 27)) * (1 - 0.3 * np.maximum(lines(UU, 4, 0.01), lines(VV, 2, 0.01)))
    k *= 1 - 0.2 * lines(VV * 1.0, 24, 0.25) * (frac(UU * 4) > 0.5)
    return shade(col(170, 168, 162), k)


def t_glass():
    frame = np.maximum(lines(UU, 4, 0.05), lines(VV, 2, 0.06))
    g = shade(col(58, 70, 88), 1 + 0.25 * (UU - VV) + 0.04 * noise(30, 30, 28))
    return np.where(frame[..., None] > 0, col(150, 152, 150)[None, None], g)


def t_jersey():
    k = 1 + 0.05 * noise(50, 50, 29) + 0.03 * noise(2, 2, 30) - 0.05 * np.clip(noise(3, 3, 31) - 1.5, 0, None)
    return shade(col(150, 140, 123), k)


# ---- new surfaces for the M1 structures
def t_gconc():         # weathered grey fortified concrete, form-panel joints, tie holes, rust drips (S = 4 m)
    k = grime(60, 0.09) - 0.06 * np.clip(noise(12, 12, 63) - 1.0, 0, None)
    k *= 1 - 0.16 * np.maximum(lines(VV, 2, 0.006), lines(UU, 2, 0.005))
    tie = ((np.abs(frac(UU * 8) - 0.5) < 0.012) & (np.abs(frac(VV * 6) - 0.5) < 0.016))
    k = np.where(tie, k * 0.55, k)
    img = shade(col(122, 119, 110), k)
    rust = np.clip(noise(1.5, 40, 64) - 1.6, 0, None) * 0.25
    return img * (1 - rust[..., None]) + rust[..., None] * col(120, 82, 50)


def t_sandbag():       # running-bond sandbags, 6 rows per tile (S = 1.8 m)
    rows = 6
    r = VV * rows; ri = np.floor(r); fr = r - ri
    uu = UU * 3 + 0.5 * (ri % 2); fu = frac(uu)
    k = (0.62 + 0.38 * np.sin(np.clip(fr, 0, 1) * PI) ** 0.5) * (0.7 + 0.3 * np.sin(np.clip(fu, 0, 1) * PI) ** 0.35)
    k *= 1 + 0.07 * noise(6, 6, 65) + 0.04 * noise(2, 2, 66)
    return shade(col(150, 132, 100), k)


def t_hesco():         # HESCO: tan geotextile behind a welded mesh, cell seams every half tile (S = 2 m)
    k = 1 + 0.05 * noise(12, 30, 67) + 0.03 * noise(2, 2, 68)
    mesh = np.maximum(lines(UU, 12, 0.07), lines(VV, 12, 0.07))
    k *= 1 - 0.35 * lines(UU, 2, 0.02)
    img = shade(col(158, 140, 104), k)
    return np.where(mesh[..., None] > 0, (img * 0.55 + col(130, 128, 118) * 0.45), img)


def t_grate():         # steel floor grating / drain (S = 1 m)
    k = np.where(frac(UU * 16) < 0.35, 1.25, 0.35) * (1 - 0.4 * lines(VV, 4, 0.08)) * (1 + 0.05 * noise(10, 10, 69))
    return shade(col(80, 80, 76), k)


def t_vent():          # louvre blades (S = 1.2 m, 12 blades)
    f = frac(VV * 12)
    k = np.where(f < 0.22, 0.28, 0.62 + 0.55 * f) * (1 + 0.04 * noise(20, 20, 70))
    return shade(col(92, 94, 88), k)


def t_roofg():         # grey-tan flat roof membrane with patched sheets (S = 6 m)
    k = 1 + 0.03 * noise(90, 90, 71) + 0.025 * noise(3, 3, 72) - 0.05 * np.clip(noise(30, 30, 73) - 1.0, 0, None)
    k *= 1 - 0.12 * np.maximum(lines(UU, 3, 0.004), lines(VV, 2, 0.004))
    return shade(col(150, 143, 131), k)


def t_rooft():         # light tan roof membrane (barracks) (S = 6 m)
    k = 1 + 0.03 * noise(90, 90, 74) + 0.02 * noise(3, 3, 75) - 0.05 * np.clip(noise(30, 30, 76) - 1.1, 0, None)
    k *= 1 - 0.1 * lines(VV, 3, 0.004)
    return shade(col(176, 164, 146), k)


def t_corr():          # grey corrugated metal (S = 2 m, 14 corrugations along u)
    s = np.sin(UU * 2 * PI * 14)
    k = (1 + 0.16 * np.tanh(2.5 * s)) * (1 + 0.03 * noise(40, 40, 77) + 0.02 * noise(2, 2, 78))
    k *= 1 - 0.08 * np.clip(noise(2, 60, 79), 0, None)
    return shade(col(150, 151, 150), k)


def t_winlit():        # warm lit glazing with mullions (S = 2 m)
    frame = np.maximum(lines(UU, 4, 0.06), lines(VV, 1, 0.08))
    g = shade(col(228, 176, 92), 1 + 0.18 * (VV - 0.5) + 0.06 * noise(20, 20, 80))
    return np.where(frame[..., None] > 0, col(52, 52, 50)[None, None], g)


def t_win():           # dark window with frame (S = 1.2 m)
    frame = np.maximum(lines(UU, 1, 0.1), lines(VV, 1, 0.1)) + lines(UU + 0.5, 1, 0.04)
    g = shade(col(48, 58, 70), 1 + 0.35 * (UU - VV) + 0.05 * noise(20, 20, 81))
    return np.where(frame[..., None] > 0, col(70, 72, 62)[None, None], g)


def t_shade():         # olive shade sail canvas (S = 3 m)
    k = 1 + 0.06 * noise(30, 8, 82) + 0.04 * noise(8, 30, 83) + 0.02 * noise(2, 2, 84)
    k *= 1 - 0.12 * lines(UU, 3, 0.006)
    return shade(col(128, 124, 88), k)


def t_tank():          # olive painted steel with weld seams and stains (S = 3 m)
    k = 1 + 0.04 * noise(50, 50, 85) + 0.02 * noise(2, 2, 86) - 0.07 * np.clip(noise(3, 50, 87), 0, None)
    k *= 1 - 0.22 * lines(UU, 2, 0.006)
    return shade(col(98, 106, 70), k)


def t_cabinet():       # olive equipment cabinet doors (S = 1.6 m)
    k = 1 + 0.03 * noise(30, 30, 88) + 0.02 * noise(2, 2, 89) - 0.05 * np.clip(noise(2, 40, 90), 0, None)
    k *= 1 - 0.4 * np.maximum(lines(UU, 2, 0.012), lines(VV, 1, 0.012))
    hand = (np.abs(frac(UU * 2) - 0.85) < 0.015) & (np.abs(frac(VV) - 0.5) < 0.06)
    k = np.where(hand, 0.5, k)
    return shade(col(88, 96, 64), k)


def t_tanwall():       # warm tan block wall, coursed (barracks ground floor, factory annex) (S = 3 m)
    k = grime(91, 0.05) * (1 - 0.16 * lines(VV, 7, 0.02)) * (1 - 0.1 * lines(UU + 0.5 * np.floor(VV * 7) % 1, 4, 0.01))
    return shade(col(176, 154, 122), k)


def t_floor():         # dark interior floor (S = 4 m)
    k = 1 + 0.06 * noise(40, 40, 92) + 0.03 * noise(2, 2, 93)
    k *= 1 - 0.2 * np.maximum(lines(UU, 2, 0.006), lines(VV, 2, 0.006))
    return shade(col(92, 90, 84), k)


def t_bconc():         # beige-grey precast panels (power plant hall) (S = 4 m)
    k = grime(94, 0.07)
    k *= 1 - 0.14 * np.maximum(lines(VV, 2, 0.006), lines(UU, 2, 0.005))
    return shade(col(160, 152, 138), k)


def t_olivewall():     # olive painted ribbed upper storey (barracks / factory) (S = 3 m)
    f = frac(UU * 6)
    k = np.where(f < 0.08, 0.72, np.where(f < 0.16, 1.12, 1.0))
    k = k * (1 + 0.03 * noise(60, 60, 95) + 0.02 * noise(2, 2, 96) - 0.07 * np.clip(noise(2, 60, 97), 0, None))
    return shade(col(96, 98, 68), k)


SURF = {  # name: (texture fn, world size of one tile in metres)
    "conc": (t_conc, 4.0), "slab": (t_slab, 6.0), "roof": (t_roof, 4.0), "clad": (t_clad, 3.0),
    "door": (t_door, 2.0), "cont": (t_container, 3.0), "tarp": (t_tarp, 2.0), "crate": (t_crate, 1.2),
    "pallet": (t_pallet, 1.2), "hazard": (t_hazard, 1.6), "hvac": (t_hvac, 2.0), "glass": (t_glass, 2.0),
    "jersey": (t_jersey, 3.0),
    "metal": (t_flat((84, 86, 84), 0.05, 40), 2.0), "dark": (t_flat((30, 30, 28), 0.05, 42), 1.0),
    "yellow": (t_flat((214, 172, 42), 0.05, 44), 2.0), "lamp": (t_flat((255, 238, 186), 0.02, 46), 1.0),
    "rubber": (t_flat((26, 26, 25), 0.05, 48), 1.0), "olive": (t_flat((86, 92, 60), 0.06, 50), 2.0),
    "team": (t_flat((235, 235, 235), 0.0, 52), 1.0),
    "gconc": (t_gconc, 4.0), "sandbag": (t_sandbag, 1.8), "hesco": (t_hesco, 2.0), "grate": (t_grate, 1.0),
    "vent": (t_vent, 1.2), "roofg": (t_roofg, 6.0), "rooft": (t_rooft, 6.0), "corr": (t_corr, 2.0),
    "winlit": (t_winlit, 2.0), "win": (t_win, 1.2), "shade": (t_shade, 3.0), "tank": (t_tank, 3.0),
    "cabinet": (t_cabinet, 1.6), "tanwall": (t_tanwall, 3.0), "floor": (t_floor, 4.0),
    "steel": (t_flat((128, 128, 124), 0.05, 54), 2.0), "red": (t_flat((150, 44, 34), 0.06, 56), 1.0),
    "white": (t_flat((214, 214, 208), 0.03, 58), 2.0), "wood": (t_pallet, 1.2),
    "bconc": (t_bconc, 4.0), "olivewall": (t_olivewall, 3.0),
}


# ====================================================================== kit state
class Kit:
    def __init__(self, asset_id, prefix, mat_name, atlas=4096, ao_res=2048):
        self.id, self.prefix, self.mat_name = asset_id, prefix, mat_name
        self.atlas, self.ao_res = atlas, ao_res
        self.tmp = tempfile.mkdtemp(prefix=prefix + "3d_")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.mats = {}
        self.lights = []        # (object, kind)
        self.empties = []
        self.fence_quads = []   # ((x0,y0),(x1,y1), zbase, height)

    # ---------------------------------------------------------------- images / materials
    def np_to_image(self, name, arr, alpha=None, colorspace="sRGB"):
        a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
        if alpha is not None:
            a8 = np.concatenate([a8, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)[..., None]], 2)
        path = os.path.join(self.tmp, name + ".png")
        Image.fromarray(a8[::-1]).save(path)
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = colorspace
        return img

    def mat(self, sname):
        if sname in self.mats:
            return self.mats[sname]
        fn, _ = SURF[sname]
        m = bpy.data.materials.new("SA_Team" if sname == "team" else "SRC_" + sname)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.85
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = self.np_to_image("tile_" + sname, fn()); tex.interpolation = "Cubic"
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "tile"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        self.mats[sname] = m
        return m

    def part(self, name):
        return Part(self, name)

    # ---------------------------------------------------------------- lights and empties
    def light(self, name, center, kind="dome", r=0.16, size=(0.3, 0.1, 0.2), rot=(0, 0, 0), up=(0, 0, 1)):
        """Separate emissive mesh object `name` with its own material SA_Light_<name> (white, emission 1).
        kind 'dome': small lathe dome of radius r pointing along `up`; 'box': lens box of `size` rotated by `rot`."""
        bm = bmesh.new()
        if kind == "dome":
            prof = [(0, 0.0), (r, 0.0), (r, r * 0.45), (r * 0.8, r * 0.95), (r * 0.42, r * 1.25), (0, r * 1.35)]
            q = V(up).to_track_quat("Z", "Y").to_matrix().to_4x4()
            _lathe_into(bm, prof, 10, q)
        else:
            M = Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
            bmesh.ops.create_cube(bm, size=1.0, matrix=M)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); o.location = V(center); self.scene.collection.objects.link(o)
        m = bpy.data.materials.new("SA_Light_" + name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Strength"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.4
        me.materials.append(m)
        for p in me.polygons:
            p.use_smooth = kind == "dome"
        self.lights.append(o)
        return o

    def empty(self, name, loc):
        o = bpy.data.objects.new(name, None); o.location = V(loc); o.empty_display_type = "SINGLE_ARROW"
        o.empty_display_size = 1.5
        self.scene.collection.objects.link(o)
        self.empties.append(o)
        return o

    def fence(self, a, b, z0, h):
        self.fence_quads.append((a, b, z0, h))

    # ---------------------------------------------------------------- finish: atlas, bake, export
    def finish(self, building, props, out_dir):
        scene = self.scene
        os.makedirs(out_dir, exist_ok=True)
        objs = [building.build(), props.build()]
        building_o, props_o = objs
        # chain-link fence object
        fence = None
        if self.fence_quads:
            fbm = bmesh.new(); fuv = fbm.loops.layers.uv.new("UVMap")
            for (x0, y0), (x1, y1), z0, h in self.fence_quads:
                L = math.hypot(x1 - x0, y1 - y0)
                vs = [fbm.verts.new(p) for p in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z0 + h), (x0, y0, z0 + h))]
                f = fbm.faces.new(vs)
                for lp, (uu, vv) in zip(f.loops, ((0, 0), (L, 0), (L, h), (0, h))):
                    lp[fuv].uv = (uu, vv)
            fme = bpy.data.meshes.new("Fence"); fbm.to_mesh(fme); fbm.free()
            fence = bpy.data.objects.new("Fence", fme); scene.collection.objects.link(fence)
            fm = bpy.data.materials.new(self.prefix + "_Fence"); fm.use_nodes = True; fm.use_backface_culling = False
            fb = fm.node_tree.nodes["Principled BSDF"]; fb.inputs["Roughness"].default_value = 0.6
            fb.inputs["Metallic"].default_value = 0.3
            n = 256
            u = (np.arange(n) + 0.5)[None, :].repeat(n, 0); v = (np.arange(n) + 0.5)[:, None].repeat(n, 1)
            per = 32.0
            d1 = np.abs(frac((u + v) / per) - 0.5) * per; d2 = np.abs(frac((u - v) / per) - 0.5) * per
            ca = np.clip(1.9 - np.minimum(d1, d2), 0, 1)
            ftex = fm.node_tree.nodes.new("ShaderNodeTexImage")
            ftex.image = self.np_to_image(self.id + "_chainlink", np.full((n, n, 3), 0.62, np.float32), ca)
            fm.node_tree.links.new(ftex.outputs["Color"], fb.inputs["Base Color"])
            fm.node_tree.links.new(ftex.outputs["Alpha"], fb.inputs["Alpha"])
            fme.materials.append(fm)

        # atlas UVs
        for o in objs:
            o.data.uv_layers.new(name="atlas")
            o.data.uv_layers.active = o.data.uv_layers["atlas"]
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = building_o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0015, area_weight=0.0)
        bpy.ops.uv.pack_islands(rotate=True, margin=0.0015, shape_method="AABB")
        bpy.ops.object.mode_set(mode="OBJECT")

        # bake colour then AO
        scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.seed = 7
        scene.render.bake.margin = 8
        col_img = bpy.data.images.new("bake_col", self.atlas, self.atlas)
        ao_img = bpy.data.images.new("bake_ao", self.ao_res, self.ao_res); ao_img.colorspace_settings.name = "Non-Color"
        src_mats = {m for o in objs for m in o.data.materials}
        targets = {}
        for m in src_mats:
            nd = m.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = col_img
            m.node_tree.nodes.active = nd; targets[m] = nd
        hidden = ([fence] if fence else []) + self.lights
        for o in hidden:
            o.hide_render = True
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = building_o
        scene.cycles.samples = 8
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=8, use_clear=True)
        for m, nd in targets.items():
            nd.image = ao_img
        world = bpy.data.worlds.new("bakeworld"); scene.world = world
        world.light_settings.distance = 4.0
        bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, -0.001)); ground = bpy.context.active_object
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = building_o
        scene.cycles.samples = 24
        bpy.ops.object.bake(type="AO", margin=8, use_clear=True)
        bpy.data.objects.remove(ground)
        for o in hidden:
            o.hide_render = False

        def img_np(img):
            a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
            return a.reshape(img.size[1], img.size[0], 4)[..., :3]

        # composite colour x AO in row chunks (keeps peak memory low on a shared machine; same result)
        c = img_np(col_img)
        bpy.data.images.remove(col_img)
        ao8 = (img_np(ao_img)[..., 0] * 255).astype(np.uint8)
        bpy.data.images.remove(ao_img)
        ao_full = np.asarray(Image.fromarray(ao8).resize((self.atlas, self.atlas), Image.BILINEAR), np.uint8)
        out8 = np.empty((self.atlas, self.atlas, 3), np.uint8)
        for r0 in range(0, self.atlas, 512):
            cc = c[r0:r0 + 512]
            ao = ao_full[r0:r0 + 512].astype(np.float32) / 255
            lin = np.where(cc <= 0.04045, cc / 12.92, ((cc + 0.055) / 1.055) ** 2.4)
            lin *= (0.28 + 0.72 * ao ** 1.1)[..., None]
            srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
            out8[r0:r0 + 512] = (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)
        del c, ao_full
        out8 = out8[::-1]
        atlas_path = os.path.join(self.tmp, self.id + "_albedo.jpg")
        Image.fromarray(out8).save(atlas_path, quality=90, optimize=True)

        # final materials
        fin = bpy.data.materials.new(self.mat_name); fin.use_nodes = True; fin.use_backface_culling = True
        bs = fin.node_tree.nodes["Principled BSDF"]
        bs.inputs["Roughness"].default_value = 0.82; bs.inputs["Metallic"].default_value = 0.0
        at = fin.node_tree.nodes.new("ShaderNodeTexImage"); at.image = bpy.data.images.load(atlas_path)
        fin.node_tree.links.new(at.outputs["Color"], bs.inputs["Base Color"])
        team = self.mats.get("team")
        if team:
            team.use_backface_culling = True
            for nd in [nd for nd in team.node_tree.nodes if nd.type in ("TEX_IMAGE", "UVMAP")]:
                team.node_tree.nodes.remove(nd)
            team.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
        for o in objs:
            me = o.data
            idx = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("material_index", idx)
            is_team = np.array([m.name == "SA_Team" for m in me.materials])
            new_idx = np.where(is_team[idx], 1, 0).astype(np.int32)
            me.materials.clear(); me.materials.append(fin); me.materials.append(team if team else fin)
            me.polygons.foreach_set("material_index", new_idx)
            if not is_team.any():
                me.materials.pop(index=1)
            me.uv_layers.remove(me.uv_layers["tile"])
            me.uv_layers["atlas"].name = "UVMap"
        if fence:
            bpy.ops.object.select_all(action="DESELECT")
            props_o.select_set(True); fence.select_set(True); bpy.context.view_layer.objects.active = props_o
            bpy.ops.object.join()
            props_o = bpy.context.active_object; props_o.name = "Props"; props_o.data.name = "Props"
        objs = [building_o, props_o]

        ntris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs + self.lights}
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs + self.lights + self.empties:
            o.select_set(True)
        glb = os.path.join(out_dir, self.id + ".glb")
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True, use_selection=True,
                                  export_image_format="AUTO")
        total = sum(ntris.values())
        print(self.id.upper(), "OK tris", {k: v for k, v in ntris.items() if not k.startswith("Light_")},
              "lights", len(self.lights), "light tris", sum(v for k, v in ntris.items() if k.startswith("Light_")),
              "total", total, "dims", [round(v, 2) for v in building_o.dimensions], "glb bytes", os.path.getsize(glb))
        return glb


def _lathe_into(bm, prof, seg, M):
    """Surface of revolution about local Z. prof = [(r, z), ...]; r == 0 makes a pole. Closed if both ends are poles."""
    rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([bm.verts.new(M @ V((0, 0, z)))])
        else:
            rings.append([bm.verts.new(M @ V((r * math.cos(2 * PI * i / seg), r * math.sin(2 * PI * i / seg), z)))
                          for i in range(seg)])
    faces = []
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                faces.append(bm.faces.new((a[0], b[i], b[j])))
            elif len(b) == 1:
                faces.append(bm.faces.new((a[i], a[j], b[0])))
            else:
                faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(rings[0][::-1]))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


# ====================================================================== geometry accumulator
class Part:
    """Accumulates primitives per (surface, bevel) into bmeshes; build() makes one joined object."""

    def __init__(self, kit, name):
        self.kit, self.name, self.bms = kit, name, {}
        self._once = set()

    def once(self, *key):
        """True the first time a key is seen (avoids coincident duplicate posts, which bake black AO)."""
        k = tuple(round(v, 3) if isinstance(v, float) else v for v in key)
        if k in self._once:
            return False
        self._once.add(k)
        return True

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

    def pipe(self, m, pts, r, seg=6):
        """Polyline pipe: struts between consecutive points plus small joint balls (cylinders)."""
        for a, b in zip(pts, pts[1:]):
            self.strut(m, a, b, r, seg)

    def prism(self, m, pts, axis, a0, a1, bev=False, drop=True):
        """Extrude a closed 2D profile. axis 'x': pts are (y, z) over x in [a0, a1]; axis 'y': pts are (x, z) over y."""
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
        if drop:
            self._drop_bottom(bm, A + B)

    def frustum(self, m, x0, x1, y0, y1, z0, z1, inset, bev=False, insety=None):
        bm = self.bm(m, bev)
        iy = inset if insety is None else insety
        A = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
        B = [bm.verts.new(p) for p in ((x0 + inset, y0 + iy, z1), (x1 - inset, y0 + iy, z1),
                                       (x1 - inset, y1 - iy, z1), (x0 + inset, y1 - iy, z1))]
        bm.faces.new(B)
        for i in range(4):
            bm.faces.new((A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]))

    def quad(self, m, pts):
        """One planar face from 4 points; winding defines the visible side (counter-clockwise = front)."""
        bm = self.bm(m, "in")                              # 'in' = keep winding (no normal recalculation)
        bm.faces.new([bm.verts.new(p) for p in pts])

    def room(self, wall, floor, ceil, x0, x1, y0, y1, z0, z1, open_side="-y"):
        """Inward-facing interior box (seen from inside through the open side), e.g. an open vehicle bay."""
        a = (x0, y0, z0); b = (x1, y0, z0); c = (x1, y1, z0); d = (x0, y1, z0)
        e = (x0, y0, z1); f = (x1, y0, z1); g = (x1, y1, z1); h = (x0, y1, z1)
        self.quad(floor, (a, b, c, d))                     # normal +z
        self.quad(ceil, (e, h, g, f))                      # normal -z
        if open_side != "+y":
            self.quad(wall, (d, c, g, h))                  # back wall, normal -y
        if open_side != "-y":
            self.quad(wall, (a, e, f, b))
        if open_side != "-x":
            self.quad(wall, (a, d, h, e))                  # normal +x
        if open_side != "+x":
            self.quad(wall, (b, f, g, c))                  # normal -x

    def lathe(self, m, prof, c=(0, 0, 0), axis=(0, 0, 1), seg=12):
        M = Matrix.Translation(c) @ V(axis).to_track_quat("Z", "Y").to_matrix().to_4x4()
        _lathe_into(self.bm(m), prof, seg, M)

    def tank(self, m, c, r, length, axis=(1, 0, 0), seg=14, cap=None):
        """Capsule-like horizontal tank with domed ends."""
        cap = r * 0.55 if cap is None else cap
        h = length / 2 - cap
        prof = [(0, -h - cap)]
        for k in range(1, 4):
            t = k / 4 * PI / 2
            prof.append((r * math.sin(t), -h - cap * math.cos(t)))
        prof += [(r, -h), (r, h)]
        for k in range(3, 0, -1):
            t = k / 4 * PI / 2
            prof.append((r * math.sin(t), h + cap * math.cos(t)))
        prof.append((0, h + cap))
        self.lathe(m, prof, c, axis, seg)

    def dish(self, m, c, R, depth, axis, t=0.06, seg=16):
        """Parabolic dish shell, concave side facing `axis`."""
        prof = [(0, -t)]
        rs = [0.3, 0.55, 0.78, 1.0]
        for f in rs:
            prof.append((R * f, depth * f * f - t))
        for f in reversed(rs):
            prof.append((R * f * (0.985 if f == 1.0 else 1.0), depth * f * f + (0.0 if f < 1 else 0.0)))
        prof.append((0, 0))
        self.lathe(m, prof, c, axis, seg)

    def railing(self, m, pts, z, h=1.05, spacing=1.6, r=0.025):
        """Hand railing along a polyline at base height z: posts, top rail, mid rail."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / spacing)))
            for k in range(n + (1 if (x1, y1) == pts[-1] else 0)):
                t = k / n
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                self.strut(m, (x, y, z), (x, y, z + h), r, seg=4)
            self.strut(m, (x0, y0, z + h), (x1, y1, z + h), r, seg=4)
            self.strut(m, (x0, y0, z + h * 0.5), (x1, y1, z + h * 0.5), r * 0.7, seg=4)

    def stairs(self, m, x0, x1, y0, y1, z0, z1, rise_axis, steps=None, stringer="metal", rail=True):
        """Steel stair: treads rising from (low end) to (high end). rise_axis '+y','-y','+x','-x' = run direction."""
        H = z1 - z0
        n = steps or max(3, int(round(H / 0.2)))
        ax = rise_axis[1]; sgn = 1 if rise_axis[0] == "+" else -1
        if ax == "y":
            a0, a1 = (y0, y1) if sgn > 0 else (y1, y0)
        else:
            a0, a1 = (x0, x1) if sgn > 0 else (x1, x0)
        run = (a1 - a0) / n
        for k in range(n):
            s0 = a0 + run * k; s1 = s0 + run
            zt = z0 + H * (k + 1) / n
            if ax == "y":
                self.span(m, x0 + 0.06, x1 - 0.06, min(s0, s1), max(s0, s1), zt - 0.05, zt, bottom=True)
            else:
                self.span(m, min(s0, s1), max(s0, s1), y0 + 0.06, y1 - 0.06, zt - 0.05, zt, bottom=True)
        # stringers + rails
        sides = (x0 + 0.03, x1 - 0.03) if ax == "y" else (y0 + 0.03, y1 - 0.03)
        for s in sides:
            if ax == "y":
                p0, p1 = (s, a0, z0), (s, a1, z1)
            else:
                p0, p1 = (a0, s, z0), (a1, s, z1)
            self.strut(stringer, p0, p1, 0.06, seg=4)
            if rail:
                self.strut(stringer, (p0[0], p0[1], p0[2] + 0.95), (p1[0], p1[1], p1[2] + 0.95), 0.022, seg=4)
                self.strut(stringer, p0, (p0[0], p0[1], p0[2] + 0.95), 0.022, seg=4)
                self.strut(stringer, p1, (p1[0], p1[1], p1[2] + 0.95), 0.022, seg=4)

    def ladder(self, p0, along, height, out, n_rungs=None, m="metal"):
        p0 = V(p0); along = V(along); out = V(out)
        n_rungs = n_rungs or max(4, int(height / 0.35))
        for s in (-0.22, 0.22):
            a = p0 + along * s
            self.strut(m, a + out * 0.12, a + out * 0.12 + V((0, 0, height)), 0.025, seg=4)
        for k in range(n_rungs):
            z = 0.35 + k * (height - 0.4) / (n_rungs - 1)
            self.strut(m, p0 + along * -0.22 + out * 0.12 + V((0, 0, z)), p0 + along * 0.22 + out * 0.12 + V((0, 0, z)), 0.015, seg=4)

    def build(self):
        kit = self.kit
        objs = []
        for (sname, bev), bm in sorted(self.bms.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
            if not bm.faces:
                bm.free(); continue
            if bev != "in":
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            else:
                bm.normal_update()
            S = SURF[sname][1]
            uv = bm.loops.layers.uv.new("tile")
            for f in bm.faces:
                n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
                for lp in f.loops:
                    p = lp.vert.co
                    u, v = ((p.x, p.y) if ax == 2 else (p.y, p.z) if ax == 0 else (p.x, p.z))
                    lp[uv].uv = (u / S, v / S)
            me = bpy.data.meshes.new(f"{self.name}_{sname}_{bev}")
            bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(me.name, me); kit.scene.collection.objects.link(o)
            me.materials.append(kit.mat(sname))
            if bev is True:
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


# ====================================================================== previews of the exported GLB
LIGHT_PREVIEW = {"Light_Status": (0.15, 1.0, 0.25), "Light_Beacon": (1.0, 0.08, 0.05), "Light_Flood": (1.0, 0.9, 0.7)}


def previews(glb, out_dir, asset_id, extent, concept=None, only=None, res=(640, 400), samples=24,
             target_z=2.5, rts=(-35, 50)):
    """Render rts/front/side/rear PNGs (m1_<id>_*.png) of the exported GLB. `extent` = largest footprint side (m).
    Light objects are tinted in the preview only (status green, beacon red, flood warm) to mimic the game."""
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=glb)
    for o in scene.objects:
        for pre, c in LIGHT_PREVIEW.items():
            if o.name.startswith(pre) and o.type == "MESH":
                for m in o.data.materials:
                    b = m.node_tree.nodes.get("Principled BSDF")
                    if b:
                        b.inputs["Base Color"].default_value = (*c, 1)
                        b.inputs["Emission Color"].default_value = (*c, 1)
                        b.inputs["Emission Strength"].default_value = 6.0
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = samples
    scene.cycles.use_denoising = True; scene.cycles.max_bounces = 3
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.32, 0.33, 0.36, 1); bg.inputs["Strength"].default_value = 0.6
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.2; sun.angle = math.radians(3)
    so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
    so.rotation_euler = Euler((math.radians(42), 0, math.radians(-38)))
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.11, 0.10, 0.075, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.002)); bpy.context.active_object.data.materials.append(gm)
    cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam
    k = extent / 22.0
    paths = {}

    def shot(name, az_deg, el_deg, dist=46.0, lens=50):
        tgt = V((0, 0, target_z)); az, el = math.radians(az_deg), math.radians(el_deg)
        d = V((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        cam.location = tgt + d * dist * k
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam_d.type = "PERSP"; cam_d.lens = lens
        p = os.path.join(out_dir, f"m1_{asset_id}_{name}.png")
        paths[name] = p
        if only and name not in only:
            return
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print("rendered", p)

    shot("rts", rts[0], rts[1], dist=56)
    shot("front", 0, 20, dist=54)
    shot("side", -90, 14, dist=54)
    shot("rear", 150, 32, dist=56)
    if concept and os.path.exists(paths["rts"]):
        a = Image.open(paths["rts"]).convert("RGB")
        b = Image.open(concept).convert("RGB")
        b = b.resize((int(b.width * a.height / b.height), a.height), Image.LANCZOS)
        sbs = Image.new("RGB", (a.width + b.width + 12, a.height), (20, 20, 20))
        sbs.paste(a, (0, 0)); sbs.paste(b, (a.width + 12, 0))
        sbs.save(os.path.join(out_dir, f"m1_{asset_id}_vs_concept.png"))
        print("wrote side-by-side")


def cli(argv):
    """Common CLI: <out_dir> [--previews dir] [--concept png] [--only rts,front] [--previews-only]"""
    argv = list(argv)

    def _opt(name):
        if name in argv:
            i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
        return None
    o = {"previews": _opt("--previews"), "concept": _opt("--concept"), "only": _opt("--only")}
    o["skip_build"] = "--previews-only" in argv
    if o["skip_build"]:
        argv.remove("--previews-only")
    o["only"] = o["only"].split(",") if o["only"] else None
    o["out"] = argv[0] if argv else "."
    return o


# ====================================================================== shared prop / detail helpers
JP = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.12, 0.3), (0.08, 0.81), (-0.08, 0.81), (-0.12, 0.3), (-0.3, 0.08)]


def _runs(a, b, seglen, gap):
    L = abs(b - a); n = max(1, int(round(L / (seglen + gap)))); s = L / n
    return [(min(a, b) + k * s + gap / 2, min(a, b) + (k + 1) * s - gap / 2) for k in range(n)]


def jersey_run(P, a, b, fixed, axis, z, seglen=2.8, gap=0.12, sx=1.0, sz=1.0, m="jersey"):
    """Concrete barrier segments along `axis` ('x' or 'y') between a..b, centred across the run at `fixed`."""
    for t0, t1 in _runs(a, b, seglen, gap):
        P.prism(m, [(fixed + px * sx, z + pz * sz) for px, pz in JP], axis, t0, t1)


def sandbag_run(P, a, b, fixed, axis, z, h=0.95, w=0.95):
    prof = [(-w / 2, 0), (w / 2, 0), (w * 0.47, h * 0.45), (w * 0.38, h * 0.85), (w * 0.2, h), (-w * 0.2, h),
            (-w * 0.38, h * 0.85), (-w * 0.47, h * 0.45)]
    P.prism("sandbag", [(fixed + p, z + q) for p, q in prof], axis, min(a, b), max(a, b))


def hesco_run(P, a, b, fixed, axis, z, size=1.1, h=1.4):
    for t0, t1 in _runs(a, b, size, 0.04):
        c = (t0 + t1) / 2
        if axis == "x":
            P.span("hesco", t0, t1, fixed - size / 2, fixed + size / 2, z, z + h)
            P.span("tarp", t0 + 0.04, t1 - 0.04, fixed - size / 2 + 0.04, fixed + size / 2 - 0.04, z + h - 0.06, z + h - 0.02)
        else:
            P.span("hesco", fixed - size / 2, fixed + size / 2, t0, t1, z, z + h)
            P.span("tarp", fixed - size / 2 + 0.04, fixed + size / 2 - 0.04, t0 + 0.04, t1 - 0.04, z + h - 0.06, z + h - 0.02)


def pallet(P, cx, cy, base, sx=1.2, sy=1.0):
    P.span("pallet", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, base, base + 0.14)
    return base + 0.14


def ammo_pallet(P, cx, cy, base, layers=2):
    z = pallet(P, cx, cy, base)
    cw, cd, ch = 0.57, 0.47, 0.36
    for l in range(layers):
        for i in (-1, 1):
            for j in (-1, 1):
                P.box("crate", (cx + i * (cw / 2 + 0.01), cy + j * (cd / 2 + 0.01), z + l * (ch + 0.01) + ch / 2), (cw, cd, ch))
    P.span("rubber", cx - 0.6, cx + 0.6, cy - 0.04, cy + 0.04, base + 0.14, z + layers * (ch + 0.01) + 0.015)
    return z + layers * (ch + 0.01)


def crate(P, cx, cy, base, sx, sy, sz, m="crate", yaw=0.0):
    P.box(m, (cx, cy, base + sz / 2), (sx, sy, sz), (0, 0, yaw))


def tarp_stack(P, cx, cy, base, sx, sy, h):
    z = base + 0.14
    P.span("pallet", cx - sx / 2 + 0.05, cx + sx / 2 - 0.05, cy - sy / 2 + 0.05, cy + sy / 2 - 0.05, base, z)
    P.span("tarp", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z, z + h - 0.15, bev=True)
    P.frustum("tarp", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z + h - 0.15, z + h, 0.12)
    for t in (-0.28, 0.28):
        if sx >= sy:
            x = cx + t * sx
            P.span("rubber", x - 0.04, x + 0.04, cy - sy / 2 - 0.02, cy + sy / 2 + 0.02, z, z + h + 0.015)
        else:
            y = cy + t * sy
            P.span("rubber", cx - sx / 2 - 0.02, cx + sx / 2 + 0.02, y - 0.04, y + 0.04, z, z + h + 0.015)


def drum(P, x, y, base, m="olive"):
    P.cyl(m, (x, y, base + 0.45), 0.29, 0.9, seg=10)
    P.cyl("metal", (x, y, base + 0.91), 0.3, 0.03, seg=10, bottom=True)


def hvac(P, x, y, z, sx=1.5, sy=1.15, h=0.85, fans=1, axis="x"):
    """Rooftop condenser: plinth, louvred box, fan disc(s) on top."""
    P.span("metal", x - sx / 2 - 0.08, x + sx / 2 + 0.08, y - sy / 2 - 0.08, y + sy / 2 + 0.08, z, z + 0.12)
    P.span("hvac", x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, z + 0.12, z + h, bev=True)
    r = min(sx / fans if axis == "x" else sx, sy / fans if axis == "y" else sy) * 0.36
    for k in range(fans):
        t = (k + 0.5) / fans - 0.5
        fx, fy = (x + t * sx, y) if axis == "x" else (x, y + t * sy)
        P.cyl("dark", (fx, fy, z + h + 0.01), r, 0.04, seg=14)
        P.cyl("metal", (fx, fy, z + h + 0.035), r * 0.28, 0.05, seg=8)
        P.strut("metal", (fx - r, fy, z + h + 0.05), (fx + r, fy, z + h + 0.05), 0.012, seg=4)
        P.strut("metal", (fx, fy - r, z + h + 0.05), (fx, fy + r, z + h + 0.05), 0.012, seg=4)


def louvre_panel(P, axis, fixed, a, z, out, w=2.0, h=1.0, frame="metal"):
    """Framed louvre on a wall. axis 'x': wall normal along x (a = y centre); 'y': wall normal along y (a = x)."""
    fw = 0.09
    if axis == "x":
        P.span(frame, *sorted((fixed, fixed + out * 0.07)), a - w / 2 - fw, a + w / 2 + fw, z - h / 2 - fw, z + h / 2 + fw)
        P.span("vent", *sorted((fixed + out * 0.07, fixed + out * 0.08)), a - w / 2, a + w / 2, z - h / 2, z + h / 2)
        P.span(frame, *sorted((fixed, fixed + out * 0.14)), a - w / 2 - fw, a + w / 2 + fw, z + h / 2, z + h / 2 + fw)
    else:
        P.span(frame, a - w / 2 - fw, a + w / 2 + fw, *sorted((fixed, fixed + out * 0.07)), z - h / 2 - fw, z + h / 2 + fw)
        P.span("vent", a - w / 2, a + w / 2, *sorted((fixed + out * 0.07, fixed + out * 0.08)), z - h / 2, z + h / 2)
        P.span(frame, a - w / 2 - fw, a + w / 2 + fw, *sorted((fixed, fixed + out * 0.14)), z + h / 2, z + h / 2 + fw)


def wall_lamp(P, kit, axis, fixed, a, z, out, name, status=True):
    """Bracket + housing on a wall; the lens is a separate emissive Light object."""
    if axis == "y":
        P.span("metal", a - 0.12, a + 0.12, *sorted((fixed, fixed + out * 0.16)), z - 0.14, z + 0.14, bottom=True)
        kit.light(name, (a, fixed + out * 0.16, z), "dome", r=0.1, up=(0, out, 0))
    else:
        P.span("metal", *sorted((fixed, fixed + out * 0.16)), a - 0.12, a + 0.12, z - 0.14, z + 0.14, bottom=True)
        kit.light(name, (fixed + out * 0.16, a, z), "dome", r=0.1, up=(out, 0, 0))


def roof_beacon(P, kit, x, y, z, name, r=0.13):
    """Small socket + red aviation beacon dome (separate Light object) on top of a mast at height z."""
    P.cyl("metal", (x, y, z + 0.06), r * 0.9, 0.12, seg=8, bottom=True)
    kit.light(name, (x, y, z + 0.12), "dome", r=r)


def flood_head(P, kit, x, y, z, yaw, name, tilt=35):
    """Flood-light head aimed along yaw (radians, 0 = +X) and tilted down; lens is a Light object."""
    P.box("metal", (x, y, z), (0.36, 0.42, 0.3), (0, math.radians(tilt), yaw), bottom=True)
    d = V((math.cos(yaw), math.sin(yaw), 0)) * 0.19
    kit.light(name, (x + d.x, y + d.y, z - 0.19 * math.sin(math.radians(tilt))), "box", size=(0.05, 0.34, 0.24),
              rot=(0, math.radians(tilt), yaw))


def light_pole(P, kit, x, y, base, height, yaw, names):
    P.span("conc", x - 0.25, x + 0.25, y - 0.25, y + 0.25, base, base + 0.35, bev=True)
    P.cyl("metal", (x, y, base + 0.35 + height / 2), 0.09, height, seg=8, r2=0.06)
    zt = base + 0.35 + height
    P.box("metal", (x, y, zt), (0.9, 0.08, 0.08), (0, 0, yaw + PI / 2), bottom=True)
    for s, nm in zip((-1, 1), names):
        hx = x + s * 0.38 * math.cos(yaw + PI / 2); hy = y + s * 0.38 * math.sin(yaw + PI / 2)
        flood_head(P, kit, hx, hy, zt - 0.12, yaw, nm, tilt=30)
