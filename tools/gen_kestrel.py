#!/usr/bin/env python3
"""Generate the original B1.1 'Kestrel' dev scout: textures, W3D models, UI icon, previews.

All output is procedurally authored by this script (no external source images).
Outputs (relative to repo root):
  content/dev/Art/Textures/pzkestrel.tga        256x256 atlas (body + housecolor panels)
  content/dev/Art/Textures/pzkestrelhk.tga      256x256 burnt-hulk variant
  content/dev/Art/W3D/PZKESTREL.W3D             HLOD + hierarchy + 2 meshes
  content/dev/Art/W3D/PZKESTRELHK.W3D           wreck model
  build/previews/*.png                          review renders (not shipped)
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga, w3d
from pzlib.meshbuild import Mesh
from pzlib.raster import render

ART = os.path.join(ROOT, "content", "dev", "Art")
PREV = os.path.join(ROOT, "build", "previews")
for d in ("Textures", "W3D"):
    os.makedirs(os.path.join(ART, d), exist_ok=True)
os.makedirs(PREV, exist_ok=True)
RNG = np.random.default_rng(20261021)

# ---------------------------------------------------------------- atlas regions (top-down px)
R = dict(
    hull=(0, 0, 128, 128),       # slate composite panels
    frame=(128, 0, 256, 128),     # dark chassis / underside
    cage=(0, 128, 128, 192),      # cabin glazing + roll cage
    tread=(128, 128, 192, 192),   # tyre tread
    hub=(192, 128, 256, 192),     # wheel hub disc
    gun=(128, 192, 192, 256),     # gunmetal
    team=(0, 192, 128, 256),      # light panel for HOUSECOLOR mesh (tinted in engine)
    lamp=(192, 192, 256, 256),    # amber sensor lens
)


def noise(h, w, scale, octaves=4, seed=0):
    """Periodic value noise (tileable)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = max(2, int(scale * 2 ** o))
        g = rng.random((n, n))
        ys = np.linspace(0, n, h, endpoint=False); xs = np.linspace(0, n, w, endpoint=False)
        y0 = ys.astype(int); x0 = xs.astype(int); fy = ys - y0; fx = xs - x0
        y1 = (y0 + 1) % n; x1 = (x0 + 1) % n
        sy = fy * fy * (3 - 2 * fy); sx = fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
        top = a + (b - a) * sx; bot = c + (d - c) * sx
        out += amp * (top + (bot - top) * sy[:, None]); tot += amp; amp *= 0.5
    return out / tot


