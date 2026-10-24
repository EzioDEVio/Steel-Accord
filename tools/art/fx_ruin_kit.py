#!/usr/bin/env python3
"""Steel Accord - procedural ruin kit for destroyed structures (original, project-owned).

Builds broken-building pieces from code with the Blender Python module (bpy + bmesh) and exports one GLB.
Every piece has up to two materials: "RuinConcrete" (neutral light grey; the game tints it per building with
colours sampled from that building's own textures) and "RuinRebar" (rusty steel, never tinted).
No textures are embedded: the game applies concrete_detail.png tri-planar.

  python3 -I tools/art/fx_ruin_kit.py godot/assets/fx/ruin_kit.glb

Pieces (1 unit = 1 m, Blender Z up, exported Y up; origin at the base centre):
  wall_a, wall_b, wall_c   4 m wide, 0.35 m thick wall stubs with jagged broken tops and rebar sticking out
  corner_a                 L-shaped corner stub (3 m + 3 m) with a jagged top
  slab_a, slab_b           fallen roof slabs (5 x 4 x 0.3 m) with a fractured edge and protruding rebar grid
  beam_a                   bent steel I-beam, 6 m
  column_a                 snapped concrete column with exposed reinforcement
  mound_a, mound_b         rubble heaps (about 6 x 6 x 1.6 m) with blocks bedded in them
  chunk_a .. chunk_d       irregular concrete blocks, about 1 m
"""
import math
import random
import sys

import bpy  # noqa: E402  (bpy must be imported before bmesh / mathutils)
import bmesh
from mathutils import Matrix, Vector, noise

SEED = 20261023


def material(name, rgb, metal, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*rgb, 1.0)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    return m


