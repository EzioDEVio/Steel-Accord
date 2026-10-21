"""Flat-shaded low-poly mesh construction helpers (original tooling).

Frame: +X forward, +Y left, +Z up, units = game feet (W3D/Zero Hour convention).
UV rects are given in top-down atlas pixels (x0, y0, x1, y1) on a square atlas;
they are converted to W3D file V (bottom-up) on export.
"""
import math


class Mesh:
    def __init__(self, atlas=256):
        self.v, self.n, self.uv, self.t = [], [], [], []
        self.atlas = atlas

    def _uv(self, rect, s, t):
        x0, y0, x1, y1 = rect
        u = (x0 + (x1 - x0) * s) / self.atlas
        v_img = (y0 + (y1 - y0) * t) / self.atlas
        return (u, 1.0 - v_img)

    def quad(self, p0, p1, p2, p3, rect):
        """p0..p3 counter-clockwise seen from outside; rect maps p0=(0,1) p1=(1,1) p2=(1,0) p3=(0,0)."""
        e1 = [p1[i] - p0[i] for i in range(3)]; e2 = [p3[i] - p0[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        L = math.sqrt(sum(x * x for x in n)) or 1.0
        n = tuple(x / L for x in n)
        base = len(self.v)
        for p, (s, t) in zip((p0, p1, p2, p3), ((0, 1), (1, 1), (1, 0), (0, 0))):
            self.v.append(tuple(p)); self.n.append(n); self.uv.append(self._uv(rect, s, t))
        self.t += [(base, base + 1, base + 2), (base, base + 2, base + 3)]

    def tri(self, p0, p1, p2, rect):
        e1 = [p1[i] - p0[i] for i in range(3)]; e2 = [p2[i] - p0[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        L = math.sqrt(sum(x * x for x in n)) or 1.0
        n = tuple(x / L for x in n)
        base = len(self.v)
        for p, st in zip((p0, p1, p2), ((0, 1), (1, 1), (0.5, 0))):
            self.v.append(tuple(p)); self.n.append(n); self.uv.append(self._uv(rect, *st))
        self.t.append((base, base + 1, base + 2))

    def prism(self, bottom, top, rects):
        """bottom/top: 4 corners each, CCW seen from above. rects: dict side/top/bottom."""
        b, t = bottom, top
        self.quad(t[0], t[1], t[2], t[3], rects.get("top", rects["side"]))
        self.quad(b[3], b[2], b[1], b[0], rects.get("bottom", rects["side"]))
        for i in range(4):
            j = (i + 1) % 4
            self.quad(b[i], b[j], t[j], t[i], rects["side"])

    def box(self, x0, x1, y0, y1, z0, z1, rects, taper_top=(0, 0, 0, 0)):
        """Axis box; taper_top = (front_dx, rear_dx, side_dy, unused) shrinks the top face."""
        fdx, rdx, sdy, _ = taper_top
        bot = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
        top = [(x0 + rdx, y0 + sdy, z1), (x1 - fdx, y0 + sdy, z1), (x1 - fdx, y1 - sdy, z1), (x0 + rdx, y1 - sdy, z1)]
        self.prism(bot, top, rects)

    def wheel(self, cx, cy, cz, r, w, seg, tread_rect, hub_rect):
        """Cylinder with axis along Y."""
        y0, y1 = cy - w / 2, cy + w / 2
        ring = [(cx + r * math.cos(2 * math.pi * k / seg), cz + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
        for k in range(seg):
            (xa, za), (xb, zb) = ring[k], ring[(k + 1) % seg]
            # outward-facing tread quad (CCW from outside)
            self.quad((xa, y0, za), (xa, y1, za), (xb, y1, zb), (xb, y0, zb), tread_rect)
        hx0, hy0, hx1, hy1 = hub_rect
        cxr, cyr, rr = (hx0 + hx1) / 2, (hy0 + hy1) / 2, (hx1 - hx0) / 2
        for side, y in ((1, y1), (-1, y0)):
            for k in range(seg):
                (xa, za), (xb, zb) = ring[k], ring[(k + 1) % seg]
                pa, pb, pc = (cx, y, cz), (xa, y, za), (xb, y, zb)
                if side > 0:
                    pb, pc = pc, pb
                base = len(self.v)
                e1 = [pb[i] - pa[i] for i in range(3)]; e2 = [pc[i] - pa[i] for i in range(3)]
                n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                L = math.sqrt(sum(x * x for x in n)) or 1.0
                n = tuple(x / L for x in n)
                for p in (pa, pb, pc):
                    du, dv = (p[0] - cx) / r, (p[2] - cz) / r
                    self.v.append(p); self.n.append(n)
                    self.uv.append(((cxr + du * rr * 0.95) / self.atlas, 1.0 - (cyr - dv * rr * 0.95) / self.atlas))
                self.t.append((base, base + 1, base + 2))

    def check_outward(self, center):
        """Count faces whose normal points toward a reference interior point (should be ~0 for convex parts)."""
        bad = 0
        for a, b, c in self.t:
            p = [(self.v[a][i] + self.v[b][i] + self.v[c][i]) / 3 for i in range(3)]
            n = self.n[a]
            if sum((p[i] - center[i]) * n[i] for i in range(3)) < -1e-6:
                bad += 1
        return bad

    def merge(self, other):
        base = len(self.v)
        self.v += other.v; self.n += other.n; self.uv += other.uv
        self.t += [(a + base, b + base, c + base) for a, b, c in other.t]