def make_atlas(burnt=False):
    S = 256
    img = np.zeros((S, S, 3), float)

    def fill(rect, base, var=0.08, nscale=3, seed=1):
        x0, y0, x1, y1 = rect
        h, w = y1 - y0, x1 - x0
        n = noise(h, w, nscale, seed=seed)[:, :, None] - 0.5
        img[y0:y1, x0:x1] = np.clip(np.array(base)[None, None] * (1 + var * 2 * n), 0, 1)

    fill(R["hull"], (0.36, 0.42, 0.40), 0.18, 4, 2)
    fill(R["frame"], (0.16, 0.17, 0.17), 0.20, 6, 3)
    fill(R["cage"], (0.10, 0.20, 0.24), 0.25, 2, 4)
    fill(R["tread"], (0.09, 0.09, 0.09), 0.25, 8, 5)
    fill(R["hub"], (0.30, 0.31, 0.31), 0.10, 3, 6)
    fill(R["gun"], (0.22, 0.23, 0.25), 0.12, 5, 7)
    fill(R["team"], (0.86, 0.86, 0.84), 0.06, 3, 8)
    fill(R["lamp"], (1.0, 0.62, 0.10), 0.10, 2, 9)

    pil = Image.fromarray((img * 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)
    # hull: composite panel seams + fasteners
    for x in (0, 42, 86, 127):
        d.line([(x, 0), (x, 127)], fill=(52, 60, 58), width=2)
    for y in (0, 64, 127):
        d.line([(0, y), (127, y)], fill=(52, 60, 58), width=2)
    for x in range(6, 128, 14):
        for y in (5, 59, 69, 122):
            d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(128, 138, 132))
    d.rectangle([8, 90, 34, 100], fill=(205, 205, 196))  # stencil plate (blank, no insignia)
    # frame: tread plate
    for y in range(4, 128, 10):
        for x in range(132 + (y // 10) % 2 * 5, 256, 10):
            d.line([(x, y), (x + 4, y + 3)], fill=(70, 72, 72), width=1)
    # cage: tubes over glazing
    for x in (2, 40, 86, 125):
        d.rectangle([x, 128, x + 3, 191], fill=(40, 42, 44))
    d.rectangle([0, 128, 127, 131], fill=(40, 42, 44)); d.rectangle([0, 188, 127, 191], fill=(40, 42, 44))
    d.line([(10, 182), (32, 140)], fill=(90, 140, 150), width=2)  # glint
    # tread chevrons
    for y in range(128, 192, 8):
        d.line([(128, y), (160, y + 4), (192, y)], fill=(40, 40, 40), width=2)
    # hub: bolt circle
    cx, cy = 224, 160
    d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], outline=(40, 40, 40), width=3)
    d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(115, 115, 110))
    for k in range(6):
        a = 2 * math.pi * k / 6
        d.ellipse([cx + 19 * math.cos(a) - 2, cy + 19 * math.sin(a) - 2, cx + 19 * math.cos(a) + 2, cy + 19 * math.sin(a) + 2],
                  fill=(25, 25, 25))
    # gun: cooling slots
    for x in range(132, 192, 7):
        d.rectangle([x, 200, x + 2, 248], fill=(30, 30, 33))
    # team panel: chevron + numerals block (generic, original)
    d.polygon([(10, 238), (40, 206), (70, 238), (58, 238), (40, 220), (22, 238)], fill=(150, 150, 146))
    d.rectangle([84, 206, 118, 238], outline=(150, 150, 146), width=3)
    # lamp highlight
    d.ellipse([206, 206, 226, 226], fill=(255, 230, 170))

    a = np.asarray(pil).astype(float) / 255
    if burnt:
        soot = noise(S, S, 5, seed=11)[:, :, None]
        a = a * (0.18 + 0.25 * soot) + np.array([0.05, 0.03, 0.02]) * soot
        scorch = noise(S, S, 9, seed=12)[:, :, None] > 0.62
        a = np.where(scorch, a * 0.5 + np.array([0.20, 0.08, 0.02]) * 0.4, a)
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def build_kestrel():
    body, team = Mesh(), Mesh()
    parts = []

    def part(m, fn, *a, **k):
        tmp = Mesh(); getattr(tmp, fn)(*a, **k)
        parts.append((fn, tmp)); m.merge(tmp)
        return tmp

    side = lambda r: {"side": R[r], "top": R[r], "bottom": R["frame"]}
    # chassis tub
    part(body, "box", -10.0, 10.0, -4.6, 4.6, 1.8, 4.2, side("frame"))
    # upper hull with sloped glacis
    part(body, "box", -9.0, 7.0, -5.0, 5.0, 4.2, 6.3, side("hull"), taper_top=(2.0, 0.6, 0.5, 0))
    part(body, "box", 7.0, 11.2, -4.4, 4.4, 2.6, 5.0, side("hull"), taper_top=(2.2, 0, 0.4, 0))
    # open cabin with cage glazing (tapered)
    part(body, "box", -3.2, 3.0, -3.9, 3.9, 6.3, 9.0, side("cage"), taper_top=(1.4, 0.4, 0.5, 0))
    # rear stowage rack
    part(body, "box", -11.4, -9.0, -4.0, 4.0, 3.0, 6.0, side("frame"))
    # weapon pedestal + receiver + barrel + sensor
    part(body, "box", -6.0, -4.6, -0.7, 0.7, 6.3, 9.6, side("gun"))
    part(body, "box", -7.0, -2.0, -0.9, 0.9, 9.6, 10.9, side("gun"))
    part(body, "box", -2.0, 4.6, -0.28, 0.28, 10.0, 10.5, side("gun"))
    part(body, "box", -6.4, -5.2, 0.9, 1.7, 9.8, 10.7, side("lamp"))
    # wheels
    for wx in (-6.4, 6.6):
        for wy in (-5.5, 5.5):
            part(body, "wheel", wx, wy, 2.3, 2.3, 1.9, 12, R["tread"], R["hub"])
    # HOUSECOLOR panels: side armour skirts + rear plate (tinted by team colour)
    part(team, "box", -7.5, 5.5, 5.0, 5.35, 4.4, 6.0, side("team"))
    part(team, "box", -7.5, 5.5, -5.35, -5.0, 4.4, 6.0, side("team"))
    part(team, "box", -11.8, -11.4, -3.0, 3.0, 3.6, 5.6, side("team"))

    for fn, p in parts:
        c = tuple(sum(v[i] for v in p.v) / len(p.v) for i in range(3))
        assert p.check_outward(c) == 0, f"inward-facing faces in part {fn}"
    return body, team


