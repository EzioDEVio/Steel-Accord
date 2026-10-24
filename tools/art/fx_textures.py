#!/usr/bin/env python3
"""Steel Accord - procedural VFX textures (original, project-owned).

Generates every combat-effect sprite used by godot/scripts/fx.gd from seeded numpy noise; no external images,
scans or AI image generation. Re-running with the same seed reproduces the files bit for bit.

  python3 -I tools/art/fx_textures.py godot/assets/fx

Outputs (PNG, RGBA unless noted):
  smoke_atlas.png     512x512, 4x4 cells: 16 different smoke puffs, grey with baked top light (tinted per particle)
  fire_atlas.png      512x512, 4x4 flipbook: a fireball breaking up into flame tongues over 16 frames (additive)
  dust_atlas.png      512x512, 4x4 cells: soft, wispy dust puffs (tinted per particle)
  scorch.png          512x512: blast scorch decal (soot centre, radial streaks, ragged edge)
  ruin_ash.png        512x512: ground decal under a ruin (ash, soot, scattered grit, ragged rectangular edge)
  concrete_detail.png 256x256 tileable greyscale: concrete / plaster detail for ruin pieces (tinted per building)
  ring.png            256x256: noisy dust / shock ring
  flash.png           128x128: muzzle-flash star
  spark.png           32x32: hot spark dot
"""
import os
import sys

import numpy as np
from PIL import Image

RNG = np.random.default_rng(20261023)


def value_noise(n, freq, rng, tile=True):
    """Tileable smooth value noise in [0, 1] on an n x n grid with `freq` cells per side."""
    g = rng.random((freq, freq))
    x = np.linspace(0, freq, n, endpoint=False)
    i0 = np.floor(x).astype(int)
    f = x - i0
    f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % freq if tile else np.minimum(i0 + 1, freq - 1)
    a = g[np.ix_(i0, i0)]
    b = g[np.ix_(i0, i1)]
    c = g[np.ix_(i1, i0)]
    d = g[np.ix_(i1, i1)]
    fy = f[:, None]
    fx = f[None, :]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(n, base, octaves, rng, gain=0.5, tile=True):
    out = np.zeros((n, n))
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        out += value_noise(n, base * 2 ** o, rng, tile) * amp
        tot += amp
        amp *= gain
    return out / tot


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def grid(n):
    y, x = np.mgrid[0:n, 0:n].astype(float)
    return (x + 0.5) / n * 2 - 1, (y + 0.5) / n * 2 - 1


def save(img, path):
    Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)).save(path, optimize=True)
    print("wrote", path)


def puff(n, rng, wisp=False):
    """One smoke / dust puff: clustered blobs displaced by fbm, alpha with soft edge, baked top-left light."""
    x, y = grid(n)
    dens = np.zeros((n, n))
    for _ in range(rng.integers(4, 8)):
        cx, cy = rng.uniform(-0.25, 0.25, 2)
        r = rng.uniform(0.38, 0.62)
        dens = np.maximum(dens, 1 - ((x - cx) ** 2 + (y - cy) ** 2) / r ** 2)
    nz = fbm(n, 3, 5, rng, tile=False)
    dens = dens * 0.75 + (nz - 0.5) * (1.3 if wisp else 0.9)
    dens *= smoothstep(1.0, 0.7, np.sqrt(x * x + y * y))
    a = smoothstep(0.02, 0.55 if wisp else 0.4, dens)
    if wisp:
        a *= 0.75
    # baked light: the sun comes from the top; inner folds darker
    shade = 0.62 + 0.38 * smoothstep(0.6, -0.8, y + 0.3 * x) + 0.15 * (fbm(n, 6, 3, rng, tile=False) - 0.5)
    shade = shade * (0.8 + 0.2 * a)
    rgb = np.repeat(np.clip(shade, 0, 1)[..., None], 3, axis=2)
    return np.dstack([rgb, a])


def atlas(cells, n):
    k = int(np.sqrt(len(cells)))
    out = np.zeros((k * n, k * n, 4))
    for i, c in enumerate(cells):
        r, q = divmod(i, k)
        out[r * n:(r + 1) * n, q * n:(q + 1) * n] = c
    return out


def fire_frame(n, t, rng, seed_noise):
    """Fireball at normalised age t: a dense hot core that expands, cools and tears into flame tongues."""
    x, y = grid(n)
    r = np.sqrt(x * x + (y * 1.1) ** 2)
    nz = seed_noise[0] * (1 - t) + seed_noise[1] * t
    radius = 0.45 + 0.35 * t
    dens = 1 - r / radius + (nz - 0.5) * (0.6 + 1.4 * t)
    dens += (y < 0) * (-y) * 0.25 * t       # tongues lick upward as it ages
    dens = np.clip(dens, 0, 1)
    a = smoothstep(0.0, 0.35, dens) * (1.0 - 0.65 * t)
    heat = np.clip(dens * (1.25 - 0.9 * t), 0, 1)
    # black-body-ish ramp: deep red -> orange -> yellow -> white core
    rr = np.clip(0.55 + heat * 1.2, 0, 1)
    gg = np.clip(heat * 1.25 - 0.15, 0, 1)
    bb = np.clip(heat * 1.6 - 1.0, 0, 1)
    return np.dstack([rr, gg, bb, a])


