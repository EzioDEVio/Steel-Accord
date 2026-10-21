"""Structured decode/encode of the Zero Hour .map chunks used by B1 test maps.

Mirrors (pinned fork):
  HeightMapData v4   - Tools/WorldBuilder/src/WHeightMapEdit.cpp saveToFile
  BlendTileData v8   - same + Core/.../W3DDevice/GameClient/WorldHeightMap.cpp
  WorldInfo v1       - dict
  SidesList v3       - Core/GameEngine/Source/GameLogic/Map/SidesList.cpp
  ObjectsList v3     - WHeightMapEdit.cpp
  PolygonTriggers v4 - PolygonTrigger.cpp
  GlobalLighting v3  - WHeightMapEdit.cpp (MAX_GLOBAL_LIGHTS = 3)
  WaypointsList v1   - WorldBuilderDoc.cpp (link list)

Original Steel Accord tooling.
"""
import struct
from .datachunk import Reader, Writer, split_chunks, parse_file

MAX_GLOBAL_LIGHTS = 3


def decode(data):
    names, chunks = parse_file(data)
    m = {"_names": names, "order": []}
    for name, ver, payload in chunks:
        r = Reader(payload, names)
        m["order"].append((name, ver))
        if name == "HeightMapData":
            w, h, border = r.i32(), r.i32(), r.i32()
            nb = r.i32()
            bounds = [(r.i32(), r.i32()) for _ in range(nb)]
            size = r.i32()
            m["height"] = dict(width=w, height=h, border=border, boundaries=bounds,
                               data=r.raw(size))
        elif name == "BlendTileData":
            hd = m["height"]; n = r.i32(); assert n == hd["width"] * hd["height"]
            b = {}
            for k in ("tiles", "blend", "extra", "cliff"):
                b[k] = list(struct.unpack_from(f"<{n}h", r.raw(2 * n)))
            fw = (hd["width"] + 7) // 8
            b["cliffState"] = r.raw(fw * hd["height"])
            b["numBitmapTiles"], b["numBlendedTiles"], b["numCliffInfo"] = r.i32(), r.i32(), r.i32()
            b["classes"] = []
            for _ in range(r.i32()):
                first, num, width, legacy = r.i32(), r.i32(), r.i32(), r.i32()
                b["classes"].append(dict(first=first, num=num, width=width, legacy=legacy, name=r.ascii()))
            b["numEdgeTiles"] = r.i32()
            b["edgeClasses"] = []
            for _ in range(r.i32()):
                first, num, width = r.i32(), r.i32(), r.i32()
                b["edgeClasses"].append(dict(first=first, num=num, width=width, name=r.ascii()))
            b["blendedTiles"] = [r.raw(4 + 6 + 4 + 4) for _ in range(1, b["numBlendedTiles"])]
            b["cliffInfo"] = [r.raw(4 + 32 + 2) for _ in range(1, b["numCliffInfo"])]
            assert r.eof(), "BlendTileData trailing bytes"
            m["blend"] = b
        elif name == "WorldInfo":
            m["world"] = r.dict()
        elif name == "SidesList":
            sides = []
            for _ in range(r.i32()):
                d = r.dict(); bl = []
                for _ in range(r.i32()):
                    bl.append(dict(name=r.ascii(), tmpl=r.ascii(), x=r.f32(), y=r.f32(), z=r.f32(),
                                   angle=r.f32(), built=r.u8(), rebuilds=r.i32(), script=r.ascii(),
                                   health=r.i32(), whiner=r.u8(), unsellable=r.u8(), repairable=r.u8()))
                sides.append(dict(dict=d, build=bl))
            teams = [r.dict() for _ in range(r.i32())]
            m["sides"] = sides; m["teams"] = teams
            m["sidesTail"] = split_chunks(payload[r.p:], names)
        elif name == "ObjectsList":
            objs = []
            for oname, over, op in split_chunks(payload, names):
                o = Reader(op, names)
                objs.append(dict(x=o.f32(), y=o.f32(), z=o.f32(), angle=o.f32(), flags=o.i32(),
                                 tmpl=o.ascii(), props=o.dict()))
                assert o.eof()
            m["objects"] = objs
        elif name == "PolygonTriggers":
            trig = []
            for _ in range(r.i32()):
                t = dict(name=r.ascii())
                if ver >= 4: t["layer"] = r.ascii()
                t.update(id=r.i32(), water=r.u8(), river=r.u8(), riverStart=r.i32())
                t["pts"] = [(r.i32(), r.i32(), r.i32()) for _ in range(r.i32())]
                trig.append(t)
            m["triggers"] = trig
        elif name == "GlobalLighting":
            m["lighting"] = payload
        elif name == "WaypointsList":
            m["waypointLinks"] = [(r.i32(), r.i32()) for _ in range(r.i32())]
        else:
            m.setdefault("unknown", []).append((name, ver, payload))
    return m


