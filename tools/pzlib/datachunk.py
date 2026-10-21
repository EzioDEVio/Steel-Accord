"""DataChunk (.map) reader/writer and RefPack decoder.

Format mirrors GeneralsMD/Code/GameEngine/Source/Common/System/DataChunk.cpp
(TheSuperHackers fork, pinned commit in docs/RECON.md):

  file  := ["EAR\\0" u32 rawSize refpack-stream]   (optional compression)
           "CkMp" i32 count { u8 len, name[len], u32 id }*   (symbol table)
           chunk*
  chunk := u32 id, u16 version, i32 size, payload[size]
  dict  := u16 pairs { i32 (nameId<<8 | type), value }*
           type 0 bool(u8) 1 int(i32) 2 real(f32) 3 ascii(u16 len + bytes)
                4 unicode(u16 len + len*2 bytes UTF-16LE)

Original code for Steel Accord tooling. License: see repository LICENSE.
"""
import struct

DICT_BOOL, DICT_INT, DICT_REAL, DICT_ASCII, DICT_UNICODE = range(5)


def refpack_decode(data: bytes) -> bytes:
    """Decode an EA RefPack stream (as wrapped by CompressionManager 'EAR\\0')."""
    if data[:4] == b"EAR\x00":
        raw_size = struct.unpack_from("<I", data, 4)[0]
        data = data[8:]
    else:
        raw_size = None
    pos = 0
    flags = (data[0] << 8) | data[1]
    pos = 2
    if flags & 0x8000:  # 4-byte sizes
        if flags & 0x0100:
            pos += 4
        size = int.from_bytes(data[pos:pos + 4], "big"); pos += 4
    else:
        if flags & 0x0100:
            pos += 3
        size = int.from_bytes(data[pos:pos + 3], "big"); pos += 3
    out = bytearray()
    while pos < len(data):
        b0 = data[pos]
        if b0 < 0x80:
            b1 = data[pos + 1]; pos += 2
            lit = b0 & 3
            out += data[pos:pos + lit]; pos += lit
            length = ((b0 & 0x1C) >> 2) + 3
            offset = ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xC0:
            b1, b2 = data[pos + 1], data[pos + 2]; pos += 3
            lit = b1 >> 6
            out += data[pos:pos + lit]; pos += lit
            length = (b0 & 0x3F) + 4
            offset = ((b1 & 0x3F) << 8) + b2 + 1
        elif b0 < 0xE0:
            b1, b2, b3 = data[pos + 1], data[pos + 2], data[pos + 3]; pos += 4
            lit = b0 & 3
            out += data[pos:pos + lit]; pos += lit
            length = ((b0 & 0x0C) << 6) + b3 + 5
            offset = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif b0 < 0xFC:
            pos += 1
            lit = ((b0 & 0x1F) << 2) + 4
            out += data[pos:pos + lit]; pos += lit
            continue
        else:
            pos += 1
            lit = b0 & 3
            out += data[pos:pos + lit]; pos += lit
            break
        start = len(out) - offset
        for i in range(length):
            out.append(out[start + i])
    if raw_size is not None and len(out) != raw_size:
        raise ValueError(f"refpack size mismatch {len(out)} != {raw_size}")
    if len(out) != size:
        raise ValueError(f"refpack inner size mismatch {len(out)} != {size}")
    return bytes(out)


class Reader:
    def __init__(self, data: bytes, names=None):
        self.d = data
        self.p = 0
        self.names = names or {}

    def eof(self):
        return self.p >= len(self.d)

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]; self.p += 4; return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]; self.p += 2; return v

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]; self.p += 4; return v

    def raw(self, n):
        v = self.d[self.p:self.p + n]; self.p += n; return v

    def ascii(self):
        n = self.u16(); return self.raw(n).decode("latin-1")

    def unicode(self):
        n = self.u16(); return self.raw(n * 2).decode("utf-16-le")

    def dict(self):
        n = self.u16()
        out = []
        for _ in range(n):
            kt = self.i32()
            key = self.names.get(kt >> 8, f"#{kt >> 8}")
            t = kt & 0xFF
            if t == DICT_BOOL: v = bool(self.u8())
            elif t == DICT_INT: v = self.i32()
            elif t == DICT_REAL: v = self.f32()
            elif t == DICT_ASCII: v = self.ascii()
            elif t == DICT_UNICODE: v = self.unicode()
            else: raise ValueError(f"bad dict type {t}")
            out.append((key, t, v))
        return out


def parse_file(data: bytes):
    """Return (names{id:name}, top-level chunk list[(name, version, payload)])."""
    if data[:4] == b"EAR\x00":
        data = refpack_decode(data)
    r = Reader(data)
    if r.raw(4) != b"CkMp":
        raise ValueError("not a CkMp data chunk file")
    names = {}
    for _ in range(r.i32()):
        n = r.u8(); nm = r.raw(n).decode("latin-1"); names[r.u32()] = nm
    r.names = names
    return names, split_chunks(data[r.p:], names)


def split_chunks(buf: bytes, names):
    out, p = [], 0
    while p + 10 <= len(buf):
        cid, ver, size = struct.unpack_from("<IHi", buf, p); p += 10
        out.append((names.get(cid, f"#{cid}"), ver, buf[p:p + size])); p += size
    if p != len(buf):
        raise ValueError(f"chunk overrun at {p}/{len(buf)}")
    return out


class Writer:
    """Equivalent of DataChunkOutput: chunks + symbol table assembled at end."""

    def __init__(self):
        self.ids = {}          # name -> id (allocation order = engine allocateID)
        self.body = bytearray()
        self.stack = []

    def id(self, name):
        if name not in self.ids:
            self.ids[name] = len(self.ids) + 1
        return self.ids[name]

    def open(self, name, ver):
        self.body += struct.pack("<IH", self.id(name), ver)
        self.stack.append(len(self.body))
        self.body += struct.pack("<i", 0xFFFF)

    def close(self):
        at = self.stack.pop()
        struct.pack_into("<i", self.body, at, len(self.body) - at - 4)

    def i32(self, v): self.body += struct.pack("<i", v)
    def u8(self, v): self.body += struct.pack("<B", v & 0xFF)
    def f32(self, v): self.body += struct.pack("<f", v)
    def raw(self, b): self.body += b

    def ascii(self, s):
        b = s.encode("latin-1"); self.body += struct.pack("<H", len(b)) + b

    def unicode(self, s):
        b = s.encode("utf-16-le"); self.body += struct.pack("<H", len(b) // 2) + b

    def dict(self, pairs):
        """pairs: list of (key, type, value)."""
        self.body += struct.pack("<H", len(pairs))
        for key, t, v in pairs:
            self.i32((self.id(key) << 8) | t)
            if t == DICT_BOOL: self.u8(1 if v else 0)
            elif t == DICT_INT: self.i32(v)
            elif t == DICT_REAL: self.f32(v)
            elif t == DICT_ASCII: self.ascii(v)
            elif t == DICT_UNICODE: self.unicode(v)
            else: raise ValueError(t)

    def finish(self) -> bytes:
        assert not self.stack, "unclosed chunk"
        head = bytearray(b"CkMp") + struct.pack("<i", len(self.ids))
        for name, i in self.ids.items():
            nb = name.encode("latin-1")
            head += struct.pack("<B", len(nb)) + nb + struct.pack("<I", i)
        return bytes(head + self.body)
