"""Steel Accord - original environment props (Blender bpy 5.x).
Run: python3 env_props.py <out_dir> -> props.glb with nodes Rock0..Rock5, Bush0..Bush3, Barrier, Pole, Drum."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix, Euler
OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
PI = math.pi


def mat(name, rgb, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


M = {"rock": mat("SA_Rock", (0.2, 0.19, 0.17), 0.85), "leaf": mat("SA_Leaf", (0.06, 0.09, 0.03), 0.8),
     "wood": mat("SA_Wood", (0.12, 0.08, 0.05), 0.85), "concrete": mat("SA_Concrete", (0.35, 0.34, 0.32), 0.9),
     "drum": mat("SA_Drum", (0.1, 0.16, 0.08), 0.5), "metal": mat("SA_Metal", (0.03, 0.03, 0.03), 0.5)}


def apply_all(o):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)


def finish(o, name, m, x, smooth=None):
    o.name = name; o.data.name = name
    o.data.materials.clear(); o.data.materials.append(m)
    apply_all(o)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if smooth is not None:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth))
    o.location = (x, 0, 0)


# ---- boulders: two displacement layers (broad form + fractured faces), then decimated to faceted low-poly
for i in range(6):
    random.seed(300 + i)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1.0)
    o = bpy.context.active_object
    o.scale = (1.0 + random.random() * 0.6, 0.8 + random.random() * 0.5, 0.7 + random.random() * 0.5)
    t1 = bpy.data.textures.new(f"r1{i}", "CLOUDS"); t1.noise_scale = 0.9; t1.noise_depth = 3
    d1 = o.modifiers.new("d1", "DISPLACE"); d1.texture = t1; d1.strength = 0.5; d1.texture_coords = "OBJECT"
    t2 = bpy.data.textures.new(f"r2{i}", "VORONOI"); t2.noise_scale = 0.45; t2.distance_metric = "DISTANCE"
    d2 = o.modifiers.new("d2", "DISPLACE"); d2.texture = t2; d2.strength = -0.35; d2.texture_coords = "OBJECT"
    dec = o.modifiers.new("dec", "DECIMATE"); dec.ratio = 0.06
    finish(o, f"Rock{i}", M["rock"], i * 4.0, smooth=25)

# ---- bushes: clusters of noisy leaf blobs around a short trunk
for i in range(4):
    random.seed(500 + i)
    parts = []
    for k in range(7 + i):
        r = 0.45 + random.random() * 0.4
        a = random.random() * 2 * PI; d = random.random() * 0.7
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r,
                                              location=(math.cos(a) * d, math.sin(a) * d, 0.55 + random.random() * 0.6))
        b = bpy.context.active_object
        tx = bpy.data.textures.new(f"b{i}{k}", "CLOUDS"); tx.noise_scale = 0.25
        dm = b.modifiers.new("d", "DISPLACE"); dm.texture = tx; dm.strength = 0.28
        dc = b.modifiers.new("dec", "DECIMATE"); dc.ratio = 0.35
        apply_all(b); parts.append(b)
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    finish(bpy.context.active_object, f"Bush{i}", M["leaf"], 30 + i * 4, smooth=60)

# ---- concrete road barrier (extruded safety-barrier profile, chamfered ends)
bm = bmesh.new()
prof = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.14, 0.3), (0.09, 0.82), (-0.09, 0.82), (-0.14, 0.3), (-0.3, 0.08)]
A = [bm.verts.new((x, -1.5, z)) for x, z in prof]; B = [bm.verts.new((x, 1.5, z)) for x, z in prof]
bm.faces.new(A[::-1]); bm.faces.new(B)
for k in range(len(prof)):
    bm.faces.new((A[k], A[(k + 1) % len(prof)], B[(k + 1) % len(prof)], B[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("Barrier"); bm.to_mesh(me)
o = bpy.data.objects.new("Barrier", me); sc.collection.objects.link(o)
bv = o.modifiers.new("bv", "BEVEL"); bv.width = 0.03; bv.segments = 2; bv.limit_method = "ANGLE"
finish(o, "Barrier", M["concrete"], 50, smooth=30)

# ---- telegraph pole with crossarm and insulators
bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.13, depth=8.0, location=(0, 0, 4.0))
pole = bpy.context.active_object
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 7.4)); arm = bpy.context.active_object; arm.scale = (2.0, 0.12, 0.12)
bpy.ops.object.transform_apply(scale=True)
for x in (-0.85, -0.3, 0.3, 0.85):
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.04, depth=0.18, location=(x, 0, 7.55))
bpy.ops.object.select_all(action="SELECT"); bpy.context.view_layer.objects.active = pole
for ob in bpy.context.selected_objects:
    if ob.name.startswith(("Rock", "Bush", "Barrier")):
        ob.select_set(False)
bpy.ops.object.join()
finish(bpy.context.active_object, "Pole", M["wood"], 60, smooth=40)

# ---- 200 l fuel drum with rolling hoops
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.29, depth=0.88, location=(0, 0, 0.44))
drum = bpy.context.active_object
for z in (0.3, 0.58):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.29, minor_radius=0.015, location=(0, 0, z), major_segments=24, minor_segments=6)
bpy.ops.object.select_all(action="DESELECT")
for ob in sc.objects:
    if ob.name.startswith(("Cylinder", "Torus")):
        ob.select_set(True)
bpy.context.view_layer.objects.active = drum
bpy.ops.object.join()
finish(bpy.context.active_object, "Drum", M["drum"], 70, smooth=40)

bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "props.glb"), export_format="GLB")
print("PROPS OK", [o.name for o in sc.objects])