def export_model(path, model, meshes, texture):
    pivots = [("ROOTTRANSFORM", -1, (0, 0, 0))] + [(n, 0, (0, 0, 0)) for n, _ in meshes]
    data = w3d.hierarchy(model, pivots)
    for name, m in meshes:
        data += w3d.mesh(name, model, m.v, m.n, m.uv, m.t, texture)
    data += w3d.hlod(model, model, [(i + 1, f"{model}.{n}") for i, (n, _) in enumerate(meshes)])
    w3d.walk(data)  # structural self-check (raises on bad sizes)
    open(path, "wb").write(data)
    return data


def main():
    atlas = make_atlas(False); burnt = make_atlas(True)
    tga.save(os.path.join(ART, "Textures", "pzkestrel.tga"), atlas)
    tga.save(os.path.join(ART, "Textures", "pzkestrelhk.tga"), burnt)
    body, team = build_kestrel()
    print("Kestrel: verts", len(body.v) + len(team.v), "tris", len(body.t) + len(team.t))
    export_model(os.path.join(ART, "W3D", "PZKESTREL.W3D"), "PZKESTREL",
                 [("BODY", body), ("HOUSECOLOR01", team)], "pzkestrel.tga")
    # wreck: same silhouette, flattened wheels/cabin, burnt texture, no housecolor
    hb, ht = build_kestrel()
    wreck = Mesh(); wreck.merge(hb); wreck.merge(ht)
    wreck.v = [(x, y, z * 0.82 if z > 6 else z) for x, y, z in wreck.v]
    export_model(os.path.join(ART, "W3D", "PZKESTRELHK.W3D"), "PZKESTRELHK", [("BODY", wreck)], "pzkestrelhk.tga")

    # ---- renders straight from exported W3D data (proves the files carry the geometry/UVs)
    team_rgb = (0.12, 0.45, 0.95)
    hero = render(os.path.join(ART, "W3D", "PZKESTREL.W3D"), atlas, 640, 480, yaw=-35, pitch=24,
                  team=team_rgb, bg=((22, 27, 33), (46, 56, 66)), zoom=1.0)
    Image.fromarray(hero).save(os.path.join(PREV, "kestrel_hero.png"))
    wreck_img = render(os.path.join(ART, "W3D", "PZKESTRELHK.W3D"), burnt, 320, 240, yaw=-35, pitch=24,
                       team=None, bg=((22, 27, 33), (46, 56, 66)), zoom=1.0)
    Image.fromarray(wreck_img).save(os.path.join(PREV, "kestrel_wreck.png"))
    views = [render(os.path.join(ART, "W3D", "PZKESTREL.W3D"), atlas, 320, 240, yaw=y, pitch=p, team=team_rgb,
                    bg=((22, 27, 33), (46, 56, 66))) for y, p in ((0, 0), (-90, 0), (0, 89), (-145, 20))]
    sheet = np.concatenate([np.concatenate(views[:2], 1), np.concatenate(views[2:], 1)], 0)
    Image.fromarray(sheet).save(os.path.join(PREV, "kestrel_orthos.png"))

    # ---- unit icon render (composited into the UI sheet by tools/gen_ui_sheet.py)
    icon = render(os.path.join(ART, "W3D", "PZKESTREL.W3D"), atlas, 240, 192, yaw=-40, pitch=28,
                  team=(0.85, 0.55, 0.15), bg=((16, 30, 44), (40, 70, 92)), zoom=1.25)
    np.save(os.path.join(ROOT, "build", "kestrel_icon.npy"), icon)
    Image.fromarray(atlas).save(os.path.join(PREV, "pzkestrel_atlas.png"))


if __name__ == "__main__":
    main()
