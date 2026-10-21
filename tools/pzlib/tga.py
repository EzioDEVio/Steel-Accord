"""Uncompressed Truevision TGA writer/reader (type 2, bottom-up origin).

The engine's terrain tile reader (WorldHeightMap::readTiles) and texture
loader both accept type-2 24/32-bit images; bottom-left origin is the
classic default (descriptor bit 5 clear).
"""
import struct
import numpy as np


def save(path, rgb_or_rgba: np.ndarray):
    a = np.asarray(rgb_or_rgba, dtype=np.uint8)
    h, w, c = a.shape
    assert c in (3, 4)
    desc = 8 if c == 4 else 0  # alpha bits; origin bottom-left
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 8 * c, desc)
    bgr = a[::-1, :, [2, 1, 0] + ([3] if c == 4 else [])]  # flip to bottom-up, RGB->BGR
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(np.ascontiguousarray(bgr).tobytes())


def load(path) -> np.ndarray:
    d = open(path, "rb").read()
    idlen, cmap, itype = d[0], d[1], d[2]
    w, h, bpp, desc = struct.unpack_from("<HHBB", d, 12)
    assert itype == 2 and cmap == 0, "only uncompressed truecolor"
    c = bpp // 8
    px = np.frombuffer(d, np.uint8, w * h * c, 18 + idlen).reshape(h, w, c)
    px = px[:, :, [2, 1, 0] + ([3] if c == 4 else [])]
    if not (desc & 0x20):
        px = px[::-1]
    return px.copy()
