#!/usr/bin/env python3
"""Generate the original B1 building 'Field Depot': textures, W3D models (intact / damaged / rubble), icon.

A prefab forward vehicle depot: poured slab, arched corrugated hangar (door facing +X),
two container offices, a comms mast and team-colour roof bands. All procedural.
Outputs:
  content/dev/Art/Textures/pzdepot.tga, pzdepotd.tga
  content/dev/Art/W3D/PZFIELDDEPOT.W3D, PZFIELDDEPOTD.W3D (damaged), PZDEPOTRUBBLE.W3D
  build/previews/fielddepot_*.png ; icon pixels returned for the UI sheet (see gen_ui_sheet)
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga, w3d
from pzlib.meshbuild import Mesh
from pzlib.raster import render
from gen_kestrel import noise, export_model

ART = os.path.join(ROOT, "content", "dev", "Art")
PREV = os.path.join(ROOT, "build", "previews")
R = dict(slab=(0, 0, 128, 128), wall=(128, 0, 256, 128), roof=(0, 128, 128, 192), door=(128, 128, 192, 192),
         box=(192, 128, 256, 192), team=(0, 192, 128, 256), frame=(128, 192, 192, 256), lamp=(192, 192, 256, 256))


def atlas(burnt=False):
    S = 256; img = np.zeros((S, S, 3))

    def fill(rect, base, var, sc, seed):
        x0, y0, x1, y1 = rect
        n = noise(y1 - y0, x1 - x0, sc, seed=seed)[:, :, None] - 0.5
        img[y0:y1, x0:x1] = np.clip(np.array(base) * (1 + var * 2 * n), 0, 1)
    fill(R["slab"], (0.55, 0.55, 0.53), 0.12, 4, 101)
    fill(R["wall"], (0.44, 0.47, 0.45), 0.10, 3, 102)
    fill(R["roof"], (0.38, 0.41, 0.40), 0.10, 3, 103)
    fill(R["door"], (0.30, 0.31, 0.30), 0.10, 4, 104)
    fill(R["box"], (0.52, 0.47, 0.36), 0.12, 3, 105)
    fill(R["team"], (0.88, 0.88, 0.86), 0.05, 3, 106)
    fill(R["frame"], (0.18, 0.19, 0.20), 0.15, 5, 107)
    fill(R["lamp"], (1.0, 0.72, 0.20), 0.08, 2, 108)
    pil = Image.fromarray((img * 255).astype(np.uint8)); d = ImageDraw.Draw(pil)
    for k in range(0, 128, 32):                       # slab joints
        d.line([(k, 0), (k, 127)], fill=(105, 105, 100), width=1); d.line([(0, k), (127, k)], fill=(105, 105, 100), width=1)
    d.rectangle([4, 100, 60, 108], fill=(200, 170, 40))  # painted bay line
    for x in range(128, 256, 6):                      # corrugation
        d.line([(x, 0), (x, 127)], fill=(85, 90, 88), width=2)
    for y in range(128, 192, 5):                      # roof ribs
        d.line([(0, y), (127, y)], fill=(80, 86, 84), width=1)
    for y in range(132, 192, 6):                      # roller shutter slats
        d.line([(128, y), (191, y)], fill=(48, 50, 48), width=2)
    d.rectangle([196, 140, 222, 160], fill=(40, 60, 70)); d.rectangle([228, 140, 252, 160], fill=(40, 60, 70))  # windows
    d.rectangle([10, 214, 118, 232], outline=(150, 150, 146), width=3)  # team band marking (blank, no insignia)
    a = np.asarray(pil).astype(float) / 255
    if burnt:
        soot = noise(S, S, 5, seed=111)[:, :, None]
        a = a * (0.25 + 0.30 * soot)
        holes = noise(S, S, 11, seed=112)[:, :, None] > 0.66
        a = np.where(holes, a * 0.35, a)
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def side(r): return {"side": R[r], "top": R[r], "bottom": R["frame"]}


def hangar(m, x0, x1, half_w, wall_h, rise, seg=8):
    """Arched roof over x0..x1 (door at +X end): half-cylinder strips + gable fans."""
    pts = [(-half_w * math.cos(math.pi * k / seg), wall_h + rise * math.sin(math.pi * k / seg)) for k in range(seg + 1)]
    for k in range(seg):
        (ya, za), (yb, zb) = pts[k], pts[k + 1]
        m.quad((x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb), R["roof"])
    # walls
    m.quad((x0, -half_w, 0), (x1, -half_w, 0), (x1, -half_w, wall_h), (x0, -half_w, wall_h), R["wall"])
    m.quad((x1, half_w, 0), (x0, half_w, 0), (x0, half_w, wall_h), (x1, half_w, wall_h), R["wall"])
    # gables: rear wall + front with door
    for x, sgn in ((x1, 1), (x0, -1)):
        for k in range(seg):
            (ya, za), (yb, zb) = pts[k], pts[k + 1]
            p0, p1, p2 = (x, 0, wall_h), (x, ya, za), (x, yb, zb)
            if sgn > 0: p1, p2 = p2, p1
            m.tri(p0, p1, p2, R["wall"] if sgn < 0 else R["frame"])
        if sgn > 0:
            m.quad((x, -half_w, 0), (x, half_w, 0), (x, half_w, wall_h), (x, -half_w, wall_h), R["door"])
        else:
            m.quad((x, half_w, 0), (x, -half_w, 0), (x, -half_w, wall_h), (x, half_w, wall_h), R["wall"])


def build(state="intact"):
    body, team = Mesh(), Mesh()
    drop = 0.0 if state != "rubble" else 1.0
    body.box(-30, 30, -26, 26, 0, 1.2, side("slab"))                         # slab
    if state == "rubble":
        for i, (x, y, s) in enumerate(((-12, -6, 7), (4, 8, 6), (-2, -14, 5), (14, -4, 4), (-18, 12, 5))):
            body.box(x - s, x + s, y - s * 0.7, y + s * 0.7, 1.2, 1.2 + s * 0.5, side("wall" if i % 2 else "roof"),
                     taper_top=(s * 0.4, s * 0.3, s * 0.2, 0))
        body.box(-26, -16, 14, 22, 1.2, 4.0, side("box"))
        return body, None
    hangar(body, -22, 12, 13, 9.0, 10.0)
    body.box(12, 15, -13.6, -12.4, 1.2, 9.0, side("frame")); body.box(12, 15, 12.4, 13.6, 1.2, 9.0, side("frame"))  # door frame
    body.box(-28, -12, 15, 23, 1.2, 9.5, side("box"))                        # container office x2
    body.box(-10, 4, 16, 23, 1.2, 8.5, side("box"))
    body.box(16, 18, 16, 18, 1.2, 30, side("frame"))                         # mast
    body.box(15.2, 18.8, 15.2, 18.8, 30, 31.5, side("lamp"))
    body.box(22, 29, -22, -12, 1.2, 4.0, side("box"))                        # fuel cube
    # team colour: roof bands + container stripe
    for xb in (-18, 2):
        pts = [(-13.25 * math.cos(math.pi * k / 8), 9.25 + 10.25 * math.sin(math.pi * k / 8)) for k in range(9)]
        for k in range(8):
            (ya, za), (yb, zb) = pts[k], pts[k + 1]
            team.quad((xb, ya, za), (xb + 3, ya, za), (xb + 3, yb, zb), (xb, yb, zb), R["team"])
    team.box(-28.2, -11.8, 14.8, 15.0, 6.5, 8.0, side("team"))
    return body, team


def main():
    a, b = atlas(False), atlas(True)
    tga.save(os.path.join(ART, "Textures", "pzdepot.tga"), a)
    tga.save(os.path.join(ART, "Textures", "pzdepotd.tga"), b)
    bo, te = build("intact")
    export_model(os.path.join(ART, "W3D", "PZFIELDDEPOT.W3D"), "PZFIELDDEPOT", [("BODY", bo), ("HOUSECOLOR01", te)], "pzdepot.tga")
    bo, te = build("intact")
    export_model(os.path.join(ART, "W3D", "PZFIELDDEPOTD.W3D"), "PZFIELDDEPOTD", [("BODY", bo), ("HOUSECOLOR01", te)], "pzdepotd.tga")
    ru, _ = build("rubble")
    export_model(os.path.join(ART, "W3D", "PZDEPOTRUBBLE.W3D"), "PZDEPOTRUBBLE", [("BODY", ru)], "pzdepotd.tga")
    print("Field Depot tris:", len(bo.t) + len(te.t))
    team = (0.85, 0.30, 0.20)
    hero = render(os.path.join(ART, "W3D", "PZFIELDDEPOT.W3D"), a, 640, 480, yaw=-40, pitch=28, team=team,
                  bg=((22, 27, 33), (46, 56, 66)))
    dmg = render(os.path.join(ART, "W3D", "PZFIELDDEPOTD.W3D"), b, 320, 240, yaw=-40, pitch=28, team=team, bg=((22, 27, 33), (46, 56, 66)))
    rub = render(os.path.join(ART, "W3D", "PZDEPOTRUBBLE.W3D"), b, 320, 240, yaw=-40, pitch=28, bg=((22, 27, 33), (46, 56, 66)))
    Image.fromarray(hero).save(os.path.join(PREV, "fielddepot_hero.png"))
    Image.fromarray(np.concatenate([dmg, rub], 1)).save(os.path.join(PREV, "fielddepot_damaged_rubble.png"))
    icon = render(os.path.join(ART, "W3D", "PZFIELDDEPOT.W3D"), a, 240, 192, yaw=-40, pitch=30, team=(0.85, 0.55, 0.15),
                  bg=((16, 30, 44), (40, 70, 92)), zoom=1.2)
    np.save(os.path.join(ROOT, "build", "fielddepot_icon.npy"), icon)


if __name__ == "__main__":
    main()
