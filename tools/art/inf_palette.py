"""Steel Accord - sample a camouflage palette from a role's concept art (k-means on uniform pixels).

Run ISOLATED (the concept PNGs are untrusted input):
    python3 -I tools/art/inf_palette.py <role> [--k 6] [--json out.json]

Pixels are taken from rectangular regions given as fractions of the image (thighs/trousers and upper sleeve,
where the uniform fabric dominates), alpha > 200 only, then clustered. The six clusters are mapped to camo layer
names: darkest -> dark, brightest -> cream, most populous of the rest -> base, then the most green -> olive,
most red -> brown, remaining -> khaki. Only the resulting RGB values are used; no pixels reach the model.
"""
import sys, os, json
import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "godot", "assets", "us", "infantry")
# role -> list of (pose file suffix, (x0, y0, x1, y1) fractional box)
REGIONS = {
    "rifleman": [("stand", (0.25, 0.52, 0.75, 0.75)), ("walk", (0.25, 0.52, 0.75, 0.72))],
    "at4": [("aim_stand", (0.10, 0.55, 0.60, 0.80)), ("carry_stand", (0.15, 0.50, 0.65, 0.75)),
            ("carry_walk", (0.20, 0.55, 0.70, 0.75)), ("aim_stand", (0.20, 0.22, 0.60, 0.32))],
}
DEFAULT = [("stand", (0.25, 0.50, 0.75, 0.75)), ("walk", (0.25, 0.50, 0.75, 0.72))]


def kmeans(x, k, it=40, seed=7):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), k, replace=False)]
    for _ in range(it):
        lab = np.argmin(((x[:, None, :] - c[None]) ** 2).sum(-1), 1)
        c = np.array([x[lab == i].mean(0) if (lab == i).any() else c[i] for i in range(k)])
    return c, np.bincount(lab, minlength=k)


def sample(role, k=6, regions=None):
    px = []
    for pose, (x0, y0, x1, y1) in (regions or REGIONS.get(role, DEFAULT)):
        p = os.path.join(ROOT, role, f"{role}_{pose}.png")
        im = np.asarray(Image.open(p).convert("RGBA")).astype(float)
        h, w = im.shape[:2]
        sub = im[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].reshape(-1, 4)
        px.append(sub[sub[:, 3] > 200][:, :3])
    x = np.concatenate(px)
    c, n = kmeans(x, k)
    lum = c @ np.array([0.299, 0.587, 0.114])
    idx = list(range(k))
    dark = min(idx, key=lambda i: lum[i]); idx.remove(dark)
    cream = max(idx, key=lambda i: lum[i]); idx.remove(cream)
    base = max(idx, key=lambda i: n[i]); idx.remove(base)
    olive = max(idx, key=lambda i: c[i][1] - c[i][0]); idx.remove(olive)
    brown = max(idx, key=lambda i: c[i][0] - c[i][1]); idx.remove(brown)
    khaki = idx[0]
    out = {nm: tuple(int(round(v)) for v in c[i]) for nm, i in
           (("base", base), ("khaki", khaki), ("olive", olive), ("brown", brown), ("dark", dark), ("cream", cream))}
    return out, {"pixels": int(len(x)), "counts": {nm: int(n[i]) for nm, i in (("base", base), ("khaki", khaki),
                 ("olive", olive), ("brown", brown), ("dark", dark), ("cream", cream))}}


if __name__ == "__main__":
    a = sys.argv[1:]
    role = a[0]
    k = int(a[a.index("--k") + 1]) if "--k" in a else 6
    pal, info = sample(role, k)
    print(json.dumps({"role": role, "palette": pal, **info}))
    if "--json" in a:
        with open(a[a.index("--json") + 1], "w") as fh:
            json.dump({"role": role, "palette": pal, **info}, fh, indent=1)


# ------------------------------------------------------------------ albedo calibration
# The approved rifleman palette (hand-tuned albedo, see inf_kit.RIFLEMAN_PALETTE) versus what this sampler reads from
# the rifleman concept gives a per-luminance-rank colour gain (the concept is shaded and darker than the albedo).
# Other roles: albedo = sample * gain, matched by luminance rank, so every role is lit/calibrated the same way.
APPROVED = {"base": (158, 138, 104), "khaki": (126, 108, 80), "olive": (98, 97, 62), "brown": (108, 82, 58),
            "dark": (50, 41, 29), "cream": (198, 182, 148)}


def _rank(p):
    return sorted(p, key=lambda n: 0.299 * p[n][0] + 0.587 * p[n][1] + 0.114 * p[n][2])


def albedo(role, k=6):
    ref, _ = sample("rifleman", k)
    smp, _ = sample(role, k)
    out = {}
    for an, rn, sn in zip(_rank(APPROVED), _rank(ref), _rank(smp)):
        out[an] = tuple(int(max(0, min(255, round(smp[sn][c] * APPROVED[an][c] / max(ref[rn][c], 1))))) for c in range(3))
    return out


if __name__ == "__main__" and "--albedo" in sys.argv:
    print(json.dumps({"role": sys.argv[1], "albedo": albedo(sys.argv[1])}))
