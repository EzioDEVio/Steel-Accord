"""Steel Accord - original low-poly boulder set (5 variants) for terrain dressing.
Run: python3 rocks.py <out_dir>   -> rocks.glb (nodes Rock0..Rock4)"""
import bpy, math, sys, os, random
OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
m = bpy.data.materials.new("SA_Rock"); m.use_nodes = True
b = m.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.27, 0.26, 0.24, 1); b.inputs["Roughness"].default_value = 0.85
for i in range(5):
    random.seed(90 + i)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(i * 4, 0, 0))
    o = bpy.context.active_object; o.name = f"Rock{i}"
    tex = bpy.data.textures.new(f"rn{i}", "CLOUDS"); tex.noise_scale = 0.6 + 0.1 * i
    d = o.modifiers.new("d", "DISPLACE"); d.texture = tex; d.strength = 0.55
    o.scale = (1 + random.random() * 0.8, 1 + random.random() * 0.5, 0.55 + random.random() * 0.3)
    dec = o.modifiers.new("dec", "DECIMATE"); dec.ratio = 0.35
    o.data.materials.append(m)
    bpy.context.view_layer.objects.active = o
    for mod in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.transform_apply(scale=True)
    o.location = (i * 4, 0, 0)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "rocks.glb"), export_format="GLB")
print("ROCKS OK")
