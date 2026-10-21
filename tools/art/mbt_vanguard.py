"""Steel Accord - original main battle tank 'Vanguard' (procedurally modelled in Blender).

Run: python3 mbt_vanguard.py <out_dir>
Outputs: <out_dir>/vanguard.glb and <out_dir>/vanguard_<part>_ao.png (baked ambient occlusion).
Forward is Blender +Y (becomes Godot -Z). Units are metres. Original design; no reference meshes used.
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector

OUT = sys.argv[-1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, rough, metal=0.0, emit=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 3.0
    return m


PAINT = mat("SA_Paint", (0.20, 0.22, 0.15), 0.62)
TEAM = mat("SA_Team", (0.75, 0.75, 0.75), 0.5)
METAL = mat("SA_Metal", (0.06, 0.06, 0.06), 0.45, 0.7)
RUBBER = mat("SA_Rubber", (0.025, 0.025, 0.025), 0.9)
GLASS = mat("SA_Glass", (0.02, 0.05, 0.06), 0.05, 0.0, emit=(0.2, 0.75, 0.9))


def obj_from_bm(bm, name, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    me.materials.append(material)
    return o


def side_profile(pts_yz, width, name, material, x0=0.0):
    """Extrude a side-view polygon (y forward, z up) across X."""
    bm = bmesh.new()
    a = [bm.verts.new((x0 - width / 2, y, z)) for y, z in pts_yz]
    f = bm.faces.new(a)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(width, 0, 0), verts=[v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, material)


def plan_prism(pts_xy, z0, z1, name, material, top_scale=1.0, top_shift=(0, 0)):
    """Extrude a top-view polygon upward, optionally tapering the roof (chamfered armour)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in pts_xy]
    f = bm.faces.new(a)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    vs = [v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)]
    cx = sum(v.co.x for v in vs) / len(vs); cy = sum(v.co.y for v in vs) / len(vs)
    for v in vs:
        v.co.x = cx + (v.co.x - cx) * top_scale + top_shift[0]
        v.co.y = cy + (v.co.y - cy) * top_scale + top_shift[1]
        v.co.z = z1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, material)


