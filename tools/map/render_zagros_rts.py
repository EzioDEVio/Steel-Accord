"""Steel Accord - perspective preview of the Zagros Basin map from a 52-degree RTS camera (Blender bpy 5.x, Cycles CPU).

Run:  python3 -I tools/map/render_zagros_rts.py <map_dir> <albedo.png> <out.png> [--target x,z] [--dist 260] [--yaw 0]
        map_dir   godot/maps/zagros_basin (height.r16 + map.json)
        albedo    colour map from gen_zagros_basin.py --albedo (approximates the in-game terrain shader)
Places every prop of map.json (and the oil derricks) as collection instances of the GLBs in
godot/assets/units3d/props. Coordinates: Godot (x, y, z) -> Blender (x, -z, y); Godot yaw = Blender Z rotation.
This is a PREVIEW render, not an in-game screenshot.
"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector as V, Euler

argv = sys.argv[1:]


def opt(name, default):
    if name in argv:
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
    return default


TARGET = [float(v) for v in opt("--target", "0,350").split(",")]
DIST = float(opt("--dist", "270"))
YAW = float(opt("--yaw", "0"))
RES = [int(v) for v in opt("--res", "1600,900").split(",")]
SAMPLES = int(opt("--samples", "24"))
MAP, ALB, OUT = argv[0], argv[1], argv[2]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROPS = os.path.join(ROOT, "godot", "assets", "units3d", "props")

mj = json.load(open(os.path.join(MAP, "map.json")))
hs = mj["height_scale"]
raw = np.fromfile(os.path.join(MAP, "height.r16"), "<u2")
n = int(round(math.sqrt(raw.size)))
H = raw.reshape(n, n).astype(np.float64) / 65535.0 * hs
half = mj["size_m"][0] / 2
step = mj["size_m"][0] / (n - 1)


def h_at(x, z):
    fx = (x + half) / step; fz = (z + half) / step
    i0 = int(np.clip(math.floor(fz), 0, n - 2)); j0 = int(np.clip(math.floor(fx), 0, n - 2))
    tz = fz - i0; tx = fx - j0
    a = H[i0, j0] * (1 - tx) + H[i0, j0 + 1] * tx
    b = H[i0 + 1, j0] * (1 - tx) + H[i0 + 1, j0 + 1] * tx
    return a * (1 - tz) + b * tz


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ------------------------------------------------------------------ terrain mesh
xs = -half + step * np.arange(n)
gx, gz = np.meshgrid(xs, xs)
co = np.stack([gx.ravel(), -gz.ravel(), H.ravel()], 1).astype(np.float32)
idx = np.arange(n * n).reshape(n, n)
a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
quads = np.stack([a, d, c, b], 1)               # winding so normals face +Z in Blender (y is flipped)
me = bpy.data.meshes.new("Terrain")
me.vertices.add(n * n); me.vertices.foreach_set("co", co.ravel())
nq = quads.shape[0]
me.loops.add(nq * 4); me.loops.foreach_set("vertex_index", quads.ravel().astype(np.int32))
me.polygons.add(nq)
me.polygons.foreach_set("loop_start", (np.arange(nq) * 4).astype(np.int32))
me.polygons.foreach_set("loop_total", np.full(nq, 4, np.int32))
uvl = me.uv_layers.new(name="UVMap")
vi = quads.ravel()
uv = np.stack([(vi % n) / (n - 1), 1.0 - (vi // n) / (n - 1)], 1).astype(np.float32)
uvl.data.foreach_set("uv", uv.ravel())
me.update(calc_edges=True); me.validate()
me.polygons.foreach_set("use_smooth", np.ones(nq, bool))
ter = bpy.data.objects.new("Terrain", me); sc.collection.objects.link(ter)
print("terrain up-facing normal z of first face:", me.polygons[0].normal.z)

mat = bpy.data.materials.new("TerrainMat"); mat.use_nodes = True
nt = mat.node_tree; bs = nt.nodes["Principled BSDF"]
bs.inputs["Roughness"].default_value = 0.95
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(ALB); tex.interpolation = "Cubic"
tex.extension = "EXTEND"
noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 2400.0; noise.inputs["Detail"].default_value = 6.0
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 0.22
nt.links.new(tex.outputs["Color"], mix.inputs["A"])
ramp = nt.nodes.new("ShaderNodeMapRange"); ramp.inputs["From Min"].default_value = 0.3; ramp.inputs["From Max"].default_value = 0.7
ramp.inputs["To Min"].default_value = 0.75; ramp.inputs["To Max"].default_value = 1.25
nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
comb = nt.nodes.new("ShaderNodeCombineColor")
for k in ("Red", "Green", "Blue"):
    nt.links.new(ramp.outputs["Result"], comb.inputs[k])
nt.links.new(comb.outputs["Color"], mix.inputs["B"])
nt.links.new(mix.outputs["Result"], bs.inputs["Base Color"])
me.materials.append(mat)

# ------------------------------------------------------------------ props as collection instances
protos = {}


def proto(name):
    if name in protos:
        return protos[name]
    path = os.path.join(PROPS, name + ".glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    col = bpy.data.collections.new("P_" + name)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    protos[name] = col
    return col


def place(name, x, z, yaw=0.0, s=1.0):
    e = bpy.data.objects.new(f"{name}", None)
    e.instance_type = "COLLECTION"; e.instance_collection = proto(name)
    e.location = (x, -z, h_at(x, z))
    e.rotation_euler = (0, 0, math.radians(yaw))
    e.scale = (s, s, s)
    sc.collection.objects.link(e)


tx, tz = TARGET
cnt = 0
for p in mj["props"]:
    if p["type"] not in ("village_house", "ruin", "rock_cluster", "date_palm", "scrub", "pylon"):
        continue
    x, z = p["pos"]
    if abs(x - tx) > 520 or abs(z - tz) > 620:
        continue
    place(p["type"], x, z, p.get("yaw_deg", 0.0), p.get("scale", 1.0)); cnt += 1
for d in mj["oil_derricks"]:
    x, z = d["pos"]
    place("oil_derrick", x, z, 0.0, 1.0); cnt += 1
print("instances", cnt)

# ------------------------------------------------------------------ light, sky, camera
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.55, 0.62, 0.72, 1); bg.inputs["Strength"].default_value = 0.55
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.0; sun.angle = math.radians(1.5); sun.color = (1.0, 0.94, 0.85)
so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
so.rotation_euler = Euler((math.radians(58), 0, math.radians(-125)))
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 32; cam_d.clip_end = 5000
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
tgt = V((tx, -tz, h_at(tx, tz)))
el = math.radians(52.0); az = math.radians(YAW)
# YAW 0: camera south of the target looking north (Godot -Z = Blender +Y)
dvec = V((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
cam.location = tgt + dvec * DIST
cam.rotation_euler = (-dvec).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True; sc.cycles.max_bounces = 3
sc.render.resolution_x, sc.render.resolution_y = RES
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
