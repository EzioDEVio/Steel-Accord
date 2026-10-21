"""BIG archive packer/reader matching Core/GameEngine/Source/Common/System/BIGFileSystem.cpp.

Layout: "BIGF" | u32le archiveSize | u32be fileCount | u32be headerEnd |
        { u32be offset, u32be size, path\\0 }* | file data
Paths use backslashes (e.g. Art\\W3D\\PZKESTREL.W3D). The engine lowercases names on load.
Original Project Zero Hour tooling.
"""
import os, struct


def pack(src_root, out_path, include=lambda rel: True):
    entries = []
    for dp, dn, fn in os.walk(src_root):
        dn.sort()
        for f in sorted(fn):
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, src_root).replace("/", "\\")
            if include(rel):
                entries.append((rel, open(full, "rb").read()))
    header = 16 + sum(8 + len(r.encode("ascii")) + 1 for r, _ in entries)
    off = header
    table = bytearray()
    for rel, data in entries:
        table += struct.pack(">II", off, len(data)) + rel.encode("ascii") + b"\0"
        off += len(data)
    blob = b"BIGF" + struct.pack("<I", off) + struct.pack(">II", len(entries), header) + bytes(table)
    blob += b"".join(d for _, d in entries)
    assert len(blob) == off
    open(out_path, "wb").write(blob)
    return [(r, len(d)) for r, d in entries]


def read(path):
    d = open(path, "rb").read()
    assert d[:4] == b"BIGF", "bad BIG id"
    size = struct.unpack_from("<I", d, 4)[0]
    n, hdr = struct.unpack_from(">II", d, 8)
    assert size == len(d), f"archive size field {size} != file length {len(d)}"
    p, out = 16, {}
    for _ in range(n):
        off, sz = struct.unpack_from(">II", d, p); p += 8
        e = d.index(b"\0", p); name = d[p:e].decode("ascii"); p = e + 1
        assert off + sz <= len(d)
        out[name] = d[off:off + sz]
    assert p == hdr, f"directory end {p} != header field {hdr}"
    return out