def box(name, size, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    return o


def cyl(name, r, depth, loc, material, rot=(0, math.pi / 2, 0), verts=24, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(material)
    return o


def bevel(o, w=0.03, seg=2, angle=35):
    m = o.modifiers.new("bevel", "BEVEL")
    m.width = w; m.segments = seg; m.limit_method = "ANGLE"; m.angle_limit = math.radians(angle)
    m.harden_normals = True


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    for o in objs:
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    j = bpy.context.active_object; j.name = name
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(32))
    return j


# ------------------------------------------------------------------ hull
L, W = 7.2, 3.5           # hull length / width
hull_parts = []
upper = side_profile([(-3.5, 0.75), (3.1, 0.75), (3.7, 1.05), (3.55, 1.25), (2.2, 1.78), (-3.3, 1.82), (-3.6, 1.55)],
                     3.1, "hull_upper", PAINT)
bevel(upper, 0.05, 3); hull_parts.append(upper)
lower = side_profile([(-3.3, 0.55), (3.0, 0.55), (3.45, 0.85), (-3.5, 0.85)], 2.3, "hull_lower", PAINT)
bevel(lower, 0.04); hull_parts.append(lower)
# side skirts: segmented armour panels over the tracks
for s in (-1, 1):
    for i in range(6):
        y0 = -3.3 + i * 1.12
        p = box(f"skirt{s}{i}", (0.08, 1.08, 0.62), (s * 1.72, y0 + 0.54, 1.2), PAINT)
        bevel(p, 0.02); hull_parts.append(p)
    # stowage bins on the fenders
    for y in (-2.4, -1.4):
        b = box(f"bin{s}{y}", (0.42, 0.85, 0.32), (s * 1.42, y, 1.98), PAINT); bevel(b, 0.03); hull_parts.append(b)
# engine deck grilles (dark recessed slats)
for i in range(7):
    g = box(f"grille{i}", (1.9, 0.08, 0.04), (0, -2.9 + i * 0.22, 1.84), METAL); hull_parts.append(g)
# driver's periscopes + headlight clusters + tow hooks
for x in (-0.25, 0, 0.25):
    hull_parts.append(box(f"peri{x}", (0.16, 0.08, 0.07), (x, 2.05, 1.76), GLASS, rot=(math.radians(-25), 0, 0)))
for s in (-1, 1):
    hull_parts.append(box(f"lightbox{s}", (0.3, 0.12, 0.18), (s * 1.25, 3.5, 1.12), METAL))
    hull_parts.append(box(f"lens{s}", (0.2, 0.03, 0.1), (s * 1.25, 3.57, 1.12), GLASS))
    t = cyl(f"tow{s}", 0.07, 0.25, (s * 0.9, 3.65, 0.78), METAL, rot=(math.pi / 2, 0, 0), verts=10); hull_parts.append(t)
# team-colour ID panel on the rear
hull_parts.append(box("team_rear", (2.2, 0.03, 0.22), (0, -3.62, 1.45), TEAM))
for s in (-1, 1):
    hull_parts.append(box(f"team_skirt{s}", (0.02, 2.2, 0.12), (s * 1.77, 0.6, 1.38), TEAM))
hull = join(hull_parts, "Hull")

# ------------------------------------------------------------------ running gear (tracks + wheels)
gear = []
for s in (-1, 1):
    x = s * 1.42
    for i in range(7):
        y = -2.75 + i * 0.9
        gear.append(cyl(f"rw{s}{i}", 0.36, 0.55, (x, y, 0.42), RUBBER, verts=28))
        gear.append(cyl(f"hub{s}{i}", 0.2, 0.6, (x, y, 0.42), METAL, verts=16))
    gear.append(cyl(f"spr{s}", 0.42, 0.5, (x, -3.2, 0.62), METAL, verts=12))     # drive sprocket (rear)
    gear.append(cyl(f"idl{s}", 0.38, 0.5, (x, 3.25, 0.62), METAL, verts=24))     # idler (front)
    # continuous track as a stadium-shaped band, with grousers
    bm = bmesh.new()
    path = []
    for k in range(13):                     # front arc
        a = math.pi / 2 - k * math.pi / 12
        path.append((3.25 + 0.46 * math.cos(a), 0.62 + 0.46 * math.sin(a)))
    path += [(2.7, 0.06), (-2.7, 0.06)]
    for k in range(13):                     # rear arc
        a = -math.pi / 2 - k * math.pi / 12
        path.append((-3.2 + 0.5 * math.cos(a), 0.62 + 0.5 * math.sin(a)))
    outer = [bm.verts.new((x - 0.33, y, z)) for y, z in path]
    outer2 = [bm.verts.new((x + 0.33, y, z)) for y, z in path]
    n = len(path)
    for k in range(n):
        bm.faces.new((outer[k], outer[(k + 1) % n], outer2[(k + 1) % n], outer2[k]))
    r = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.09)
    o = obj_from_bm(bm, f"track{s}", RUBBER); gear.append(o)
    for k in range(40):                      # grouser cleats along the ground run and the top return
        y = -2.9 + k * 0.149
        gear.append(box(f"gr{s}{k}", (0.68, 0.06, 0.05), (x, y, 0.02), METAL))
running = join(gear, "Tracks")

# ------------------------------------------------------------------ turret (angular wedge armour)
tparts = []
plan = [(-1.25, -2.0), (1.25, -2.0), (1.45, -0.3), (1.3, 1.1), (0.55, 2.0), (-0.55, 2.0), (-1.3, 1.1), (-1.45, -0.3)]
t = plan_prism(plan, 1.82, 2.55, "turret_body", PAINT, top_scale=0.9, top_shift=(0, -0.08))
bevel(t, 0.045, 3); tparts.append(t)
b = plan_prism([(-1.1, -2.9), (1.1, -2.9), (1.2, -2.0), (-1.2, -2.0)], 1.95, 2.45, "bustle", PAINT, top_scale=0.95)
bevel(b, 0.03); tparts.append(b)
for i in range(5):                                   # bustle stowage rack bars
    tparts.append(box(f"rack{i}", (2.5, 0.04, 0.04), (0, -2.95 - 0 * i, 1.98 + i * 0.12), METAL))