def main(dst):
    os.makedirs(dst, exist_ok=True)
    # smoke and dust atlases
    save(atlas([puff(128, RNG) for _ in range(16)], 128), os.path.join(dst, "smoke_atlas.png"))
    save(atlas([puff(128, RNG, wisp=True) for _ in range(16)], 128), os.path.join(dst, "dust_atlas.png"))
    # fire flipbook: two noise fields blended over the 16 frames so the shape evolves continuously
    sn = (fbm(128, 4, 5, RNG, tile=False), fbm(128, 5, 5, RNG, tile=False))
    save(atlas([fire_frame(128, i / 15.0, RNG, sn) for i in range(16)], 128), os.path.join(dst, "fire_atlas.png"))
    # scorch decal
    n = 512
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    ang = np.arctan2(y, x)
    rays = RNG.random(64)
    ai = ((ang + np.pi) / (2 * np.pi) * 64).astype(int) % 64
    ray = rays[ai] * 0.6 + rays[(ai + 1) % 64] * 0.4
    edge = 0.6 + 0.14 * ray + 0.3 * (fbm(n, 5, 4, RNG) - 0.5)
    a = smoothstep(edge, edge * 0.35, r)
    soot = fbm(n, 8, 5, RNG)
    a = np.clip(a * (0.75 + 0.5 * soot), 0, 1) * 0.95
    col = 0.03 + 0.07 * soot + 0.05 * smoothstep(0.2, 0.8, r)
    save(np.dstack([col, col * 0.93, col * 0.85, a]), os.path.join(dst, "scorch.png"))
    # ruin ground decal (rectangular with ragged edge)
    bx = np.maximum(np.abs(x), np.abs(y))
    edge = 0.8 + 0.16 * (fbm(n, 5, 4, RNG) - 0.5) * 2
    a = smoothstep(edge, edge - 0.22, bx)
    ash = fbm(n, 10, 5, RNG)
    grit = (RNG.random((n, n)) > 0.985).astype(float)
    a = np.clip(a * (0.7 + 0.45 * ash) + grit * a * 0.4, 0, 1) * 0.92
    col = 0.06 + 0.16 * ash + 0.25 * grit
    save(np.dstack([col, col * 0.95, col * 0.9, a]), os.path.join(dst, "ruin_ash.png"))
    # concrete detail (tileable greyscale): mottling, aggregate speckle and a few hairline cracks
    n = 256
    mott = fbm(n, 4, 5, RNG)
    speck = value_noise(n, 64, RNG)
    crack = np.abs(fbm(n, 6, 4, RNG) - 0.5)
    crack = smoothstep(0.012, 0.0, crack)
    g = 0.72 + 0.22 * (mott - 0.5) + 0.12 * (speck - 0.5) - 0.16 * crack
    save(np.clip(g, 0, 1)[..., None].repeat(3, axis=2), os.path.join(dst, "concrete_detail.png"))
    # dust / shock ring
    n = 256
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    wob = fbm(n, 6, 4, RNG) - 0.5
    a = smoothstep(0.45, 0.82, r + wob * 0.15) * smoothstep(1.0, 0.86, r + wob * 0.1)
    save(np.dstack([np.ones_like(r), np.ones_like(r), np.ones_like(r), a * (0.6 + 0.4 * fbm(n, 12, 3, RNG))]), os.path.join(dst, "ring.png"))
    # muzzle flash star
    n = 128
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    ang = np.arctan2(y, x)
    petals = np.abs(np.cos(ang * 2.5)) ** 6 * 0.75 + np.abs(np.cos(ang * 4 + 0.4)) ** 10 * 0.4
    a = np.clip(smoothstep(0.35 + 0.6 * petals, 0.0, r) + smoothstep(0.35, 0.0, r), 0, 1)
    heat = smoothstep(0.6, 0.0, r)
    save(np.dstack([np.ones_like(r), 0.55 + 0.45 * heat, 0.15 + 0.8 * heat ** 2, a]), os.path.join(dst, "flash.png"))
    # spark
    n = 32
    x, y = grid(n)
    r = np.sqrt(x * x + y * y)
    a = smoothstep(1.0, 0.0, r) ** 2.2
    save(np.dstack([np.ones_like(r), 0.75 + 0.25 * a, 0.35 + 0.6 * a ** 2, a]), os.path.join(dst, "spark.png"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "godot/assets/fx")
