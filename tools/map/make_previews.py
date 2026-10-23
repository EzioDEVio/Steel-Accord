# Steel Accord - map preview images for the Skirmish screen (maps/<id>/preview.png). Run: python3 -I tools/map/make_previews.py
import json, os, numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "godot", "maps")


def zagros():
    d = json.load(open(os.path.join(ROOT, "zagros_basin/map.json")))
    n = 601
    h = np.frombuffer(open(os.path.join(ROOT, "zagros_basin/height.r16"), "rb").read(), dtype="<u2").reshape(n, n).astype(np.float32) / 65535 * d["height_scale"]
    sp = np.array(Image.open(os.path.join(ROOT, "zagros_basin/splat.png")).convert("RGBA").resize((n, n))).astype(np.float32) / 255
    gy, gx = np.gradient(h, 2.0)
    nrm = np.dstack([-gx, np.ones_like(h), -gy]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    L = np.array([-0.5, 0.75, -0.45]); L /= np.linalg.norm(L)
    shade = np.clip((nrm * L).sum(2) * 1.25, 0.35, 1.15)
    c = np.zeros((n, n, 3)) + np.array([0.62, 0.53, 0.39])
    mix = lambda c, col, w: c * (1 - w[..., None]) + np.array(col) * w[..., None]
    c = mix(c, [0.55, 0.52, 0.46], sp[..., 1]); c = mix(c, [0.40, 0.42, 0.25], sp[..., 2]); c = mix(c, [0.72, 0.68, 0.60], sp[..., 3])
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    c = mix(c, [0.45, 0.40, 0.35], np.clip(sp[..., 0] + slope / 40, 0, 1))
    img = Image.fromarray((np.clip(c * shade[..., None], 0, 1) * 255).astype(np.uint8)).resize((300, 300), Image.LANCZOS)
    dr = ImageDraw.Draw(img)
    px = lambda p: ((p[0] + 600) / 1200 * 300, (p[1] + 600) / 1200 * 300)
    for r in d["roads"]: dr.line([px(p) for p in r["points"]], fill=(70, 62, 50), width=2)
    for s in d["supply_piles"]:
        x, y = px(s["pos"]); dr.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(240, 200, 70), outline=(0, 0, 0))
    for o in d["oil_derricks"]:
        x, y = px(o["pos"]); dr.polygon([(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)], fill=(170, 110, 240), outline=(0, 0, 0))
    for st, col in zip(d["starts"], [(60, 110, 230), (220, 60, 50)]):
        x, y = px(st["pos"]); dr.ellipse([x - 7, y - 7, x + 7, y + 7], fill=col, outline=(255, 255, 255), width=2)
    img.save(os.path.join(ROOT, "zagros_basin/preview.png"))


def proving_ground():
    pg = Image.new("RGB", (300, 300), (58, 72, 38)); dr = ImageDraw.Draw(pg)
    p2 = lambda x, z: ((x + 300) / 600 * 300, (z + 300) / 600 * 300)
    for (x, z) in [(-124, 0), (116, -16), (-20, -110), (28, 104), (-220, 140), (210, -150), (-200, -200), (-90, 230)]:
        a, b = p2(x, z); dr.ellipse([a - 8, b - 8, a + 8, b + 8], fill=(95, 90, 82))
    for (x, z) in [(-75, 195), (80, 250), (75, -195), (-80, -250), (0, 0)]:
        a, b = p2(x, z); dr.rectangle([a - 3, b - 3, a + 3, b + 3], fill=(240, 200, 70), outline=(0, 0, 0))
    for (x, z), col in [((0, 225), (60, 110, 230)), ((0, -225), (220, 60, 50))]:
        a, b = p2(x, z); dr.ellipse([a - 7, b - 7, a + 7, b + 7], fill=col, outline=(255, 255, 255), width=2)
    os.makedirs(os.path.join(ROOT, "proving_ground"), exist_ok=True)
    pg.save(os.path.join(ROOT, "proving_ground/preview.png"))


if __name__ == "__main__":
    zagros(); proving_ground(); print("previews written")
