"""Minimal W3D writer/reader for Steel Accord original assets.

Chunk layout and struct sizes follow Generals/Code/Libraries/Source/WWVegas/WW3D2/w3d_file.h
in the pinned TheSuperHackers fork:
  chunk header := u32 type, u32 size (bit31 set => payload is sub-chunks)
  W3dMeshHeader3Struct  = 116 bytes   W3dTriangleStruct   = 32 bytes
  W3dVertexMaterialStruct = 32 bytes  W3dShaderStruct     = 16 bytes
  W3dMaterialInfoStruct = 16 bytes    W3dHierarchyStruct  = 36 bytes
  W3dPivotStruct        = 60 bytes    W3dHLodHeaderStruct = 40 bytes
  W3dHLodArrayHeaderStruct = 8 bytes  W3dHLodSubObjectStruct = 36 bytes

Exports a static, single-pass, single-texture mesh bound to bone 0 of a
one-pivot hierarchy, wrapped in an HLOD named after the model — the same
container structure the engine's W3DModelDraw resolves via
WW3DAssetManager::Create_Render_Obj(<model name>).

Original Steel Accord tooling.
"""
import struct

CH = dict(
    MESH=0x000, VERTICES=0x002, VERTEX_NORMALS=0x003, MESH_HEADER3=0x01F, TRIANGLES=0x020,
    VERTEX_SHADE_INDICES=0x022, MATERIAL_INFO=0x028, SHADERS=0x029, VERTEX_MATERIALS=0x02A,
    VERTEX_MATERIAL=0x02B, VERTEX_MATERIAL_NAME=0x02C, VERTEX_MATERIAL_INFO=0x02D,
    TEXTURES=0x030, TEXTURE=0x031, TEXTURE_NAME=0x032, MATERIAL_PASS=0x038,
    VERTEX_MATERIAL_IDS=0x039, SHADER_IDS=0x03A, TEXTURE_STAGE=0x048, TEXTURE_IDS=0x049,
    STAGE_TEXCOORDS=0x04A, VERTEX_INFLUENCES=0x00E, AABTREE=0x090,
    HIERARCHY=0x100, HIERARCHY_HEADER=0x101, PIVOTS=0x102, PIVOT_FIXUPS=0x103,
    HLOD=0x700, HLOD_HEADER=0x701, HLOD_LOD_ARRAY=0x702, HLOD_SUB_OBJECT_ARRAY_HEADER=0x703,
    HLOD_SUB_OBJECT=0x704, HLOD_AGGREGATE_ARRAY=0x705, HLOD_PROXY_ARRAY=0x706,
)
NAMES = {v: k for k, v in CH.items()}
W3D_NAME_LEN = 16
W3D_CURRENT_MESH_VERSION = (4 << 16) | 2
W3D_CURRENT_HTREE_VERSION = (4 << 16) | 1
W3D_CURRENT_HLOD_VERSION = (1 << 16) | 0
W3D_MESH_FLAG_GEOMETRY_TYPE_NORMAL = 0x00000000
W3D_MESH_FLAG_CAST_SHADOW = 0x00001000
W3D_VERTEX_CHANNEL_LOCATION, W3D_VERTEX_CHANNEL_NORMAL, W3D_VERTEX_CHANNEL_TEXCOORD = 1, 2, 4
W3D_FACE_CHANNEL_FACE = 1


def name16(s):
    b = s.encode("ascii")
    assert len(b) < W3D_NAME_LEN, f"W3D name too long: {s}"
    return b + b"\0" * (W3D_NAME_LEN - len(b))


def chunk(ctype, payload, sub=False):
    size = len(payload) | (0x80000000 if sub else 0)
    return struct.pack("<II", ctype, size) + payload


def cstr(s):
    return s.encode("ascii") + b"\0"


def shader_opaque():
    # W3dShaderStruct (16 bytes): DepthCompare, DepthMask, ColorMask, DestBlend, FogFunc,
    # PriGradient, SecGradient, SrcBlend, Texturing, DetailColorFunc, DetailAlphaFunc,
    # ShaderPreset, AlphaTest, PostDetailColorFunc, PostDetailAlphaFunc, pad
    # Values = the W3D "Opaque" preset: LEQUAL(3), write depth, dest ZERO, src ONE,
    # primary gradient MODULATE(1), texturing ENABLE(1).
    return struct.pack("<16B", 3, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0)