tparts.append(box("rack_l", (0.04, 0.95, 0.5), (-1.25, -2.5, 2.22), METAL))
tparts.append(box("rack_r", (0.04, 0.95, 0.5), (1.25, -2.5, 2.22), METAL))
# mantlet
m = box("mantlet", (0.95, 0.5, 0.62), (0, 2.1, 2.18), PAINT); bevel(m, 0.04); tparts.append(m)
# gunner's primary sight (left) + commander's independent sight (right, raised)
gs = box("gsight", (0.42, 0.55, 0.36), (-0.75, 1.55, 2.73), PAINT); bevel(gs, 0.03); tparts.append(gs)
tparts.append(box("gsight_glass", (0.32, 0.02, 0.22), (-0.75, 1.83, 2.75), GLASS))
tparts.append(cyl("csight_post", 0.12, 0.35, (0.65, -0.2, 2.72), METAL, rot=(0, 0, 0), verts=12))
cs = box("csight_head", (0.5, 0.42, 0.34), (0.65, -0.2, 3.05), PAINT); bevel(cs, 0.03); tparts.append(cs)
tparts.append(box("csight_glass", (0.36, 0.02, 0.22), (0.65, 0.02, 3.06), GLASS))
# remote weapon station (small turret on the roof)
rws = box("rws_base", (0.45, 0.6, 0.25), (-0.15, -0.9, 2.68), METAL); bevel(rws, 0.02); tparts.append(rws)
tparts.append(cyl("rws_gun", 0.035, 1.1, (-0.15, -0.2, 2.75), METAL, rot=(math.pi / 2, 0, 0), verts=10))
# hatches
for xh, yh in ((0.65, -1.1), (-0.65, -0.6)):
    h = cyl(f"hatch{xh}", 0.33, 0.07, (xh, yh, 2.58), PAINT, rot=(0, 0, 0), verts=24); bevel(h, 0.015); tparts.append(h)
# smoke grenade launchers: angled 4-tube banks on both front cheeks
for s in (-1, 1):
    for k in range(4):
        tparts.append(cyl(f"smk{s}{k}", 0.055, 0.32, (s * (1.2 + 0.0 * k), 0.75 - k * 0.15, 2.4 + 0.02 * k), METAL,
                          rot=(math.radians(-60), 0, s * math.radians(35)), verts=10))
# antenna mounts + whips
for s in (-1, 1):
    tparts.append(cyl(f"ant{s}", 0.012, 2.2, (s * 0.95, -1.8, 3.6), METAL, rot=(0, 0, 0), verts=6))
    tparts.append(cyl(f"antb{s}", 0.06, 0.12, (s * 0.95, -1.8, 2.52), METAL, rot=(0, 0, 0), verts=10))
# team-colour stripe around the turret sides
for s in (-1, 1):
    tparts.append(box(f"team_t{s}", (0.02, 1.6, 0.14), (s * 1.42, -0.5, 2.15), TEAM))
turret = join(tparts, "Turret")

# ------------------------------------------------------------------ gun (tapered barrel, thermal sleeve, muzzle ref)
gparts = [cyl("barrel", 0.13, 5.2, (0, 4.6, 2.18), METAL, rot=(math.pi / 2, 0, 0), verts=24, r2=0.105)]
for i in range(3):
    s = cyl(f"sleeve{i}", 0.155, 1.15, (0, 2.9 + i * 1.3, 2.18), PAINT, rot=(math.pi / 2, 0, 0), verts=24)
    bevel(s, 0.02); gparts.append(s)
gparts.append(cyl("evac", 0.19, 0.6, (0, 4.95, 2.18), PAINT, rot=(math.pi / 2, 0, 0), verts=24))  # bore evacuator
gparts.append(cyl("muzzle", 0.14, 0.25, (0, 7.15, 2.18), METAL, rot=(math.pi / 2, 0, 0), verts=24))
gun = join(gparts, "Gun")

# muzzle point for the engine (empty exported as a node)
mz = bpy.data.objects.new("Muzzle", None); mz.location = (0, 7.3, 2.18); scene.collection.objects.link(mz)

# ------------------------------------------------------------------ UVs + baked ambient occlusion
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.device = "CPU"
for o in (hull, running, turret, gun):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")
for o in (hull, running, turret, gun):
    img = bpy.data.images.new(f"{o.name}_ao", 1024, 1024)
    for m in o.data.materials:
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img
        m.node_tree.nodes.active = n
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type="AO", margin=6)
    img.filepath_raw = os.path.join(OUT, f"vanguard_{o.name.lower()}_ao.png"); img.file_format = "PNG"; img.save()
    for m in o.data.materials:                       # remove bake node so it isn't exported as base colour
        for n in [n for n in m.node_tree.nodes if n.type == "TEX_IMAGE"]:
            m.node_tree.nodes.remove(n)

# turret hierarchy: Turret -> Gun -> Muzzle (turret rotates about its own origin at hull centre)
gun.parent = turret; mz.parent = gun
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "vanguard.glb"), export_format="GLB", export_apply=True)
tris = sum(len(o.data.polygons) for o in (hull, running, turret, gun))
print("VANGUARD OK polys", tris)