def encode(m):
    w = Writer()
    hd = m["height"]
    w.open("HeightMapData", 4)
    w.i32(hd["width"]); w.i32(hd["height"]); w.i32(hd["border"])
    w.i32(len(hd["boundaries"]))
    for x, y in hd["boundaries"]: w.i32(x); w.i32(y)
    w.i32(len(hd["data"])); w.raw(hd["data"])
    w.close()

    b = m["blend"]; n = hd["width"] * hd["height"]
    w.open("BlendTileData", 8)
    w.i32(n)
    for k in ("tiles", "blend", "extra", "cliff"):
        w.raw(struct.pack(f"<{n}h", *b[k]))
    w.raw(b["cliffState"])
    w.i32(b["numBitmapTiles"]); w.i32(b["numBlendedTiles"]); w.i32(b["numCliffInfo"])
    w.i32(len(b["classes"]))
    for c in b["classes"]:
        w.i32(c["first"]); w.i32(c["num"]); w.i32(c["width"]); w.i32(c.get("legacy", 0)); w.ascii(c["name"])
    w.i32(b["numEdgeTiles"]); w.i32(len(b["edgeClasses"]))
    for c in b["edgeClasses"]:
        w.i32(c["first"]); w.i32(c["num"]); w.i32(c["width"]); w.ascii(c["name"])
    for t in b["blendedTiles"]: w.raw(t)
    for c in b["cliffInfo"]: w.raw(c)
    w.close()

    w.open("WorldInfo", 1); w.dict(m["world"]); w.close()

    w.open("SidesList", 3)
    w.i32(len(m["sides"]))
    for s in m["sides"]:
        w.dict(s["dict"]); w.i32(len(s["build"]))
        for e in s["build"]:
            w.ascii(e["name"]); w.ascii(e["tmpl"]); w.f32(e["x"]); w.f32(e["y"]); w.f32(e["z"])
            w.f32(e["angle"]); w.u8(e["built"]); w.i32(e["rebuilds"]); w.ascii(e["script"])
            w.i32(e["health"]); w.u8(e["whiner"]); w.u8(e["unsellable"]); w.u8(e["repairable"])
    w.i32(len(m["teams"]))
    for t in m["teams"]: w.dict(t)
    # Script lists: B1 maps carry empty per-side lists (no scripts).
    tail = m.get("sidesTail")
    if tail is None:
        w.open("PlayerScriptsList", 1)
        for _ in m["sides"]:
            w.open("ScriptList", 1); w.close()
        w.close()
    else:
        for name, ver, payload in tail:
            w.open(name, ver); w.raw(payload); w.close()
    w.close()

    w.open("ObjectsList", 3)
    for o in m["objects"]:
        w.open("Object", 3)
        w.f32(o["x"]); w.f32(o["y"]); w.f32(o["z"]); w.f32(o["angle"]); w.i32(o["flags"])
        w.ascii(o["tmpl"]); w.dict(o["props"])
        w.close()
    w.close()

    w.open("PolygonTriggers", 4)
    w.i32(len(m.get("triggers", [])))
    for t in m.get("triggers", []):
        w.ascii(t["name"]); w.ascii(t.get("layer", "")); w.i32(t["id"]); w.u8(t["water"]); w.u8(t["river"])
        w.i32(t["riverStart"]); w.i32(len(t["pts"]))
        for p in t["pts"]:
            for v in p: w.i32(v)
    w.close()

    w.open("GlobalLighting", 3); w.raw(m["lighting"]); w.close()

    w.open("WaypointsList", 1)
    links = m.get("waypointLinks", [])
    w.i32(len(links))
    for a, c in links: w.i32(a); w.i32(c)
    w.close()
    return w.finish()


def lighting_blob(time_of_day, slots, shadow_color):
    """Build a GlobalLighting v3 payload.

    slots: 4 entries (morning, afternoon, evening, night); each a dict with
    'terrain' and 'objects', each a list of MAX_GLOBAL_LIGHTS (ambient rgb, diffuse rgb, pos xyz).
    Write order follows WHeightMapEdit.cpp exactly.
    """
    out = bytearray(struct.pack("<i", time_of_day))
    f = lambda L: struct.pack("<9f", *L)
    for s in slots:
        out += f(s["terrain"][0]) + f(s["objects"][0])
        for j in range(1, MAX_GLOBAL_LIGHTS): out += f(s["objects"][j])
        for j in range(1, MAX_GLOBAL_LIGHTS): out += f(s["terrain"][j])
    out += struct.pack("<I", shadow_color)
    return bytes(out)