def vertex_material(name="PZMat"):
    # W3dVertexMaterialStruct: Attributes u32, Ambient/Diffuse/Specular/Emissive RGBA(4B each),
    # Shininess f32, Opacity f32, Translucency f32  -> 32 bytes
    info = struct.pack("<I4B4B4B4Bfff", 0, 255, 255, 255, 0, 255, 255, 255, 0,
                       0, 0, 0, 0, 0, 0, 0, 0, 1.0, 1.0, 0.0)
    assert len(info) == 32
    return chunk(CH["VERTEX_MATERIAL"],
                 chunk(CH["VERTEX_MATERIAL_NAME"], cstr(name)) +
                 chunk(CH["VERTEX_MATERIAL_INFO"], info), sub=True)


def mesh(mesh_name, container, verts, normals, uvs, tris, texture, cast_shadow=False):
    """verts/normals: [(x,y,z)], uvs: [(u,v)], tris: [(a,b,c)] CCW, Z-up, units = game feet."""
    nv, nt = len(verts), len(tris)
    xs, ys, zs = zip(*verts)
    mn, mx = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
    ctr = tuple((a + b) / 2 for a, b in zip(mn, mx))
    rad = max(((x - ctr[0]) ** 2 + (y - ctr[1]) ** 2 + (z - ctr[2]) ** 2) ** 0.5 for x, y, z in verts)
    flags = W3D_MESH_FLAG_GEOMETRY_TYPE_NORMAL | (W3D_MESH_FLAG_CAST_SHADOW if cast_shadow else 0)
    # Layout check against W3dMeshHeader3Struct (116 bytes):
    # Version, Attributes, MeshName[16], ContainerName[16], NumTris, NumVertices, NumMaterials,
    # NumDamageStages, SortLevel(int32), PrelitVersion, FutureCounts[1], VertexChannels,
    # FaceChannels, Min(3f), Max(3f), SphCenter(3f), SphRadius(f)
    hdr = struct.pack("<II16s16sIIIIiIIII3f3f3ff",
                      W3D_CURRENT_MESH_VERSION, flags, name16(mesh_name), name16(container),
                      nt, nv, 1, 0, 0, 0, 0,
                      W3D_VERTEX_CHANNEL_LOCATION | W3D_VERTEX_CHANNEL_NORMAL | W3D_VERTEX_CHANNEL_TEXCOORD,
                      W3D_FACE_CHANNEL_FACE, *mn, *mx, *ctr, rad)
    assert len(hdr) == 116, len(hdr)

    vbuf = b"".join(struct.pack("<3f", *v) for v in verts)
    nbuf = b"".join(struct.pack("<3f", *n) for n in normals)
    tbuf = bytearray()
    for a, b, c in tris:
        p0, p1, p2 = verts[a], verts[b], verts[c]
        u = [p1[i] - p0[i] for i in range(3)]; w = [p2[i] - p0[i] for i in range(3)]
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        L = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
        n = tuple(x / L for x in n)
        dist = n[0] * p0[0] + n[1] * p0[1] + n[2] * p0[2]
        # W3dTriangleStruct: Vindex[3] u32, Attributes u32 (surface type), Normal(3f), Dist f
        tbuf += struct.pack("<IIII3ff", a, b, c, 0, *n, dist)
    assert len(tbuf) == 32 * nt
    shade = b"".join(struct.pack("<I", i) for i in range(nv))
    matinfo = struct.pack("<IIII", 1, 1, 1, 1)  # PassCount, VertexMaterialCount, ShaderCount, TextureCount
    uvbuf = b"".join(struct.pack("<2f", u, v) for u, v in uvs)

    body = (chunk(CH["MESH_HEADER3"], hdr) +
            chunk(CH["VERTICES"], vbuf) +
            chunk(CH["VERTEX_NORMALS"], nbuf) +
            chunk(CH["TRIANGLES"], bytes(tbuf)) +
            chunk(CH["VERTEX_SHADE_INDICES"], shade) +
            chunk(CH["MATERIAL_INFO"], matinfo) +
            chunk(CH["VERTEX_MATERIALS"], vertex_material(), sub=True) +
            chunk(CH["SHADERS"], shader_opaque()) +
            chunk(CH["TEXTURES"], chunk(CH["TEXTURE"], chunk(CH["TEXTURE_NAME"], cstr(texture)), sub=True), sub=True) +
            chunk(CH["MATERIAL_PASS"],
                  chunk(CH["VERTEX_MATERIAL_IDS"], struct.pack("<I", 0)) +
                  chunk(CH["SHADER_IDS"], struct.pack("<I", 0)) +
                  chunk(CH["TEXTURE_STAGE"],
                        chunk(CH["TEXTURE_IDS"], struct.pack("<I", 0)) +
                        chunk(CH["STAGE_TEXCOORDS"], uvbuf), sub=True), sub=True))
    return chunk(CH["MESH"], body, sub=True)