def new_obj(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for poly in me.polygons:
        poly.use_smooth = False
    return ob


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude a closed CCW outline [(x, y), ...] from z0 to z1. Returns the new faces."""
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    top = [bm.verts.new((x, y, z1)) for x, y in outline]
    faces = [bm.faces.new(list(reversed(bot))), bm.faces.new(top)]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat_index
    return faces


def rod(bm, a, b, r=0.022, mat_index=1, seg=5):
    """Thin cylinder from a to b (rebar)."""
    d = Vector(b) - Vector(a)
    ln = d.length
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=ln)
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    mid = (Vector(a) + Vector(b)) / 2
    bmesh.ops.transform(bm, matrix=Matrix.Translation(mid) @ rot, verts=res["verts"])
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat_index


def bent_rod(bm, base, direction, length, droop, rng):
    """Rebar that leaves the concrete and bends over: two segments."""
    d = Vector(direction).normalized()
    mid = Vector(base) + d * length * 0.5
    tip = mid + (d + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), -droop))).normalized() * length * 0.5
    rod(bm, base, mid)
    rod(bm, mid, tip)


def wall_stub(name, rng, mats, width=4.0, thick=0.35, hmin=0.9, hmax=3.0, corner=False):
    bm = bmesh.new()
    n = 14
    xs = [(-width / 2 + width * i / (n - 1)) for i in range(n)]
    base_amp = rng.uniform(0.0, 1.0)
    hs = []
    for i, x in enumerate(xs):
        t = i / (n - 1)
        h = hmin + (hmax - hmin) * (0.5 + 0.5 * math.sin(t * math.pi * rng.uniform(0.6, 1.6) + base_amp * 6))
        h += rng.uniform(-0.35, 0.35) * (1 if i % 2 else 0.4)
        hs.append(max(hmin * 0.6, min(hmax, h)))
    # wall as a strip of columns with a jagged top (front and back faces share the profile)
    fb = [bm.verts.new((x, -thick / 2, 0)) for x in xs]
    bb = [bm.verts.new((x, thick / 2, 0)) for x in xs]
    ft = [bm.verts.new((x, -thick / 2 + rng.uniform(-0.04, 0.04), h)) for x, h in zip(xs, hs)]
    bt = [bm.verts.new((x, thick / 2 + rng.uniform(-0.04, 0.04), h - rng.uniform(0.0, 0.25))) for x, h in zip(xs, hs)]
    for i in range(n - 1):
        bm.faces.new((fb[i], fb[i + 1], ft[i + 1], ft[i]))
        bm.faces.new((bb[i + 1], bb[i], bt[i], bt[i + 1]))
        bm.faces.new((ft[i], ft[i + 1], bt[i + 1], bt[i]))
        bm.faces.new((bb[i], bb[i + 1], fb[i + 1], fb[i]))
    bm.faces.new((fb[0], ft[0], bt[0], bb[0]))
    bm.faces.new((bb[-1], bt[-1], ft[-1], fb[-1]))
    for f in bm.faces:
        f.material_index = 0
    # exposed reinforcement from the broken top
    for i in range(1, n - 1, 2):
        if rng.random() < 0.65:
            base = Vector((xs[i] + rng.uniform(-0.1, 0.1), rng.uniform(-0.08, 0.08), hs[i] - 0.15))
            bent_rod(bm, base, (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1.0), rng.uniform(0.4, 1.1), rng.uniform(0.2, 1.2), rng)
    if corner:
        # second leg at a right angle along +Y from the -X end
        bm2 = bm
        m = Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Translation((width / 2 - thick / 2, 0, 0))
        geom = bmesh.ops.duplicate(bm2, geom=list(bm2.verts) + list(bm2.edges) + list(bm2.faces))
        dv = [e for e in geom["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.scale(bm2, vec=(0.75, 1, 0.8), verts=dv)
        bmesh.ops.transform(bm2, matrix=m, verts=dv)
        bmesh.ops.translate(bm2, vec=(-width / 2, 0, 0), verts=dv)
    return new_obj(name, bm, mats)


def slab(name, rng, mats, sx=5.0, sy=4.0, th=0.3):
    bm = bmesh.new()
    # outline: three straight sides, the +X side fractured
    out = [(-sx / 2, -sy / 2)]
    k = 9
    for i in range(k + 1):
        y = -sy / 2 + sy * i / k
        out.append((sx / 2 - rng.uniform(0.0, 0.9) * (0.3 if i in (0, k) else 1.0), y))
    out.append((-sx / 2, sy / 2))
    # second fractured side (-Y) on some slabs
    prism(bm, out, 0, th, 0)
    # rebar grid poking out of the fracture
    for i in range(1, k, 1):
        y = -sy / 2 + sy * i / k
        x0 = out[i + 1][0] - 0.05
        bent_rod(bm, (x0, y, th * 0.5), (1, rng.uniform(-0.15, 0.15), 0), rng.uniform(0.4, 1.0), rng.uniform(0.3, 1.0), rng)
    # surface crack relief: lift a few top vertices
    for v in bm.verts:
        if v.co.z > th * 0.9:
            v.co.z += rng.uniform(-0.04, 0.05)
    return new_obj(name, bm, mats)


def ibeam(name, rng, mats, length=6.0):
    bm = bmesh.new()
    w, h, tf, tw = 0.3, 0.4, 0.04, 0.03
    prof = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, -h / 2 + tf), (tw / 2, -h / 2 + tf), (tw / 2, h / 2 - tf), (w / 2, h / 2 - tf),
            (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, h / 2 - tf), (-tw / 2, h / 2 - tf), (-tw / 2, -h / 2 + tf), (-w / 2, -h / 2 + tf)]
    segs = 10
    rings = []
    bend = rng.uniform(0.25, 0.6)
    for s in range(segs + 1):
        t = s / segs
        x = -length / 2 + length * t
        ang = bend * math.sin(t * math.pi) * (1 if t < 0.5 else -1)
        lift = 0.6 * math.sin(t * math.pi) ** 2
        ring = []
        for py, pz in prof:
            ring.append(bm.verts.new((x + pz * math.sin(ang), py, pz * math.cos(ang) + h / 2 + lift)))
        rings.append(ring)
    n = len(prof)
    for s in range(segs):
        a, b = rings[s], rings[s + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    for f in bm.faces:
        f.material_index = 1
    return new_obj(name, bm, mats)


def column(name, rng, mats):
    bm = bmesh.new()
    s = 0.5
    hgt = rng.uniform(2.2, 3.0)
    out = [(-s / 2, -s / 2), (s / 2, -s / 2), (s / 2, s / 2), (-s / 2, s / 2)]
    prism(bm, out, 0, hgt, 0)
    for v in bm.verts:
        if v.co.z > hgt - 0.01:
            v.co.z -= rng.uniform(0.0, 0.6)
    for cx in (-0.15, 0.15):
        for cy in (-0.15, 0.15):
            bent_rod(bm, (cx, cy, hgt - 0.7), (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1), rng.uniform(0.6, 1.3), rng.uniform(0.2, 0.9), rng)
    return new_obj(name, bm, mats)


def chunk_bm(bm, rng, center, size):
    pts = []
    for _ in range(14):
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
        pts.append(bm.verts.new(Vector(center) + Vector((d.x * size[0], d.y * size[1], d.z * size[2])) * rng.uniform(0.7, 1.0)))
    res = bmesh.ops.convex_hull(bm, input=pts)
    for g in res.get("geom_interior", []) + res.get("geom_unused", []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid and not g.link_faces:
            bm.verts.remove(g)


def chunk(name, rng, mats):
    bm = bmesh.new()
    chunk_bm(bm, rng, (0, 0, 0.35), (0.55, 0.45, 0.35))
    for f in bm.faces:
        f.material_index = 0
    return new_obj(name, bm, mats)


def mound(name, rng, mats):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    for v in bm.verts:
        n = noise.noise(v.co * 2.2 + off) * 0.25 + noise.noise(v.co * 5.0 + off) * 0.1
        v.co = v.co * (1.0 + n)
        v.co.x *= 3.0
        v.co.y *= 3.0
        v.co.z = max(v.co.z * 1.5, 0.0)
    for f in bm.faces:
        f.material_index = 0
    # blocks bedded in the heap, and a few rebar ends
    for _ in range(9):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.5, 2.4)
        cz = max(0.2, 1.4 * (1 - (r / 3.0) ** 2))
        chunk_bm(bm, rng, (math.cos(a) * r, math.sin(a) * r, cz), (rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.6), rng.uniform(0.2, 0.4)))
    for f in bm.faces:
        if f.material_index != 1:
            f.material_index = 0
    for _ in range(4):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.3, 1.8)
        base = (math.cos(a) * r, math.sin(a) * r, max(0.2, 1.3 * (1 - (r / 3.0) ** 2)))
        bent_rod(bm, base, (rng.uniform(-1, 1), rng.uniform(-1, 1), 0.8), rng.uniform(0.5, 1.2), rng.uniform(0.2, 1.0), rng)
    return new_obj(name, bm, mats)


def main(dst):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = random.Random(SEED)
    conc = material("RuinConcrete", (0.8, 0.8, 0.8), 0.0, 0.92)
    reb = material("RuinRebar", (0.23, 0.13, 0.08), 0.55, 0.7)
    mats = [conc, reb]
    wall_stub("wall_a", rng, mats, hmin=1.0, hmax=3.2)
    wall_stub("wall_b", rng, mats, hmin=0.6, hmax=2.2)
    wall_stub("wall_c", rng, mats, hmin=1.6, hmax=4.2)
    wall_stub("corner_a", rng, mats, width=3.0, hmin=1.2, hmax=3.4, corner=True)
    slab("slab_a", rng, mats)
    slab("slab_b", rng, mats, sx=4.0, sy=3.4)
    ibeam("beam_a", rng, mats)
    column("column_a", rng, mats)
    mound("mound_a", rng, mats)
    mound("mound_b", rng, mats)
    for k in "abcd":
        chunk("chunk_" + k, rng, mats)
    # empty material slots are dropped by the exporter (beam_a uses only rebar, chunks only concrete)
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_apply=True, export_yup=True)
    for ob in bpy.data.objects:
        print("piece", ob.name, len(ob.data.vertices), "verts", len(ob.data.polygons), "faces")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "godot/assets/fx/ruin_kit.glb")
