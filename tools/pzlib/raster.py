"""Tiny software rasterizer that renders straight from a .W3D file.

Used for review previews and the UI icon. It reads the exported file back
(vertices, triangles, stage-0 texcoords, mesh names), so a preview is a check
that the shipped bytes carry the intended geometry and UV layout. It is NOT
an engine render; in-game appearance must still be verified in the game.
"""
import math, struct
import numpy as np
from .w3d import walk


def load_w3d_meshes(path):
    ch = walk(open(path, "rb").read())
    meshes, cur = [], None
    for d, t, s, sub, p in ch:
        if t == 0x000:
            cur = dict(name="", v=None, t=None, uv=None); meshes.append(cur)
        elif t == 0x01F and cur is not None:
            cur["name"] = p[8:24].split(b"\0")[0].decode()
        elif t == 0x002 and cur is not None:
            cur["v"] = np.frombuffer(p, "<f4").reshape(-1, 3).astype(float)
        elif t == 0x020 and cur is not None:
            cur["t"] = np.array([struct.unpack_from("<III", p, i * 32) for i in range(len(p) // 32)])
        elif t == 0x04A and cur is not None:
            cur["uv"] = np.frombuffer(p, "<f4").reshape(-1, 2).astype(float)
    return meshes


def render(path, tex, W, H, yaw=-35, pitch=25, team=None, bg=((20, 20, 20), (50, 50, 50)), zoom=1.0):
    meshes = load_w3d_meshes(path)
    allv = np.concatenate([m["v"] for m in meshes])
    ctr = (allv.min(0) + allv.max(0)) / 2
    rad = np.linalg.norm(allv - ctr, axis=1).max()
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    # camera looks at ctr from direction (yaw, pitch); build view basis (Z-up world)
    fwd = np.array([-cp * cy, -cp * sy, -sp])          # from camera toward target
    right = np.cross(fwd, [0, 0, 1.0])
    if np.linalg.norm(right) < 1e-6:
        right = np.array([0, -1.0, 0])
    right /= np.linalg.norm(right); up = np.cross(right, fwd)
    dist = rad * 3.2
    cam = ctr - fwd * dist
    f = min(W, H) * 1.45 * zoom
    light = np.array([0.45, -0.35, 0.82]); light /= np.linalg.norm(light)

    img = np.zeros((H, W, 3))
    gy = np.linspace(0, 1, H)[:, None, None]
    img[:] = np.array(bg[1]) / 255 * (1 - gy) + np.array(bg[0]) / 255 * gy
    zb = np.full((H, W), np.inf)
    th, tw = tex.shape[:2]
    texf = tex[:, :, :3].astype(float) / 255

    for m in meshes:
        V, T, UV = m["v"], m["t"], m["uv"]
        rel = V - cam
        xc, yc, zc = rel @ right, rel @ up, rel @ fwd
        sx = W / 2 + f * xc / zc; syy = H / 2 - f * yc / zc
        is_team = m["name"].upper().startswith("HOUSECOLOR")
        for a, b, c in T:
            P = np.array([[sx[a], syy[a]], [sx[b], syy[b]], [sx[c], syy[c]]])
            # face normal (world) for shading + backface cull (CCW-front as in W3D data)
            n = np.cross(V[b] - V[a], V[c] - V[a]); ln = np.linalg.norm(n)
            if ln == 0: continue
            n /= ln
            if np.dot(n, (V[a] - cam)) >= 0: continue
            x0, x1 = int(max(0, math.floor(P[:, 0].min()))), int(min(W - 1, math.ceil(P[:, 0].max())))
            y0, y1 = int(max(0, math.floor(P[:, 1].min()))), int(min(H - 1, math.ceil(P[:, 1].max())))
            if x0 > x1 or y0 > y1: continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx_, cy_) = P
            den = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
            if abs(den) < 1e-9: continue
            w0 = ((by - cy_) * (xs - cx_) + (cx_ - bx) * (ys - cy_)) / den
            w1 = ((cy_ - ay) * (xs - cx_) + (ax - cx_) * (ys - cy_)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any(): continue
            iz = w0 / zc[a] + w1 / zc[b] + w2 / zc[c]
            z = 1 / iz
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            vis = inside & (z < sub)
            if not vis.any(): continue
            u = (w0 * UV[a, 0] / zc[a] + w1 * UV[b, 0] / zc[b] + w2 * UV[c, 0] / zc[c]) * z
            v = (w0 * UV[a, 1] / zc[a] + w1 * UV[b, 1] / zc[b] + w2 * UV[c, 1] / zc[c]) * z
            px = np.clip((u * tw).astype(int), 0, tw - 1)
            py = np.clip(((1 - v) * th).astype(int), 0, th - 1)   # file V is bottom-up (loader does 1-V)
            col = texf[py, px]
            if is_team and team is not None:
                col = col * np.array(team)
            shade = 0.38 + 0.72 * max(0.0, float(np.dot(n, light)))
            col = np.clip(col * shade, 0, 1)
            sub[vis] = z[vis]
            img[y0:y1 + 1, x0:x1 + 1][vis] = col[vis]
    # simple silhouette edge for legibility
    mask = np.isfinite(zb)
    edge = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    img[edge] = img[edge] * 0.35
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)