def hierarchy(name, pivots):
    """pivots: [(name, parent_index, (tx,ty,tz))]; pivot 0 must be ROOTTRANSFORM, parent -1."""
    # W3dHierarchyStruct: Version u32, Name[16], NumPivots u32, Center(3f) -> 36 bytes
    hdr = struct.pack("<I16sI3f", W3D_CURRENT_HTREE_VERSION, name16(name), len(pivots), 0, 0, 0)
    assert len(hdr) == 36
    pv = bytearray()
    for pname, parent, t in pivots:
        # W3dPivotStruct: Name[16], ParentIdx u32, Translation(3f), EulerAngles(3f), Rotation quat(4f) -> 60
        pv += struct.pack("<16si3f3f4f", name16(pname), parent, *t, 0, 0, 0, 0, 0, 0, 1)
    assert len(pv) == 60 * len(pivots)
    return chunk(CH["HIERARCHY"], chunk(CH["HIERARCHY_HEADER"], hdr) + chunk(CH["PIVOTS"], bytes(pv)), sub=True)


def hlod(name, htree, subobjects, max_screen_size=0.0):
    """subobjects: [(bone_index, 'CONTAINER.MESH')]"""
    # W3dHLodHeaderStruct: Version u32, LodCount u32, Name[16], HierarchyName[16] -> 40 bytes
    hdr = struct.pack("<II16s16s", W3D_CURRENT_HLOD_VERSION, 1, name16(name), name16(htree))
    # W3dHLodArrayHeaderStruct: ModelCount u32, MaxScreenSize f32 -> 8
    arr = chunk(CH["HLOD_SUB_OBJECT_ARRAY_HEADER"], struct.pack("<If", len(subobjects), max_screen_size))
    for bone, full in subobjects:
        b = full.encode("ascii"); assert len(b) < 32
        # W3dHLodSubObjectStruct: BoneIndex u32, Name[32] -> 36
        arr += chunk(CH["HLOD_SUB_OBJECT"], struct.pack("<I32s", bone, b + b"\0" * (32 - len(b))))
    return chunk(CH["HLOD"], chunk(CH["HLOD_HEADER"], hdr) + chunk(CH["HLOD_LOD_ARRAY"], arr, sub=True), sub=True)


def walk(buf, depth=0, out=None, p=0, end=None):
    """Recursively list chunks: [(depth, type, size, has_sub, payload)]. Raises on overrun."""
    out = [] if out is None else out
    end = len(buf) if end is None else end
    while p < end:
        if p + 8 > end:
            raise ValueError(f"truncated chunk header at {p}")
        t, s = struct.unpack_from("<II", buf, p)
        sub, size = bool(s & 0x80000000), s & 0x7FFFFFFF
        q = p + 8
        if q + size > end:
            raise ValueError(f"chunk 0x{t:x} overruns parent ({q + size} > {end})")
        out.append((depth, t, size, sub, buf[q:q + size]))
        if sub:
            walk(buf, depth + 1, out, q, q + size)
        p = q + size
    return out
